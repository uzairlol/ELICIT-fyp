# vllm_client.py

"""
OpenAI-compatible client for a local vLLM server.

Replaces the Ollama backend: unlike ``OllamaClient`` it sends only the
standard OpenAI ``/v1/chat/completions`` parameters (no Ollama ``options`` /
``keep_alive`` extra_body), never unloads the model between rounds, and trusts
vLLM continuous batching to keep the GPU saturated.

Launch a compatible server with ``scripts/serve_vllm.gguf.sh`` or
``scripts/serve_vllm.gptq_tp2.sh`` and keep ``LLM_BASE_URL`` pointing at the
``/v1`` endpoint.
"""

import logging
import threading

from openai import OpenAI, OpenAIError

from core import parameters
from llm.chat_template import render_chat
from llm.retry import run_with_retries

logger = logging.getLogger(__name__)


def _use_fixed_template() -> bool:
    """Whether ELICIT renders the chat template itself for cross-model parity."""
    from llm.chat_template import fixed_template_mode

    return fixed_template_mode()


class VLLMClient:
    def __init__(self, model_name, base_url=parameters.LLM_BASE_URL):
        """
        Initialize the VLLMClient to use a local vLLM OpenAI-compatible server.

        Parameters:
        - model_name (str): The served model name (--served-model-name in vLLM).
        - base_url (str): The vLLM OpenAI-compatible endpoint (default /v1).
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key="unused",
            timeout=float(parameters.LLM_REQUEST_TIMEOUT_SECONDS),
        )
        self.model_name = model_name
        self.deployment_name = model_name
        self.total_cost = 0.0

        self.max_concurrency = max(
            1,
            int(getattr(parameters, "VLLM_MAX_CONCURRENCY", 1)),
        )
        general_concurrency = max(1, int(getattr(parameters, "LLM_MAX_CONCURRENCY", 1)))
        tom_concurrency = max(
            1, int(getattr(parameters, "TOM_MAX_CONCURRENCY", general_concurrency))
        )
        required = max(self.max_concurrency, general_concurrency, tom_concurrency)
        if required > self.max_concurrency:
            logger.warning(
                "VLLM_MAX_CONCURRENCY=%s is below LLM_MAX_CONCURRENCY=%s / "
                "TOM_MAX_CONCURRENCY=%s; raising client semaphore to %s. "
                "Keep the vLLM --max-num-seqs at least this high.",
                self.max_concurrency,
                general_concurrency,
                tom_concurrency,
                required,
            )
            self.max_concurrency = required

        logger.info(
            "vLLM server: model=%s, base_url=%s, timeout=%.0fs, "
            "LLM_MAX_CONCURRENCY=%s, TOM_MAX_CONCURRENCY=%s, "
            "client_max_inflight=%s (must not exceed server --max-num-seqs).",
            self.model_name,
            base_url,
            float(parameters.LLM_REQUEST_TIMEOUT_SECONDS),
            general_concurrency,
            tom_concurrency,
            self.max_concurrency,
        )

        self._request_semaphore = threading.BoundedSemaphore(self.max_concurrency)

    def send_request(
        self,
        model_name,
        prompt,
        max_tokens=768,
        temperature=0.7,
        top_p=1.0,
        response_format=None,
        max_attempts=None,
        request_label="vLLM request",
        **kwargs,
    ):
        """
        Send a prompt through the shared bounded retry helper.
        """
        attempts = (
            int(max_attempts)
            if max_attempts is not None
            else int(getattr(parameters, "LLM_MAX_ATTEMPTS", 5))
        )
        return run_with_retries(
            lambda _attempt: self._send_request_once(
                model_name=model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                response_format=response_format,
                **kwargs,
            ),
            max_attempts=attempts,
            label=request_label,
            logger=logger,
        )

    def _send_request_once(
        self,
        model_name,
        prompt,
        max_tokens=768,
        temperature=0.7,
        top_p=1.0,
        response_format=None,
        **kwargs,
    ):
        """Perform exactly one transport attempt."""
        with self._request_semaphore:
            try:
                create_args = {
                    "model": self.model_name,
                    # max_tokens is deliberately omitted: vLLM then derives the
                    # budget as min(max_model_len - prompt_len, ...) via
                    # get_max_tokens(), so reasoning is never truncated.
                    "temperature": temperature,
                    "top_p": top_p,
                    "min_p": float(getattr(parameters, "LLM_MIN_P", 0.0)),
                    "repetition_penalty": float(getattr(parameters, "LLM_REPETITION_PENALTY", 1.0)),
                    "n": 1,
                    # Seed the sampler explicitly. Historically this was
                    # `parameters.SEED`, which tied sampling to the Python RNG
                    # and made "nine seeds" indistinguishable from one draw.
                    "seed": int(getattr(parameters, "LLM_SEED", parameters.SEED)),
                }

                if _use_fixed_template():
                    # Cross-model prompt parity: ELICIT renders the chat string
                    # and posts raw text, so the prompt is byte-identical across
                    # model families instead of inheriting each family's own
                    # default template.
                    rendered = render_chat(prompt)
                    create_args["prompt"] = rendered
                    response = self.client.completions.create(**create_args)
                    generated_text = (response.choices[0].text or "").strip()
                    logger.debug(
                        "Fixed-template raw completion (%d chars) for %s",
                        len(rendered),
                        self.model_name,
                    )
                    return generated_text

                create_args["messages"] = [{"role": "user", "content": prompt}]
                # vLLM supports guided JSON via the standard response_format.
                if response_format:
                    create_args["response_format"] = response_format
                create_args.update(kwargs)

                response = self.client.chat.completions.create(**create_args)

                message = response.choices[0].message
                generated_text = (getattr(message, "content", None) or "").strip()
                if not generated_text:
                    reasoning_text = getattr(message, "reasoning_content", None) or ""
                    generated_text = reasoning_text.strip()

                logger.info(
                    "\n%s\n[RESPONSE ← %s]\n%s\n%s",
                    "═" * 72,
                    self.model_name,
                    generated_text,
                    "═" * 72,
                )
                return generated_text

            except OpenAIError as e:
                raise Exception(f"vLLM Error: {e!s}") from e

    def soft_reset_model(self):
        """
        No-op: vLLM keeps the model resident between rounds.

        Unloading/reloading weights every round would re-read ~9 GB from disk
        30 times per run, so this backend intentionally does nothing.
        """
        logger.debug(
            "vLLM soft-reset skipped: model '%s' stays loaded on the GPU.",
            self.model_name,
        )
        return {
            "unloaded": [],
            "still_loaded": [self.model_name],
            "killed_runners": [],
        }

    def get_total_cost(self):
        """Return the total cost (always 0.0 for local runs)."""
        return 0.0

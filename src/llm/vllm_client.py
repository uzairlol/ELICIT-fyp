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
from llm.retry import run_with_retries

logger = logging.getLogger(__name__)


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
                messages = [{"role": "user", "content": prompt}]
                create_args = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": int(max_tokens),
                    "temperature": temperature,
                    "top_p": top_p,
                    "n": 1,
                    "seed": int(getattr(parameters, "SEED", 0)),
                }
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

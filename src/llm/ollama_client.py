#ollama_client.py

import logging
import os
import threading
import json
import urllib.request
from openai import OpenAI, OpenAIError
from core import parameters
from llm.retry import run_with_retries

logger = logging.getLogger(__name__)


def _is_reasoning_model(model_name):
    model_name = str(model_name or "").lower()
    return "deepseek-r1" in model_name or "reasoning" in model_name


def _ollama_runtime_options(max_tokens):
    """Build Ollama option dict shared across HTTP and OpenAI-compatible calls."""
    return {
        "num_gpu": int(getattr(parameters, 'OLLAMA_NUM_GPU', 1)),
        "num_ctx": int(getattr(parameters, 'OLLAMA_NUM_CTX', 4096)),
        "num_predict": int(max_tokens),
        "seed": int(getattr(parameters, 'SEED', 0)),
    }


class OllamaClient:
    def __init__(self, model_name, base_url="http://localhost:11434/v1"):
        """
        Initialize the OllamaClient to use a local Ollama instance.

        Parameters:
        - model_name (str): The name of the model in Ollama (e.g., "llama3.1", "mistral").
        - base_url (str): The local endpoint for Ollama's OpenAI-compatible API.
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama",
            timeout=float(parameters.OLLAMA_REQUEST_TIMEOUT_SECONDS)
        )
        self.model_name = model_name
        self.deployment_name = model_name
        self.total_cost = 0.0

        parallel = max(1, int(getattr(parameters, 'OLLAMA_NUM_PARALLEL', 1)))
        os.environ.setdefault("OLLAMA_NUM_PARALLEL", str(parallel))
        logger.info(
            f"Ollama GPU options: num_gpu={getattr(parameters, 'OLLAMA_NUM_GPU', 1)}, "
            f"num_ctx={getattr(parameters, 'OLLAMA_NUM_CTX', 4096)}, "
            f"OLLAMA_NUM_PARALLEL={parallel} "
            f"(restart the Ollama server if it was already running)"
        )

        self._request_semaphore = threading.BoundedSemaphore(parallel)

    def send_request(
        self,
        model_name,
        prompt,
        max_tokens=768,
        temperature=0.7,
        top_p=1.0,
        response_format=None,
        max_attempts=None,
        request_label="Ollama request",
        **kwargs,
    ):
        """
        Send a prompt through the shared bounded retry helper.
        """
        attempts = (
            int(max_attempts)
            if max_attempts is not None
            else int(getattr(parameters, 'LLM_MAX_ATTEMPTS', 5))
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
                if _is_reasoning_model(self.model_name):
                    return self._send_request_via_http(
                        prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        require_json=bool(response_format),
                    )

                messages = [{"role": "user", "content": prompt}]
                create_args = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "n": 1,
                    "seed": parameters.SEED,
                    "extra_body": {
                        "options": _ollama_runtime_options(max_tokens),
                    },
                }
                if response_format and not _is_reasoning_model(self.model_name):
                    create_args["response_format"] = response_format

                create_args.update(kwargs)

                response = self.client.chat.completions.create(**create_args)

                message = response.choices[0].message
                generated_text = (getattr(message, "content", None) or "").strip()

                if not generated_text:
                    reasoning_text = getattr(message, "reasoning_content", None) or ""
                    generated_text = reasoning_text.strip()

                return generated_text

            except OpenAIError as e:
                raise Exception(f"Ollama Error: {str(e)}")

    def _send_request_via_http(self, prompt, max_tokens=768, temperature=0.7, top_p=1.0, require_json=False):
        """
        Use Ollama's native HTTP API for reasoning models.
        """
        options = _ollama_runtime_options(max_tokens)
        options.update({
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": min(max_tokens, 768),
        })
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": options,
        }
        response_data = self._post_native_json("/api/chat", payload)

        message = response_data.get("message", {}) if isinstance(response_data, dict) else {}
        content = (message.get("content") or response_data.get("response") or "").strip() if isinstance(response_data, dict) else ""
        reasoning = (
            message.get("thinking")
            or message.get("reasoning")
            or message.get("reasoning_content")
            or response_data.get("thinking")
            or response_data.get("reasoning")
            or response_data.get("reasoning_content")
            or ""
        ) if isinstance(response_data, dict) else ""

        reasoning = str(reasoning).strip()
        content = str(content).strip()

        if reasoning and content:
            return f"<think>\n{reasoning}\n</think>\n{content}"
        if reasoning:
            return f"<think>\n{reasoning}\n</think>"
        return content

    def _post_native_json(self, endpoint, payload, timeout=None):
        """POST JSON to an Ollama native API endpoint."""
        base_url = parameters.LLM_BASE_URL.rstrip("/").removesuffix("/v1")
        request = urllib.request.Request(
            base_url + endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        request_timeout = (
            float(timeout)
            if timeout is not None
            else float(parameters.OLLAMA_REQUEST_TIMEOUT_SECONDS)
        )
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body.strip() else {}

    def soft_reset_model(self):
        """
        Unload the active model via Ollama's API.

        Ollama does not expose an API that restarts ``ollama serve``. Sending
        ``keep_alive: 0`` safely releases the model; the next request reloads it.
        """
        label = f"Ollama soft reset ({self.model_name})"

        def unload_once(_attempt):
            with self._request_semaphore:
                return self._post_native_json(
                    "/api/generate",
                    {"model": self.model_name, "keep_alive": 0},
                    timeout=getattr(
                        parameters,
                        'OLLAMA_SOFT_RESET_TIMEOUT_SECONDS',
                        30.0,
                    ),
                )

        run_with_retries(
            unload_once,
            max_attempts=2,
            label=label,
            logger=logger,
            base_delay_seconds=1.0,
        )
        logger.info(
            "Ollama model %s unloaded; the next request will reload it.",
            self.model_name,
        )

    def get_total_cost(self):
        """Return the total cost (always 0.0 for local runs)."""
        return 0.0

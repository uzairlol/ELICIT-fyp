#ollama_client.py

import logging
import os
import subprocess
import threading
import time
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


def _ollama_keep_alive():
    return getattr(parameters, 'OLLAMA_KEEP_ALIVE', '2m')


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
        general_concurrency = max(1, int(getattr(parameters, 'LLM_MAX_CONCURRENCY', 1)))
        tom_concurrency = max(1, int(getattr(parameters, 'TOM_MAX_CONCURRENCY', general_concurrency)))
        required_parallel = max(parallel, general_concurrency, tom_concurrency)
        if required_parallel > parallel:
            logger.warning(
                "OLLAMA_NUM_PARALLEL=%s is below max concurrency "
                "(LLM=%s, ToM=%s); raising client semaphore to %s. "
                "Restart `ollama serve` with OLLAMA_NUM_PARALLEL=%s for full effect.",
                parallel,
                general_concurrency,
                tom_concurrency,
                required_parallel,
                required_parallel,
            )
            parallel = required_parallel
        os.environ.setdefault("OLLAMA_NUM_PARALLEL", str(parallel))
        logger.info(
            f"Ollama GPU options: num_gpu={getattr(parameters, 'OLLAMA_NUM_GPU', 1)}, "
            f"num_ctx={getattr(parameters, 'OLLAMA_NUM_CTX', 4096)}, "
            f"OLLAMA_NUM_PARALLEL={parallel}, "
            f"OLLAMA_KEEP_ALIVE={_ollama_keep_alive()}, "
            f"LLM_MAX_CONCURRENCY={general_concurrency}, "
            f"TOM_MAX_CONCURRENCY={tom_concurrency} "
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
        max_tokens=-1,
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
                        # Prevents llama-server from staying loaded forever between calls.
                        "keep_alive": _ollama_keep_alive(),
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

                logger.info(
                    "\n%s\n[RESPONSE ← %s]\n%s\n%s",
                    "═" * 72, self.model_name, generated_text, "═" * 72,
                )
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
            "keep_alive": _ollama_keep_alive(),
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
            result = f"<think>\n{reasoning}\n</think>\n{content}"
        elif reasoning:
            result = f"<think>\n{reasoning}\n</think>"
        else:
            result = content

        logger.info(
            "\n%s\n[RESPONSE ← %s]\n%s\n%s",
            "═" * 72, self.model_name, result, "═" * 72,
        )
        return result

    def _native_base_url(self):
        return parameters.LLM_BASE_URL.rstrip("/").removesuffix("/v1")

    def _post_native_json(self, endpoint, payload, timeout=None):
        """POST JSON to an Ollama native API endpoint."""
        request = urllib.request.Request(
            self._native_base_url() + endpoint,
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

    def _list_loaded_models(self):
        """Return model names currently held by Ollama runners (/api/ps)."""
        request = urllib.request.Request(
            self._native_base_url() + "/api/ps",
            method="GET",
        )
        timeout = float(getattr(parameters, 'OLLAMA_SOFT_RESET_TIMEOUT_SECONDS', 30.0))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
        names = set()
        for entry in payload.get("models", []) or []:
            name = entry.get("name") or entry.get("model")
            if name:
                names.add(str(name))
        return names

    @staticmethod
    def _kill_leftover_runners():
        """
        On Windows, keep_alive=0 sometimes leaves llama-server.exe resident.
        Kill only the runner processes — never ollama.exe / the app itself.
        """
        if os.name != "nt":
            return []
        runner_names = (
            "llama-server.exe",
            "ollama_llama_server.exe",
        )
        killed = []
        for name in runner_names:
            try:
                completed = subprocess.run(
                    ["taskkill", "/F", "/IM", name, "/T"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                output = (completed.stdout or "") + (completed.stderr or "")
                if completed.returncode == 0 or "SUCCESS" in output.upper():
                    killed.append(name)
                    logger.info("Force-killed leftover runner process: %s", name)
                elif "not found" not in output.lower() and completed.returncode not in (128, 1):
                    logger.debug("taskkill %s: %s", name, output.strip())
            except Exception as exc:
                logger.warning("Failed to taskkill %s: %s", name, exc)
        return killed

    def soft_reset_model(self):
        """
        Unload loaded models via Ollama's API and release llama-server RAM.

        Sends keep_alive: 0, waits until /api/ps is empty, then on Windows
        force-kills any leftover llama-server.exe runner if still present.
        """
        label = f"Ollama soft reset ({self.model_name})"
        timeout = float(getattr(parameters, 'OLLAMA_SOFT_RESET_TIMEOUT_SECONDS', 30.0))

        def unload_model(model_name):
            with self._request_semaphore:
                return self._post_native_json(
                    "/api/generate",
                    {"model": model_name, "keep_alive": 0},
                    timeout=timeout,
                )

        def unload_once(_attempt):
            models = {self.model_name}
            try:
                models |= self._list_loaded_models()
            except Exception as exc:
                logger.debug("Could not list Ollama /api/ps models: %s", exc)

            for model_name in sorted(models):
                unload_model(model_name)

            # Wait briefly for runners to exit after unload.
            deadline = time.monotonic() + min(10.0, timeout)
            remaining = models
            while time.monotonic() < deadline:
                try:
                    remaining = self._list_loaded_models()
                except Exception:
                    remaining = set()
                    break
                if not remaining:
                    break
                time.sleep(0.5)

            killed = []
            if getattr(parameters, 'OLLAMA_FORCE_KILL_RUNNER', True):
                if remaining:
                    logger.warning(
                        "Models still listed in /api/ps after unload: %s. "
                        "Force-killing llama-server runners.",
                        sorted(remaining),
                    )
                killed = self._kill_leftover_runners()

            return {
                "unloaded": sorted(models),
                "still_loaded": sorted(remaining),
                "killed_runners": killed,
            }

        result = run_with_retries(
            unload_once,
            max_attempts=2,
            label=label,
            logger=logger,
            base_delay_seconds=1.0,
        )
        logger.info(
            "Ollama soft reset complete; unloaded=%s still_loaded=%s killed_runners=%s.",
            result.get("unloaded", [self.model_name]),
            result.get("still_loaded", []),
            result.get("killed_runners", []),
        )

    def get_total_cost(self):
        """Return the total cost (always 0.0 for local runs)."""
        return 0.0

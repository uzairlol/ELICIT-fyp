# llm package — LLM client / API communication
import logging

from .ollama_client import OllamaClient
from .vllm_client import VLLMClient

logger = logging.getLogger(__name__)


def create_llm_client():
    """Build the OpenAI-compatible client for the active backend."""
    from core import parameters

    backend = str(getattr(parameters, "LLM_BACKEND", "vllm")).strip().lower()
    model_name = parameters.LLM_MODEL
    base_url = parameters.LLM_BASE_URL
    if backend == "ollama":
        logger.info("LLM backend: Ollama (model=%s, base_url=%s).", model_name, base_url)
        return OllamaClient(model_name=model_name, base_url=base_url)
    logger.info("LLM backend: vLLM (model=%s, base_url=%s).", model_name, base_url)
    return VLLMClient(model_name=model_name, base_url=base_url)


__all__ = ["OllamaClient", "VLLMClient", "create_llm_client"]

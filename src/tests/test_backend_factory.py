"""Tests for the LLM backend factory (vLLM default, Ollama fallback)."""

from core import parameters
from llm import create_llm_client
from llm.ollama_client import OllamaClient
from llm.vllm_client import VLLMClient


def test_factory_defaults_to_vllm(monkeypatch):
    monkeypatch.setattr(parameters, "LLM_BACKEND", "vllm", raising=False)
    client = create_llm_client()
    assert isinstance(client, VLLMClient)
    assert client.model_name == parameters.LLM_MODEL


def test_factory_selects_ollama(monkeypatch):
    monkeypatch.setattr(parameters, "LLM_BACKEND", "ollama", raising=False)
    client = create_llm_client()
    assert isinstance(client, OllamaClient)
    assert client.model_name == parameters.LLM_MODEL


def test_factory_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(parameters, "LLM_BACKEND", "VLLM", raising=False)
    assert isinstance(create_llm_client(), VLLMClient)


def test_factory_unknown_backend_falls_back_to_vllm(monkeypatch):
    monkeypatch.setattr(parameters, "LLM_BACKEND", "not-a-backend", raising=False)
    assert isinstance(create_llm_client(), VLLMClient)

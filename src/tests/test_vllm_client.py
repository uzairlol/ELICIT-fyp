"""Unit tests for the vLLM OpenAI-compatible client wrapper."""

import pytest
from openai import OpenAIError

from core import parameters
from llm.vllm_client import VLLMClient


class _FakeMessage:
    def __init__(self, content):
        self.content = content
        self.reasoning_content = None


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeResponse:
    def __init__(self, message):
        self.choices = [_FakeChoice(message)]


class _FakeCompletions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.captured: dict | None = None

    def create(self, **kwargs):
        self.captured = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(parameters, "SEED", 7, raising=False)
    c = VLLMClient(model_name="qwen2.5-14b", base_url="http://localhost:8000/v1")
    return c


def test_send_request_uses_standard_openai_args(client):
    completions = _FakeCompletions(response=_FakeResponse(_FakeMessage('{"ok": 1}')))
    client.client = _FakeOpenAIClient(completions)

    result = client.send_request(
        model_name="qwen2.5-14b",
        prompt="Hello",
        max_tokens=96,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    assert result == '{"ok": 1}'
    captured = completions.captured
    assert captured is not None
    assert captured["model"] == "qwen2.5-14b"
    assert captured["max_tokens"] == 96
    assert captured["temperature"] == 0.3
    assert captured["seed"] == 7
    assert captured["response_format"] == {"type": "json_object"}
    assert "extra_body" not in captured
    assert "options" not in captured
    assert "keep_alive" not in captured
    assert captured["messages"][0]["content"] == "Hello"


def test_send_request_falls_back_to_reasoning_content(client):
    empty_message = _FakeMessage("")
    empty_message.reasoning_content = "hidden chain of thought"
    completions = _FakeCompletions(response=_FakeResponse(empty_message))
    client.client = _FakeOpenAIClient(completions)

    result = client.send_request(model_name="qwen2.5-14b", prompt="p", max_tokens=64)
    assert result == "hidden chain of thought"


def test_send_request_wraps_openai_errors(client):
    completions = _FakeCompletions(error=OpenAIError("boom"))
    client.client = _FakeOpenAIClient(completions)

    with pytest.raises(Exception, match="vLLM Error: boom"):
        client.send_request(model_name="qwen2.5-14b", prompt="p", max_tokens=64)


def test_soft_reset_model_is_noop(client):
    result = client.soft_reset_model()
    assert result["still_loaded"] == ["qwen2.5-14b"]
    assert result["unloaded"] == []
    assert result["killed_runners"] == []


def test_semaphore_bounds_concurrency(client):
    assert client.max_concurrency >= parameters.LLM_MAX_CONCURRENCY
    assert client.max_concurrency >= parameters.TOM_MAX_CONCURRENCY

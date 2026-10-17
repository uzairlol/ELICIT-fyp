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
    def __init__(self, message=None, text=None):
        self.message = message
        self.text = text


class _FakeResponse:
    def __init__(self, message=None, text=None):
        if text is not None:
            self.choices = [_FakeChoice(text=text)]
        else:
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
        # The raw-completions transport used when CHAT_TEMPLATE_MODE == "fixed".
        self.completions = completions


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
    # The reasoning token cap was removed: max_tokens is deliberately not sent,
    # so vLLM derives the budget as min(max_model_len - prompt_len, ...).
    assert "max_tokens" not in captured
    assert captured["temperature"] == 0.3
    # Sampling is pinned by LLM_SEED, not by the Python RNG seed. Tying them
    # together meant the replication unit of the nine historical seeds could not
    # be shown to be independent of the Python-side draw.
    assert captured["seed"] == parameters.LLM_SEED
    assert captured["response_format"] == {"type": "json_object"}
    assert "options" not in captured
    assert "keep_alive" not in captured
    assert captured["extra_body"] == {
        "min_p": parameters.LLM_MIN_P,
        "repetition_penalty": parameters.LLM_REPETITION_PENALTY,
    }
    assert captured["messages"][0]["content"] == "Hello"


def test_sampling_seed_follows_llm_seed_not_python_seed(client, monkeypatch):
    """Changing the Python RNG seed must not change what is sent to the sampler."""
    monkeypatch.setattr(parameters, "LLM_SEED", 1013, raising=False)
    completions = _FakeCompletions(response=_FakeResponse(_FakeMessage("{}")))
    client.client = _FakeOpenAIClient(completions)

    client.send_request(model_name="qwen2.5-14b", prompt="p")
    assert completions.captured["seed"] == 1013


def test_fixed_template_mode_posts_raw_prompt(client, monkeypatch):
    """Cross-model prompt parity: ELICIT renders the chat string and posts it raw."""
    monkeypatch.setattr(parameters, "CHAT_TEMPLATE_MODE", "fixed", raising=False)
    monkeypatch.setattr(parameters, "CHAT_TEMPLATE_NAME", "chatml", raising=False)
    completions = _FakeCompletions(response=_FakeResponse(text="{}"))
    client.client = _FakeOpenAIClient(completions)

    client.send_request(model_name="mistral-7b", prompt="Hello")

    # Compared against the renderer rather than against literal control tokens,
    # so the assertion states the contract (ELICIT renders and posts raw) without
    # hard-coding a family's template syntax into the test.
    from llm.chat_template import render_chat

    captured = completions.captured
    assert "messages" not in captured
    assert captured["prompt"] == render_chat("Hello", "chatml")
    assert "Hello" in captured["prompt"]

    # The same prompt under any registered template renders to one string that
    # ELICIT owns, so the prompt is byte-identical across model families.
    rendered = {name: render_chat("Hello", name) for name in ("chatml", "llama3", "mistral")}
    assert all("Hello" in text for text in rendered.values())


def test_server_template_mode_keeps_messages(client, monkeypatch):
    monkeypatch.setattr(parameters, "CHAT_TEMPLATE_MODE", "server", raising=False)
    completions = _FakeCompletions(response=_FakeResponse(_FakeMessage("{}")))
    client.client = _FakeOpenAIClient(completions)

    client.send_request(model_name="mistral-7b", prompt="Hello")

    captured = completions.captured
    assert captured["messages"][0]["content"] == "Hello"
    assert "prompt" not in captured


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

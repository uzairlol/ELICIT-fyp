"""Unit tests for shared LLM retry orchestration."""

import pytest

from llm.retry import (
    RetryExhaustedError,
    build_failure_retry_prompt,
    request_with_retries,
    run_with_retries,
)


def test_build_failure_retry_prompt_appends_block():
    prompt = build_failure_retry_prompt(
        "Answer the question.",
        "Punishment Stage",
        "response was not valid JSON",
        fix_guidance='Return {"value": 3}.',
    )
    assert prompt.startswith("Answer the question.")
    assert "IMPORTANT RETRY (Punishment Stage)" in prompt
    assert "response was not valid JSON" in prompt
    assert 'Return {"value": 3}.' in prompt


def test_build_failure_retry_prompt_handles_blank_reason():
    prompt = build_failure_retry_prompt("base", "Vote", None)
    assert "unknown validation error" in prompt
    assert "How to fix" not in prompt


def test_run_with_retries_succeeds_on_first_try(monkeypatch):
    monkeypatch.setattr("llm.retry.time.sleep", lambda *a, **k: None)
    calls = []

    def operation(attempt):
        calls.append(attempt)
        return "ok"

    result = run_with_retries(operation, max_attempts=3, label="job")
    assert result == "ok"
    assert calls == [1]


def test_run_with_retries_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("llm.retry.time.sleep", lambda *a, **k: None)
    calls = []

    def operation(attempt):
        calls.append(attempt)
        if attempt < 3:
            raise ValueError(f"attempt {attempt} failed")
        return "done"

    result = run_with_retries(operation, max_attempts=3, label="job")
    assert result == "done"
    assert calls == [1, 2, 3]


def test_run_with_retries_raises_when_exhausted(monkeypatch):
    monkeypatch.setattr("llm.retry.time.sleep", lambda *a, **k: None)

    def operation(attempt):
        raise ValueError("boom")

    with pytest.raises(RetryExhaustedError) as excinfo:
        run_with_retries(operation, max_attempts=2, label="failing-job")
    assert excinfo.value.label == "failing-job"
    assert excinfo.value.attempts == 2
    assert "boom" in str(excinfo.value)


class _FakeAPIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def send_request(self, prompt=None, max_attempts=1, request_label="", **kwargs):
        self.calls.append({"prompt": prompt, "max_attempts": max_attempts, "kwargs": kwargs})
        return self.responses.pop(0)


def test_request_with_retries_returns_response_and_parsed(monkeypatch):
    monkeypatch.setattr("llm.retry.time.sleep", lambda *a, **k: None)
    client = _FakeAPIClient(['{"value": 3}'])

    def parse(raw):
        return {"raw": raw}

    def validate(parsed):
        return ""

    response, parsed = request_with_retries(
        client,
        base_prompt="P",
        parse_response=parse,
        validate_result=validate,
        request_kwargs={"model_name": "qwen2.5-14b", "max_tokens": 64},
        max_attempts=2,
        label="proposal",
    )
    assert response == '{"value": 3}'
    assert parsed == {"raw": '{"value": 3}'}
    assert len(client.calls) == 1


def test_request_with_retries_reruns_with_repair_prompt(monkeypatch):
    monkeypatch.setattr("llm.retry.time.sleep", lambda *a, **k: None)
    client = _FakeAPIClient(['{"bad": 1}', '{"value": 9}'])
    observed = []

    def parse(raw):
        return {"raw": raw}

    def validate(parsed):
        return "" if parsed["raw"] == '{"value": 9}' else "value not in allowed set"

    def retry_factory(base, attempt, failure):
        observed.append((base, attempt, failure))
        return base + "\n== RETRY =="

    response, parsed = request_with_retries(
        client,
        base_prompt="P",
        parse_response=parse,
        validate_result=validate,
        request_kwargs={"model_name": "qwen2.5-14b", "max_tokens": 64},
        max_attempts=3,
        label="proposal",
        retry_prompt_factory=retry_factory,
    )
    assert response == '{"value": 9}'
    assert parsed == {"raw": '{"value": 9}'}
    assert len(client.calls) == 2
    assert client.calls[1]["prompt"] == "P\n== RETRY =="
    assert observed == [("P", 2, "value not in allowed set")]

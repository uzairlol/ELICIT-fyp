"""Shared retry orchestration for all LLM operations."""

import logging
import time


class RetryExhaustedError(RuntimeError):
    """Raised when an LLM operation fails all configured attempts."""

    def __init__(self, label, attempts, last_error, last_parsed=None):
        super().__init__(
            f"{label} failed after {attempts} attempt(s): {last_error}"
        )
        self.label = label
        self.attempts = attempts
        self.last_error = last_error
        self.last_parsed = last_parsed  # last successfully-parsed (but invalid) result, if any


def build_failure_retry_prompt(
    base_prompt,
    stage_name,
    failure_reason,
    fix_guidance="",
):
    """
    Append a retry block that tells the model the previous attempt failed and why.

    Changing the prompt text is required under a fixed Ollama seed; a bare
    resend of the same prompt tends to reproduce the same invalid output.
    """
    failure = str(failure_reason or "unknown validation error").strip()
    guidance = str(fix_guidance or "").strip()
    lines = [
        str(base_prompt).rstrip(),
        "",
        f"IMPORTANT RETRY ({stage_name}): Your previous response FAILED validation.",
        f"Failure reason: {failure}",
    ]
    if guidance:
        lines.append(f"How to fix: {guidance}")
    lines.extend([
        "Correct that exact problem.",
        "Return ONLY one valid JSON object matching the Required JSON shape / response contract.",
        "No markdown, no code fences, no text outside the JSON.",
    ])
    return "\n".join(lines)


def run_with_retries(
    operation,
    *,
    max_attempts,
    label,
    logger=None,
    base_delay_seconds=1.0,
    max_delay_seconds=8.0,
):
    """
    Run ``operation(attempt_number)`` with bounded exponential backoff.

    The operation may include transport, parsing, and validation. It should
    return the accepted result or raise an exception describing why the
    attempt failed.
    """
    attempts = max(1, int(max_attempts))
    log = logger or logging.getLogger(__name__)
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return operation(attempt)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                break

            delay = min(
                float(max_delay_seconds),
                float(base_delay_seconds) * (2 ** (attempt - 1)),
            )
            log.warning(
                "%s attempt %s/%s failed: %s. Retrying in %.1fs.",
                label,
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)

    raise RetryExhaustedError(label, attempts, last_error)


def request_with_retries(
    api_client,
    *,
    base_prompt,
    parse_response,
    validate_result,
    request_kwargs,
    max_attempts,
    label,
    retry_prompt_factory=None,
    logger=None,
):
    """
    Send, parse, and validate an LLM response through one retry path.

    ``validate_result`` returns an empty string for a valid parsed result or
    a human-readable error for a response that must be retried.

    If ``retry_prompt_factory`` is omitted, retries use
    ``build_failure_retry_prompt`` with the validation failure reason.
    """
    state = {"last_error": "", "last_parsed": None}

    def default_retry_prompt(prompt, _attempt, failure_reason):
        return build_failure_retry_prompt(prompt, label, failure_reason)

    repair = retry_prompt_factory or default_retry_prompt

    def attempt_request(attempt):
        prompt = base_prompt
        if attempt > 1:
            prompt = repair(
                base_prompt,
                attempt,
                state["last_error"],
            )

        response = api_client.send_request(
            prompt=prompt,
            max_attempts=1,
            request_label=label,
            **request_kwargs,
        )
        parsed = parse_response(response)
        state["last_parsed"] = parsed  # preserve even if validation fails
        validation_error = str(validate_result(parsed) or "")
        if validation_error:
            state["last_error"] = validation_error
            raise ValueError(validation_error)
        return response, parsed

    try:
        return run_with_retries(
            attempt_request,
            max_attempts=max_attempts,
            label=label,
            logger=logger,
        )
    except RetryExhaustedError as exc:
        exc.last_parsed = state["last_parsed"]
        raise

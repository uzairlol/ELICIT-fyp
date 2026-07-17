"""Shared retry orchestration for all LLM operations."""

import logging
import time


class RetryExhaustedError(RuntimeError):
    """Raised when an LLM operation fails all configured attempts."""

    def __init__(self, label, attempts, last_error):
        super().__init__(
            f"{label} failed after {attempts} attempt(s): {last_error}"
        )
        self.label = label
        self.attempts = attempts
        self.last_error = last_error


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
    """
    state = {"last_error": ""}

    def attempt_request(attempt):
        prompt = base_prompt
        if attempt > 1 and retry_prompt_factory is not None:
            prompt = retry_prompt_factory(
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
        validation_error = str(validate_result(parsed) or "")
        if validation_error:
            state["last_error"] = validation_error
            raise ValueError(validation_error)
        return response, parsed

    return run_with_retries(
        attempt_request,
        max_attempts=max_attempts,
        label=label,
        logger=logger,
    )

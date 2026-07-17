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

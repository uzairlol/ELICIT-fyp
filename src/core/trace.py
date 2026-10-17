"""Sampled deliberation traces.

Rationale fields average 8.45 words across 7,020 agent-rounds and only 41.2% are
unique, which is why the report's qualitative section had to concede that these
texts are not evidence of intrinsic motivation. A post-hoc one-liner cannot
show deliberation that was never serialised.

This module records the full prompt and raw completion for a sampled subset of
decisions, to a gitignored JSONL sidecar. Sampling keeps a 30-round, 26-agent run
bounded; the sampler is seeded from the run's seed vector, so the same run
traces the same decisions.
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
from typing import Any

from core import parameters

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


class TraceWriter:
    """Append-only JSONL writer, sampled, capped, and disabled by default."""

    def __init__(self, run_label: str | None = None, base_dir: str | None = None):
        self.enabled = bool(getattr(parameters, "TRACE_ENABLED", False))
        self.rate = float(getattr(parameters, "TRACE_SAMPLING_RATE", 0.05))
        self.max_records = int(getattr(parameters, "TRACE_MAX_RECORDS", 20_000))
        self.written = 0
        self.considered = 0
        self.path: str | None = None
        self._rng = random.Random((parameters.SEED_VECTOR or {}).get("python", parameters.SEED))
        if not self.enabled:
            return
        base = base_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "debug_logs", "traces"
        )
        os.makedirs(base, exist_ok=True)
        label = str(run_label or getattr(parameters, "BATCH_NAME", "run"))
        self.path = os.path.join(base, f"trace_{label}_seed{parameters.SEED}.jsonl")
        logger.info("Deliberation tracing enabled -> %s (rate=%.3f)", self.path, self.rate)

    def should_record(self) -> bool:
        if not self.enabled or self.written >= self.max_records:
            return False
        self.considered += 1
        return self._rng.random() < self.rate

    def record(self, *, agent_id: int, round_number: int, stage: str, prompt: str, response: Any):
        if not self.should_record():
            return
        with _LOCK:
            if self.written >= self.max_records or not self.path:
                return
            entry = {
                "agent_id": agent_id,
                "round": round_number,
                "stage": stage,
                "prompt_variant": getattr(parameters, "PROMPT_VARIANT", "P0_canonical"),
                "prompt": prompt,
                "response": response,
            }
            try:
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError as exc:  # pragma: no cover - disk failure must not kill a run
                logger.warning("Trace write failed: %s", exc)
                return
            self.written += 1

    def summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "rate": self.rate,
            "considered": self.considered,
            "written": self.written,
            "path": self.path,
            "capped": self.written >= self.max_records,
        }


_ACTIVE: TraceWriter | None = None


def get_writer(run_label: str | None = None) -> TraceWriter | None:
    """Process-wide writer, created on first use."""
    global _ACTIVE
    if _ACTIVE is None and getattr(parameters, "TRACE_ENABLED", False):
        _ACTIVE = TraceWriter(run_label)
    return _ACTIVE


def reset_writer():
    global _ACTIVE
    _ACTIVE = None

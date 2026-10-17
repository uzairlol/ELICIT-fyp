"""Sampled deliberation traces.

Rationale fields average 8.45 words across 7,020 agent-rounds and only 41.2% are
unique, which is why the report's qualitative section had to concede that these
texts are not evidence of intrinsic motivation. A post-hoc one-liner cannot
show deliberation that was never serialised.

This module records the full prompt and raw completion for a sampled subset of
decisions, to a gitignored JSONL sidecar. Sampling keeps a 30-round, 26-agent run
bounded; the sampler is seeded from its own named stream, so the same run traces
the same decisions.

Enabled by default at a low sampling rate. The doc calls this the highest-value
fix for an economics audience precisely because the qualitative section is
otherwise an interpretation of 8.45-word summaries, and an opt-in switch that
nobody flips leaves the gap exactly where it was.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

from core import parameters
from core.seeding import active_rng

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def default_trace_dir() -> str:
    """Where traces land.

    Repo-relative rather than ``src/``-relative: the path has to agree with
    ``.gitignore`` or traces show up as untracked files, which is how a
    "gitignored sidecar" stops being one.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(repo_root, "debug_logs", "traces")


class TraceWriter:
    """Append-only JSONL writer, sampled, capped."""

    def __init__(self, run_label: str | None = None, base_dir: str | None = None):
        self.enabled = bool(getattr(parameters, "TRACE_ENABLED", True))
        self.rate = float(getattr(parameters, "TRACE_SAMPLING_RATE", 0.05))
        self.max_records = int(getattr(parameters, "TRACE_MAX_RECORDS", 20_000))
        self.written = 0
        self.considered = 0
        self.path: str | None = None
        if not self.enabled:
            return
        # Own named stream: sampling must not consume from a stream the
        # simulation itself draws on.
        self._rng = active_rng("trace_sampling")
        base = base_dir or default_trace_dir()
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
    if _ACTIVE is None and getattr(parameters, "TRACE_ENABLED", True):
        _ACTIVE = TraceWriter(run_label)
    return _ACTIVE


def reset_writer():
    global _ACTIVE
    _ACTIVE = None

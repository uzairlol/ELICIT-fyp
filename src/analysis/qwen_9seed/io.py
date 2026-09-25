"""Input discovery and provenance helpers for the Qwen run pack."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

QWEN_PATTERN = re.compile(
    r"^simulation_qwen2\.5-14b_Full_scnldf_sh1_ldf1_"
    r"seed(?P<seed>\d+)_26agents_30rounds_(?P<stamp>\d{8}_\d{6})\.json$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_qwen_runs(results_dir: Path) -> list[Path]:
    """Return the nine expected Qwen files, rejecting ambiguous matches."""
    matches = []
    for path in sorted(results_dir.iterdir()):
        match = QWEN_PATTERN.match(path.name)
        if match:
            matches.append((int(match.group("seed")), path))
    seeds = [seed for seed, _ in matches]
    if len(matches) != 9 or sorted(seeds) != list(range(1, 10)):
        found = sorted(seeds)
        raise FileNotFoundError(f"Expected Qwen seeds 1..9 under {results_dir}; found {found}")
    return [path for _, path in sorted(matches)]


def parse_run_name(path: Path) -> dict[str, Any]:
    match = QWEN_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Not an expected Qwen filename: {path.name}")
    return {
        "seed": int(match.group("seed")),
        "timestamp": match.group("stamp"),
        "filename": path.name,
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_rounds(payload: Any) -> list[dict[str, Any]]:
    """Normalize the known list payload and common wrapper forms."""
    if isinstance(payload, list):
        rounds = payload
    elif isinstance(payload, dict):
        for key in ("rounds", "history", "round_history", "results"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                rounds = candidate
                break
        else:
            # A few exports use a dictionary keyed by round number.
            numeric_keys = [key for key in payload if str(key).isdigit()]
            if numeric_keys:
                rounds = [payload[key] for key in sorted(numeric_keys, key=int)]
            else:
                raise ValueError("Could not locate a round history in JSON payload")
    else:
        raise TypeError(f"Unsupported JSON root type: {type(payload).__name__}")
    if not all(isinstance(item, dict) for item in rounds):
        raise ValueError("Every round history entry must be an object")
    return rounds

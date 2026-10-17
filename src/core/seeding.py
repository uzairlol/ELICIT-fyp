"""Explicit, serialised seed vectors.

The nine historical "replications" were not demonstrably independent:
``SEED`` reached ``random.seed()`` but the served model sampled without a
pinned seed, and the seed never appeared in the run filenames. Run-level
inference — the analysis pipeline's central methodological commitment — is
invalid if the replication unit is not actually independent.

This module makes that checkable. A run declares every stochastic source it
uses; :func:`build_seed_vector` derives them from one integer so a cell is
reproducible from a single number, :func:`apply_seed_vector` pushes them into
``parameters`` and the Python RNG, and the vector is serialised verbatim into
``resolved_config.json`` and the result JSON.
"""

from __future__ import annotations

import hashlib
import os
import random
from collections.abc import Iterable
from typing import Any

from core import parameters


class SeedVectorError(RuntimeError):
    """Raised when a declared seed vector is incomplete or inconsistent."""


#: Every stochastic source a run must pin. Adding one here is deliberately
#: expensive: it forces every existing config to declare it.
REQUIRED_KEYS: tuple[str, ...] = (
    "python",
    "llm_seed",
    "python_streams",
    "persona_streams",
    "chat_template_seed",
)

#: Sampling settings that must be identical across model families for the
#: variance decomposition in ``analysis`` to attribute anything to the model.
PARITY_SAMPLING_KEYS: tuple[str, ...] = ("temperature", "top_p", "min_p", "repetition_penalty")


def _derive(base: int, label: str, modulus: int = 2**31 - 1) -> int:
    """Derive a stable sub-seed from a base seed and a label.

    Uses SHA-256 rather than a bare offset so the sub-seeds for different labels
    are uncorrelated and adding a new stream does not shift the existing ones.
    """
    digest = hashlib.sha256(f"elicit:{base}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def derive_seed_vector(
    base_seed: int,
    *,
    n_agents: int,
    temperature: float,
    top_p: float,
    min_p: float = 0.0,
    repetition_penalty: float = 1.0,
    max_model_len: int = 8192,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a complete vector from one base integer.

    ``extra`` is merged last so a caller can pin a value the derivation would
    otherwise own (useful when reproducing a historical run).
    """
    base_seed = int(base_seed)
    vector: dict[str, Any] = {
        "base_seed": base_seed,
        "python": _derive(base_seed, "python"),
        "llm_seed": _derive(base_seed, "llm-seed"),
        # One stream per agent so the sequential democracy tie-breaks and the
        # profile shuffle cannot correlate across agents.
        "python_streams": {
            f"agent_{agent_id}": _derive(base_seed, f"agent:{agent_id}")
            for agent_id in range(int(n_agents))
        },
        # Per-persona sampling seeds: a run mixes DEFAULT / RANDOM / GREEDY
        # personas and each must be independently reproducible.
        "persona_streams": {
            "DEFAULT": _derive(base_seed, "persona:DEFAULT"),
            "RANDOM": _derive(base_seed, "persona:RANDOM"),
            "GREEDY": _derive(base_seed, "persona:GREEDY"),
        },
        "chat_template_seed": _derive(base_seed, "chat-template"),
        "sampling": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "min_p": float(min_p),
            "repetition_penalty": float(repetition_penalty),
            "max_model_len": int(max_model_len),
        },
    }
    if extra:
        vector.update(extra)
    return vector


def build_seed_vector(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a vector from a resolved config, honouring an explicit override."""
    config = dict(config or {})
    explicit = config.get("seed_vector") or {}

    base_seed = explicit.get("base_seed")
    if base_seed is None:
        base_seed = int(config.get("seed", parameters.SEED))
    sampling = dict(config.get("sampling") or {})
    vector = derive_seed_vector(
        base_seed,
        n_agents=int(config.get("agents", parameters.NUM_AGENTS)),
        temperature=float(sampling.get("temperature", parameters.LLM_TEMPERATURE)),
        top_p=float(sampling.get("top_p", parameters.LLM_TOP_P)),
        min_p=float(sampling.get("min_p", parameters.LLM_MIN_P)),
        repetition_penalty=float(
            sampling.get("repetition_penalty", parameters.LLM_REPETITION_PENALTY)
        ),
        max_model_len=int(sampling.get("max_model_len", parameters.VLLM_MAX_MODEL_LEN)),
    )

    # An explicit per-key value in the config always wins over the derivation.
    for key in REQUIRED_KEYS:
        if key in explicit and explicit[key] is not None:
            vector[key] = explicit[key]
    for key, value in explicit.items():
        if key not in vector and key != "base_seed":
            vector[key] = value
    return vector


def validate_seed_vector(vector: Any) -> list[str]:
    """Return a list of problems; empty means the vector is complete."""
    problems: list[str] = []
    if not isinstance(vector, dict) or not vector:
        return ["seed vector is missing or empty"]
    for key in REQUIRED_KEYS:
        if key not in vector:
            problems.append(f"missing key: {key}")
    sampling = vector.get("sampling")
    if not isinstance(sampling, dict):
        problems.append("missing key: sampling")
    else:
        for key in PARITY_SAMPLING_KEYS:
            if key not in sampling:
                problems.append(f"missing sampling key: {key}")
    streams = vector.get("python_streams")
    if not isinstance(streams, dict) or not streams:
        problems.append("python_streams must be a non-empty mapping")
    personas = vector.get("persona_streams")
    if not isinstance(personas, dict) or not personas:
        problems.append("persona_streams must be a non-empty mapping")
    if vector.get("python") == vector.get("llm_seed"):
        problems.append("python and llm_seed are identical; sampling would be tied to the RNG")
    return problems


def require_complete(vector: Any) -> dict[str, Any]:
    """Raise :class:`SeedVectorError` unless the vector is complete."""
    problems = validate_seed_vector(vector)
    if problems:
        raise SeedVectorError("Incomplete seed vector: " + "; ".join(problems))
    return dict(vector)


def apply_seed_vector(vector: dict[str, Any], seed_env_var: bool = True) -> None:
    """Install a seed vector into ``parameters`` and the global Python RNG.

    ``seed_env_var`` also exports ``ELICIT_SEED_VECTOR`` so worker processes and
    the deliberation-trace sampler observe the same vector.
    """
    require_complete(vector)
    python_seed = int(vector["python"])
    parameters.SEED = python_seed
    parameters.LLM_SEED = int(vector["llm_seed"])
    parameters.SEED_VECTOR = dict(vector)

    random.seed(python_seed)
    if seed_env_var:
        os.environ["ELICIT_SEED_VECTOR"] = repr(vector)
        os.environ["ELICIT_SEED"] = str(python_seed)


def fingerprint(vector: dict[str, Any]) -> str:
    """Stable short hash of a vector, for run filenames and manifests."""
    import json

    payload = json.dumps(vector, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def distinct_fingerprints(vectors: Iterable[dict[str, Any]]) -> int:
    """Count unique vectors — used by ``elicit doctor`` to catch reused seeds."""
    return len({fingerprint(vector) for vector in vectors})

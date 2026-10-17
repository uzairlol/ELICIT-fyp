"""Serialise the inference environment into every result file.

The historical manifest could only say ``"model provenance is limited to the
filename alias"``. TRAILS argues robustness must be measured per *served
artefact*; without the checkpoint, quantisation, engine version and server flags
in the artefact, that claim cannot be checked by a referee and cross-model
contrasts cannot be decomposed.

Everything here is collected from values that already exist in ``parameters``,
which the CLI populates from the resolved config. Nothing is inferred at run time
from the GPU, because the simulation process does not own the serving process.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Any

from core import parameters
from core.seeding import stream_usage_report
from llm.chat_template import template_fingerprint
from prompts.prompt_variants import all_variant_hashes, variant_hash


def persona_sampling_profile() -> dict[str, dict[str, float]]:
    """Sampling settings actually sent, per persona.

    Mirrors ``Agent._persona_sampling_profile``; kept declarative here so the
    manifest can state the numbers without importing an Agent instance.
    """
    return {
        "DEFAULT": {
            "temperature": float(parameters.LLM_TEMPERATURE),
            "top_p": float(parameters.LLM_TOP_P),
        },
        "RANDOM": {"temperature": 0.95, "top_p": 1.0},
        "GREEDY": {"temperature": 0.15, "top_p": 0.8},
        "RANDOM_punishment": {"temperature": 1.0, "top_p": 1.0},
    }


def checkpoint_identity(checkpoint: str | None = None) -> dict[str, Any]:
    """Identify the exact weights a run served, not just their repo name.

    A Hub alias like ``Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4`` is a mutable pointer:
    the branch can be re-uploaded, so two runs a month apart can differ while
    reporting the same checkpoint string. The resolved commit sha is what makes
    "same weights" checkable, which is the whole point of the item-6 finding that
    model provenance was unrecoverable.

    Resolution is best-effort and offline-safe: if the cache or the Hub is
    unreachable the sha is null and ``resolved`` says so, rather than the run
    failing or the field being quietly absent.
    """
    name = str(checkpoint or getattr(parameters, "MODEL_CHECKPOINT", "") or "")
    identity: dict[str, Any] = {
        "checkpoint": name,
        "revision": None,
        "source": "unset",
        "resolved": True,
    }
    if not name:
        identity["source"] = "unset"  # nothing to resolve; not a failure
        return identity

    # 1. The local HF cache, which is where vLLM actually loaded from.
    revision = _cached_revision(name)
    if revision:
        identity["revision"] = revision
        identity["resolved"] = True
        identity["source"] = "hf_cache"
        return identity

    # 2. The Hub. Short timeout: this runs inside every simulation's manifest
    #    write, so a slow network must not become a slow run.
    revision = _hub_revision(name)
    if revision:
        identity["revision"] = revision
        identity["resolved"] = True
        identity["source"] = "hub"
        return identity

    identity["source"] = "unresolved"
    identity["resolved"] = False
    return identity


def _cached_revision(name: str) -> str | None:
    """Commit sha of a snapshot already present in the HuggingFace cache."""
    from pathlib import Path

    cache = Path(os.environ.get("HF_HUB_CACHE") or Path.home() / ".cache" / "huggingface" / "hub")
    folder = cache / ("models--" + name.replace("/", "--"))
    refs = folder / "refs"
    try:
        if not refs.is_dir():
            return None
        main = (refs / "main").read_text(encoding="utf-8").strip()
        return main or None
    except OSError:
        return None


def _hub_revision(name: str) -> str | None:
    """Commit sha for the model's main branch on the Hub."""
    try:
        import json as _json
        import urllib.request

        url = f"https://huggingface.co/api/models/{name}"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = _json.loads(response.read())
        return str(payload.get("sha") or "") or None
    except Exception:  # provenance must never break a run
        return None


def inference_provenance() -> dict[str, Any]:
    """Return the block embedded in every result JSON."""
    variant_name = str(parameters.PROMPT_VARIANT)
    checkpoint = checkpoint_identity()
    return {
        "model": {
            "alias": parameters.LLM_MODEL,
            "checkpoint": parameters.MODEL_CHECKPOINT,
            "checkpoint_revision": checkpoint["revision"],
            "checkpoint_revision_source": checkpoint["source"],
            "checkpoint_revision_resolved": checkpoint["resolved"],
            "quantization": parameters.MODEL_QUANTIZATION,
            "parameter_count_billions": parameters.MODEL_PARAM_COUNT_B,
            "served_model_name_matches_alias": bool(parameters.LLM_MODEL),
        },
        "serving": {
            "backend": parameters.LLM_BACKEND,
            "base_url": parameters.LLM_BASE_URL,
            "vllm_version": parameters.VLLM_VERSION,
            "serve_flags": parameters.VLLM_SERVE_FLAGS,
            "max_model_len": parameters.VLLM_MAX_MODEL_LEN,
            "client_max_concurrency": parameters.VLLM_MAX_CONCURRENCY,
        },
        "sampling": {
            "declared": {
                "temperature": parameters.LLM_TEMPERATURE,
                "top_p": parameters.LLM_TOP_P,
                "min_p": parameters.LLM_MIN_P,
                "repetition_penalty": parameters.LLM_REPETITION_PENALTY,
            },
            "per_persona": persona_sampling_profile(),
            "llm_seed": parameters.LLM_SEED,
        },
        "chat_template": {
            "mode": parameters.CHAT_TEMPLATE_MODE,
            "name": parameters.CHAT_TEMPLATE_NAME,
            "fingerprint": template_fingerprint(),
            "rendered_in_python": str(parameters.CHAT_TEMPLATE_MODE).lower() == "fixed",
        },
        "prompt_variant": {
            "name": variant_name,
            "hash": variant_hash(variant_name),
            "registered_hashes": all_variant_hashes(),
        },
        "seed_vector": dict(parameters.SEED_VECTOR or {}),
        "seed_vector_usage": stream_usage_report(),
        "concurrency": {
            "llm_max_concurrency": parameters.LLM_MAX_CONCURRENCY,
            "tom_max_concurrency": parameters.TOM_MAX_CONCURRENCY,
            "democracy_max_concurrency": parameters.DEMOCRACY_MAX_CONCURRENCY,
        },
        "instrumentation": {
            "log_start_of_round_wealth": parameters.LOG_START_OF_ROUND_WEALTH,
            "log_gossip_exposure": parameters.LOG_GOSSIP_EXPOSURE,
            "log_tom_completion_order": parameters.LOG_TOM_COMPLETION_ORDER,
            "raw_allocation_reporting": parameters.RAW_ALLOCATION_REPORTING,
            "trace_enabled": parameters.TRACE_ENABLED,
            "trace_sampling_rate": parameters.TRACE_SAMPLING_RATE,
        },
        "governance": {
            "mode": parameters.LDF_GOVERNANCE_MODE,
            "allocation_rule": parameters.LDF_ALLOCATION_RULE,
            "board_always_accepts": parameters.LDF_BOARD_ALWAYS_ACCEPTS,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "pid": os.getpid(),
        },
    }


def simulation_parameters_snapshot() -> dict[str, Any]:
    """Effective values of the parameters that define the payoff structure.

    Selecting the payoff-relevant subset (rather than dumping every global)
    keeps the artefact readable and keeps changes in logging-only parameters
    from looking like changes in the experiment.
    """
    keys = (
        "NUM_AGENTS",
        "NUM_ROUNDS",
        "SCENARIO",
        "AGENT_TYPE",
        "PUBLIC_GOOD_MULTIPLIER",
        "MIN_CONTRIBUTION",
        "ENDOWMENT_STAGE_1",
        "ENDOWMENT_STAGE_2",
        "STAGE_2_WEALTH_FRACTION",
        "PUNISHMENT_EFFECT",
        "PUNISHMENT_COST",
        "REWARD_EFFECT",
        "REWARD_COST",
        "SUBSIDY_ENABLED",
        "SUBSIDY_FRACTION",
        "SUBSIDY_TOP_N",
        "TOM_ENABLED",
        "GOSSIP_ENABLED",
        "GOSSIP_TRIGGER_SCORE",
        "MAX_GOSSIP_ITEMS",
        "DEMOCRACY_ENABLED",
        "DEMOCRACY_INTERVAL",
        "BELIEF_TRACKING_ENABLED",
        "DISPLAY_PAST_ACTIONS",
        "CLIMATE_SHOCK_ENABLED",
        "CLIMATE_SHOCK_SCHEDULE",
        "CLIMATE_SHOCK_DETERMINISTIC",
        "CLIMATE_DAMAGE_BASE",
        "DEVELOPED_VULNERABILITY",
        "DEVELOPING_VULNERABILITY",
        "DEVELOPED_HISTORICAL_EMISSIONS",
        "DEVELOPING_HISTORICAL_EMISSIONS",
        "DEVELOPED_CONTRIBUTION_CAPACITY",
        "DEVELOPING_CONTRIBUTION_CAPACITY",
        "CONTRIBUTION_CAPACITY_ENABLED",
        "LDF_ENABLED",
        "LDF_PAYOUT_DAMAGE_WEIGHT",
        "LDF_MAX_COVERAGE",
        "LDF_EQUITY_WEIGHT",
        "LDF_AGENT_GROUP_COUNTS",
    )
    return {key: _jsonable(getattr(parameters, key, None)) for key in keys}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

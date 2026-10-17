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


def inference_provenance() -> dict[str, Any]:
    """Return the block embedded in every result JSON."""
    variant_name = str(parameters.PROMPT_VARIANT)
    return {
        "model": {
            "alias": parameters.LLM_MODEL,
            "checkpoint": parameters.MODEL_CHECKPOINT,
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

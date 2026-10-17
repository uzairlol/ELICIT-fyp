"""Apply a resolved config to the live ``parameters`` module and start a run.

This is the only place that writes config values into ``parameters``. Keeping it
in one function means the pre-flight manifest, the run itself and the post-run
sidecar all observe the same values, and there is no second code path that could
disagree about what a run actually was.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from core import parameters
from core.parameter_schema import ParameterError, coerce

#: Where resolved configs are written. One directory so `elicit grid run` and the
#: Kaggle notebooks agree on the layout.
DEFAULT_CONFIG_DIR = Path("results")


class ResolutionError(RuntimeError):
    """Raised when a config cannot be turned into a runnable state."""


def apply_parameters(resolved: dict[str, Any], strict: bool = True) -> list[str]:
    """Assign resolved values onto ``parameters`` and return what was set.

    With ``strict`` an unknown name is fatal. Without it the name is skipped and
    reported, which is what a hand-written legacy cell needs.
    """
    applied: list[str] = []
    for name, value in sorted(resolved.items()):
        if not hasattr(parameters, name):
            if strict:
                raise ResolutionError(f"parameters has no attribute {name!r}")
            continue
        try:
            setattr(parameters, name, coerce(name, value))
        except ParameterError as exc:
            if strict:
                raise ResolutionError(str(exc)) from exc
            continue
        applied.append(name)
    return applied


def apply_provenance(config: dict[str, Any]) -> None:
    """Populate the provenance block from the cell's model declaration.

    The served alias in a config must match ``--served-model-name`` on the vLLM
    command line; recording the checkpoint and quantisation here is what lets a
    referee tell "Qwen2.5-14B" apart from "Qwen2.5-14B served at 4-bit".
    """
    from cli.config import SERVER_REQUIREMENTS

    model = str(getattr(parameters, "LLM_MODEL", ""))
    spec = SERVER_REQUIREMENTS.get(model, {})
    parameters.MODEL_CHECKPOINT = str(config.get("checkpoint") or spec.get("checkpoint", ""))
    parameters.MODEL_QUANTIZATION = str(config.get("quantization") or spec.get("quantization", ""))
    parameters.MODEL_PARAM_COUNT_B = float(
        config.get("parameter_count_billions") or spec.get("parameter_count_billions", 0.0)
    )
    parameters.VLLM_VERSION = str(config.get("vllm_version", parameters.VLLM_VERSION))
    parameters.VLLM_SERVE_FLAGS = str(config.get("serve_flags", parameters.VLLM_SERVE_FLAGS))


def prepare_run(config: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """Put the process into the state one run of ``config`` describes.

    Order matters and is fixed: parameters, then provenance, then the prompt
    variant hash, then the seed vector. The seed vector is applied last because
    it seeds the Python RNG, and anything that consumed randomness beforehand
    would make the run depend on application order.
    """
    from core.provenance import simulation_parameters_snapshot
    from core.seeding import apply_seed_vector, build_seed_vector, fingerprint

    resolved = dict(config.get("parameters") or {})
    apply_parameters(resolved, strict=strict)
    apply_provenance(config)

    from prompts.prompt_variants import active_variant, variant_hash

    active = active_variant()
    parameters.PROMPT_VARIANT_HASH = variant_hash(active)

    vector = config.get("seed_vector") or build_seed_vector(
        {
            "seed": int(resolved.get("SEED", parameters.SEED)),
            "agents": int(resolved.get("NUM_AGENTS", parameters.NUM_AGENTS)),
            "sampling": {
                "temperature": getattr(parameters, "LLM_TEMPERATURE", 0.7),
                "top_p": getattr(parameters, "LLM_TOP_P", 0.9),
                "min_p": getattr(parameters, "LLM_MIN_P", 0.0),
                "repetition_penalty": getattr(parameters, "LLM_REPETITION_PENALTY", 1.0),
                "max_model_len": getattr(parameters, "VLLM_MAX_MODEL_LEN", 8192),
            },
        }
    )
    if getattr(parameters, "SEED_VECTOR_REQUIRED", True):
        apply_seed_vector(vector)
    else:
        parameters.SEED_VECTOR = dict(vector)

    return {
        "name": config.get("name"),
        "arm": config.get("arm"),
        "prompt_variant": active.name,
        "prompt_variant_hash": parameters.PROMPT_VARIANT_HASH,
        "seed_fingerprint": fingerprint(vector),
        "effective_parameters": simulation_parameters_snapshot(),
    }


def write_preflight(config: dict[str, Any], summary: dict[str, Any], directory=None) -> Path:
    """Write the resolved config, seed vector and manifest *before* the first call.

    A crashed run must still have provenance; that is only true if the manifest is
    written first. This is the by-product that makes the manifest extension in
    ``analysis.qwen_9seed.manifest`` unnecessary rather than a task.
    """
    directory = Path(directory or DEFAULT_CONFIG_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"resolved_{config.get('name', 'run')}.json"
    payload = {
        "config": {k: v for k, v in config.items() if k != "seed_vector"},
        "seed_vector": config.get("seed_vector") or parameters.SEED_VECTOR,
        "summary": summary,
        "cwd": os.getcwd(),
        "argv": sys.argv,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    return Path(path)


def run_one(
    config: dict[str, Any], *, strict: bool = True, dry_run: bool = False
) -> dict[str, Any]:
    """Prepare, preflight, and (unless ``dry_run``) execute one run."""
    summary = prepare_run(config, strict=strict)
    preflight = write_preflight(config, summary)

    if dry_run:
        return {"status": "dry-run", "preflight": str(preflight), **summary}

    import main as simulation_main

    original_argv = sys.argv[:]
    sys.argv = [
        "main.py",
        "--num-rounds",
        str(parameters.NUM_ROUNDS),
        "--num-agents",
        str(parameters.NUM_AGENTS),
        "--model-name",
        str(parameters.LLM_MODEL),
        "--scenario",
        str(parameters.SCENARIO),
        "--agent-type",
        str(parameters.AGENT_TYPE),
    ]
    if getattr(parameters, "CLIMATE_SHOCK_ENABLED", False):
        sys.argv.append("--enable-climate-shocks")
    if getattr(parameters, "LDF_ENABLED", False):
        sys.argv.append("--enable-ldf")
    try:
        simulation_main.main()
    finally:
        sys.argv = original_argv

    return {"status": "ok", "preflight": str(preflight), **summary}

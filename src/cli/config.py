"""Config loading, presets and resolution.

A "run" used to be defined by hand-editing ``parameters.py``. That fails three
requirements at once: the seed vector has nowhere to be serialised, a config
cannot travel into a Kaggle notebook as a file, and "pre-registered, fully
reproducible" is not credible if a condition cannot be re-instantiated from a
versioned artefact.

So this layer is thin on purpose. A config may only set values that already exist
as attributes on ``parameters`` (plus an explicit, auditable whitelist below), and
its blast radius is zero. ``parameters`` stays a mutable module of globals that
the democracy module writes into; nothing here replaces it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from core.parameter_schema import SPECS_BY_NAME, coerce

#: Structured keys mapped onto flat parameter names. Adding a key here is a
#: deliberate act: each entry is one more way for a cell to differ, and the grid
#: audit depends on knowing every way.
STRUCTURED_MAP: dict[str, str] = {
    "model": "LLM_MODEL",
    "scenario": "SCENARIO",
    "rounds": "NUM_ROUNDS",
    "agents": "NUM_AGENTS",
    "seed": "SEED",
    "prompt_variant": "PROMPT_VARIANT",
    "governance_mode": "LDF_GOVERNANCE_MODE",
    "allocation_rule": "LDF_ALLOCATION_RULE",
    "shocks.enabled": "CLIMATE_SHOCK_ENABLED",
    "shocks.deterministic": "CLIMATE_SHOCK_DETERMINISTIC",
    "ldf.enabled": "LDF_ENABLED",
    "modules.tom": "TOM_ENABLED",
    "modules.gossip": "GOSSIP_ENABLED",
    "modules.democracy": "DEMOCRACY_ENABLED",
    "modules.belief_tracking": "BELIEF_TRACKING_ENABLED",
    "modules.interval": "DEMOCRACY_INTERVAL",
    "sampling.temperature": "LLM_TEMPERATURE",
    "sampling.top_p": "LLM_TOP_P",
    "sampling.min_p": "LLM_MIN_P",
    "sampling.repetition_penalty": "LLM_REPETITION_PENALTY",
    "sampling.max_model_len": "VLLM_MAX_MODEL_LEN",
    "sampling.chat_template": "CHAT_TEMPLATE_NAME",
    "chat_template_mode": "CHAT_TEMPLATE_MODE",
}

#: Top-level config keys that are not parameter assignments.
RESERVED_KEYS = {
    "name",
    "arm",
    "condition",
    "description",
    "notes",
    "overrides",
    "group_counts",
    "seed_vector",
    "budget_gpu_hours",
    "priority",
    "preset",
    "seed_index",
    "seed",
}

#: Parameters that must be identical across every cell that shares a condition.
#: Only ``LLM_MODEL`` is allowed to differ within a comparison group; everything
#: here appearing twice with different values means a model contrast is really a
#: composite of several factors, and the variance decomposition becomes
#: uninterpretable. This is checked across a grid, not per cell: parity is a
#: property of the comparison set, and a preset legitimately *declares* the
#: baseline values it must hold.
PARITY_CRITICAL: tuple[str, ...] = (
    "PUBLIC_GOOD_MULTIPLIER",
    "NUM_ROUNDS",
    "NUM_AGENTS",
    "ENDOWMENT_STAGE_1",
    "ENDOWMENT_STAGE_2",
    "STAGE_2_WEALTH_FRACTION",
    "PUNISHMENT_EFFECT",
    "PUNISHMENT_COST",
    "REWARD_EFFECT",
    "REWARD_COST",
    "SUBSIDY_FRACTION",
    "SUBSIDY_TOP_N",
    "LDF_MAX_COVERAGE",
    "LDF_PAYOUT_DAMAGE_WEIGHT",
    "LDF_EQUITY_WEIGHT",
    "LDF_AGENT_GROUP_COUNTS",
    "LLM_TEMPERATURE",
    "LLM_TOP_P",
    "LLM_MIN_P",
    "LLM_REPETITION_PENALTY",
    "VLLM_MAX_MODEL_LEN",
    "CHAT_TEMPLATE_MODE",
    "CHAT_TEMPLATE_NAME",
    "PROMPT_VARIANT",
    "CLIMATE_SHOCK_SCHEDULE",
    "CLIMATE_SHOCK_ENABLED",
    "CLIMATE_DAMAGE_BASE",
    "DEMOCRACY_INTERVAL",
    "DEMOCRACY_ENABLED",
    "TOM_ENABLED",
    "GOSSIP_ENABLED",
    "GOSSIP_TRIGGER_SCORE",
    "MAX_GOSSIP_ITEMS",
    "CONTRIBUTION_CAPACITY_ENABLED",
    "CONTRIBUTION_CAPACITY_FLOOR",
    "DEVELOPED_VULNERABILITY",
    "DEVELOPING_VULNERABILITY",
    "DEVELOPED_CONTRIBUTION_CAPACITY",
    "DEVELOPING_CONTRIBUTION_CAPACITY",
    "DEVELOPED_HISTORICAL_EMISSIONS",
    "DEVELOPING_HISTORICAL_EMISSIONS",
    "DISPLAY_PAST_ACTIONS",
)

#: The one parameter allowed to vary inside a comparison group.
COMPARISON_GROUP_EXCEPTION = "LLM_MODEL"

#: Serving requirements that must match the cell's model declaration. A cell
#: whose served alias disagrees with its checkpoint is silently a different model.
SERVER_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "qwen2.5-14b": {
        "checkpoint": "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4",
        "quantization": "gptq-int4",
        "parameter_count_billions": 14.0,
        "template": "chatml",
        "tensor_parallel": 2,
    },
    "llama-3.1-8b": {
        "checkpoint": "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "quantization": "bnb-4bit",
        "parameter_count_billions": 8.0,
        "template": "chatml",
        "tensor_parallel": 2,
    },
    "mistral-7b": {
        "checkpoint": "TheBloke/Mistral-7B-Instruct-v0.2-GPTQ",
        "quantization": "gptq",
        "parameter_count_billions": 7.0,
        "template": "chatml",
        "tensor_parallel": 2,
    },
}

KNOWN_MODELS = tuple(SERVER_REQUIREMENTS)


class ConfigError(ValueError):
    """Raised for a malformed config, an unknown key, or a parity violation."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Read one YAML cell or preset."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config must be a mapping: {path}")
    data["_source"] = str(path)
    return data


def _get_nested(data: dict[str, Any], dotted: str) -> Any:
    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def flatten(config: dict[str, Any]) -> dict[str, Any]:
    """Resolve a config into flat ``PARAMETER_NAME -> typed value`` assignments.

    The tree is walked with dotted paths, so ``sampling.temperature`` and
    ``ldf.enabled`` address parameters the same way the flat form does.

    Unknown keys are a hard error. A typo'd override that silently no-ops is the
    exact failure mode this layer exists to remove.
    """
    resolved: dict[str, Any] = {}

    def walk(node: dict[str, Any], prefix: str = "") -> None:
        for key, value in node.items():
            if key.startswith("_"):
                continue
            dotted = f"{prefix}.{key}" if prefix else key

            if dotted == "overrides":
                if not isinstance(value, dict):
                    raise ConfigError("'overrides' must be a mapping of PARAMETER -> value")
                for name, raw in value.items():
                    if name not in SPECS_BY_NAME:
                        raise ConfigError(_unknown_message(name, {"__override__": name}))
                    resolved[name] = coerce(name, raw)
                continue

            if dotted == "shocks.schedule":
                resolved["CLIMATE_SHOCK_SCHEDULE"] = _normalise_schedule(value)
                continue

            if dotted == "group_counts":
                if isinstance(value, dict) and {"developed", "developing"} <= set(value):
                    resolved["LDF_AGENT_GROUP_COUNTS"] = {
                        "developed": int(value.get("developed", 0)),
                        "developing": int(value.get("developing", 0)),
                    }
                else:
                    raise ConfigError("'group_counts' needs both 'developed' and 'developing'")
                continue

            if dotted == "sampling.chat_template":
                resolved["CHAT_TEMPLATE_NAME"] = str(value)
                continue

            if isinstance(value, dict):
                if dotted in RESERVED_KEYS and dotted != "overrides":
                    continue
                walk(value, prefix=dotted)
                continue

            if dotted in STRUCTURED_MAP:
                if value is None:
                    continue
                param = STRUCTURED_MAP[dotted]
                resolved[param] = coerce(param, value)
                continue

            if dotted in RESERVED_KEYS:
                continue

            raise ConfigError(_unknown_message(dotted, node))

    walk(config)

    if not resolved:
        raise ConfigError("Config sets no parameters")
    return resolved


def _normalise_schedule(schedule: Any) -> list[tuple[int, float]]:
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ConfigError("'shocks.schedule' must be a non-empty list of [round, severity]")
    out: list[tuple[int, float]] = []
    for entry in schedule:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            round_number, severity = entry
        elif isinstance(entry, dict) and {"round", "severity"} <= set(entry):
            round_number, severity = entry["round"], entry["severity"]
        else:
            raise ConfigError(f"Bad shock schedule entry: {entry!r}")
        out.append((int(round_number), float(severity)))
    return out


def _unknown_message(key: str, context: Any) -> str:
    import difflib

    # Candidates depend on where the key appeared: a bad structured key should be
    # compared against structured keys, a bad override against parameter names.
    if isinstance(context, dict) and not any(
        str(v) == str(key) for v in context.values() if isinstance(v, (int, float, str, bool))
    ):
        candidates = sorted(set(STRUCTURED_MAP) | set(RESERVED_KEYS) | {"overrides"})
        hint_pool = candidates
    else:
        hint_pool = sorted(SPECS_BY_NAME)
        candidates = hint_pool
    close = difflib.get_close_matches(str(key), hint_pool, n=3, cutoff=0.6)
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    return (
        f"Unknown config key {key!r}.{hint}\n"
        f"Structured keys: {', '.join(sorted(STRUCTURED_MAP))}\n"
        f"Reserved keys: {', '.join(sorted(RESERVED_KEYS))}\n"
        f"Any other parameter goes under 'overrides:'."
    )


# ---------------------------------------------------------------------------
# Parity checks
# ---------------------------------------------------------------------------


def condition_key(config: dict[str, Any]) -> str:
    """Identity of the *treatment* a cell implements, ignoring the model.

    Cells that share a condition key are the ones whose cross-model contrast is
    supposed to be a model contrast, so their parity-critical values must match
    exactly. ``LLM_MODEL`` is excluded by construction.
    """
    parts = [
        str(config.get("arm", "")).upper(),
        str(config.get("condition", "")),
    ]
    return "|".join(parts)


def check_grid_parity(configs: list[dict[str, Any]]) -> list[str]:
    """Report every parity-critical parameter that varies inside a condition group.

    This is the check that decides whether ``sigma^2_model`` means "model". It
    runs over a whole grid, because a single cell cannot violate parity on its own.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for config in configs:
        groups.setdefault(condition_key(config), []).append(config)

    violations: list[str] = []
    for key, members in sorted(groups.items()):
        models = {str(m.get("parameters", {}).get(COMPARISON_GROUP_EXCEPTION, "")) for m in members}
        if len(models) < 2:
            # Only one model in the group: nothing to hold constant.
            continue
        for name in PARITY_CRITICAL:
            values = {
                json.dumps(m.get("parameters", {}).get(name), sort_keys=True, default=str)
                for m in members
            }
            if len(values) > 1:
                violations.append(
                    f"condition {key!r}: {name} differs across its models {sorted(models)}; "
                    f"values {sorted(values)}"
                )
    return violations


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise one config, raising on anything fatal."""
    name = str(config.get("name") or "").strip()
    if not name:
        raise ConfigError("Config must declare a 'name'")
    resolved = flatten(config)
    model = str(resolved.get("LLM_MODEL", ""))
    if model and model not in SERVER_REQUIREMENTS:
        raise ConfigError(
            f"Unknown model {model!r}. Known served aliases: {', '.join(KNOWN_MODELS)}"
        )
    return {
        "name": name,
        "arm": str(config.get("arm", "")).upper(),
        "condition": str(config.get("condition", "")),
        "description": str(config.get("description", "")),
        "notes": str(config.get("notes", "")),
        "priority": config.get("priority"),
        "budget_gpu_hours": config.get("budget_gpu_hours"),
        "parameters": resolved,
        "seed_vector": config.get("seed_vector"),
        "source": config.get("_source"),
    }


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


def _preset(
    name: str,
    arm: str,
    model: str,
    prompt_variant: str,
    *,
    seeds: int = 4,
    description: str = "",
    condition: str = "",
    **overrides: Any,
) -> dict[str, Any]:
    """One family of cells: a condition crossed with ``seeds`` independent draws.

    ``condition`` names the treatment the cell implements. Cells sharing a
    condition across different models are a comparison group, and their
    parity-critical parameters are asserted identical by
    :func:`check_grid_parity`.
    """
    return {
        "name": name,
        "arm": arm,
        "condition": condition or name.rsplit("_", 1)[0],
        "model": model,
        "prompt_variant": prompt_variant,
        "description": description,
        "seeds": seeds,
        "overrides": overrides,
    }


def preset(name: str) -> dict[str, Any] | None:
    """Look up a named preset, or return ``None``."""
    return PRESETS.get(name)


def preset_names() -> list[str]:
    return sorted(PRESETS)


#: Parameter parity baseline (§8.2.1). Every arm starts from these values and the
#: only thing that varies is the factor under test. Chat template is fixed so the
#: rendered prompt is byte-identical across model families.
def _baseline() -> dict[str, Any]:
    return {
        "SCENARIO": "ldf",
        "NUM_ROUNDS": 30,
        "NUM_AGENTS": 26,
        "CLIMATE_SHOCK_ENABLED": True,
        "CLIMATE_SHOCK_DETERMINISTIC": True,
        "CLIMATE_SHOCK_SCHEDULE": [(7, 0.10), (17, 0.20)],
        "LDF_ENABLED": True,
        "LDF_GOVERNANCE_MODE": "fixed",
        "LDF_ALLOCATION_RULE": "damage_proportional",
        "PUBLIC_GOOD_MULTIPLIER": 1.6,
        "TOM_ENABLED": False,
        "GOSSIP_ENABLED": True,
        "DEMOCRACY_ENABLED": True,
        "DEMOCRACY_INTERVAL": 5,
        "CHAT_TEMPLATE_MODE": "fixed",
        "CHAT_TEMPLATE_NAME": "chatml",
        "LLM_TEMPERATURE": 0.7,
        "LLM_TOP_P": 0.9,
        "VLLM_MAX_MODEL_LEN": 8192,
        "CONTRIBUTION_CAPACITY_ENABLED": True,
    }


#: Named presets. The 140-run grid is a list of these, not 140 command lines.
#:
#: Arm A is the paper: 3 model families x 3 prompt variants x 4 seeds. Arm B buys
#: identification with control conditions. Arm C is the theory test. Arm D makes
#: redistribution endogenous at four governance levels. Arm E is the ToM
#: confound control and is the first thing to cut.
PRESETS: dict[str, dict[str, Any]] = {}

for _model, _short in (
    ("qwen2.5-14b", "qwen"),
    ("llama-3.1-8b", "llama"),
    ("mistral-7b", "mistral"),
):
    for _variant, _short_variant in (
        ("P0_canonical", "p0"),
        ("P1_lexical", "p1"),
        ("P2_minimal_control", "p2"),
    ):
        _baseline_name = _baseline()
        PRESETS[f"a_{_short}_{_short_variant}"] = _preset(
            f"arm_a_{_short_variant}_{_short}",
            "A",
            _model,
            _variant,
            seeds=4,
            # The comparison group is the prompt variant: within it, only the
            # model changes, so any parameter difference inside the group is a
            # parity violation.
            condition=f"A|variant={_variant}",
            description=(f"Arm A: {_model} x {_variant}, canonical Full-LDF condition, ToM off."),
            **{k: v for k, v in _baseline_name.items() if k not in {"NUM_ROUNDS"}},
            NUM_ROUNDS=30,
        )

for _model, _short in (("qwen2.5-14b", "qwen"), ("llama-3.1-8b", "llama")):
    PRESETS[f"b_full_{_short}"] = _preset(
        f"arm_b_full_{_short}",
        "B",
        _model,
        "P0_canonical",
        seeds=4,
        condition="B|cond=full",
        description="Arm B reference: shocks + LDF + enforcement.",
        **(_baseline()),
    )
    PRESETS[f"b_noldf_{_short}"] = _preset(
        f"arm_b_noldf_{_short}",
        "B",
        _model,
        "P0_canonical",
        seeds=4,
        condition="B|cond=no_ldf",
        description="Arm B control: shocks on, LDF off.",
        **{**_baseline(), "LDF_ENABLED": False},
    )
    PRESETS[f"b_noshock_{_short}"] = _preset(
        f"arm_b_noshock_{_short}",
        "B",
        _model,
        "P0_canonical",
        seeds=4,
        condition="B|cond=no_shock",
        description="Arm B control: LDF on, no shocks.",
        **{**_baseline(), "CLIMATE_SHOCK_ENABLED": False},
    )
    PRESETS[f"b_noenf_{_short}"] = _preset(
        f"arm_b_noenf_{_short}",
        "B",
        _model,
        "P0_canonical",
        seeds=4,
        condition="B|cond=no_enforcement",
        description="Arm B control: shocks + LDF, Stage-2 enforcement disabled.",
        **{**_baseline(), "PUNISHMENT_EFFECT": 0.0},
    )

# Arm C: MCPR sweep. n=14 halves the quadratic term; beta spans 0.4..20 so the
# design brackets MCPR = 1 (beta = n) and therefore contains a real prediction
# test rather than only describing a sub-threshold regime.
for _model, _short in (("qwen2.5-14b", "qwen"), ("llama-3.1-8b", "llama")):
    for _beta in (0.4, 0.8, 1.0, 1.2, 1.6, 2.4, 14.0, 20.0):
        _tag = f"{_beta:g}".replace(".", "p")
        PRESETS[f"c_beta{_tag}_{_short}"] = _preset(
            f"arm_c_beta{_tag}_{_short}",
            "C",
            _model,
            "P0_canonical",
            seeds=4,
            condition=f"C|beta={_beta:g}|n=14",
            description=(
                f"Arm C: n=14, beta={_beta}, MCPR={_beta / 14:.3f}"
                f"{' (threshold)' if _beta >= 14 else ''}."
            ),
            **{
                **_baseline(),
                "NUM_AGENTS": 14,
                "PUBLIC_GOOD_MULTIPLIER": _beta,
                "LDF_AGENT_GROUP_COUNTS": {"developed": 6, "developing": 8},
            },
        )

# Arm D: endogenous redistribution, G0..G3c. G0 is Arm A's P0 cell and is not
# re-run here, which is why the governance arm is cheap: the reference arm is
# already paid for.
for _model, _short in (
    ("qwen2.5-14b", "qwen"),
    ("llama-3.1-8b", "llama"),
    ("mistral-7b", "mistral"),
):
    PRESETS[f"d_g1_{_short}"] = _preset(
        f"arm_d_g1_{_short}",
        "D",
        _model,
        "P0_canonical",
        seeds=3,
        condition="D|level=G1",
        description="Arm D G1: assembly elects the LDF allocation rule (D4, zero extra calls).",
        **{**_baseline(), "LDF_GOVERNANCE_MODE": "election"},
    )
    PRESETS[f"d_g2_{_short}"] = _preset(
        f"arm_d_g2_{_short}",
        "D",
        _model,
        "P0_canonical",
        seeds=3,
        condition="D|level=G2",
        description="Arm D G2: elected rule plus an elected payout board (D5).",
        **{**_baseline(), "LDF_GOVERNANCE_MODE": "election+board"},
    )
    PRESETS[f"d_g3_{_short}"] = _preset(
        f"arm_d_g3_{_short}",
        "D",
        _model,
        "P0_canonical",
        seeds=3,
        condition="D|level=G3",
        description="Arm D G3: full governance including peer-adjudicated claims (D6).",
        **{**_baseline(), "LDF_GOVERNANCE_MODE": "full"},
    )
PRESETS["d_g3c_qwen"] = _preset(
    "arm_d_g3c_qwen",
    "D",
    "qwen2.5-14b",
    "P0_canonical",
    seeds=3,
    condition="D|level=G3c",
    description="Arm D G3c control: claim machinery on, adjudication forced to accept all.",
    **{**_baseline(), "LDF_GOVERNANCE_MODE": "full", "LDF_BOARD_ALWAYS_ACCEPTS": True},
)

# Arm E: ToM confound control. Optional, and the first thing to cut.
for _model, _short in (("qwen2.5-14b", "qwen"),):
    PRESETS[f"e_tom_{_short}"] = _preset(
        f"arm_e_tom_{_short}",
        "E",
        _model,
        "P0_canonical",
        seeds=2,
        condition="E|tom=on",
        description="Arm E: ToM restored, to show the audit's conclusions survive it.",
        **{**_baseline(), "TOM_ENABLED": True},
    )

del _model, _short, _variant, _short_variant, _tag, _baseline_name


# ---------------------------------------------------------------------------
# Cell expansion
# ---------------------------------------------------------------------------


def expand_preset(name: str, seeds: int | None = None) -> list[dict[str, Any]]:
    """Turn a preset into one cell per seed, each with a complete seed vector."""
    from core.seeding import build_seed_vector

    spec = preset(name)
    if spec is None:
        raise ConfigError(f"Unknown preset {name!r}. Run `elicit preset list` to see the registry.")
    n_seeds = int(seeds if seeds is not None else spec.get("seeds", 1))
    overrides = dict(spec.get("overrides") or {})
    group_counts = overrides.pop("LDF_AGENT_GROUP_COUNTS", None)

    cells: list[dict[str, Any]] = []
    for seed_index in range(1, n_seeds + 1):
        cell: dict[str, Any] = {
            "name": f"{spec['name']}_s{seed_index}",
            "arm": spec["arm"],
            "condition": spec.get("condition", spec["name"]),
            "description": spec.get("description", ""),
            "model": spec["model"],
            "prompt_variant": spec["prompt_variant"],
            "preset": name,
            "seed_index": seed_index,
            "overrides": copy.deepcopy(overrides),
        }
        if group_counts is not None:
            cell["group_counts"] = dict(group_counts)
        cells.append(cell)

    # Seed vectors are derived per cell so the declared sampling is used, and
    # every cell in the grid carries a distinct, complete vector.
    resolved_overrides = {name_: coerce(name_, value) for name_, value in overrides.items()}
    base_seed_from = int(resolved_overrides.get("SEED", 42))
    for index, cell in enumerate(cells, start=1):
        base_seed = base_seed_from + 1000 * index
        sampling = {
            "temperature": resolved_overrides.get("LLM_TEMPERATURE", 0.7),
            "top_p": resolved_overrides.get("LLM_TOP_P", 0.9),
            "min_p": resolved_overrides.get("LLM_MIN_P", 0.0),
            "repetition_penalty": resolved_overrides.get("LLM_REPETITION_PENALTY", 1.0),
            "max_model_len": resolved_overrides.get("VLLM_MAX_MODEL_LEN", 8192),
        }
        n_agents = int(
            (cell.get("group_counts") or {}).get("developed", 0)
            + (cell.get("group_counts") or {}).get("developing", 0)
            or resolved_overrides.get("NUM_AGENTS", 26)
        )
        vector = build_seed_vector({"seed": base_seed, "agents": n_agents, "sampling": sampling})
        cell["seed_vector"] = vector
        cell["seed"] = base_seed
    return cells

"""Typed, range-checked registry for every tunable simulation parameter.

Three consumers depend on this module and nothing else:

* ``elicit params`` prints it, so the terminal view of the configuration and the
  docs cannot drift apart.
* ``elicit run --set KEY=VALUE`` and the YAML config layer coerce and range-check
  against it, so a typo'd override fails loudly instead of silently no-opping.
* ``tests/test_parameter_integrity.py`` walks it to assert that every parameter is
  *read* somewhere outside its own definition. That is the structural fix for the
  "decorative parameter" defect: a parameter that is stored, logged and prompted
  but never enters a payoff is a referee finding waiting to happen.

The registry is deliberately a plain tuple of specs rather than a dataclass on
``parameters`` itself: ``parameters`` stays a mutable module of globals that the
democracy module writes into, and this file only describes it.
"""

from __future__ import annotations

import ast
import difflib
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).resolve().parent.parent


class ParameterError(ValueError):
    """Raised when an override names an unknown parameter or fails range checks."""


class ParameterSpec:
    """One tunable parameter: its identity, type, admissible range and meaning."""

    __slots__ = ("category", "default", "description", "maximum", "minimum", "name", "type_name")

    def __init__(
        self,
        name: str,
        category: str,
        type_name: str,
        default: Any,
        minimum: Any,
        maximum: Any,
        description: str,
    ) -> None:
        self.name = name
        self.category = category
        self.type_name = type_name
        self.default = default
        self.minimum = minimum
        self.maximum = maximum
        self.description = description

    @property
    def is_categorical(self) -> bool:
        return self.type_name == "choice"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"ParameterSpec({self.name!r}, {self.type_name!r}, "
            f"range=({self.minimum!r}, {self.maximum!r}))"
        )


def _s(name, category, type_name, default, minimum, maximum, description) -> ParameterSpec:
    return ParameterSpec(name, category, type_name, default, minimum, maximum, description)


# ``minimum``/``maximum`` are inclusive where meaningful. ``None`` means unbounded
# on that side. ``choice`` specs use minimum=None, maximum=None and list the legal
# values in ``description``.
SPECS: tuple[ParameterSpec, ...] = (
    # --- Simulation ---
    _s("NUM_AGENTS", "simulation", "int", 7, 2, 200, "Number of agents in the simulation."),
    _s("NUM_ROUNDS", "simulation", "int", 30, 1, 200, "Number of rounds per run."),
    _s("SEED", "simulation", "int", 42, 0, 2**31 - 1, "Python RNG seed (see SEED_VECTOR)."),
    _s(
        "SEED_VECTOR_REQUIRED",
        "simulation",
        "bool",
        True,
        None,
        None,
        "Refuse runs with an incomplete seed vector.",
    ),
    _s(
        "SCENARIO",
        "simulation",
        "choice",
        "abstract",
        None,
        None,
        "Prompt scenario: abstract | ldf | tax.",
    ),
    _s(
        "AGENT_TYPE",
        "simulation",
        "choice",
        "LLM",
        None,
        None,
        "Control baseline: LLM | Random | Greedy.",
    ),
    _s(
        "BATCH_NAME",
        "simulation",
        "str",
        "Control",
        None,
        None,
        "Experiment batch label used in run filenames.",
    ),
    # --- LLM backend ---
    _s(
        "LLM_MODEL",
        "llm",
        "str",
        "qwen2.5-14b",
        None,
        None,
        "Served model name; must match --served-model-name.",
    ),
    _s(
        "LLM_BASE_URL",
        "llm",
        "str",
        "http://localhost:8000/v1",
        None,
        None,
        "OpenAI-compatible endpoint.",
    ),
    _s("LLM_BACKEND", "llm", "choice", "vllm", None, None, "Backend: vllm | ollama."),
    _s(
        "LLM_REQUEST_TIMEOUT_SECONDS",
        "llm",
        "float",
        300.0,
        1.0,
        3600.0,
        "Per-request HTTP timeout.",
    ),
    _s(
        "LLM_MAX_ATTEMPTS",
        "llm",
        "int",
        3,
        1,
        20,
        "Total transport attempts including the first call.",
    ),
    _s(
        "LLM_DECISION_MAX_ATTEMPTS",
        "llm",
        "int",
        2,
        1,
        20,
        "Send+parse attempts for most agent decisions.",
    ),
    _s(
        "LLM_PUNISHMENT_MAX_ATTEMPTS",
        "llm",
        "int",
        1,
        1,
        20,
        "Attempts for Stage-2 punishment decisions.",
    ),
    _s(
        "BELIEF_UPDATE_MAX_TOKENS",
        "llm",
        "int",
        256,
        32,
        8192,
        "Output budget for belief-state JSON.",
    ),
    _s("LLM_MAX_CONCURRENCY", "llm", "int", 8, 1, 256, "Thread-pool workers for decision stages."),
    _s(
        "TOM_MAX_CONCURRENCY",
        "llm",
        "int",
        24,
        1,
        256,
        "Thread-pool workers for pairwise ToM audits.",
    ),
    _s(
        "DEMOCRACY_MAX_CONCURRENCY",
        "llm",
        "int",
        8,
        1,
        256,
        "Thread-pool workers for constitutional sessions.",
    ),
    _s(
        "VLLM_MAX_CONCURRENCY",
        "llm",
        "int",
        24,
        1,
        256,
        "Client in-flight ceiling; keep <= server --max-num-seqs.",
    ),
    # --- Sampling ---
    _s(
        "LLM_TEMPERATURE",
        "sampling",
        "float",
        0.7,
        0.0,
        2.0,
        "Default-persona sampling temperature.",
    ),
    _s("LLM_TOP_P", "sampling", "float", 0.9, 0.0, 1.0, "Default-persona nucleus sampling mass."),
    _s("LLM_MIN_P", "sampling", "float", 0.0, 0.0, 1.0, "Default-persona min-p truncation."),
    _s(
        "LLM_REPETITION_PENALTY",
        "sampling",
        "float",
        1.0,
        0.5,
        2.0,
        "Default-persona repetition penalty.",
    ),
    _s("LLM_SEED", "sampling", "int", 42, 0, 2**31 - 1, "Seed handed to the inference backend."),
    _s(
        "CHAT_TEMPLATE_MODE",
        "sampling",
        "choice",
        "server",
        None,
        None,
        "server | fixed (render chat template in Python).",
    ),
    _s(
        "CHAT_TEMPLATE_NAME",
        "sampling",
        "str",
        "chatml",
        None,
        None,
        "Template used when CHAT_TEMPLATE_MODE == 'fixed'.",
    ),
    # --- Endowments ---
    _s(
        "INITIAL_TOKENS",
        "endowments",
        "float",
        1000.0,
        0.0,
        None,
        "Starting tokens per agent in abstract mode.",
    ),
    _s(
        "ENDOWMENT_STAGE_1",
        "endowments",
        "float",
        20.0,
        0.0,
        None,
        "Tokens per agent per round at Stage 1.",
    ),
    _s(
        "ENDOWMENT_STAGE_2",
        "endowments",
        "float",
        20.0,
        0.0,
        None,
        "Tokens per agent per round at Stage 2.",
    ),
    _s(
        "STAGE_2_WEALTH_FRACTION",
        "endowments",
        "float",
        0.05,
        0.0,
        1.0,
        "Climate-mode Stage-2 budget as a fraction of wealth.",
    ),
    # --- Public goods ---
    _s(
        "PUBLIC_GOOD_MULTIPLIER",
        "public_goods",
        "float",
        1.6,
        0.0,
        100.0,
        "Public-good multiplier beta; MCPR = beta / group size.",
    ),
    _s(
        "MIN_CONTRIBUTION", "public_goods", "float", 0.0, 0.0, None, "Minimum Stage-1 contribution."
    ),
    # --- Sanctions ---
    _s(
        "PUNISHMENT_EFFECT",
        "sanctions",
        "float",
        3.0,
        0.0,
        100.0,
        "Payoff reduction per unit of punishment assigned.",
    ),
    _s(
        "PUNISHMENT_COST",
        "sanctions",
        "float",
        1.0,
        0.0,
        100.0,
        "Sender cost per unit of punishment assigned.",
    ),
    _s(
        "REWARD_EFFECT",
        "sanctions",
        "float",
        1.0,
        0.0,
        100.0,
        "Payoff increase per unit of reward assigned.",
    ),
    _s(
        "REWARD_COST",
        "sanctions",
        "float",
        1.0,
        0.0,
        100.0,
        "Sender cost per unit of reward assigned.",
    ),
    _s(
        "RULE_OF_LAW_ENABLED",
        "sanctions",
        "bool",
        False,
        None,
        None,
        "Block punishments of above-average contributors.",
    ),
    # --- Information / modules ---
    _s(
        "ANONYMITY",
        "modules",
        "bool",
        False,
        None,
        None,
        "Mask peer identity with stable pseudonyms.",
    ),
    _s(
        "DISPLAY_PAST_ACTIONS",
        "modules",
        "int",
        1,
        1,
        30,
        "Rounds of peer data retained for prompts.",
    ),
    _s(
        "BELIEF_TRACKING_ENABLED",
        "modules",
        "bool",
        True,
        None,
        None,
        "Structured belief-state updates after each round.",
    ),
    _s(
        "TOM_ENABLED",
        "modules",
        "bool",
        True,
        None,
        None,
        "Pairwise Theory-of-Mind audits each round.",
    ),
    _s(
        "TOM_VERBOSE",
        "modules",
        "bool",
        True,
        None,
        None,
        "Log every published trust score to the terminal.",
    ),
    _s("TOM_MAX_ATTEMPTS", "modules", "int", 2, 1, 20, "Attempts per evaluator-target ToM score."),
    _s(
        "DEMOCRACY_ENABLED",
        "modules",
        "bool",
        True,
        None,
        None,
        "Constitutional sessions every DEMOCRACY_INTERVAL rounds.",
    ),
    _s("DEMOCRACY_INTERVAL", "modules", "int", 5, 1, 100, "Rounds between constitutional votes."),
    _s(
        "GOSSIP_ENABLED",
        "modules",
        "bool",
        True,
        None,
        None,
        "Publish low-trust ToM scores as social pressure.",
    ),
    _s(
        "GOSSIP_TRIGGER_SCORE",
        "modules",
        "float",
        7.0,
        0.0,
        10.0,
        "Only share gossip for trust scores at or below this.",
    ),
    _s("MAX_GOSSIP_ITEMS", "modules", "int", 5, 1, 50, "Maximum gossip items per bulletin."),
    # --- Oracle ---
    _s(
        "ORACLE_PUNISHMENT_WEIGHT",
        "oracle",
        "float",
        1.5,
        0.0,
        100.0,
        "Heuristic weight on free-rider rate for punishment proposals.",
    ),
    _s(
        "ORACLE_REWARD_WEIGHT",
        "oracle",
        "float",
        1.2,
        0.0,
        100.0,
        "Heuristic weight on cooperation rate for reward proposals.",
    ),
    _s(
        "ORACLE_ENDOWMENT_SCALING",
        "oracle",
        "float",
        50.0,
        0.0,
        1000.0,
        "Heuristic scaling for Stage-2 endowment proposals.",
    ),
    # --- Subsidy / curiosity ---
    _s(
        "SUBSIDY_ENABLED",
        "subsidy",
        "bool",
        True,
        None,
        None,
        "Redistribute part of the punishment pool to top contributors.",
    ),
    _s(
        "SUBSIDY_FRACTION",
        "subsidy",
        "float",
        0.2,
        0.0,
        1.0,
        "Share of SI punishment costs pooled for subsidy.",
    ),
    _s(
        "SUBSIDY_TOP_N",
        "subsidy",
        "int",
        2,
        1,
        26,
        "Number of top SI contributors sharing the subsidy pool.",
    ),
    _s(
        "CURIOSITY_ENABLED",
        "subsidy",
        "bool",
        False,
        None,
        None,
        "Suggest unexplored parameters in proposals.",
    ),
    _s(
        "CURIOSITY_BONUS_PROMPT",
        "subsidy",
        "bool",
        False,
        None,
        None,
        "Inject novelty suggestions into decision prompts.",
    ),
    # --- Output / measurement ---
    _s("SAVE_RESULTS", "output", "bool", True, None, None, "Write results JSON after the run."),
    _s("VERBOSE", "output", "bool", True, None, None, "Print round-by-round logs."),
    _s(
        "RESULTS_SPILL_TO_DISK",
        "output",
        "bool",
        True,
        None,
        None,
        "Spill full round JSON to disk and slim in RAM.",
    ),
    _s(
        "DEBUG_LLM_IO",
        "output",
        "bool",
        False,
        None,
        None,
        "Write per-decision prompt/response JSON (very large).",
    ),
    _s(
        "TRACE_ENABLED",
        "output",
        "bool",
        True,
        None,
        None,
        "Write sampled deliberation traces to a sidecar file.",
    ),
    _s(
        "TRACE_SAMPLING_RATE",
        "output",
        "float",
        0.05,
        0.0,
        1.0,
        "Share of decisions recorded in the trace sidecar.",
    ),
    _s("TRACE_MAX_RECORDS", "output", "int", 20000, 1, 10**7, "Hard cap on trace records per run."),
    _s(
        "LOG_START_OF_ROUND_WEALTH",
        "output",
        "bool",
        True,
        None,
        None,
        "Record pre-decision wealth so the intensity cap needs no reconstruction.",
    ),
    _s(
        "LOG_GOSSIP_EXPOSURE",
        "output",
        "bool",
        True,
        None,
        None,
        "Record the live gossip bulletin and its exact recipient list.",
    ),
    _s(
        "LOG_TOM_COMPLETION_ORDER",
        "output",
        "bool",
        True,
        None,
        None,
        "Record concurrent ToM completion order.",
    ),
    _s(
        "RAW_ALLOCATION_REPORTING",
        "output",
        "bool",
        True,
        None,
        None,
        "Keep raw requested Stage-2 allocations alongside the applied ones.",
    ),
    # --- Heterogeneous climate economy ---
    _s(
        "DEVELOPED_VULNERABILITY",
        "climate",
        "float",
        0.30,
        0.0,
        10.0,
        "Climate-damage vulnerability of developed-country agents.",
    ),
    _s(
        "DEVELOPING_VULNERABILITY",
        "climate",
        "float",
        1.50,
        0.0,
        10.0,
        "Climate-damage vulnerability of developing-country agents.",
    ),
    _s(
        "DEVELOPED_HISTORICAL_EMISSIONS",
        "climate",
        "float",
        1.50,
        0.0,
        10.0,
        "Historical-emissions index; cbdr payout weight.",
    ),
    _s(
        "DEVELOPING_HISTORICAL_EMISSIONS",
        "climate",
        "float",
        0.30,
        0.0,
        10.0,
        "Historical-emissions index; cbdr payout weight.",
    ),
    _s(
        "DEVELOPED_CONTRIBUTION_CAPACITY",
        "climate",
        "float",
        1.00,
        0.0,
        10.0,
        "Contribution capacity; Stage-1 cap multiplier.",
    ),
    _s(
        "DEVELOPING_CONTRIBUTION_CAPACITY",
        "climate",
        "float",
        0.10,
        0.0,
        10.0,
        "Contribution capacity; Stage-1 cap multiplier.",
    ),
    _s(
        "CONTRIBUTION_CAPACITY_ENABLED",
        "climate",
        "bool",
        True,
        None,
        None,
        "Let contribution capacity scale the Stage-1 cap.",
    ),
    _s(
        "CONTRIBUTION_CAPACITY_FLOOR",
        "climate",
        "float",
        0.0,
        0.0,
        1.0,
        "Floor on the capacity multiplier so the cap cannot vanish.",
    ),
    _s("CLIMATE_SHOCK_ENABLED", "climate", "bool", False, None, None, "Enable climate shocks."),
    _s(
        "CLIMATE_SHOCK_BASE_PROB",
        "climate",
        "float",
        0.20,
        0.0,
        1.0,
        "Stochastic shock probability per round.",
    ),
    _s(
        "CLIMATE_SHOCK_SEVERITY_MIN",
        "climate",
        "float",
        0.05,
        0.0,
        1.0,
        "Minimum stochastic shock severity.",
    ),
    _s(
        "CLIMATE_SHOCK_SEVERITY_MAX",
        "climate",
        "float",
        0.25,
        0.0,
        1.0,
        "Maximum stochastic shock severity.",
    ),
    _s(
        "CLIMATE_DAMAGE_BASE",
        "climate",
        "float",
        150000.0,
        0.0,
        None,
        "Damage scale before severity x vulnerability.",
    ),
    _s(
        "CLIMATE_SHOCK_DETERMINISTIC",
        "climate",
        "bool",
        True,
        None,
        None,
        "Use CLIMATE_SHOCK_SCHEDULE instead of the stochastic roll.",
    ),
    _s(
        "CLIMATE_SHOCK_SCHEDULE",
        "climate",
        "schedule",
        [(7, 0.10), (17, 0.20)],
        None,
        None,
        "Deterministic shocks as (round, severity) pairs. Decoupled from DEMOCRACY_INTERVAL.",
    ),
    # --- Loss & Damage Fund ---
    _s("LDF_ENABLED", "ldf", "bool", False, None, None, "Enable the Loss & Damage Fund."),
    _s(
        "LDF_COLLECT_EVERY_ROUND",
        "ldf",
        "bool",
        True,
        None,
        None,
        "Collect contributions every round rather than every interval.",
    ),
    _s(
        "LDF_REPLENISHMENT_INTERVAL",
        "ldf",
        "int",
        5,
        1,
        100,
        "Round interval between collections when not every round.",
    ),
    _s(
        "LDF_PAYOUT_DAMAGE_WEIGHT",
        "ldf",
        "float",
        1.0,
        0.0,
        10.0,
        "How strongly damage drives the payout weight.",
    ),
    _s(
        "LDF_MAX_COVERAGE",
        "ldf",
        "float",
        0.90,
        0.0,
        1.0,
        "Cap on the fraction of damage a single payout may cover.",
    ),
    _s(
        "LDF_EQUITY_WEIGHT",
        "ldf",
        "float",
        0.0,
        0.0,
        10.0,
        "Wealth-tilt applied inside the fixed rule; live under poverty_tilted.",
    ),
    # --- Endogenous redistribution governance ---
    _s(
        "LDF_GOVERNANCE_MODE",
        "governance",
        "choice",
        "fixed",
        None,
        None,
        "fixed | election | election+board | full.",
    ),
    _s(
        "LDF_ALLOCATION_RULE",
        "governance",
        "choice",
        "damage_proportional",
        None,
        None,
        "Named rule from core.allocation_rules.",
    ),
    _s(
        "LDF_BOARD_DEVELOPED_SEATS",
        "governance",
        "int",
        3,
        0,
        26,
        "Developed-country seats on the rotating payout board.",
    ),
    _s(
        "LDF_BOARD_DEVELOPING_SEATS",
        "governance",
        "int",
        3,
        0,
        26,
        "Developing-country seats on the rotating payout board.",
    ),
    _s(
        "LDF_CLAIM_ACCEPT_FRACTION",
        "governance",
        "float",
        2.0 / 3.0,
        0.0,
        1.0,
        "Adjudicator acceptance share required to pay a claim.",
    ),
    _s(
        "LDF_BOARD_ALWAYS_ACCEPTS",
        "governance",
        "bool",
        False,
        None,
        None,
        "G3c control: accept every filed claim.",
    ),
    _s(
        "LDF_AGENT_GROUP_COUNTS",
        "climate",
        "group_counts",
        {"developed": 12, "developing": 14},
        None,
        None,
        "Head-count split of the LDF population into developed and developing agents.",
    ),
    # --- Provenance ---
    _s(
        "MODEL_CHECKPOINT",
        "provenance",
        "str",
        "",
        None,
        None,
        "Hugging Face checkpoint id actually served.",
    ),
    _s(
        "MODEL_QUANTIZATION",
        "provenance",
        "str",
        "",
        None,
        None,
        "Quantisation of the served artefact.",
    ),
    _s(
        "MODEL_PARAM_COUNT_B",
        "provenance",
        "float",
        0.0,
        0.0,
        1000.0,
        "Nominal parameter count in billions.",
    ),
    _s("VLLM_VERSION", "provenance", "str", "", None, None, "vLLM version of the serving engine."),
    _s("VLLM_SERVE_FLAGS", "provenance", "str", "", None, None, "Verbatim server flags."),
    _s("VLLM_MAX_MODEL_LEN", "provenance", "int", 8192, 512, 131072, "Server --max-model-len."),
    _s(
        "PROMPT_VARIANT",
        "provenance",
        "choice",
        "P0_canonical",
        None,
        None,
        "Prompt registry variant in use.",
    ),
    _s(
        "PROMPT_VARIANT_HASH",
        "provenance",
        "str",
        "",
        None,
        None,
        "SHA-256 of the rendered variant registry (set at run time).",
    ),
)

SPECS_BY_NAME: dict[str, ParameterSpec] = {spec.name: spec for spec in SPECS}


def iter_specs(category: str | None = None) -> Iterator[ParameterSpec]:
    """Yield specs, optionally filtered to one category."""
    for spec in SPECS:
        if category is None or spec.category == category:
            yield spec


def spec_names() -> list[str]:
    return [spec.name for spec in SPECS]


def get_spec(name: str) -> ParameterSpec:
    """Return a spec or raise :class:`ParameterError` with a did-you-mean hint."""
    try:
        return SPECS_BY_NAME[name]
    except KeyError:
        close = difflib.get_close_matches(name, SPECS_BY_NAME, n=3, cutoff=0.6)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        raise ParameterError(f"Unknown parameter {name!r}.{hint}") from None


_CHOICE_ALIASES: dict[str, tuple[str, ...]] = {
    "SCENARIO": ("abstract", "ldf", "climate", "tax"),
    "AGENT_TYPE": ("LLM", "Random", "Greedy", "RANDOM", "GREEDY"),
    "LLM_BACKEND": ("vllm", "ollama"),
    "CHAT_TEMPLATE_MODE": ("server", "fixed"),
    "LDF_GOVERNANCE_MODE": ("fixed", "election", "election+board", "full"),
}


def _parse_bool(raw: Any, name: str) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ParameterError(f"{name}: expected a boolean, got {raw!r}")


def _coerce_schedule(name: str, raw: Any) -> list[tuple[int, float]]:
    """Normalise a shock schedule to ``[(round, severity), ...]``.

    Accepts ``[[7, 0.10], ...]``, ``[(7, 0.10), ...]`` and the YAML mapping form
    ``[{round: 7, severity: 0.10}, ...]`` so a cell can be written the way it
    reads best.
    """
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ParameterError(f"{name}: expected a non-empty list of [round, severity]")
    out: list[tuple[int, float]] = []
    for entry in raw:
        if isinstance(entry, dict) and {"round", "severity"} <= set(entry):
            round_number, severity = entry["round"], entry["severity"]
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            round_number, severity = entry
        else:
            raise ParameterError(f"{name}: bad schedule entry {entry!r}")
        try:
            round_int = int(round_number)
            severity_float = float(severity)
        except (TypeError, ValueError) as exc:
            raise ParameterError(f"{name}: non-numeric schedule entry {entry!r}") from exc
        if round_int < 1:
            raise ParameterError(f"{name}: round must be >= 1, got {round_int}")
        if not 0.0 <= severity_float <= 1.0:
            raise ParameterError(f"{name}: severity must be in [0, 1], got {severity_float}")
        out.append((round_int, severity_float))
    return out


def _coerce_group_counts(name: str, raw: Any) -> dict[str, int]:
    """Validate a developed/developing head-count split."""
    if not isinstance(raw, dict) or {"developed", "developing"} - set(raw):
        raise ParameterError(f"{name}: expected both 'developed' and 'developing' keys")
    try:
        developed = int(raw["developed"])
        developing = int(raw["developing"])
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"{name}: head counts must be integers") from exc
    if developed < 0 or developing < 0:
        raise ParameterError(f"{name}: head counts must be non-negative")
    if developed + developing < 2:
        raise ParameterError(f"{name}: need at least 2 agents in total")
    return {"developed": developed, "developing": developing}


def coerce(name: str, raw: Any) -> Any:
    """Coerce ``raw`` to the spec's type and enforce its range.

    Raises :class:`ParameterError` with an actionable message on unknown keys,
    unparseable values and out-of-range values.
    """
    spec = get_spec(name)
    if spec.type_name == "bool":
        return _parse_bool(raw, name)

    if spec.type_name == "schedule":
        return _coerce_schedule(name, raw)

    if spec.type_name == "group_counts":
        return _coerce_group_counts(name, raw)

    if spec.type_name == "choice":
        legal = _CHOICE_ALIASES.get(name, ())
        text = str(raw).strip()
        for candidate in legal:
            if text == candidate:
                return candidate
        if legal:
            lowered = {c.lower(): c for c in legal}
            if text.lower() in lowered:
                return lowered[text.lower()]
            raise ParameterError(f"{name}: {raw!r} is not one of {', '.join(sorted(legal))}")
        return text

    value: float
    if spec.type_name == "int":
        try:
            # int, not float: a float-typed NUM_AGENTS breaks `range(NUM_AGENTS)`
            # in the pseudonym mapping, which is how an int spec silently
            # becomes a runtime crash downstream.
            integer = int(float(raw))
        except (TypeError, ValueError) as exc:
            raise ParameterError(f"{name}: expected an integer, got {raw!r}") from exc
        value = integer
    elif spec.type_name == "float":
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ParameterError(f"{name}: expected a number, got {raw!r}") from exc
    else:  # str
        return str(raw)

    if spec.minimum is not None and value < spec.minimum:
        raise ParameterError(f"{name}: {value} is below the minimum {spec.minimum}")
    if spec.maximum is not None and value > spec.maximum:
        raise ParameterError(f"{name}: {value} is above the maximum {spec.maximum}")
    return value


# ---------------------------------------------------------------------------
# Read detection — the structural guard against decorative parameters
# ---------------------------------------------------------------------------


def _iter_source_files(root: Path | None = None) -> Iterable[Path]:
    root = root or SRC_ROOT
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or ".egg-info" in path.parts:
            continue
        yield path


def _direct_from_import_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.parameters":
            names.update(alias.name for alias in node.names)
    return names


def collect_parameter_reads(root: Path | None = None) -> dict[str, set[str]]:
    """Map each parameter name to the files that read it.

    A parameter counts as *read* when some module other than ``parameters.py``
    dereferences it — either as ``parameters.NAME`` (including inside
    ``getattr(parameters, "NAME")``) or via ``from core.parameters import NAME``.
    Assigning to ``parameters.NAME`` is a write, not a read, and is excluded.
    """
    root = root or SRC_ROOT
    reads: dict[str, set[str]] = {name: set() for name in SPECS_BY_NAME}
    for path in _iter_source_files(root):
        if path.name == "parameters.py":
            continue
        try:
            # utf-8-sig: a stray BOM must not make a file invisible to the
            # integrity check, which is how two unreadable parameters hid here.
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except OSError as exc:  # pragma: no cover - unreadable file
            raise ParameterError(
                f"Cannot read source file for the parameter audit: {path}"
            ) from exc
        rel = str(path.relative_to(root))
        local = set()
        for node in ast.walk(tree):
            # getattr(parameters, "NAME") — a read regardless of the default.
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
            ):
                target = node.args[0]
                attr = node.args[1]
                if (
                    isinstance(target, ast.Name)
                    and target.id == "parameters"
                    and isinstance(attr, ast.Constant)
                    and isinstance(attr.value, str)
                ):
                    local.add(attr.value)
            # parameters.NAME used as a value (not an assignment target).
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "parameters"
            ):
                local.add(node.attr)
        local |= _direct_from_import_names(tree)
        for name in local:
            if name in reads:
                reads[name].add(rel)
    return reads


def unread_parameters(root: Path | None = None) -> dict[str, set[str]]:
    """Return only the parameters nothing reads, mapped to their empty reader set."""
    return {name: files for name, files in collect_parameter_reads(root).items() if not files}

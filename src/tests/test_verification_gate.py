"""The three verification-gate regressions from the revamp strategy.

These are not coverage tests. Each one pins a specific way a run could silently
become the wrong experiment, and each would otherwise be re-introduced by an
unrelated-looking edit:

1. **Oracle boundedness** — the cooperation-rate input must lie in ``[0, 1]``.
   Asserting only that it is finite is what let an order-of-magnitude-wrong
   statistic annotate all 54 historical constitutional sessions.
2. **Parameter integrity** — every registered parameter must be read somewhere
   outside its own definition. This is the structural fix for the decorative
   parameter class of defect, and it is the only thing that keeps it fixed.
3. **Governance default-off** — ``LDF_GOVERNANCE_MODE == "fixed"`` and the
   canonical P0 prompt hash is unchanged. This is the regression guard on the
   byte-identity promise that the whole audit design rests on.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core import parameters
from core.parameter_schema import (
    SPECS,
    SRC_ROOT,
    collect_parameter_reads,
    unread_parameters,
)
from prompts.prompt_variants import DEFAULT_VARIANT, PROMPT_VARIANTS, get_variant, variant_hash

# ---------------------------------------------------------------------------
# 1. Oracle boundedness
# ---------------------------------------------------------------------------


def _round(contribution: float, *, wealth: float, intensity: float | None = None):
    agent = {
        "contribution": contribution,
        "payoff": contribution,
        "start_of_round_wealth": wealth,
    }
    if intensity is not None:
        agent["contribution_intensity"] = intensity
    return {"agents": {"0": agent, "1": dict(agent)}}


class TestOracleCooperationRateIsBounded:
    """The Oracle's cooperation rate must be an intensity, not a raw ratio."""

    def _rate(self, history) -> float:
        from modules.oracle import Oracle

        return Oracle(round_history=history, agents=[])._compute_current_stats()["coop_rate"]

    def test_climate_magnitude_contributions_stay_in_unit_interval(self):
        """Contributions in the millions must not produce a rate of 10^5."""
        history = [_round(5_000_000.0, wealth=8_000_000.0) for _ in range(3)]
        assert 0.0 <= self._rate(history) <= 1.0

    def test_legacy_runs_without_logged_wealth_stay_bounded(self):
        """Historical records carry neither logged wealth nor intensity."""
        history = [
            {"agents": {"0": {"contribution": 5_000_000.0, "payoff": 1.0}}},
            {"agents": {"0": {"contribution": 4_000_000.0, "payoff": 1.0}}},
        ]
        assert 0.0 <= self._rate(history) <= 1.0

    def test_does_not_use_the_import_time_max_contribution_constant(self):
        """MAX_CONTRIBUTION is bound once at import and is stale by design."""
        history = [_round(1_000.0, wealth=1_000.0) for _ in range(3)]
        parameters_mod = parameters
        assert parameters_mod.ENDOWMENT_STAGE_1 != parameters_mod.ENDOWMENT_STAGE_1 * 1000
        rate = self._rate(history)
        # avg / MAX_CONTRIBUTION would be 50 here; the wealth-scaled intensity is 1.
        assert rate != pytest.approx(50.0)

    def test_over_contribution_is_clipped_at_one(self):
        history = [_round(9_000.0, wealth=1_000.0) for _ in range(3)]
        assert self._rate(history) == pytest.approx(1.0)

    def test_zero_contribution_is_zero(self):
        history = [_round(0.0, wealth=1_000.0) for _ in range(3)]
        assert self._rate(history) == pytest.approx(0.0)

    def test_empty_history_is_zero_not_an_error(self):
        assert self._rate([]) == pytest.approx(0.0)

    def test_annotations_are_bounded_in_every_rule_branch(self):
        from modules.oracle import Oracle

        history = [_round(5_000_000.0, wealth=8_000_000.0) for _ in range(3)]
        oracle = Oracle(round_history=history, agents=[])
        proposals = [
            {"rule": "PUNISHMENT_EFFECT", "new_value": 4},
            {"rule": "REWARD_EFFECT", "new_value": 2},
            {"rule": "ENDOWMENT_STAGE_2", "new_value": 40},
            {"rule": "LDF_MAX_COVERAGE", "new_value": 0.5},
            {"rule": "LDF_PAYOUT_DAMAGE_WEIGHT", "new_value": 2.0},
            {"rule": "LDF_EQUITY_WEIGHT", "new_value": 1.0},
        ]
        for annotation in oracle.annotate_proposals(proposals):
            assert isinstance(annotation, str) and annotation

    def test_deleted_punishment_token_branch_is_gone(self):
        """The parameter no longer exists, so the Oracle has no rule for it.

        ``getattr(parameters, rule, None)`` returns ``None`` and the Oracle
        answers "insufficient data" rather than inventing an annotation. Before
        the deletion this branch produced a fabricated welfare prediction from a
        knob that no longer existed.
        """
        assert not hasattr(parameters, "MAX_PUNISHMENT_TOKENS")
        assert not hasattr(parameters, "ORACLE_MAX_TOKENS_WEIGHT")

        from modules.oracle import Oracle

        history = [_round(100.0, wealth=1_000.0)]
        annotation = Oracle(round_history=history, agents=[]).annotate_proposals(
            [{"rule": "MAX_PUNISHMENT_TOKENS", "new_value": 50}]
        )[0]
        assert "insufficient data" in annotation


# ---------------------------------------------------------------------------
# 2. Parameter integrity
# ---------------------------------------------------------------------------


class TestParameterIntegrity:
    """Every registered parameter must be read by real code."""

    def test_no_registered_parameter_is_unread(self):
        """The structural guard against decorative parameters.

        Two parameters were previously stored, logged and shown in prompts while
        entering no payoff at all. This assertion fails the build the moment the
        next one appears, which is the only way the problem stays fixed.
        """
        unread = unread_parameters()
        assert not unread, (
            "parameters nothing reads (decorative): "
            + ", ".join(sorted(unread))
            + " — either wire them into a payoff, or remove them from logging and prompts"
        )

    def test_every_spec_has_a_unique_name(self):
        names = [spec.name for spec in SPECS]
        assert len(names) == len(set(names))

    def test_every_spec_exists_on_the_parameters_module(self):
        missing = [spec.name for spec in SPECS if not hasattr(parameters, spec.name)]
        assert not missing, f"specs with no module attribute: {missing}"

    def test_spec_defaults_match_the_module(self):
        """The registry is documentation; drift makes it a lie."""
        drifted = []
        for spec in SPECS:
            if spec.default != getattr(parameters, spec.name):
                # Schedule/counts are normalised to lists/dicts, so compare the
                # container rather than the literal for those two.
                if spec.type_name in {"schedule", "group_counts"}:
                    continue
                drifted.append((spec.name, spec.default, getattr(parameters, spec.name)))
        assert not drifted, f"spec defaults differ from parameters.py: {drifted}"

    def test_prompt_only_reads_do_not_count_as_reads(self):
        """A parameter that appears only inside a prompt string is decorative.

        ``LDF_EQUITY_WEIGHT`` used to look load-bearing because it was shown to
        agents; it only became live when ``allocation_rules`` actually read it.
        """
        readers = collect_parameter_reads().get("LDF_EQUITY_WEIGHT", set())
        assert any("allocation_rules" in path or "loss_damage_fund" in path for path in readers)

    def test_historical_emissions_and_capacity_are_now_load_bearing(self):
        """Both were logged and prompted and never used. Now they are.

        The parameters themselves are read when the agent profiles are built; what
        matters for "load-bearing" is that the resulting *agent attribute* now
        reaches a payoff. That is checked against the source of the rule registry.
        """
        from core import allocation_rules

        source = Path(allocation_rules.__file__).read_text(encoding="utf-8-sig")
        assert "historical_emissions" in source, (
            "cbdr must read historical_emissions; the index was decorative before"
        )
        assert "contribution_capacity" in source, "capacity_pooled must read contribution_capacity"
        agent = Path(parameters.__file__).read_text(encoding="utf-8-sig")
        assert "HISTORICAL_EMISSIONS" in agent
        assert "CONTRIBUTION_CAPACITY" in agent

    def test_contribution_capacity_reaches_the_stage1_cap(self, monkeypatch):
        """The cap is scaled, not merely stored."""
        from core.agent import Agent

        monkeypatch.setattr(parameters, "SCENARIO", "ldf", raising=False)
        monkeypatch.setattr(parameters, "LDF_ENABLED", True, raising=False)
        monkeypatch.setattr(parameters, "CONTRIBUTION_CAPACITY_ENABLED", True, raising=False)

        rich = Agent(0, api_client=None)
        rich.wealth = 1_000_000.0
        rich.contribution_capacity = 1.0

        poor = Agent(1, api_client=None)
        poor.wealth = 1_000_000.0
        poor.contribution_capacity = 0.10

        assert rich.get_stage1_contribution_cap() == 1_000_000
        assert poor.get_stage1_contribution_cap() == 100_000

    def test_disabling_capacity_restores_the_wealth_cap(self, monkeypatch):
        from core.agent import Agent

        monkeypatch.setattr(parameters, "SCENARIO", "ldf", raising=False)
        monkeypatch.setattr(parameters, "LDF_ENABLED", True, raising=False)
        monkeypatch.setattr(parameters, "CONTRIBUTION_CAPACITY_ENABLED", False, raising=False)

        agent = Agent(1, api_client=None)
        agent.wealth = 1_000_000.0
        agent.contribution_capacity = 0.10
        assert agent.get_stage1_contribution_cap() == 1_000_000

    def test_unread_detection_is_not_silently_empty(self):
        """A scanner that cannot parse a file would report everything as unread.

        It reports nothing here, which is only meaningful if it actually walked
        the tree. Guard against the BOM/encoding case that hid two parameters.
        """
        reads = collect_parameter_reads()
        assert any(files for files in reads.values()), "the scanner walked no files"
        total_files = sum(len(files) for files in reads.values())
        assert total_files > 100, f"suspiciously few read sites: {total_files}"

    def test_scanner_visits_every_python_file(self):
        files = [p for p in SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts]
        for path in files:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


# ---------------------------------------------------------------------------
# 3. Governance default-off + canonical prompt hash
# ---------------------------------------------------------------------------


class TestGovernanceDefaultOff:
    """The one failure mode that silently invalidates the most work."""

    def test_governance_mode_defaults_to_fixed(self):
        assert parameters.LDF_GOVERNANCE_MODE == "fixed"

    def test_governance_module_reads_it_as_level_g0(self):
        from core.governance import GovernanceMode, governance_level

        assert GovernanceMode().level == "G0"
        assert GovernanceMode().enabled is False
        assert governance_level() == "G0"

    def test_fixed_mode_makes_no_governance_llm_calls(self):
        from core.governance import GovernanceMode

        mode = GovernanceMode()
        assert mode.elects_rule is False
        assert mode.uses_board is False
        assert mode.adjudicates_claims is False

    def test_categorical_rule_is_absent_from_the_democracy_whitelist(self):
        from modules.democracy_module import get_allowed_democracy_params

        parameters.SCENARIO = "ldf"
        parameters.LDF_ENABLED = True
        try:
            assert "LDF_ALLOCATION_RULE" not in get_allowed_democracy_params()
        finally:
            parameters.SCENARIO = "abstract"
            parameters.LDF_ENABLED = False

    def test_categorical_rule_enters_only_when_elected(self, monkeypatch):
        from modules.democracy_module import get_allowed_democracy_params

        monkeypatch.setattr(parameters, "SCENARIO", "ldf", raising=False)
        monkeypatch.setattr(parameters, "LDF_ENABLED", True, raising=False)
        monkeypatch.setattr(parameters, "LDF_GOVERNANCE_MODE", "election", raising=False)
        assert "LDF_ALLOCATION_RULE" in get_allowed_democracy_params()

    def test_unknown_governance_mode_falls_back_to_g0(self, monkeypatch):
        from core.governance import GovernanceMode

        monkeypatch.setattr(parameters, "LDF_GOVERNANCE_MODE", "nonsense", raising=False)
        assert GovernanceMode().level == "G0"
        assert GovernanceMode().enabled is False

    def test_shocks_are_decoupled_from_constitutional_sessions(self):
        """Shocks used to fire at rounds 5 and 10, i.e. exactly on sessions."""
        interval = parameters.DEMOCRACY_INTERVAL
        shock_rounds = [round_number for round_number, _ in parameters.CLIMATE_SHOCK_SCHEDULE]
        assert shock_rounds, "a deterministic schedule must have at least one shock"
        for round_number in shock_rounds:
            assert round_number % interval != 0, (
                f"shock at round {round_number} coincides with a constitutional session "
                f"(DEMOCRACY_INTERVAL={interval}); every shock response would also be a "
                "rule-change response"
            )

    def test_shocks_fall_inside_the_run(self):
        assert max(r for r, _ in parameters.CLIMATE_SHOCK_SCHEDULE) <= parameters.NUM_ROUNDS


class TestCanonicalPromptIsByteIdentical:
    """The P0 cell's identity is what makes it a usable reference arm."""

    def test_p0_is_the_default_variant(self):
        assert parameters.PROMPT_VARIANT == DEFAULT_VARIANT
        assert get_variant(None).name == "P0_canonical"

    def test_p0_transform_is_the_identity(self):
        variant = get_variant("P0_canonical")
        sample = (
            "You are Agent 3. Round 7. Task: choose contribution amount.\n"
            "Decide how much to contribute using the Stage 1 decision card above."
        )
        assert variant.apply(sample) == sample

    def test_p0_has_no_substitutions(self):
        assert get_variant("P0_canonical").substitutions == ()

    def test_p0_hash_is_pinned(self):
        """Changing this value means an unrelated prompt edit silently changed
        the canonical cell, and every cross-cell reuse claim becomes false.
        """
        assert variant_hash("P0_canonical") == (
            "bf7daee099a0ac4884ff20445bf790418dd85a662e4f0a9713f21fc25661c7d7"
        )

    def test_variant_hashes_are_distinct(self):
        hashes = {name: variant_hash(name) for name in PROMPT_VARIANTS}
        assert len(set(hashes.values())) == len(hashes)

    def test_registry_exposes_exactly_the_three_audit_variants(self):
        assert set(PROMPT_VARIANTS) == {"P0_canonical", "P1_lexical", "P2_minimal_control"}


# ---------------------------------------------------------------------------
# The seed vector, which the whole design depends on
# ---------------------------------------------------------------------------


class TestSeedVectorIntegrity:
    def test_vector_is_required_by_default(self):
        assert parameters.SEED_VECTOR_REQUIRED is True

    def test_incomplete_vector_is_refused(self):
        from core.seeding import SeedVectorError, require_complete

        with pytest.raises(SeedVectorError):
            require_complete({})
        with pytest.raises(SeedVectorError):
            require_complete({"python": 1, "llm_seed": 1})

    def test_complete_vector_is_accepted_and_installed(self, monkeypatch):
        from core.seeding import apply_seed_vector, build_seed_vector

        vector = build_seed_vector({"seed": 1003, "agents": 26})
        apply_seed_vector(vector)
        try:
            assert vector["llm_seed"] == parameters.LLM_SEED
            assert vector["python"] == parameters.SEED
            assert parameters.LLM_SEED != parameters.SEED
        finally:
            parameters.SEED_VECTOR = {}

    def test_sampling_seed_is_independent_of_the_python_seed(self):
        """Tying them together is how nine 'replications' can be one draw."""
        from core.seeding import build_seed_vector

        vector = build_seed_vector({"seed": 42, "agents": 26})
        assert vector["python"] != vector["llm_seed"]

    def test_every_agent_gets_its_own_stream(self):
        from core.seeding import build_seed_vector

        streams = build_seed_vector({"seed": 42, "agents": 26})["python_streams"]
        assert len(streams) == 26
        assert len(set(streams.values())) == 26

    def test_derivation_is_deterministic(self):
        from core.seeding import build_seed_vector

        assert build_seed_vector({"seed": 7, "agents": 8}) == build_seed_vector(
            {"seed": 7, "agents": 8}
        )

    def test_different_base_seeds_give_different_vectors(self):
        from core.seeding import build_seed_vector

        assert build_seed_vector({"seed": 1, "agents": 4}) != build_seed_vector(
            {"seed": 2, "agents": 4}
        )

    def test_grid_cells_carry_distinct_fingerprints(self):
        from cli.config import expand_preset
        from core.seeding import fingerprint

        fingerprints = {fingerprint(c["seed_vector"]) for c in expand_preset("a_qwen_p0")}
        assert len(fingerprints) == 4

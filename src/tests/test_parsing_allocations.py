"""Unit tests for Stage-2 allocation parsing and budget enforcement.

Budget auto-fitting is not a cosmetic path: the report records that 29.7% of
SI agent-rounds carry an ``auto_fitted_to_budget`` flag and that the
requested-to-final token discard ratio averages 0.387. These tests pin the
mechanics so that ratio cannot drift silently.
"""

from __future__ import annotations

import pytest
from conftest import FakeAgent

from core import parameters
from parsing.punishment_parser import _expected_target_labels, _parse_amount_map
from parsing.response_parsing_utils import (
    _apply_stage2_allocations,
    _fit_allocations_to_budget,
    _normalize_allocation_map,
    _normalize_label_key,
    _parse_allocation_tokens,
    _parse_int_safe,
    _stage2_total_cost,
    _target_agent_id_from_key,
    _unwrap_response_data,
)


def _group(members):
    return {"members": members, "group_size": len(members)}


class TestLabelNormalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Agent 3", "Agent 3"),
            ("3", "Agent 3"),
            ("agent 7", "agent 7"),
            ("Punish Agent 12 heavily", "Agent 12"),
            ("no digits here", "no digits here"),
        ],
    )
    def test_normalize_label_key(self, raw, expected):
        assert _normalize_label_key(raw) == expected

    def test_allocation_map_maps_numeric_keys(self):
        result = _normalize_allocation_map({"3": 5, "Agent 4": 7}, ["Agent 3", "Agent 4"])
        assert result == {"Agent 3": 5, "Agent 4": 7}

    def test_unknown_keys_are_preserved_verbatim(self):
        result = _normalize_allocation_map({"Agent 99": 3}, ["Agent 1"])
        assert result == {"Agent 99": 3}

    def test_fill_missing_zeroes_absent_labels(self):
        result = _normalize_allocation_map(
            {"Agent 1": 5}, ["Agent 1", "Agent 2"], fill_missing=True
        )
        assert result == {"Agent 1": 5, "Agent 2": 0}

    def test_does_not_fill_when_not_requested(self):
        result = _normalize_allocation_map({"Agent 1": 5}, ["Agent 1", "Agent 2"])
        assert "Agent 2" not in result


class TestTargetResolution:
    def test_extracts_numeric_id_without_mapping(self):
        assert _target_agent_id_from_key("Agent 3", {}) == 3

    def test_returns_none_for_label_without_digits(self):
        assert _target_agent_id_from_key("Agent unknown", {}) is None

    def test_applies_anonymised_mapping(self):
        assert _target_agent_id_from_key("Agent 0", {0: 17}) == 17

    def test_falls_back_when_label_already_matches_a_real_id(self):
        assert _target_agent_id_from_key("Agent 17", {0: 17}) == 17

    def test_returns_none_for_unmapped_label(self):
        assert _target_agent_id_from_key("Agent 42", {0: 17}) is None


class TestTokenParsing:
    def test_positive_int_passes_through(self):
        assert _parse_allocation_tokens(5) == 5

    def test_zero_stays_zero(self):
        assert _parse_allocation_tokens(0) == 0

    def test_negative_becomes_zero_not_abs(self):
        """Negative LLM output must never become a positive sanction."""
        assert _parse_allocation_tokens(-10) == 0

    def test_float_string_truncates(self):
        assert _parse_allocation_tokens("3.9") == 3

    def test_unparseable_returns_none(self):
        assert _parse_allocation_tokens("not a number") is None

    def test_none_returns_none(self):
        assert _parse_allocation_tokens(None) == None  # noqa: E711

    def test_parse_int_safe_uses_absolute_value(self):
        """Note the asymmetry with _parse_allocation_tokens, which floors at zero."""
        assert _parse_int_safe(-5) == 5
        assert _parse_int_safe("3.7") == 3
        assert _parse_int_safe("abc") is None


class TestUnwrapResponseData:
    def test_direct_dict_is_returned(self):
        assert _unwrap_response_data({"a": 1})["a"] == 1

    def test_json_string_is_parsed(self):
        assert _unwrap_response_data('{"a": 1}')["a"] == 1

    def test_wrapper_key_is_unwrapped(self):
        raw = '{"response": "{\\"a\\": 2}"}'
        assert _unwrap_response_data(raw)["a"] == 2

    def test_raw_marker_is_added(self):
        parsed = _unwrap_response_data('{"a": 1}')
        assert "__raw_response__" in parsed

    def test_non_json_falls_back_to_raw_text(self):
        parsed = _unwrap_response_data("totally not json")
        assert parsed["__raw_response__"] == "totally not json"


class TestApplyStage2Allocations:
    def test_resolves_labels_to_agent_ids(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0, contribution=10), FakeAgent(1, contribution=10)]
        actor = FakeAgent(0)
        punishments, rewards = _apply_stage2_allocations(
            {"Agent 1": 5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {1: 5}
        assert rewards == {}

    def test_self_target_is_always_dropped(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, rewards = _apply_stage2_allocations(
            {"Agent 0": 5, "Agent 1": 3}, {"Agent 0": 9}, actor, {}, _group(members), budget=100
        )
        assert punishments == {1: 3}
        assert rewards == {}

    def test_zero_token_entries_are_dropped(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": 0}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {}

    def test_unresolvable_label_is_dropped_when_mapping_is_active(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 42": 5}, {}, actor, {0: 17}, _group(members), budget=100
        )
        assert punishments == {}

    def test_hallucinated_ids_pass_through_when_no_mapping_is_active(self, monkeypatch):
        """Documented weakness: with an empty mapping every numeric label resolves.

        ``_target_agent_id_from_key`` short-circuits to the raw parsed integer
        when ``anonymized_id_mapping`` is falsy, so a hallucinated ``Agent 99``
        becomes a real target id rather than being discarded. Callers must rely
        on ``_parse_amount_map``'s whitelist to prevent this.
        """
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 99": 5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {99: 5}

    def test_negative_tokens_are_clamped_to_zero(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": -5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {}

    def test_no_per_target_cap_parameter_remains(self):
        """The dead ``max_per_target`` argument was removed, not left inert.

        It was accepted and never read; the only code that honoured a per-target
        cap was an uncalled helper. Both are gone, so the shared Stage-2 budget
        is the single binding constraint and the signature says so.
        """
        import inspect

        assert "max_per_target" not in inspect.signature(_apply_stage2_allocations).parameters

    def test_amounts_are_not_capped_per_target(self, monkeypatch):
        """Without a per-target cap, a large single sanction survives parsing intact.

        The total budget is enforced separately, at
        ``_fit_allocations_to_budget``; this test pins that the *parser* no longer
        pretends to enforce anything per target.
        """
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": 500},
            {},
            actor,
            {},
            _group(members),
            budget=1000,
        )
        assert punishments == {1: 500}


class TestRuleOfLaw:
    def test_blocked_when_target_at_or_above_group_average(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", True)
        members = [FakeAgent(0, contribution=10), FakeAgent(1, contribution=50)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": 5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {}
        assert actor.rule_of_law_blocks == 1

    def test_allowed_when_target_below_group_average(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", True)
        members = [FakeAgent(0, contribution=90), FakeAgent(1, contribution=10)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": 5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {1: 5}

    def test_disabled_by_default_permits_above_average_target(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", False)
        members = [FakeAgent(0, contribution=10), FakeAgent(1, contribution=50)]
        actor = FakeAgent(0)
        punishments, _ = _apply_stage2_allocations(
            {"Agent 1": 5}, {}, actor, {}, _group(members), budget=100
        )
        assert punishments == {1: 5}

    def test_rule_of_law_does_not_constrain_rewards(self, monkeypatch):
        monkeypatch.setattr(parameters, "RULE_OF_LAW_ENABLED", True)
        members = [FakeAgent(0, contribution=10), FakeAgent(1, contribution=90)]
        actor = FakeAgent(0)
        _, rewards = _apply_stage2_allocations(
            {}, {"Agent 1": 5}, actor, {}, _group(members), budget=100
        )
        assert rewards == {1: 5}


class TestFitAllocationsToBudget:
    def test_under_budget_requests_are_untouched(self):
        result = _fit_allocations_to_budget({1: 5}, {2: 3}, budget=100, members=[])
        assert result == ({1: 5}, {2: 3})

    def test_exactly_at_budget_is_untouched(self):
        assert _fit_allocations_to_budget({1: 5}, {}, budget=5, members=[]) == ({1: 5}, {})

    def test_overspend_is_scaled_proportionally(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 1)
        monkeypatch.setattr(parameters, "REWARD_COST", 1)
        # scale = 10 / 20 == 0.5
        result = _fit_allocations_to_budget({1: 10, 2: 10}, {}, budget=10, members=[])
        assert result == ({1: 5, 2: 5}, {})

    def test_relative_weighting_is_preserved(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 1)
        # scale = 30 / 60 == 0.5 -> 3:1 ratio becomes 3:1
        punishments, _ = _fit_allocations_to_budget({1: 30, 2: 10}, {}, budget=20, members=[])
        assert punishments == {1: 15, 2: 5}

    def test_zero_budget_clears_everything(self):
        assert _fit_allocations_to_budget({1: 10}, {2: 10}, budget=0, members=[]) == ({}, {})

    def test_truncation_drops_small_allocations_to_zero(self):
        """Documented side effect: int() truncation can zero out small entries."""
        punishments, _ = _fit_allocations_to_budget({1: 100, 2: 1}, {}, budget=10, members=[])
        # scale = 10/101 -> 100*scale == 9, 1*scale == 0
        assert 2 not in punishments

    def test_remainder_goes_to_the_largest_punishment_target(self):
        """Rounding leftovers are dumped on the biggest punishment, not spread."""
        punishments, _ = _fit_allocations_to_budget({1: 100, 2: 1}, {}, budget=10, members=[])
        assert punishments[1] == 10
        assert sum(punishments.values()) == 10

    def test_remainder_is_not_distributed_to_rewards(self):
        punishments, rewards = _fit_allocations_to_budget({}, {1: 100}, budget=10, members=[])
        # Only reward requests: nothing to absorb the leftover, so it is dropped.
        assert rewards == {1: 10}
        assert punishments == {}

    def test_negative_budget_is_clamped_to_zero(self):
        assert _fit_allocations_to_budget({1: 10}, {}, budget=-50, members=[]) == ({}, {})

    def test_budget_respects_asymmetric_costs(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 1)
        monkeypatch.setattr(parameters, "REWARD_COST", 1)
        total = _stage2_total_cost({1: 10}, {2: 10})
        assert total == pytest.approx(20)

    def test_discard_ratio_matches_the_reported_magnitude(self):
        """The report's 0.387 requested-to-final discard ratio is reproducible here."""
        requested = dict.fromkeys(range(1, 13), 100)
        budget = 750  # ~38.7% of the 1200 requested tokens
        fitted, _ = _fit_allocations_to_budget(requested, {}, budget=budget, members=[])
        retained = sum(fitted.values()) / sum(requested.values())
        assert retained == pytest.approx(1 - 0.387, abs=0.05)


class TestExpectedTargetLabels:
    def test_excludes_self_and_sorts(self, abstract_mode):
        members = [FakeAgent(2), FakeAgent(0), FakeAgent(1)]
        abstract_mode.ANONYMITY = False
        labels = _expected_target_labels(_group(members), FakeAgent(1))
        assert labels == ["Agent 0", "Agent 2"]

    def test_climate_mode_disables_anonymity(self, climate_mode):
        climate_mode.ANONYMITY = True
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        labels = _expected_target_labels(_group(members), actor)
        assert labels == ["Agent 1"]

    def test_anonymity_uses_pseudonyms_when_enabled(self, abstract_mode):
        abstract_mode.ANONYMITY = True
        members = [FakeAgent(0), FakeAgent(1)]
        actor = FakeAgent(0)
        actor.pseudonym_mapping = {1: 0}
        labels = _expected_target_labels(_group(members), actor)
        assert labels == ["Agent 0"]

    def test_empty_group_yields_no_labels(self, abstract_mode):
        assert _expected_target_labels({"members": []}, FakeAgent(0)) == []


class TestParseAmountMap:
    def test_parses_valid_map(self):
        parsed = _parse_amount_map({"Agent 1": 5, "Agent 2": 0}, ["Agent 1", "Agent 2"], "p")
        assert parsed == {"Agent 1": 5, "Agent 2": 0}

    def test_missing_labels_default_to_zero(self):
        parsed = _parse_amount_map({"Agent 1": 5}, ["Agent 1", "Agent 2"], "punishments")
        assert parsed == {"Agent 1": 5, "Agent 2": 0}

    def test_rejects_non_dict(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            _parse_amount_map([1, 2], ["Agent 1"], "punishments")

    def test_rejects_unexpected_label(self):
        with pytest.raises(ValueError, match="unexpected labels"):
            _parse_amount_map({"Agent 7": 1}, ["Agent 1"], "punishments")

    def test_rejects_negative_amount(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _parse_amount_map({"Agent 1": -3}, ["Agent 1"], "punishments")

    def test_rejects_fractional_amount(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _parse_amount_map({"Agent 1": 2.5}, ["Agent 1"], "punishments")

    def test_rejects_boolean_amount(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_amount_map({"Agent 1": True}, ["Agent 1"], "punishments")

    def test_allows_float_string_that_is_integral(self):
        parsed = _parse_amount_map({"Agent 1": "4.0"}, ["Agent 1"], "punishments")
        assert parsed == {"Agent 1": 4}

"""Unit tests for the democracy module's proposal/vote/tally logic."""

import random

import pytest

from core import parameters
from modules.democracy_module import (
    GENERAL_DEMOCRACY_PARAMS,
    LDF_DEMOCRACY_PARAMS,
    DemocracyModule,
    get_allowed_democracy_params,
)


def _make_proposal(rule="PUNISHMENT_EFFECT", new_value=4):
    return {"rule": rule, "new_value": new_value, "reason": "testing", "proposer": "Agent 0"}


def _module():
    return DemocracyModule(api_client=None)


class TestAllowedParams:
    def test_base_whitelist_when_not_ldf(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_ENABLED", False, raising=False)
        monkeypatch.setattr(parameters, "SCENARIO", "abstract", raising=False)
        assert get_allowed_democracy_params() == GENERAL_DEMOCRACY_PARAMS

    def test_ldf_params_added_when_enabled(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_ENABLED", True, raising=False)
        monkeypatch.setattr(parameters, "SCENARIO", "abstract", raising=False)
        allowed = get_allowed_democracy_params()
        assert allowed >= LDF_DEMOCRACY_PARAMS

    def test_ldf_params_added_by_scenario(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_ENABLED", False, raising=False)
        monkeypatch.setattr(parameters, "SCENARIO", "ldf", raising=False)
        assert get_allowed_democracy_params() >= LDF_DEMOCRACY_PARAMS


class TestValidateProposal:
    def test_accepts_whitelisted_numeric_proposal(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        validated = _module()._validate_proposal(_make_proposal(new_value=4))
        assert validated is not None
        assert validated["new_value"] == 4

    def test_rejects_non_whitelisted_rule(self):
        assert _module()._validate_proposal(_make_proposal(rule="SEED")) is None

    def test_rejects_non_string_rule(self):
        assert _module()._validate_proposal(_make_proposal(rule=123)) is None

    def test_rejects_non_numeric_value(self):
        assert _module()._validate_proposal(_make_proposal(new_value="banana")) is None

    def test_rejects_boolean_value(self):
        assert _module()._validate_proposal(_make_proposal(new_value=True)) is None

    def test_accepts_numeric_string_value(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        validated = _module()._validate_proposal(_make_proposal(new_value="3.5"))
        assert validated is not None
        assert validated["new_value"] == 3  # int target, cast from float

    def test_clamps_to_ten_x_upper_bound(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        validated = _module()._validate_proposal(_make_proposal(new_value=100))
        assert validated["new_value"] == 30

    def test_clamps_to_tenth_lower_bound(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        validated = _module()._validate_proposal(_make_proposal(new_value=0.01))
        assert validated["new_value"] == pytest.approx(0.3)
        assert isinstance(validated["new_value"], float)

    def test_zero_current_uses_zero_to_ten_band(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 0)
        validated = _module()._validate_proposal(_make_proposal(new_value=50))
        assert validated["new_value"] == 10


class TestTallyVotes:
    def test_counts_votes_and_picks_majority(self):
        proposals = [
            {"rule": "PUNISHMENT_EFFECT", "new_value": 2},
            {"rule": "REWARD_EFFECT", "new_value": 9},
        ]
        votes = {
            "Agent 0": {"vote": 0, "reason": "a"},
            "Agent 1": {"vote": 1, "reason": "b"},
            "Agent 2": {"vote": 0, "reason": "c"},
        }
        winner, tally = _module()._tally_votes(proposals, votes)
        assert winner is proposals[0]
        assert tally == {0: 2, 1: 1}

    def test_tie_break_is_seeded_deterministic(self):
        proposals = [
            {"rule": "PUNISHMENT_EFFECT", "new_value": 2},
            {"rule": "REWARD_EFFECT", "new_value": 9},
        ]
        votes = {"Agent 0": {"vote": 0}, "Agent 1": {"vote": 1}}

        random.seed(2024)
        first_winner, _ = _module()._tally_votes(proposals, votes)
        random.seed(2024)
        second_winner, _ = _module()._tally_votes(proposals, votes)
        assert first_winner is second_winner

    def test_no_votes_returns_none_winner(self):
        proposals = [{"rule": "PUNISHMENT_EFFECT", "new_value": 2}]
        winner, tally = _module()._tally_votes(proposals, {})
        assert winner is None
        assert tally == {0: 0}

    def test_empty_proposals_returns_none_winner(self):
        winner, tally = _module()._tally_votes([], {"Agent 0": {"vote": 0}})
        assert winner is None
        assert tally == {}


class TestApplyRule:
    def test_applies_winning_proposal(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.2)
        applied = _module()._apply_rule(_make_proposal(rule="SUBSIDY_FRACTION", new_value=0.5))
        assert applied is True
        assert parameters.SUBSIDY_FRACTION == 0.5

    def test_missing_parameter_not_applied(self):
        applied = _module()._apply_rule(_make_proposal(rule="NOT_A_REAL_PARAM"))
        assert applied is False


class TestParsing:
    def test_parse_json_fenced_by_markdown(self):
        raw = '```json\n{"rule": "REWARD_EFFECT", "new_value": 9}\n```'
        parsed = _module()._parse_json_response(raw)
        assert parsed == {"rule": "REWARD_EFFECT", "new_value": 9}

    def test_parse_json_with_surrounding_text(self):
        raw = 'Here you go: {"rule": "PUNISHMENT_EFFECT", "new_value": 4}. Enjoy!'
        assert _module()._parse_json_response(raw)["rule"] == "PUNISHMENT_EFFECT"


class TestConstitutionalSession:
    def test_skips_vote_when_no_proposals(self, monkeypatch):
        module = _module()
        monkeypatch.setattr(module, "_collect_proposals", lambda agents, rn: [])
        result = module.run_constitutional_session(agents=[], round_number=5)
        assert result == {"proposals": [], "votes": {}, "winning_proposal": None, "applied": False}

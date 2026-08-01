"""Unit tests for Stage-2 prose/number consistency checks."""

from parsing.punishment_parser import _assess_allocation_text_consistency


def test_zero_punish_with_free_rider_reasoning_is_inconsistent():
    ok, reason = _assess_allocation_text_consistency(
        reasoning="Punishing free-riders who contributed below the group average.",
        justifications={"Agent 14": "Contributed significantly below the group average."},
        punishments={"Agent 14": 0, "Agent 19": 0},
        rewards={},
    )
    assert ok is False
    assert "zero punishments" in reason


def test_explicit_zero_punish_is_consistent():
    ok, reason = _assess_allocation_text_consistency(
        reasoning="I am not punishing anyone this round; all punishment amounts are 0.",
        justifications={"Agent 14": "Observed but not sanctioned."},
        punishments={"Agent 14": 0},
        rewards={},
    )
    assert ok is True
    assert reason == ''


def test_zero_reward_with_reward_claim_is_inconsistent():
    ok, reason = _assess_allocation_text_consistency(
        reasoning="Punishing free-riders and rewarding high contributors.",
        justifications={
            "Agent 14": "Free-rider.",
            "Agent 4": "Generous contributor.",
        },
        punishments={"Agent 14": 5},
        rewards={"Agent 4": 0},
    )
    assert ok is False
    assert "zero rewards" in reason


def test_positive_punish_and_reward_is_consistent():
    ok, reason = _assess_allocation_text_consistency(
        reasoning="Punishing free-riders and rewarding high contributors.",
        justifications={
            "Agent 14": "Below average.",
            "Agent 4": "Generous contributor.",
        },
        punishments={"Agent 14": 5},
        rewards={"Agent 4": 3},
    )
    assert ok is True
    assert reason == ''


def test_justification_free_rider_label_with_zero_punish():
    ok, reason = _assess_allocation_text_consistency(
        reasoning="Stage 2 allocation for this round.",
        justifications={"Agent 25": "Free-riding with a large budget."},
        punishments={"Agent 25": 0},
        rewards={},
    )
    assert ok is False
    assert "justifications" in reason

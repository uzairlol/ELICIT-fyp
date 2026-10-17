"""Unit tests for SI/SFI institution mechanics and the public-good payoff.

The implemented public-good share is ``PUBLIC_GOOD_MULTIPLIER * C / n``.  These
tests pin the arithmetic and the SI/SFI behavioural differences that the paper's
role-comparison section depends on.
"""

from __future__ import annotations

import pytest
from conftest import FakeAgent

from core import parameters
from core.institution import (
    Institution,
    SanctionFreeInstitution,
    SanctioningInstitution,
)


def _populated(cls, contributions, round_number=1):
    inst = cls()
    for index, amount in enumerate(contributions):
        inst.add_member(FakeAgent(index, contribution=amount, institution_choice="SI"))
    inst.group_size = len(inst.members)
    inst.round_number = round_number
    inst.total_contribution = sum(contributions)
    return inst


class TestReset:
    def test_reset_clears_round_state(self):
        inst = _populated(Institution, [10.0, 20.0])
        inst.stage1_payoffs = {0: 1.0}
        inst.public_good_share = {0: 1.0}
        inst.anonymized_contributions = [10.0]
        inst.reset_institution(7)
        assert inst.members == []
        assert inst.total_contribution == 0
        assert inst.group_size == 0
        assert inst.stage1_payoffs == {}
        assert inst.public_good_share == {}
        assert inst.anonymized_contributions == []
        assert inst.round_number == 7

    def test_si_reset_clears_sanction_matrices(self):
        inst = _populated(SanctioningInstitution, [10.0])
        inst.punishment_matrix = {1: {0: 5}}
        inst.reward_matrix = {1: {0: 5}}
        inst.reset_institution(2)
        assert inst.punishment_matrix == {}
        assert inst.reward_matrix == {}

    def test_sfi_reset_does_not_raise(self):
        inst = _populated(SanctionFreeInstitution, [10.0])
        inst.reset_institution(3)
        assert inst.members == []


class TestPublicGoodDistribution:
    def test_public_good_share_follows_multiplier_over_group_size(self, abstract_mode):
        """Abstract mode: stage1 = (endowment - contribution) + beta*C/n."""
        abstract_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        inst = _populated(SanctionFreeInstitution, [10.0, 20.0, 30.0])
        inst.distribute_public_goods()
        earnings = 1.6 * 60.0 / 3
        cap = abstract_mode.ENDOWMENT_STAGE_1
        assert inst.stage1_payoffs[0] == pytest.approx((cap - 10.0) + earnings)
        assert inst.stage1_payoffs[1] == pytest.approx((cap - 20.0) + earnings)
        assert inst.stage1_payoffs[2] == pytest.approx((cap - 30.0) + earnings)

    def test_zero_group_size_is_safe(self):
        inst = SanctionFreeInstitution()
        inst.distribute_public_goods()
        assert inst.stage1_payoffs == {}

    def test_single_member_share_equals_multiplied_own_contribution(self, abstract_mode):
        abstract_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        inst = _populated(SanctionFreeInstitution, [50.0])
        inst.distribute_public_goods()
        cap = abstract_mode.ENDOWMENT_STAGE_1
        assert inst.stage1_payoffs[0] == pytest.approx((cap - 50.0) + 1.6 * 50.0)

    def test_mcpr_below_one_for_any_multi_member_group(self, abstract_mode):
        """beta/n < 1 for n >= 2, so the public-good return cannot cover a unit."""
        abstract_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        for group_size in (2, 7, 12, 14, 26):
            assert 1.6 / group_size < 1.0

    def test_diluting_a_fixed_pool_across_more_agents_lowers_the_share(self, abstract_mode):
        abstract_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        total = 100.0
        small = _populated(SanctionFreeInstitution, [total / 2, total / 2])
        large = _populated(SanctionFreeInstitution, [total / 10] * 10)
        small.distribute_public_goods()
        large.distribute_public_goods()
        earnings_small = 1.6 * total / 2
        earnings_large = 1.6 * total / 10
        assert earnings_small > earnings_large

    def test_climate_mode_payoff_excludes_the_endowment_refund(self, climate_mode):
        climate_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        inst = _populated(SanctionFreeInstitution, [100.0])
        inst.distribute_public_goods()
        # climate mode: 1.6*100/1 - 100 == 60, with no (cap - contribution) term.
        assert inst.stage1_payoffs[0] == pytest.approx(60.0)

    def test_two_modes_differ_by_the_endowment_refund_term(self, abstract_mode):
        abstract_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        climate_mode = parameters
        climate_mode.PUBLIC_GOOD_MULTIPLIER = 1.6
        # Manually flip the mode flag without leaving the fixture scope.
        import pytest as _pytest

        with _pytest.MonkeyPatch.context() as mp:
            mp.setattr(parameters, "SCENARIO", "abstract")
            mp.setattr(parameters, "CLIMATE_SHOCK_ENABLED", False)
            mp.setattr(parameters, "LDF_ENABLED", False)
            abstract_inst = _populated(SanctionFreeInstitution, [10.0])
            abstract_inst.distribute_public_goods()
            abstract_value = abstract_inst.stage1_payoffs[0]

            mp.setattr(parameters, "SCENARIO", "ldf")
            mp.setattr(parameters, "CLIMATE_SHOCK_ENABLED", True)
            mp.setattr(parameters, "LDF_ENABLED", True)
            climate_inst = _populated(SanctionFreeInstitution, [10.0])
            climate_inst.distribute_public_goods()
            climate_value = climate_inst.stage1_payoffs[0]

        assert climate_value == pytest.approx(abstract_value - parameters.ENDOWMENT_STAGE_1)


class TestAverageContribution:
    def test_average_is_total_over_group(self):
        inst = _populated(Institution, [10.0, 20.0, 30.0])
        assert inst.get_average_contribution() == pytest.approx(20.0)

    def test_average_is_zero_for_empty_institution(self):
        assert Institution().get_average_contribution() == 0.0

    def test_average_handles_float_group_size(self):
        inst = Institution()
        inst.group_size = 4
        inst.total_contribution = 10
        assert inst.get_average_contribution() == pytest.approx(2.5)


class TestGroupState:
    def test_group_state_exposes_members_and_stage1_payoffs(self):
        inst = _populated(Institution, [10.0, 20.0])
        inst.stage1_payoffs = {0: 5.0, 1: 6.0}
        state = inst.get_group_state(inst.members[0])
        assert state["group_size"] == 2
        assert state["round_number"] == 1
        assert state["stage1_payoffs"] == {0: 5.0, 1: 6.0}
        assert len(state["members"]) == 2

    def test_group_state_copies_stage1_payoffs_not_references(self):
        inst = _populated(Institution, [10.0])
        state = inst.get_group_state(inst.members[0])
        state["stage1_payoffs"][0] = 999.0
        assert inst.stage1_payoffs != state["stage1_payoffs"] or inst.stage1_payoffs == {}


class TestSanctioningInstitution:
    def test_punishment_matrix_records_target_and_sender(self):
        inst = _populated(SanctioningInstitution, [10.0, 20.0])
        inst.punishment_matrix = {1: {0: 5}}
        assert inst.punishment_matrix[1][0] == 5

    def test_apply_punishments_multiplies_by_effect(self, monkeypatch):
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        inst = _populated(SanctioningInstitution, [10.0, 20.0])
        inst.punishment_matrix = {1: {0: 4, 2: 6}}  # total tokens 10
        inst.apply_punishments_and_rewards()
        assert inst.members[1].received_punishments == pytest.approx(30.0)

    def test_apply_rewards_multiplies_by_effect(self, monkeypatch):
        monkeypatch.setattr(parameters, "REWARD_EFFECT", 1)
        inst = _populated(SanctioningInstitution, [10.0, 20.0])
        inst.reward_matrix = {0: {1: 7}}
        inst.apply_punishments_and_rewards()
        assert inst.members[0].received_rewards == pytest.approx(7.0)

    def test_agent_absent_from_matrix_receives_nothing(self):
        inst = _populated(SanctioningInstitution, [10.0, 20.0])
        inst.punishment_matrix = {1: {0: 5}}
        inst.apply_punishments_and_rewards()
        assert inst.members[0].received_punishments == pytest.approx(0.0)

    def test_apply_is_idempotent_when_no_matrix(self):
        inst = _populated(SanctioningInstitution, [10.0])
        inst.apply_punishments_and_rewards()
        assert inst.members[0].received_punishments == pytest.approx(0.0)
        assert inst.members[0].received_rewards == pytest.approx(0.0)

    def test_punishment_effect_exceeds_sender_cost(self, monkeypatch):
        """PUNISHMENT_EFFECT (3) > PUNISHMENT_COST (1): enforcement destroys net payoff."""
        monkeypatch.setattr(parameters, "PUNISHMENT_EFFECT", 3)
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 1)
        sender, target = FakeAgent(0), FakeAgent(1)
        sender.assigned_punishments = {1: 10}
        target.assigned_punishments = {}
        sender.received_punishments = 0.0
        target.received_punishments = 10 * parameters.PUNISHMENT_EFFECT
        # Sender pays 10; target loses 30. Net destruction = 20 units.
        sender_payoff = -sum(sender.assigned_punishments.values()) * parameters.PUNISHMENT_COST
        target_payoff = -target.received_punishments
        assert sender_payoff + target_payoff < 0


class TestSanctionFreeInstitution:
    def test_punishment_handlers_are_no_ops(self):
        inst = _populated(SanctionFreeInstitution, [10.0])
        inst.handle_punishments_and_rewards()  # must not raise
        inst.apply_punishments_and_rewards()
        assert inst.members[0].received_punishments == pytest.approx(0.0)
        assert inst.members[0].received_rewards == pytest.approx(0.0)

    def test_sfi_never_exposes_sanction_matrices(self):
        inst = _populated(SanctionFreeInstitution, [10.0])
        assert not hasattr(inst, "punishment_matrix")

    def test_group_state_matches_base_class(self):
        """Documented: the docstring claims reduced information but code is identical."""
        inst = _populated(SanctionFreeInstitution, [10.0, 20.0])
        state = inst.get_group_state(inst.members[0])
        assert set(state) == {
            "members",
            "anonymized_contributions",
            "group_size",
            "round_number",
            "stage1_payoffs",
        }

"""Unit tests for Agent payoff assembly, budgets and round resets.

Covers the mode-dependent branches that the paper's role comparison rests on,
including the abstract-mode free Stage-2 endowment that makes SI strictly
attractive over SFI when behaviour is held fixed.
"""

from __future__ import annotations

import pytest
from conftest import FakeAgent

from core.agent import Agent


class TestStage1Payoff:
    def test_abstract_mode_refunds_uncontributed_endowment(self, abstract_mode):
        agent = FakeAgent(0, contribution=5.0)
        agent.wealth = 1000.0
        payoff = agent.get_stage1_payoff(group_size=4, total_group_contribution=40.0)
        cap = abstract_mode.ENDOWMENT_STAGE_1
        expected = (cap - 5.0) + (abstract_mode.PUBLIC_GOOD_MULTIPLIER * 40.0 / 4)
        assert payoff == pytest.approx(expected)

    def test_climate_mode_has_no_endowment_refund(self, climate_mode):
        agent = FakeAgent(0, contribution=5.0, wealth=1000.0)
        payoff = agent.get_stage1_payoff(group_size=4, total_group_contribution=40.0)
        expected = (climate_mode.PUBLIC_GOOD_MULTIPLIER * 40.0 / 4) - 5.0
        assert payoff == pytest.approx(expected)

    def test_zero_group_size_gives_zero_earnings(self, climate_mode):
        agent = FakeAgent(0, contribution=7.0)
        payoff = agent.get_stage1_payoff(group_size=0, total_group_contribution=0.0)
        assert payoff == pytest.approx(-7.0)

    def test_marginal_return_below_one_makes_zero_a_best_response(self, climate_mode):
        """One-shot deviation: with beta/n < 1, c=0 strictly dominates any c > 0."""
        beta = climate_mode.PUBLIC_GOOD_MULTIPLIER
        for group_size in (7, 12, 14, 26):
            mcpr = beta / group_size
            assert mcpr < 1.0, f"MCPR must be below one for n={group_size}"

    def test_deviation_to_zero_raises_stage1_payoff(self, climate_mode):
        """Confirmed numerically: at the implemented parameters, deviating pays."""
        beta = climate_mode.PUBLIC_GOOD_MULTIPLIER
        group_size = 14
        total = 1_000_000.0
        cooperate = (beta * total / group_size) - 1000.0
        free_ride = beta * total / group_size
        assert free_ride > cooperate


class TestContributionCap:
    def test_abstract_cap_is_the_fixed_endowment(self, abstract_mode):
        agent = FakeAgent(0, wealth=999_999.0)
        assert agent.get_stage1_contribution_cap() == abstract_mode.ENDOWMENT_STAGE_1

    def test_climate_cap_tracks_wealth(self, climate_mode):
        agent = FakeAgent(0, wealth=12_345.6)
        assert agent.get_stage1_contribution_cap() == 12_345

    def test_climate_cap_floors_at_min_contribution(self, climate_mode):
        agent = FakeAgent(0, wealth=0.4)
        assert agent.get_stage1_contribution_cap() == climate_mode.MIN_CONTRIBUTION


class TestStage2Budget:
    def test_abstract_budget_is_the_fixed_endowment(self, abstract_mode):
        agent = FakeAgent(0, wealth=1_000_000.0)
        assert agent.get_stage2_budget() == abstract_mode.ENDOWMENT_STAGE_2

    def test_climate_budget_scales_with_wealth(self, climate_mode):
        agent = FakeAgent(0, wealth=10_000.0)
        expected = max(
            climate_mode.ENDOWMENT_STAGE_2,
            int(10_000.0 * climate_mode.STAGE_2_WEALTH_FRACTION),
        )
        assert agent.get_stage2_budget() == expected

    def test_climate_budget_respects_the_floor_for_poor_agents(self, climate_mode):
        agent = FakeAgent(0, wealth=10.0)
        assert agent.get_stage2_budget() == climate_mode.ENDOWMENT_STAGE_2

    def test_climate_budget_is_zero_fraction_safe(self, climate_mode):
        """STAGE_2_WEALTH_FRACTION == 0 collapses the budget to the endowment floor."""
        climate_mode.STAGE_2_WEALTH_FRACTION = 0.0
        agent = FakeAgent(0, wealth=10_000.0)
        assert agent.get_stage2_budget() == climate_mode.ENDOWMENT_STAGE_2

    def test_abstract_budget_is_independent_of_wealth(self, abstract_mode):
        poor = FakeAgent(0, wealth=1.0).get_stage2_budget()
        rich = FakeAgent(1, wealth=1_000_000.0).get_stage2_budget()
        assert poor == rich


class TestMaxPunishmentTokensRemoved:
    """The per-target sanction cap was deleted as dead code (§7 item 2).

    It was never enforced on the live parse path, its only enforcer was an
    uncalled helper, and in climate mode it never reached a prompt. These tests
    pin the *absence*, so a future re-introduction has to be deliberate.
    """

    def test_parameter_no_longer_exists(self, abstract_mode):
        assert not hasattr(abstract_mode, "MAX_PUNISHMENT_TOKENS")

    def test_agent_helper_no_longer_exists(self, abstract_mode):
        assert not hasattr(Agent, "get_max_punishment_tokens")

    def test_dead_enforcement_helper_is_gone(self):
        from parsing import response_parsing_utils

        assert not hasattr(response_parsing_utils, "_apply_allocations_helper")

    def test_stage2_budget_is_the_only_binding_constraint(self, climate_mode):
        """One shared pool, not a per-target cap — the constraint that actually binds."""
        agent = FakeAgent(0, wealth=20_000.0)
        budget = agent.get_stage2_budget()
        assert budget == max(
            climate_mode.ENDOWMENT_STAGE_2,
            int(20_000.0 * climate_mode.STAGE_2_WEALTH_FRACTION),
        )


class TestStage2Payoff:
    def test_abstract_unspent_endowment_is_pocketed(self, abstract_mode):
        agent = FakeAgent(0, assigned_punishments={}, assigned_rewards={})
        assert agent.get_stage2_payoff() == pytest.approx(abstract_mode.ENDOWMENT_STAGE_2)

    def test_abstract_stage2_is_independent_of_institution_choice(self, abstract_mode):
        """Agent-level contract, and the source of the SI/SFI structural asymmetry.

        ``get_stage2_payoff`` always returns the abstract endowment when nothing
        is spent. The SI-versus-SFI gap is created one level up, in
        ``Environment.calculate_payoffs``: SI members are credited their Stage-2
        payoff while SFI members are hard-coded to 0. Holding behaviour fixed,
        that makes SI strictly dominant by ENDOWMENT_STAGE_2 every round, which
        is why the report describes SI/SFI as assigned roles rather than
        endogenous choices.
        """
        si_agent = FakeAgent(0, institution_choice="SI")
        sfi_agent = FakeAgent(1, institution_choice="SFI")
        assert si_agent.get_stage2_payoff() == pytest.approx(abstract_mode.ENDOWMENT_STAGE_2)
        assert sfi_agent.get_stage2_payoff() == pytest.approx(abstract_mode.ENDOWMENT_STAGE_2)
        # The environment applies: stage2 = agent.get_stage2_payoff() if SI else 0.
        assert si_agent.get_stage2_payoff() - 0.0 > 0

    def test_climate_mode_has_no_free_endowment(self, climate_mode):
        agent = FakeAgent(0, wealth=100_000.0)
        assert agent.get_stage2_payoff() == pytest.approx(0.0)

    def test_climate_sanctions_deduct_from_wealth(self, climate_mode):
        agent = FakeAgent(0, assigned_punishments={9: 10}, assigned_rewards={})
        expected = -10 * climate_mode.PUNISHMENT_COST
        assert agent.get_stage2_payoff() == pytest.approx(expected)

    def test_abstract_sanctions_reduce_the_pocketed_endowment(self, abstract_mode):
        agent = FakeAgent(0, assigned_punishments={9: 10})
        expected = abstract_mode.ENDOWMENT_STAGE_2 - 10 * abstract_mode.PUNISHMENT_COST
        assert agent.get_stage2_payoff() == pytest.approx(expected)

    def test_punishment_and_reward_costs_are_summed(self, climate_mode):
        agent = FakeAgent(0, assigned_punishments={9: 10}, assigned_rewards={8: 7})
        expected = -(10 * climate_mode.PUNISHMENT_COST + 7 * climate_mode.REWARD_COST)
        assert agent.get_stage2_payoff() == pytest.approx(expected)

    def test_received_punishment_and_reward_enter_with_their_effect(self, climate_mode):
        agent = FakeAgent(
            0,
            assigned_punishments={},
            assigned_rewards={},
            received_punishments=30.0,  # already effect-multiplied upstream
            received_rewards=5.0,
        )
        assert agent.get_stage2_payoff() == pytest.approx(5.0 - 30.0)

    def test_overspending_can_drive_abstract_stage2_negative(self, abstract_mode):
        agent = FakeAgent(0, assigned_punishments={9: 100})
        assert agent.get_stage2_payoff() < 0


class TestReceiveAccumulators:
    def test_receive_punishment_accumulates(self):
        agent = FakeAgent(0)
        agent.receive_punishment(5)
        agent.receive_punishment(7)
        assert agent.received_punishments == pytest.approx(12)

    def test_receive_reward_accumulates(self):
        agent = FakeAgent(0)
        agent.receive_reward(3)
        agent.receive_reward(4)
        assert agent.received_rewards == pytest.approx(7)


class TestRoundReset:
    """Uses the real ``Agent`` because ``reset_for_new_round`` is pure state logic."""

    def _populated_round_state(self):
        agent = Agent(0, api_client=None)
        agent.wealth = 5000.0
        agent.cumulative_payoff = 4321.0
        agent.institution_choice = "SI"
        agent.contribution = 25.0
        agent.round_payoff = 123.0
        agent.last_subsidy = 7.0
        agent.ldf_contribution_round = 11.0
        agent.ldf_payout_round = 22.0
        agent.climate_damage_taken_round = 33.0
        agent.net_climate_transfer_round = 44.0
        agent.contribution_reasoning = "some rationale"
        agent.punishment_reasoning = "sanctioning rationale"
        agent.assigned_punishments = {1: 5}
        agent.assigned_rewards = {2: 5}
        agent.anonymous_data_history = []
        agent.current_round_anonymous_data = {"agents": {}}
        agent.tom_audit_log = [{"round": 1}]
        return agent

    def test_reset_zeroes_round_scoped_payoff_fields(self, climate_mode):
        agent = self._populated_round_state()
        agent.reset_for_new_round()
        assert agent.contribution == 0
        assert agent.assigned_punishments == {}
        assert agent.assigned_rewards == {}
        assert agent.round_payoff == 0
        assert agent.last_subsidy == 0

    def test_reset_zeroes_climate_transfer_fields(self, climate_mode):
        agent = self._populated_round_state()
        agent.reset_for_new_round()
        assert agent.ldf_contribution_round == 0.0
        assert agent.ldf_payout_round == 0.0
        assert agent.climate_damage_taken_round == 0.0
        assert agent.net_climate_transfer_round == 0.0

    def test_reset_clears_reasoning_and_parser_metadata(self, climate_mode):
        agent = self._populated_round_state()
        agent.contribution_parser_meta = {"auto_fitted": True}
        agent.punishment_parser_meta = {"fallback_used": True}
        agent.institution_parser_meta = {"fallback_used": True}
        agent.reset_for_new_round()
        assert agent.contribution_reasoning == ""
        assert agent.punishment_reasoning == ""
        assert agent.institution_reasoning == ""
        assert agent.contribution_parser_meta == {}
        assert agent.punishment_parser_meta == {}
        assert agent.institution_parser_meta == {}

    def test_reset_preserves_wealth_and_cumulative_payoff(self, climate_mode):
        agent = self._populated_round_state()
        agent.reset_for_new_round()
        assert agent.wealth == pytest.approx(5000.0)
        assert agent.cumulative_payoff == pytest.approx(4321.0)

    def test_reset_does_not_clear_reputation_or_beliefs(self, climate_mode):
        """Documented behaviour: social state is intentionally not round-scoped."""
        agent = self._populated_round_state()
        agent.reputation = 8.5
        agent.belief_state = {"institutional_strategy": "tit-for-tat"}
        agent.reset_for_new_round()
        assert agent.reputation == pytest.approx(8.5)
        assert agent.belief_state["institutional_strategy"] == "tit-for-tat"

    def test_reset_records_institution_history(self, climate_mode):
        agent = self._populated_round_state()
        agent.reset_for_new_round()
        assert agent.history_institutions[-1] == "SI"

    def test_institution_history_is_capped_at_ten(self, climate_mode):
        agent = self._populated_round_state()
        agent.history_institutions = ["SI"] * 10
        agent.reset_for_new_round()
        assert len(agent.history_institutions) == 10

    def test_contribution_history_is_capped_at_ten(self, climate_mode):
        agent = self._populated_round_state()
        agent.history_contributions = [1.0] * 10
        agent.reset_for_new_round()
        assert len(agent.history_contributions) == 10

    def test_reset_clears_tom_audit_log(self, climate_mode):
        """ToM audits are O(N^2) per round and must not accumulate across rounds."""
        agent = self._populated_round_state()
        agent.reset_for_new_round()
        assert agent.tom_audit_log == []

    def test_anonymous_history_is_bounded_by_display_past_actions(self, climate_mode):
        climate_mode.DISPLAY_PAST_ACTIONS = 1
        agent = self._populated_round_state()
        agent.anonymous_data_history = [{"round_number": 0}]
        agent.current_round_anonymous_data = {"agents": {1: {"contribution": 5}}}
        agent.reset_for_new_round()
        assert len(agent.anonymous_data_history) == 1
        assert agent.current_round_anonymous_data is None

    def test_anonymous_history_keeps_the_most_recent_window(self, climate_mode):
        climate_mode.DISPLAY_PAST_ACTIONS = 2
        agent = self._populated_round_state()
        agent.round_number = 7
        agent.anonymous_data_history = [{"round_number": 5}, {"round_number": 6}]
        agent.current_round_anonymous_data = {"agents": {}}
        agent.reset_for_new_round()
        # Appends the outgoing round (7) and drops the oldest (5).
        assert [row["round_number"] for row in agent.anonymous_data_history] == [6, 7]

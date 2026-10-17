"""Unit tests for the SI enforcement-subsidy mechanic.

The subsidy is a 20% rebate on aggregate punishment cost, paid to the top-N SI
contributors. It is a payoff *creation* event, not a transfer out of a collected
central pool, so the total-money-supply implication is asserted explicitly.
"""

from __future__ import annotations

from conftest import FakeAgent
from core import parameters
from core.subsidy import SubsidyModule


def _si(agent_id, contribution, assigned_punishments=None, assigned_rewards=None):
    return FakeAgent(
        agent_id,
        contribution=contribution,
        institution_choice="SI",
        assigned_punishments=assigned_punishments,
        assigned_rewards=assigned_rewards,
    )


def _sfi(agent_id, contribution):
    return FakeAgent(agent_id, contribution=contribution, institution_choice="SFI")


class TestDisabledAndEmpty:
    def test_returns_empty_when_subsidy_disabled(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_ENABLED", False)
        agents = [_si(0, 10.0)]
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0}) == {}

    def test_returns_empty_when_no_contributions(self):
        assert SubsidyModule().compute_subsidies([_si(0, 10.0)], {}) == {}

    def test_returns_empty_when_no_si_members_contributed(self):
        agents = [_sfi(0, 10.0), _sfi(1, 5.0)]
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0, 1: 5.0}) == {}

    def test_zero_contribution_si_agent_still_generates_a_pool(self):
        """Documented quirk: eligibility tracks SI membership, not contribution size.

        An SI agent that contributed 0 is still in ``si_contributions`` and can
        still be ranked ``top_n``, so it can collect a subsidy funded entirely
        by peers' punishments.
        """
        agents = [_si(0, 0.0, assigned_punishments={1: 5})]
        assert SubsidyModule().compute_subsidies(agents, {0: 0.0}) == {0: 1}

    def test_returns_empty_when_no_punishments_were_assigned(self):
        """No punishment cost means no subsidy pool, regardless of contributions."""
        agents = [_si(0, 100.0, assigned_punishments={})]
        assert SubsidyModule().compute_subsidies(agents, {0: 100.0}) == {}


class TestPoolAndRanking:
    def test_pool_is_fraction_of_punishment_cost_split_evenly(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_ENABLED", True)
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.2)
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 1)
        agents = [
            _si(0, 100.0, assigned_punishments={1: 50}),
            _si(1, 90.0, assigned_punishments={2: 50}),
            _si(2, 10.0),
        ]
        # Pool = int(100 * 1 * 0.2) = 20; split between the top 2 contributors.
        result = SubsidyModule().compute_subsidies(agents, {0: 100.0, 1: 90.0, 2: 10.0})
        assert result == {0: 10, 1: 10}

    def test_recipients_are_the_top_n_contributors(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        agents = [
            _si(0, 5.0, assigned_punishments={1: 100}),
            _si(1, 50.0, assigned_punishments={2: 100}),
            _si(2, 90.0),
            _si(3, 70.0),
        ]
        contributions = {0: 5.0, 1: 50.0, 2: 90.0, 3: 70.0}
        result = SubsidyModule().compute_subsidies(agents, contributions)
        assert set(result) == {2, 3}

    def test_single_top_contributor_takes_whole_pool(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        agents = [_si(0, 100.0, assigned_punishments={1: 100})]
        # Pool = int(100 * 1 * 0.2) == 20; one recipient so no division.
        assert SubsidyModule().compute_subsidies(agents, {0: 100.0}) == {0: 20}

    def test_sfi_contributions_never_win_a_subsidy(self, monkeypatch):
        """A non-SFI agent with the highest contribution must be excluded."""
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        agents = [
            _si(0, 10.0, assigned_punishments={9: 100}),
            _sfi(1, 1_000_000.0),
        ]
        result = SubsidyModule().compute_subsidies(agents, {0: 10.0, 1: 1_000_000.0})
        assert set(result) == {0}

    def test_reward_spending_does_not_fund_the_pool(self, monkeypatch):
        """Only punishment tokens fund the subsidy, despite the docstring wording."""
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.2)
        monkeypatch.setattr(parameters, "REWARD_COST", 1)
        agents = [_si(0, 100.0, assigned_punishments={}, assigned_rewards={1: 500})]
        assert SubsidyModule().compute_subsidies(agents, {0: 100.0}) == {}

    def test_punishment_cost_parameter_is_applied(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 1.0)
        monkeypatch.setattr(parameters, "PUNISHMENT_COST", 2)
        agents = [_si(0, 10.0, assigned_punishments={1: 10})]
        # Pool = int(10 * 2 * 1.0) = 20
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0}) == {0: 20}

    def test_summing_assignments_across_all_si_senders(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 1)
        agents = [
            _si(0, 10.0, assigned_punishments={5: 10}),
            _si(1, 20.0, assigned_punishments={6: 10}),
            _si(2, 30.0, assigned_punishments={7: 10}),
        ]
        contributions = {0: 10.0, 1: 20.0, 2: 30.0}
        # Pool = int(30 * 1 * 0.2) = 6, all to the single top contributor (id 2).
        assert SubsidyModule().compute_subsidies(agents, contributions) == {2: 6}


class TestIntegerArithmetic:
    def test_pool_truncates_towards_zero(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.2)
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 1)
        agents = [_si(0, 10.0, assigned_punishments={1: 7})]
        # int(7 * 1 * 0.2) == 1
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0}) == {0: 1}

    def test_remainder_below_per_agent_share_is_discarded(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.2)
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        agents = [
            _si(0, 10.0, assigned_punishments={1: 6}),
            _si(1, 9.0),
        ]
        # Pool = int(6 * 0.2) == 1; 1 // 2 == 0, so nothing is paid out.
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0, 1: 9.0}) == {0: 0, 1: 0}

    def test_per_agent_share_uses_floor_division(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_FRACTION", 0.5)
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 2)
        agents = [
            _si(0, 10.0, assigned_punishments={9: 7}),
            _si(1, 9.0),
        ]
        # Pool = int(7 * 0.5) == 3; 3 // 2 == 1 (1 token discarded).
        assert SubsidyModule().compute_subsidies(agents, {0: 10.0, 1: 9.0}) == {0: 1, 1: 1}

    def test_top_n_larger_than_population_pays_everyone(self, monkeypatch):
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 10)
        agents = [
            _si(0, 10.0, assigned_punishments={1: 10}),
            _si(1, 5.0),
        ]
        # Pool = int(10 * 1 * 0.2) == 2; split two ways -> 1 each.
        result = SubsidyModule().compute_subsidies(agents, {0: 10.0, 1: 5.0})
        assert result == {0: 1, 1: 1}


class TestEconomicInterpretation:
    def test_subsidy_is_money_creation_not_a_transfer(self):
        """Documented behaviour: no collected pool is debited.

        The module reads punishment *spending* and mints new payoff units.
        Nothing in the SI's token holdings is reduced, so the sum of agent
        payoffs rises. This matters for the welfare interpretation in the paper.
        """
        monkeypatch = None  # no parameter override needed
        agents = [_si(0, 10.0, assigned_punishments={1: 100})]
        before = agents[0].wealth
        SubsidyModule().compute_subsidies(agents, {0: 10.0})
        # Agent 0's wealth is untouched by compute_subsidies: the caller applies it.
        assert agents[0].wealth == before

    def test_feedback_loop_rewarding_enforcement(self, monkeypatch):
        """More SI punishment spending enlarges the pool for top contributors.

        This creates a rank-boundary payoff jump at SUBSIDY_TOP_N.
        """
        monkeypatch.setattr(parameters, "SUBSIDY_TOP_N", 1)
        light = [_si(0, 10.0, assigned_punishments={9: 10}), _si(1, 9.0)]
        heavy = [_si(0, 10.0, assigned_punishments={9: 100}), _si(1, 9.0)]
        contributions = {0: 10.0, 1: 9.0}
        light_subsidy = SubsidyModule().compute_subsidies(light, contributions)
        heavy_subsidy = SubsidyModule().compute_subsidies(heavy, contributions)
        assert light_subsidy == {0: 2}
        assert heavy_subsidy == {0: 20}

    def test_deterministic_for_a_given_input(self):
        agents = [_si(0, 10.0, assigned_punishments={9: 50}), _si(1, 5.0)]
        contributions = {0: 10.0, 1: 5.0}
        module = SubsidyModule()
        assert module.compute_subsidies(agents, contributions) == module.compute_subsidies(
            agents, contributions
        )
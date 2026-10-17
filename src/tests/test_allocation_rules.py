"""The allocation-rule registry and the governance levels built on it.

The LDF's allocation rule was a hardcoded constant. These tests pin the two things
that make the registry safe to expose to agents:

* the ``fixed`` path reproduces the original arithmetic exactly, so the G0
  reference arm is byte-identical to the historical condition; and
* the three hard constraints hold for every rule, no matter which one agents elect.

The second is the point of the module. An assembly can choose the *mechanism*; it
cannot choose to over-draw the pool, over-cover the damage, or pay itself.
"""

from __future__ import annotations

import pytest

from core import parameters
from core.allocation_rules import (
    ALLOCATION_RULE_NAMES,
    DEFAULT_RULE,
    REGISTRY,
    UnknownAllocationRule,
    allocate,
    default_eligibility,
    describe_registry,
    drop_self_payments,
    normalise_rule_name,
    resolve_rule,
)
from core.loss_damage_fund import LossDamageFund


class FakeAgent:
    def __init__(
        self,
        agent_id,
        *,
        agent_group="developing",
        wealth=1_000_000.0,
        historical_emissions=0.30,
        contribution_capacity=0.10,
    ):
        self.agent_id = agent_id
        self.agent_group = agent_group
        self.wealth = wealth
        self.historical_emissions = historical_emissions
        self.contribution_capacity = contribution_capacity
        self.contribution = 0.0
        self.ldf_contribution_round = 0.0
        self.ldf_payout_round = 0.0
        self.board_member_allocating = False


@pytest.fixture
def coverage(monkeypatch):
    monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90, raising=False)
    monkeypatch.setattr(parameters, "LDF_PAYOUT_DAMAGE_WEIGHT", 1.0, raising=False)
    monkeypatch.setattr(parameters, "LDF_EQUITY_WEIGHT", 0.0, raising=False)


class TestRegistry:
    def test_contains_the_documented_menu(self):
        assert set(ALLOCATION_RULE_NAMES) == {
            "damage_proportional",
            "need_equality",
            "poverty_tilted",
            "cbdr",
            "capacity_pooled",
            "board_discretion",
        }

    def test_default_is_the_original_rule(self):
        assert DEFAULT_RULE == "damage_proportional"

    def test_every_rule_documents_theory_it_represents(self):
        for name, rule in REGISTRY.items():
            assert rule.description.strip(), name
            assert rule.theory.strip(), name

    @pytest.mark.parametrize(
        "given,expected",
        [
            ("damage_proportional", "damage_proportional"),
            ("damage", "damage_proportional"),
            ("CBDR", "cbdr"),
            ("emissions", "cbdr"),
            ("equality", "need_equality"),
            ("per-capita", "need_equality"),
            ("solidarity", "capacity_pooled"),
            ("board", "board_discretion"),
            ("  Need_Equality  ", "need_equality"),
        ],
    )
    def test_aliases_resolve(self, given, expected):
        assert normalise_rule_name(given) == expected

    def test_unknown_name_returns_none(self):
        assert normalise_rule_name("random_thing") is None

    def test_unknown_name_raises_with_the_menu(self):
        with pytest.raises(UnknownAllocationRule, match="damage_proportional"):
            resolve_rule("random_thing")

    def test_none_falls_back_to_the_default(self):
        assert resolve_rule(None).name == DEFAULT_RULE

    def test_description_order_is_deterministic_for_a_seed(self):
        assert list(describe_registry(order_seed=7)) == list(describe_registry(order_seed=7))

    def test_description_order_is_not_the_registry_order_under_a_seed(self):
        assert list(describe_registry(order_seed=11)) != list(REGISTRY)


class TestFixedPathIsByteIdentical:
    """``LDF_GOVERNANCE_MODE == "fixed"`` must reproduce the original arithmetic."""

    def test_zero_equity_weight_leaves_damage_proportional_unchanged(self, coverage):
        agents = [FakeAgent(0), FakeAgent(1)]
        damages = {0: 100_000.0, 1: 50_000.0}
        payouts = allocate(
            "damage_proportional",
            [0, 1],
            damages,
            90_000.0,
            agents_by_id={a.agent_id: a for a in agents},
        )
        total = sum(payouts.values())
        # Proportional to damage, then capped at 90% of each claimant's damage.
        assert payouts[0] == pytest.approx(total * 100_000 / 150_000)
        assert payouts[1] == pytest.approx(total * 50_000 / 150_000)
        assert payouts[0] <= 0.90 * 100_000.0 + 1e-6

    def test_fund_pools_drain_in_the_historical_order(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 100_000.0
        agents = [FakeAgent(0), FakeAgent(1), FakeAgent(2)]
        damages = {0: 10_000.0, 1: 10_000.0, 2: 10_000.0}
        payouts = fund.distribute_payouts(agents, damages)
        # Equal damage, equal pool share, served greedily in agent order.
        assert list(payouts) == [0, 1, 2]
        assert payouts[0] == pytest.approx(payouts[1])
        assert payouts[1] == pytest.approx(payouts[2])

    def test_zero_total_need_returns_an_empty_mapping(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 5_000.0
        assert fund.distribute_payouts([FakeAgent(0)], {0: 0.0}) == {}

    def test_eligible_agent_gets_a_zero_key_when_capped_out(self, coverage):
        """The historical return value carried a zero key; consumers rely on it."""
        fund = LossDamageFund()
        fund.pool_balance = 1_000.0
        payouts = fund.distribute_payouts([FakeAgent(0), FakeAgent(1)], {0: 1_000_000.0, 1: 0.0})
        assert payouts[1] == 0.0

    def test_default_eligibility_is_developing_only(self):
        agents = [FakeAgent(0, agent_group="developing"), FakeAgent(1, agent_group="developed")]
        assert default_eligibility(agents) == [0]


class TestHardConstraints:
    """Constraints that hold regardless of which rule agents elect."""

    @pytest.mark.parametrize("rule_name", list(ALLOCATION_RULE_NAMES))
    def test_no_payout_exceeds_the_pool(self, rule_name, coverage):
        agents = {i: FakeAgent(i) for i in range(4)}
        damages = dict.fromkeys(range(4), 100000.0)
        board = dict.fromkeys(range(4), 25000.0) if rule_name == "board_discretion" else None
        payouts = allocate(
            rule_name, [0, 1, 2, 3], damages, 10_000.0, agents, board_allocation=board
        )
        assert sum(payouts.values()) <= 10_000.0 + 1e-9

    @pytest.mark.parametrize("rule_name", list(ALLOCATION_RULE_NAMES))
    def test_no_payout_exceeds_the_coverage_cap(self, rule_name, coverage):
        agents = {i: FakeAgent(i) for i in range(4)}
        damages = dict.fromkeys(range(4), 100000.0)
        board = dict.fromkeys(range(4), 90000.0) if rule_name == "board_discretion" else None
        payouts = allocate(
            rule_name, [0, 1, 2, 3], damages, 1_000_000.0, agents, board_allocation=board
        )
        for claimant, amount in payouts.items():
            assert amount <= 0.90 * damages[claimant] + 1e-6

    def test_board_cannot_pay_itself(self, coverage):
        agents = {0: FakeAgent(0), 1: FakeAgent(1)}
        agents[0].board_member_allocating = True
        payouts = allocate(
            "board_discretion",
            [0, 1],
            {0: 100_000.0, 1: 100_000.0},
            50_000.0,
            agents,
            board_allocation={0: 50_000.0, 1: 50_000.0},
        )
        assert 0 not in payouts
        assert payouts.get(1, 0.0) > 0

    def test_drop_self_payments_is_explicit(self):
        assert drop_self_payments({0: 10.0, 1: 20.0}, [0]) == {1: 20.0}

    def test_board_discretion_without_a_board_pays_nothing(self, coverage):
        agents = {0: FakeAgent(0)}
        assert allocate("board_discretion", [0], {0: 100.0}, 1_000.0, agents) == {}

    def test_zero_pool_pays_nothing(self, coverage):
        assert allocate("damage_proportional", [0], {0: 100.0}, 0.0, {0: FakeAgent(0)}) == {}

    def test_zero_damage_claimants_are_not_paid(self, coverage):
        agents = {0: FakeAgent(0), 1: FakeAgent(1)}
        payouts = allocate("damage_proportional", [0, 1], {0: 100.0, 1: 0.0}, 1_000.0, agents)
        assert set(payouts) == {0}


class TestRuleSemantics:
    """Each rule must actually implement the mechanism it advertises.

    Pools are kept small relative to each claimant's coverage cap so the cap does
    not bind: otherwise every rule collapses to "whoever was capped", which is
    the coverage mechanic rather than the mechanism under test.
    """

    def _weights(self, rule_name, agents, damages, pool=10_000.0):
        return allocate(rule_name, list(damages), damages, pool, agents)

    def test_need_equality_ignores_damage(self, coverage):
        agents = {0: FakeAgent(0), 1: FakeAgent(1)}
        payouts = self._weights("need_equality", agents, {0: 100_000.0, 1: 400_000.0})
        assert payouts[0] == pytest.approx(payouts[1])

    def test_damage_proportional_does_track_damage(self, coverage):
        """The control: the baseline rule must be sensitive where equality is not."""
        agents = {0: FakeAgent(0), 1: FakeAgent(1)}
        payouts = self._weights("damage_proportional", agents, {0: 100_000.0, 1: 400_000.0})
        assert payouts[0] < payouts[1]

    def test_cbdr_weights_by_historical_emissions(self, coverage):
        """Barrett's pattern: the highest emitter draws the largest share."""
        agents = {
            0: FakeAgent(0, historical_emissions=1.50),
            1: FakeAgent(1, historical_emissions=0.30),
        }
        payouts = self._weights("cbdr", agents, {0: 100_000.0, 1: 100_000.0})
        assert payouts[0] == pytest.approx(payouts[1] * 5.0, rel=1e-6)

    def test_cbdr_is_not_damage_proportional(self, coverage):
        """Same damage, different emissions, so the two rules must disagree."""
        agents = {
            0: FakeAgent(0, historical_emissions=1.50),
            1: FakeAgent(1, historical_emissions=0.30),
        }
        damages = {0: 100_000.0, 1: 100_000.0}
        cbdr = self._weights("cbdr", agents, damages)
        baseline = self._weights("damage_proportional", agents, damages)
        assert cbdr[0] != pytest.approx(baseline[0])

    def test_capacity_pooled_weights_by_capacity(self, coverage):
        agents = {
            0: FakeAgent(0, contribution_capacity=1.00),
            1: FakeAgent(1, contribution_capacity=0.10),
        }
        payouts = self._weights("capacity_pooled", agents, {0: 100_000.0, 1: 100_000.0})
        assert payouts[0] == pytest.approx(payouts[1] * 10.0, rel=1e-6)

    def test_poverty_tilted_favours_the_poorer_when_equity_is_on(self, coverage, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_EQUITY_WEIGHT", 2.0, raising=False)
        agents = {
            0: FakeAgent(0, wealth=100_000.0),
            1: FakeAgent(1, wealth=1_000_000.0),
        }
        payouts = self._weights("poverty_tilted", agents, {0: 100_000.0, 1: 100_000.0})
        assert payouts[0] > payouts[1]

    def test_poverty_tilted_degenerates_at_zero_equity_weight(self, coverage):
        agents = {
            0: FakeAgent(0, wealth=100_000.0),
            1: FakeAgent(1, wealth=1_000_000.0),
        }
        payouts = self._weights("poverty_tilted", agents, {0: 100_000.0, 1: 100_000.0})
        assert payouts[0] == pytest.approx(payouts[1])

    def test_damage_proportional_tracks_damage(self, coverage):
        agents = {0: FakeAgent(0), 1: FakeAgent(1)}
        payouts = self._weights("damage_proportional", agents, {0: 300_000.0, 1: 100_000.0})
        assert payouts[0] == pytest.approx(payouts[1] * 3.0, rel=1e-6)


class TestGovernanceGating:
    def test_fixed_mode_never_records_a_rule_change(self):
        fund = LossDamageFund()
        assert fund.set_elected_rule("cbdr", round_number=5) is False
        assert fund.governance["elected_rule"] == DEFAULT_RULE
        assert fund.governance["rule_change_history"] == []

    def test_elected_rule_is_recorded_when_governance_is_on(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_GOVERNANCE_MODE", "election", raising=False)
        fund = LossDamageFund()
        fund.governance["mode"] = "election"
        assert fund.set_elected_rule("cbdr", round_number=10) is True
        assert fund.governance["elected_rule"] == "cbdr"
        assert fund.governance["rule_change_history"][0]["from"] == DEFAULT_RULE

    def test_claim_filter_restricts_payouts(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 100_000.0
        agents = [FakeAgent(0), FakeAgent(1)]
        fund.set_accepted_claimants([0], round_number=7)
        payouts = fund.distribute_payouts(agents, {0: 100_000.0, 1: 100_000.0})
        assert payouts[0] > 0
        assert payouts[1] == 0.0

    def test_claim_filter_does_not_leak_into_the_next_round(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 200_000.0
        agents = [FakeAgent(0), FakeAgent(1)]
        fund.set_accepted_claimants([0], round_number=7)
        fund.distribute_payouts(agents, {0: 100_000.0, 1: 100_000.0})
        second = fund.distribute_payouts(agents, {0: 100_000.0, 1: 100_000.0})
        assert second[1] > 0

    def test_board_allocation_does_not_leak_into_the_next_round(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 300_000.0
        agents = [FakeAgent(0), FakeAgent(1)]
        fund.governance["elected_rule"] = "board_discretion"
        fund.set_board_allocation({0: 10_000.0, 1: 10_000.0}, round_number=7)
        fund.distribute_payouts(agents, {0: 100_000.0, 1: 100_000.0})
        # The override is per-round; once the assembly elects a formula rule again
        # the next shock round is allocated by the formula.
        fund.governance["elected_rule"] = "damage_proportional"
        second = fund.distribute_payouts(agents, {0: 100_000.0, 1: 100_000.0})
        assert second[0] == pytest.approx(second[1])

    def test_pool_never_goes_negative(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 10.0
        fund.distribute_payouts([FakeAgent(0)], {0: 1e12})
        assert fund.pool_balance >= 0.0

    def test_pool_identity_holds(self, coverage):
        fund = LossDamageFund()
        fund.pool_balance = 1_000_000.0
        agents = [FakeAgent(0), FakeAgent(1)]
        start = fund.pool_balance
        paid = sum(fund.distribute_payouts(agents, {0: 500_000.0, 1: 250_000.0}).values())
        assert fund.pool_balance == pytest.approx(start - paid)

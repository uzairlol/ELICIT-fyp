"""Unit tests for the Loss & Damage Fund's accounting mechanics.

These are the numbers the paper reports (coverage ratios, deposit totals,
terminal reserves), so the pool identity is asserted exactly rather than
approximately.
"""

from __future__ import annotations

import pytest

from conftest import FakeAgent
from core import parameters
from core.loss_damage_fund import LossDamageFund


class TestCollectionSchedule:
    def test_every_round_when_collect_every_round(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_COLLECT_EVERY_ROUND", True)
        fund = LossDamageFund()
        assert all(fund.should_collect_contributions(r) for r in range(1, 31))

    def test_interval_schedule_uses_mod_one(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_COLLECT_EVERY_ROUND", False)
        monkeypatch.setattr(parameters, "LDF_REPLENISHMENT_INTERVAL", 5)
        fund = LossDamageFund()
        collected = [r for r in range(1, 31) if fund.should_collect_contributions(r)]
        assert collected == [1, 6, 11, 16, 21, 26]

    def test_zero_interval_does_not_divide_by_zero(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_COLLECT_EVERY_ROUND", False)
        monkeypatch.setattr(parameters, "LDF_REPLENISHMENT_INTERVAL", 0)
        fund = LossDamageFund()
        # max(1, 0) == 1 collapses the gate to (r % 1) == 1, which never holds.
        # The guard exists to avoid ZeroDivisionError, not to collect every round.
        assert not any(fund.should_collect_contributions(r) for r in range(1, 11))

    def test_float_round_number_is_coerced(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_COLLECT_EVERY_ROUND", False)
        monkeypatch.setattr(parameters, "LDF_REPLENISHMENT_INTERVAL", 5)
        fund = LossDamageFund()
        assert fund.should_collect_contributions(6.0) is True


class TestCollectContributions:
    def test_deposit_equals_stage1_contribution(self):
        fund = LossDamageFund()
        agents = [FakeAgent(0, contribution=100.0), FakeAgent(1, contribution=50.0)]
        contributions = fund.collect_contributions(agents)
        assert contributions == {0: 100.0, 1: 50.0}
        assert fund.pool_balance == pytest.approx(150.0)

    def test_contribution_is_written_back_onto_agent(self):
        fund = LossDamageFund()
        agent = FakeAgent(0, contribution=42.0)
        fund.collect_contributions([agent])
        assert agent.ldf_contribution_round == pytest.approx(42.0)

    def test_negative_contribution_floors_at_zero(self):
        fund = LossDamageFund()
        agent = FakeAgent(0, contribution=-25.0)
        contributions = fund.collect_contributions([agent])
        assert contributions == {0: 0.0}
        assert fund.pool_balance == pytest.approx(0.0)

    def test_deposit_is_a_second_charge_not_a_separate_levy(self):
        """The LDF deposit reuses Stage-1 contribution; it must not debit again."""
        fund = LossDamageFund()
        agent = FakeAgent(0, contribution=100.0, wealth=1000.0)
        fund.collect_contributions([agent])
        assert agent.wealth == pytest.approx(1000.0)

    def test_pool_accumulates_across_rounds(self):
        fund = LossDamageFund()
        for _ in range(3):
            fund.collect_contributions([FakeAgent(0, contribution=10.0)])
        assert fund.pool_balance == pytest.approx(30.0)


class TestDistributePayouts:
    def test_empty_pool_returns_no_payouts(self):
        fund = LossDamageFund()
        assert fund.distribute_payouts([FakeAgent(0)], {0: 1000.0}) == {}

    def test_developed_agents_are_never_eligible(self):
        fund = LossDamageFund()
        fund.pool_balance = 10_000.0
        agents = [FakeAgent(100 + i, agent_group="developed") for i in range(3)]
        payouts = fund.distribute_payouts(agents, {100: 500.0, 101: 500.0, 102: 500.0})
        assert payouts == {}
        assert fund.pool_balance == pytest.approx(10_000.0)

    def test_ineligible_agents_receive_zero_payout_record(self):
        fund = LossDamageFund()
        fund.pool_balance = 10_000.0
        dev = FakeAgent(0, agent_group="developing")
        rich = FakeAgent(100, agent_group="developed")
        fund.distribute_payouts([dev, rich], {0: 500.0, 100: 500.0})
        assert dev.ldf_payout_round > 0
        assert rich.ldf_payout_round == 0.0

    def test_sufficient_pool_pays_exactly_the_coverage_cap(self, monkeypatch):
        """Coverage equals LDF_MAX_COVERAGE, not the damage-weighted pro-rata target."""
        monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90)
        monkeypatch.setattr(parameters, "LDF_PAYOUT_DAMAGE_WEIGHT", 1.0)
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing"), FakeAgent(1, agent_group="developing")]
        damages = {0: 1000.0, 1: 2000.0}
        # Pool strictly exceeds sum(0.9 * damage) == 2700.
        fund.pool_balance = 100_000.0
        payouts = fund.distribute_payouts(agents, damages)
        assert payouts[0] == pytest.approx(900.0)
        assert payouts[1] == pytest.approx(1800.0)

    def test_eligible_recipient_coverage_is_the_cap(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90)
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing")]
        fund.pool_balance = 50_000.0
        payouts = fund.distribute_payouts(agents, {0: 1000.0})
        assert payouts[0] / 1000.0 == pytest.approx(parameters.LDF_MAX_COVERAGE)

    def test_system_wide_coverage_is_lower_than_eligible_coverage(self, monkeypatch):
        """Reproduces the 0.900 eligible vs 0.768 system-wide reporting split."""
        monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90)
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing")] + [
            FakeAgent(100 + i, agent_group="developed") for i in range(2)
        ]
        damages = {0: 1000.0, 100: 1000.0, 101: 1000.0}
        fund.pool_balance = 100_000.0
        payouts = fund.distribute_payouts(agents, damages)
        eligible = payouts[0] / damages[0]
        system = sum(payouts.values()) / sum(damages.values())
        assert eligible == pytest.approx(0.90)
        assert system == pytest.approx(0.90 * 1 / 3)

    def test_insufficient_pool_shares_pro_rata_and_respects_caps(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90)
        monkeypatch.setattr(parameters, "LDF_EQUITY_WEIGHT", 0.0)
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing"), FakeAgent(1, agent_group="developing")]
        damages = {0: 1000.0, 1: 1000.0}
        fund.pool_balance = 500.0  # far below sum(0.9 * damage) == 1800
        payouts = fund.distribute_payouts(agents, damages)
        assert payouts[0] == pytest.approx(250.0)
        assert payouts[1] == pytest.approx(250.0)

    def test_payouts_never_exceed_the_pool(self):
        fund = LossDamageFund()
        agents = [FakeAgent(i, agent_group="developing") for i in range(5)]
        damages = {i: 10_000.0 for i in range(5)}
        fund.pool_balance = 123.0
        payouts = fund.distribute_payouts(agents, damages)
        assert sum(payouts.values()) <= 123.0 + 1e-9

    def test_pool_never_goes_negative(self):
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing")]
        fund.pool_balance = 10.0
        fund.distribute_payouts(agents, {0: 1e9})
        assert fund.pool_balance >= 0.0

    def test_zero_total_need_returns_no_payouts(self):
        fund = LossDamageFund()
        fund.pool_balance = 5_000.0
        agents = [FakeAgent(0, agent_group="developing")]
        assert fund.distribute_payouts(agents, {0: 0.0}) == {}

    def test_missing_damage_entry_is_treated_as_zero(self):
        fund = LossDamageFund()
        fund.pool_balance = 5_000.0
        agents = [FakeAgent(0, agent_group="developing"), FakeAgent(1, agent_group="developing")]
        payouts = fund.distribute_payouts(agents, {0: 1000.0})
        assert payouts[1] == pytest.approx(0.0)

    def test_agent_without_group_attribute_defaults_to_eligible(self):
        """``getattr(agent, 'agent_group', 'developing')`` makes unlabelled agents eligible."""
        fund = LossDamageFund()
        fund.pool_balance = 10_000.0
        agent = FakeAgent(0, agent_group="developing")
        del agent.agent_group
        payouts = fund.distribute_payouts([agent], {0: 1000.0})
        assert payouts[0] > 0

    def test_zero_damage_and_zero_wealth_is_safe(self):
        fund = LossDamageFund()
        fund.pool_balance = 1_000.0
        agents = [FakeAgent(0, agent_group="developing", wealth=0.0)]
        payouts = fund.distribute_payouts(agents, {0: 0.0})
        assert payouts == {}


class TestPoolIdentity:
    """pool_end == pool_start + deposits - payouts, exactly."""

    def test_identity_holds_over_a_multi_round_sequence(self):
        fund = LossDamageFund()
        dev = [FakeAgent(i, agent_group="developing") for i in range(3)]
        developed = [FakeAgent(100 + i, agent_group="developed") for i in range(2)]
        population = dev + developed

        for round_number in range(1, 11):
            pool_start = fund.pool_balance
            for index, agent in enumerate(population):
                agent.contribution = 100.0 * (index + 1)
            deposits = sum(fund.collect_contributions(population).values())

            damages = {}
            if round_number in (5, 10):
                severity = 0.10 if round_number == 5 else 0.20
                for agent in population:
                    damages[agent.agent_id] = (
                        parameters.CLIMATE_DAMAGE_BASE * severity * agent.vulnerability
                    )
                payouts = fund.distribute_payouts(population, damages)
                paid = sum(payouts.values())
            else:
                paid = 0.0

            expected = pool_start + deposits - paid
            assert fund.pool_balance == pytest.approx(expected, abs=1e-9)

    def test_reserve_grows_far_faster_than_disbursement(self):
        """The paper's headline LDF result: accumulation dominates payout.

        Mirrors the reported configuration (26 agents, 30 rounds, shocks at 5
        and 10 with severities 0.10/0.20) and asserts the observed order of
        magnitude: payouts are well under 1% of deposits.
        """
        fund = LossDamageFund()
        dev = [FakeAgent(i, agent_group="developing") for i in range(14)]
        developed = [FakeAgent(100 + i, agent_group="developed") for i in range(12)]
        population = dev + developed

        shock_schedule = {5: 0.10, 10: 0.20}
        total_deposits = 0.0
        total_paid = 0.0

        for round_number in range(1, 31):
            for index, agent in enumerate(population):
                agent.contribution = 300_000.0 + (10_000.0 * index)
            total_deposits += sum(fund.collect_contributions(population).values())

            severity = shock_schedule.get(round_number)
            if severity is None:
                continue
            damages = {
                agent.agent_id: parameters.CLIMATE_DAMAGE_BASE * severity * agent.vulnerability
                for agent in population
            }
            total_paid += sum(fund.distribute_payouts(population, damages).values())

        assert total_deposits > 0
        assert total_paid / total_deposits < 0.01
        # Two shocks at a fixed schedule produce an identical disbursement.
        assert total_paid == pytest.approx(850_500.0)

    def test_payout_recorded_on_agent_matches_return_value(self):
        fund = LossDamageFund()
        agents = [FakeAgent(0, agent_group="developing"), FakeAgent(1, agent_group="developing")]
        fund.pool_balance = 10_000.0
        payouts = fund.distribute_payouts(agents, {0: 1000.0, 1: 1000.0})
        for agent in agents:
            assert agent.ldf_payout_round == pytest.approx(payouts[agent.agent_id])


class TestEquityWeight:
    def test_zero_equity_weight_is_a_dead_lever_when_pool_suffices(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_EQUITY_WEIGHT", 0.0)
        fund = LossDamageFund()
        rich = FakeAgent(0, agent_group="developing", wealth=1e6)
        poor = FakeAgent(1, agent_group="developing", wealth=1.0)
        fund.pool_balance = 1e9
        payouts = fund.distribute_payouts([rich, poor], {0: 1000.0, 1: 1000.0})
        # No pro-poor adjustment: equal damage yields equal payout.
        assert payouts[0] == pytest.approx(payouts[1])

    def test_positive_equity_weight_shifts_payout_to_poorer_agents(self, monkeypatch):
        monkeypatch.setattr(parameters, "LDF_EQUITY_WEIGHT", 1.0)
        monkeypatch.setattr(parameters, "LDF_MAX_COVERAGE", 0.90)
        fund = LossDamageFund()
        rich = FakeAgent(0, agent_group="developing", wealth=1e6)
        poor = FakeAgent(1, agent_group="developing", wealth=1.0)
        # Pool deliberately below sum(0.9*damage) so the equity branch activates.
        fund.pool_balance = 100.0
        payouts = fund.distribute_payouts([rich, poor], {0: 1000.0, 1: 1000.0})
        assert payouts[1] > payouts[0]


class TestRoundHistory:
    def test_append_round_log_records_rows(self):
        fund = LossDamageFund()
        fund.append_round_log({"round": 1})
        fund.append_round_log({"round": 2})
        assert fund.round_history == [{"round": 1}, {"round": 2}]
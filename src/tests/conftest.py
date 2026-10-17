"""Shared fixtures and lightweight fakes for the ELICIT test suite.

The fakes here mimic only the attributes that payoff, transfer and social
information code actually touches. Keeping them duck-typed (rather than
instantiating a real ``Agent``) avoids LLM calls and keeps the pure-logic
tests fast and hermetic.
"""

from __future__ import annotations

import pytest

from core import parameters


class FakeAgent:
    """Minimal stand-in for ``core.agent.Agent`` with controllable state."""

    def __init__(
        self,
        agent_id,
        *,
        wealth=1000.0,
        contribution=0.0,
        institution_choice="SFI",
        agent_group="developing",
        vulnerability=1.5,
        historical_emissions=0.3,
        contribution_capacity=0.1,
        assigned_punishments=None,
        assigned_rewards=None,
        received_punishments=0.0,
        received_rewards=0.0,
    ):
        self.agent_id = agent_id
        self.wealth = wealth
        self.cumulative_payoff = wealth
        self.contribution = contribution
        self.institution_choice = institution_choice
        self.agent_group = agent_group
        self.vulnerability = vulnerability
        self.historical_emissions = historical_emissions
        self.contribution_capacity = contribution_capacity
        self.assigned_punishments = dict(assigned_punishments or {})
        self.assigned_rewards = dict(assigned_rewards or {})
        self.received_punishments = received_punishments
        self.received_rewards = received_rewards
        self.ldf_contribution_round = 0.0
        self.ldf_payout_round = 0.0
        self.rule_of_law_blocks = 0
        self.contribution_reasoning = ""
        self.round_number = 1
        # Identity mapping: labels already carry real agent ids. Anonymity
        # behaviour is exercised by tests that set a non-empty mapping.
        self.anonymized_id_mapping: dict[int, int] = {}
        self.pseudonym_mapping: dict[int, int] = {}

    # Payoff helpers mirroring Agent's public surface -------------------------
    def _uses_climate_budget(self):
        from core.utils import uses_climate_budget

        return uses_climate_budget()

    def get_stage1_contribution_cap(self):
        if self._uses_climate_budget():
            return max(parameters.MIN_CONTRIBUTION, int(self.wealth))
        return parameters.ENDOWMENT_STAGE_1

    def get_stage1_payoff(self, group_size, total_group_contribution):
        if group_size > 0:
            earnings = (parameters.PUBLIC_GOOD_MULTIPLIER * total_group_contribution) / group_size
        else:
            earnings = 0
        if self._uses_climate_budget():
            return earnings - self.contribution
        return (self.get_stage1_contribution_cap() - self.contribution) + earnings

    def get_stage2_budget(self):
        if self._uses_climate_budget():
            return max(
                parameters.ENDOWMENT_STAGE_2,
                int(self.wealth * parameters.STAGE_2_WEALTH_FRACTION),
            )
        return parameters.ENDOWMENT_STAGE_2

    def get_stage2_payoff(self):
        spent = (
            sum(self.assigned_punishments.values()) * parameters.PUNISHMENT_COST
            + sum(self.assigned_rewards.values()) * parameters.REWARD_COST
        )
        if self._uses_climate_budget():
            return -spent + self.received_rewards - self.received_punishments
        remaining = parameters.ENDOWMENT_STAGE_2 - spent
        return remaining + self.received_rewards - self.received_punishments

    def receive_punishment(self, amount):
        self.received_punishments += amount

    def receive_reward(self, amount):
        self.received_rewards += amount

    def __repr__(self):  # pragma: no cover - debugging helper
        return f"FakeAgent({self.agent_id})"


class FakeClient:
    """OpenAI-compatible stub that replays a scripted response list."""

    def __init__(self, responses=None, deployment_name="fake-model"):
        self.responses = list(responses or [])
        self.deployment_name = deployment_name
        self.calls = []

    def send_request(self, prompt=None, max_attempts=1, request_label="", **kwargs):
        self.calls.append({"prompt": prompt, "kwargs": kwargs, "label": request_label})
        if not self.responses:
            raise AssertionError(f"FakeClient exhausted; unexpected call {request_label!r}")
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


# --------------------------------------------------------------------------
# Parameter-mode fixtures. Monkeypatch rather than mutate so tests that touch
# the same constants cannot leak state into each other.
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolate_parameters():
    """Snapshot and restore every module-level global on ``core.parameters``.

    ``parameters`` is a mutable module of globals by design — the democracy
    module writes into it, and the CLI writes whole configs into it. That is
    convenient in production and hazardous in a test suite: one test that runs a
    cell would otherwise leave ``NUM_AGENTS=26``, ``PROMPT_VARIANT=P2`` and
    ``CHAT_TEMPLATE_MODE=fixed`` behind for every test that runs after it.

    The symptom is not subtle flakiness, it is *wrong* results: a later test that
    believes it is in abstract mode is silently running in climate mode. So the
    snapshot is unconditional and automatic rather than left to each test.
    """
    snapshot = {
        name: getattr(parameters, name)
        for name in dir(parameters)
        if name.isupper() and not name.startswith("_")
    }
    try:
        yield parameters
    finally:
        for name, value in snapshot.items():
            setattr(parameters, name, value)
        for name in dir(parameters):
            if name.isupper() and not name.startswith("_") and name not in snapshot:
                delattr(parameters, name)


@pytest.fixture
def abstract_mode(monkeypatch):
    """Force abstract (token) budget mode with all climate features off."""
    monkeypatch.setattr(parameters, "SCENARIO", "abstract", raising=False)
    monkeypatch.setattr(parameters, "CLIMATE_SHOCK_ENABLED", False, raising=False)
    monkeypatch.setattr(parameters, "LDF_ENABLED", False, raising=False)
    return parameters


@pytest.fixture
def climate_mode(monkeypatch):
    """Force climate/LDF budget mode."""
    monkeypatch.setattr(parameters, "SCENARIO", "ldf", raising=False)
    monkeypatch.setattr(parameters, "CLIMATE_SHOCK_ENABLED", True, raising=False)
    monkeypatch.setattr(parameters, "LDF_ENABLED", True, raising=False)
    return parameters


@pytest.fixture
def developing_agents():
    """Four eligible ('developing') agents with ascending damage-relevant wealth."""

    def _build(count=4, base_wealth=1000.0, step=100.0):
        return [
            FakeAgent(
                i,
                wealth=base_wealth + (i * step),
                agent_group="developing",
            )
            for i in range(count)
        ]

    return _build


@pytest.fixture
def developed_agents():
    """Ineligible ('developed') agents that must never receive LDF payouts."""

    def _build(count=3, base_wealth=1000.0):
        return [
            FakeAgent(
                100 + i,
                wealth=base_wealth,
                agent_group="developed",
                vulnerability=0.3,
                historical_emissions=1.5,
                contribution_capacity=1.0,
            )
            for i in range(count)
        ]

    return _build

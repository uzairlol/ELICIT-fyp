# loss_damage_fund.py

from typing import Any

from core import parameters
from core.allocation_rules import (
    allocate,
    default_eligibility,
)


class LossDamageFund:
    """Persistent Loss & Damage Fund for climate-shock compensation."""

    def __init__(self):
        self.pool_balance = 0.0
        self.round_history: list[dict[str, Any]] = []
        # Governance state. Empty under LDF_GOVERNANCE_MODE == "fixed"; populated
        # by the elected rule, the payout board and the claim ledger otherwise.
        self.governance: dict[str, Any] = {
            "mode": str(getattr(parameters, "LDF_GOVERNANCE_MODE", "fixed")),
            "elected_rule": str(getattr(parameters, "LDF_ALLOCATION_RULE", "damage_proportional")),
            "rule_change_history": [],
            "board_allocations": [],
            "claims": [],
        }
        # Per-round payables supplied by the governance layer (D5 board / D6
        # adjudication). Both default to None, which routes the fixed path
        # straight through the formula.
        self._board_allocation: dict[int, float] | None = None
        self._accepted_claimants: set[int] | None = None

    def _safe_div(self, num, den):
        return num / den if den else 0.0

    def should_collect_contributions(self, round_number):
        """
        Determine whether this round is a replenishment round.
        """
        if getattr(parameters, "LDF_COLLECT_EVERY_ROUND", False):
            return True

        interval = max(1, int(getattr(parameters, "LDF_REPLENISHMENT_INTERVAL", 1)))
        return (int(round_number) % interval) == 1

    def _contribution_amount(self, agent: Any) -> float:
        """
        Voluntary contribution amount.

        The agent chooses a round contribution elsewhere in the simulation.
        """
        return max(0.0, float(getattr(agent, "contribution", 0.0)))

    def collect_contributions(self, agents: list[Any]) -> dict[int, float]:
        """Collect one-round contributions and return mapping {agent_id: amount}."""
        contributions = {}
        for agent in agents:
            amount = self._contribution_amount(agent)
            agent.ldf_contribution_round = amount
            contributions[agent.agent_id] = amount
            self.pool_balance += amount
        return contributions

    # ------------------------------------------------------------------
    # Governance plumbing
    # ------------------------------------------------------------------

    def set_elected_rule(self, rule_name: str, round_number: int | None = None) -> bool:
        """Record and apply an elected allocation rule. No-op when fixed."""
        if str(getattr(parameters, "LDF_GOVERNANCE_MODE", "fixed")) == "fixed":
            return False
        previous = self.governance["elected_rule"]
        self.governance["elected_rule"] = rule_name
        self.governance["rule_change_history"].append(
            {"round": round_number, "from": previous, "to": rule_name}
        )
        return True

    def set_board_allocation(
        self, allocation: dict[int, float], round_number: int | None = None
    ) -> None:
        """Install a board-supplied allocation vector for the next payout."""
        self._board_allocation = dict(allocation or {})
        self.governance["board_allocations"].append(
            {"round": round_number, "allocation": dict(self._board_allocation)}
        )

    def set_accepted_claimants(self, agent_ids, round_number: int | None = None) -> None:
        """Restrict payout to adjudicated claims (D6). ``None`` disables the filter."""
        self._accepted_claimants = None if agent_ids is None else {int(a) for a in agent_ids}
        if self._accepted_claimants is not None:
            self.governance["claims"].append(
                {"round": round_number, "accepted": sorted(self._accepted_claimants)}
            )

    def _eligible_ids(self, agents: list[Any]) -> list[int]:
        """Claimants admitted for this payout."""
        return default_eligibility(agents)

    def _is_admissible(self, claimant_id: int) -> bool:
        """Whether a claimant survives this round's adjudication filter."""
        if self._accepted_claimants is None:
            return True
        return int(claimant_id) in self._accepted_claimants

    # ------------------------------------------------------------------
    # Payout
    # ------------------------------------------------------------------

    def distribute_payouts(self, agents: list[Any], damages: dict[int, float]) -> dict[int, float]:
        """
        Distribute payouts to eligible claimants under the elected allocation rule.

        Under the default ``LDF_GOVERNANCE_MODE == "fixed"`` the elected rule is
        ``damage_proportional`` with no board override and no claim filter, which
        reproduces the historical arithmetic exactly.
        """
        if self.pool_balance <= 0.0:
            return {}

        agents_by_id = {agent.agent_id: agent for agent in agents}
        # Structural eligibility stays stable; the claim filter narrows who is
        # *payable* this round. Rejected claimants keep a zero key so the payout
        # map has the same shape in every round and the rejection stays visible in
        # the claim ledger rather than showing up as a missing agent.
        claimants = self._eligible_ids(agents)
        payable = [cid for cid in claimants if self._is_admissible(cid)]

        rule_name = self.governance["elected_rule"]
        board_allocation = self._board_allocation if rule_name == "board_discretion" else None

        payouts = allocate(
            rule_name,
            payable,
            damages,
            self.pool_balance,
            agents_by_id=agents_by_id,
            board_allocation=board_allocation,
        )

        paid_total = sum(payouts.values())
        self.pool_balance = max(0.0, self.pool_balance - paid_total)

        if not payouts:
            # Total need was zero: the historical code returned no keys at all,
            # which is different from paying every claimant zero.
            self._board_allocation = None
            self._accepted_claimants = None
            for agent in agents:
                agent.ldf_payout_round = 0.0
            return {}

        for cid in claimants:
            payouts.setdefault(cid, 0.0)

        # Reset the per-round governance overrides so they cannot leak forward.
        self._board_allocation = None
        self._accepted_claimants = None

        for agent in agents:
            payout = payouts.get(agent.agent_id, 0.0)
            agent.ldf_payout_round = payout

        return payouts

    def append_round_log(self, log_row: dict[str, Any]) -> None:
        self.round_history.append(log_row)

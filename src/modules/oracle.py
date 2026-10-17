# oracle.py


# version 1

"""

Oracle Module.

The Oracle is a "Synthetic Heuristic Oracle", representing an environmental,
rule-based welfare predictor used during democratic votes. It evaluates each
proposed rule change and estimates its effect on group social welfare based on:

  - Current observed cooperation rate (bounded to [0, 1])
  - Current free-rider proportion (agents below 50% of average)
  - Direction and magnitude of the proposed change

This gives agents data-grounded context when voting, replacing pure LLM
speculation with calculated signal. Note for research applications: this is
a synthetic environmental heuristic rather than an objective truth model or
trained critic.

Correctness note (was a material bug): the cooperation rate used to be
``avg_contribution / parameters.MAX_CONTRIBUTION``. ``MAX_CONTRIBUTION`` is bound
at import time to ``ENDOWMENT_STAGE_1`` (20) and is never re-derived from
wealth, while climate-mode contributions run into the millions. The statistic was
therefore of order 10^4-10^5, and it fed straight into the LDF annotation
formula, so every constitutional session in the historical nine-seed set was
decided with LDF rules annotated by a meaningless quantity. The rate is now
computed against each agent's own pre-decision contribution cap and clipped to
[0, 1]; ``tests/test_oracle.py`` asserts the bound.

Usage:
    oracle = Oracle(round_history, agents, parameters)
    annotations = oracle.annotate_proposals(proposals)
    # Returns list of strings like:
    # "PUNISHMENT_EFFECT 3→4: Oracle predicts +14% welfare. Free-rider rate: 33%."
"""

from core import parameters


class Oracle:
    """
    Computes welfare predictions for democracy proposals.
    """

    def __init__(self, round_history: list, agents: list):
        """
        Args:
            round_history: list of round result dicts from environment.results
            agents: list of Agent instances
        """
        self.round_history = round_history
        self.agents = agents

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def annotate_proposals(self, proposals: list) -> list:
        """
        For each proposal dict, compute a welfare annotation string.

        Returns:
            list of str — one annotation per proposal, in order.
        """
        stats = self._compute_current_stats()
        annotations = []
        for p in proposals:
            ann = self._annotate_single(p, stats)
            annotations.append(ann)
        return annotations

    # ------------------------------------------------------------------
    # Statistics from recent history
    # ------------------------------------------------------------------

    def _compute_current_stats(self) -> dict:
        """
        Aggregate stats from the last 3 rounds (or all rounds if fewer).
        """
        recent = self.round_history[-3:] if len(self.round_history) >= 3 else self.round_history

        all_contribs = []
        all_caps = []
        for rnd in recent:
            for agent_data in rnd.get("agents", {}).values():
                all_contribs.append(agent_data.get("contribution", 0))
                all_caps.append(self._contribution_cap(agent_data))

        n = len(all_contribs)
        avg_contrib = sum(all_contribs) / n if n > 0 else 0

        # Cooperation rate as a bounded [0, 1] intensity. The denominator is the
        # agent's own pre-decision contribution cap (logged when
        # LOG_START_OF_ROUND_WEALTH is on, reconstructed from wealth otherwise),
        # NOT the import-time constant MAX_CONTRIBUTION. Using a cap of zero
        # agents in the denominator would reintroduce the original bug, so they
        # are excluded from the intensity average entirely.
        intensities = [
            max(0.0, float(c)) / cap
            for c, cap in zip(all_contribs, all_caps, strict=False)
            if cap and cap > 0
        ]
        coop_rate = min(1.0, max(0.0, sum(intensities) / len(intensities))) if intensities else 0.0

        # Free-rider rate: fraction of contributions below half the average
        threshold = avg_contrib * 0.5
        freerider_count = sum(1 for c in all_contribs if c < threshold)
        freerider_rate = freerider_count / n if n > 0 else 0

        # Recent avg cumulative payoff trend
        payoffs = []
        for rnd in recent:
            for agent_data in rnd.get("agents", {}).values():
                payoffs.append(agent_data.get("payoff", 0))
        avg_payoff = sum(payoffs) / len(payoffs) if payoffs else 0

        return {
            "avg_contrib": round(avg_contrib, 1),
            "coop_rate": round(coop_rate, 3),
            "freerider_rate": round(freerider_rate, 3),
            "avg_payoff": round(avg_payoff, 1),
            "n_observations": n,
            "n_intensity_observations": len(intensities),
        }

    @staticmethod
    def _contribution_cap(agent_data: dict) -> float:
        """Pre-decision Stage-1 cap for one agent-round record.

        Prefers the directly logged value; falls back to the reconstructed
        start-of-round wealth, then to the abstract-mode endowment.
        """
        from core import parameters

        logged = agent_data.get("start_of_round_wealth")
        if logged is None:
            logged = agent_data.get("wealth_before_decision")
        if logged is not None:
            try:
                cap = float(logged)
            except (TypeError, ValueError):
                cap = 0.0
            if cap > 0:
                return cap

        intensity = agent_data.get("contribution_intensity")
        contribution = agent_data.get("contribution", 0)
        try:
            if intensity is not None and float(intensity) > 0:
                return float(contribution) / float(intensity)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        return float(getattr(parameters, "ENDOWMENT_STAGE_1", 20.0))

    # ------------------------------------------------------------------
    # Per-proposal annotation
    # ------------------------------------------------------------------

    def _annotate_single(self, proposal: dict, stats: dict) -> str:
        """
        Compute a welfare annotation string for one proposal.
        """
        rule = proposal.get("rule", "")
        new_val = proposal.get("new_value")
        old_val = getattr(parameters, rule, None)

        if old_val is None or new_val is None:
            return f"{rule}: Oracle has insufficient data to predict welfare impact."

        if old_val == 0:
            change_pct = float(new_val)
        else:
            change_pct = (new_val - old_val) / old_val
        fr = stats["freerider_rate"]
        coop = stats["coop_rate"]

        if rule == "PUNISHMENT_EFFECT":
            # Higher punishment helps when free-rider rate is high
            # Predicted gain = change_pct * freerider_rate * base_gain_factor
            predicted_welfare_pct = change_pct * fr * 100 * parameters.ORACLE_PUNISHMENT_WEIGHT
            rationale = (
                f"Free-rider rate: {fr * 100:.0f}%. "
                f"Harsher punishment helps more when free-riding is high. "
                f"Predicted {'welfare gain' if predicted_welfare_pct > 0 else 'welfare cost'}: "
                f"{predicted_welfare_pct:+.1f}%."
            )

        elif rule == "REWARD_EFFECT":
            # Rewards help when cooperation rate is already moderate (encourages more)
            predicted_welfare_pct = change_pct * coop * 100 * parameters.ORACLE_REWARD_WEIGHT
            rationale = (
                f"Cooperation rate: {coop * 100:.0f}%. "
                f"Rewards amplify already-cooperative behaviour. "
                f"Predicted {'welfare gain' if predicted_welfare_pct > 0 else 'welfare cost'}: "
                f"{predicted_welfare_pct:+.1f}%."
            )

        elif rule == "ENDOWMENT_STAGE_2":
            # More budget = more punishment/reward capacity but also more redistribution cost
            predicted_welfare_pct = (
                change_pct * parameters.ORACLE_ENDOWMENT_SCALING
            )  # Moderate flat scaling
            rationale = (
                f"Current avg round payoff: {stats['avg_payoff']:.1f} tokens. "
                f"Larger Stage 2 budget gives more sanctioning capacity. "
                f"Predicted redistribution effect: {predicted_welfare_pct:+.1f}%."
            )

        elif rule in {
            "LDF_PAYOUT_DAMAGE_WEIGHT",
            "LDF_MAX_COVERAGE",
            "LDF_EQUITY_WEIGHT",
        }:
            # Heuristic: LDF expansion helps most when cooperation is moderate+ and
            # free-riding is not extreme, because redistribution credibility improves resilience.
            resilience_signal = max(0.0, (coop - (fr * 0.5)))
            predicted_welfare_pct = change_pct * 100 * (8.0 + 20.0 * resilience_signal)
            rationale = (
                f"Cooperation rate: {coop * 100:.0f}%, free-rider rate: {fr * 100:.0f}%. "
                f"This rule tunes climate-loss redistribution capacity. "
                f"Predicted resilience impact: {predicted_welfare_pct:+.1f}%."
            )

        else:
            return f"{rule} {old_val}→{new_val}: Oracle has no model for this rule."

        return f"{rule} {old_val}→{new_val}: {rationale}"

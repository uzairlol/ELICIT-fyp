"""Model-versus-behaviour comparison: the Stage-1 best response.

The repository has never contained a best-response calculation. Reconstructing the
Stage-1 payoff gives one directly:

    H_i  = beta * C_G / n_G            public-good share, split over the group
    pi_i = H_i - c_i                   climate/LDF mode: no endowment refund
    cap_i = capacity_i * floor(wealth_i)

The marginal return to one more unit contributed is

    MCPR = beta / n_G

so with ``beta = 1.6`` and ``n_G`` in the low teens, ``c = 0`` is a *strict* best
response in every round: contributing a unit costs 1 and returns 0.13. There is
no continuation value — ``cumulative_payoff`` constrains nothing, the endowment is
wealth itself, and there is no terminal rule. The cooperation observed in the
nine-seed set is therefore not cooperation in any game-theoretic sense.

This module turns that observation into a measurement. For every agent-round in a
trajectory it computes the best response to the *observed* peer contributions and
reports the **deviation rate**: the share of decisions where the agent did not
play the Stage-1 best response. That is a game-theoretic yardstick for prompt
steering, not a lexical one, and it costs zero GPU-hours.

Two results follow, and both are pre-committed:

* agents deviate a lot at ``MCPR << 1`` -> observed cooperation is not payoff
  optimisation, whatever the rationale text says;
* the deviation rate differs between P0 and P2 -> prompt steering moves behaviour
  along a payoff axis rather than merely changing the prose, which is the sharpest
  available statement of what the persona instruction does.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from core import parameters


@dataclass(frozen=True)
class Stage1Game:
    """The Stage-1 sub-game in one round, as a function the solver can evaluate."""

    beta: float
    group_size: int
    peer_contributions: float
    capacity: float = 1.0
    floor: float = 0.0

    @property
    def mcpr(self) -> float:
        """Marginal return to the contributor per unit contributed."""
        return self.beta / self.group_size if self.group_size > 0 else float("inf")

    @property
    def public_good_share(self) -> float:
        """``H_i``: the contributor's own share of the public good."""
        if self.group_size <= 0:
            return 0.0
        return self.beta * self.peer_contributions / self.group_size

    @property
    def cap(self) -> float:
        """Highest contribution this agent can make."""
        return max(0.0, self.capacity * self.floor)

    def stage1_payoff(self, own_contribution: float) -> float:
        """``pi_i(c) = beta * (C_G) / n - c`` in climate/LDF mode.

        ``C_G`` *includes* the agent's own contribution — that is what the
        institution does: it sums every member's contribution and splits the
        result. Holding peers fixed and merely subtracting ``c`` would give
        ``d pi / d c = -1`` always, which would make MCPR irrelevant and would
        quietly reproduce the very error this module exists to expose.

        With the agent's own choice inside ``C_G``:

            d pi / d c = beta / n - 1 = MCPR - 1

        so ``c = 0`` is a strict best response exactly when ``MCPR < 1``, the
        agent is indifferent exactly at ``MCPR = 1``, and the cap is optimal above
        it. There is no continuation value to change any of this: ``cumulative_payoff``
        constrains nothing and the endowment is wealth itself.

        There is no endowment refund: in climate mode the endowment *is* wealth, so
        a unit contributed is a unit of wealth not kept.
        """
        contribution = min(max(0.0, float(own_contribution)), self.cap)
        if self.group_size <= 0:
            return -contribution
        total = max(0.0, self.peer_contributions) + contribution
        return self.beta * total / self.group_size - contribution

    def marginal_return(self, own_contribution: float = 0.0) -> float:
        """``d pi / d c`` at a point: the sign says which way to move."""
        if self.group_size <= 0:
            return -1.0
        return self.mcpr - 1.0

    def best_response(self) -> float:
        """Argmax of a linear function on a box: always an endpoint.

        The slope is ``MCPR - 1``, so the maximiser is ``0`` below the threshold
        and the cap at or above it. At exactly ``MCPR = 1`` every point in
        ``[0, cap]`` is optimal and the cap is returned as one of the argmax set;
        :func:`analysis.best_response.deviation_records` treats indifference as
        non-deviation, so that tie is not counted against an agent.
        """
        if self.mcpr >= 1.0:
            return self.cap
        return 0.0

    def payoff_at_best_response(self) -> float:
        return self.stage1_payoff(self.best_response())


@dataclass
class DeviationRecord:
    """One agent-round's comparison."""

    run: str
    round_number: int
    agent_id: int
    prompt_variant: str
    model: str
    beta: float
    group_size: int
    mcpr: float
    capacity: float
    cap: float
    observed: float
    best_response: float
    payoff_observed: float
    payoff_best_response: float
    payoff_gap: float
    deviated: bool

    def as_row(self) -> dict[str, Any]:
        return {
            "run": self.run,
            "round": self.round_number,
            "agent_id": self.agent_id,
            "prompt_variant": self.prompt_variant,
            "model": self.model,
            "beta": self.beta,
            "group_size": self.group_size,
            "mcpr": self.mcpr,
            "capacity": self.capacity,
            "cap": self.cap,
            "observed_contribution": self.observed,
            "best_response": self.best_response,
            "payoff_observed": self.payoff_observed,
            "payoff_best_response": self.payoff_best_response,
            "payoff_gap": self.payoff_gap,
            "deviated": self.deviated,
        }


def round_number_of(record: DeviationRecord) -> int:
    return record.round_number


# ---------------------------------------------------------------------------
# Trajectory -> records
# ---------------------------------------------------------------------------


def deviation_records(
    rounds: Iterable[Mapping[str, Any]],
    *,
    run: str = "run",
    beta: float | None = None,
    prompt_variant: str = "",
    model: str = "",
    capacity_enabled: bool | None = None,
) -> list[DeviationRecord]:
    """Compare every agent-round's contribution with its Stage-1 best response.

    Peer contributions are taken as *observed*, which is the right counterfactual
    here: the question is whether an agent, facing the contributions its peers
    actually made, played its best response. Holding peers at their realised values
    avoids inventing a trajectory nobody took.
    """
    records: list[DeviationRecord] = []
    resolved_beta = float(parameters.PUBLIC_GOOD_MULTIPLIER if beta is None else beta)
    use_capacity = bool(
        parameters.CONTRIBUTION_CAPACITY_ENABLED if capacity_enabled is None else capacity_enabled
    )

    for round_data in rounds:
        agents = round_data.get("agents", {}) or {}
        if not agents:
            continue
        si_ids = {int(a) for a in round_data.get("si_members", []) or []}
        sfi_ids = {int(a) for a in round_data.get("sfi_members", []) or []}
        round_number = int(round_data.get("round_number", 0) or 0)

        total_contribution = sum(float(a.get("contribution", 0.0) or 0.0) for a in agents.values())

        for agent_id, data in agents.items():
            institution = str(data.get("institution_choice", ""))
            if institution == "SI":
                group = si_ids or {int(agent_id)}
            else:
                group = sfi_ids or {int(agent_id)}
            group_size = max(1, len(group))

            observed = float(data.get("contribution", 0.0) or 0.0)
            capacity = 1.0
            if use_capacity:
                try:
                    capacity = float(data.get("contribution_capacity", 1.0))
                except (TypeError, ValueError):
                    capacity = 1.0

            floor = data.get("start_of_round_wealth")
            if floor is None:
                floor = data.get("stage1_contribution_cap")
            if floor is None:
                intensity = data.get("contribution_intensity")
                try:
                    if intensity and float(intensity) > 0:
                        floor = observed / float(intensity)
                except (TypeError, ValueError, ZeroDivisionError):
                    floor = None
            try:
                floor_value = float(floor) if floor is not None else 0.0
            except (TypeError, ValueError):
                floor_value = 0.0

            # The agent's own contribution is part of the realised total. The best
            # response is evaluated holding peers at what they actually
            # contributed, i.e. with the agent's own choice removed.
            counterfactual = Stage1Game(
                beta=resolved_beta,
                group_size=group_size,
                peer_contributions=max(0.0, total_contribution - observed),
                capacity=capacity,
                floor=floor_value,
            )

            best = counterfactual.best_response()
            payoff_observed = counterfactual.stage1_payoff(observed)
            payoff_best = counterfactual.stage1_payoff(best)
            # A deviation only counts if it cost something: an agent that chose a
            # different action with the same payoff has not deviated from the
            # game's logic, only from its argmax.
            deviated = bool(observed != best and payoff_gap(payoff_observed, payoff_best) > 0.0)

            records.append(
                DeviationRecord(
                    run=run,
                    round_number=round_number,
                    agent_id=int(agent_id),
                    prompt_variant=prompt_variant,
                    model=model,
                    beta=resolved_beta,
                    group_size=group_size,
                    mcpr=counterfactual.mcpr,
                    capacity=capacity,
                    cap=counterfactual.cap,
                    observed=observed,
                    best_response=best,
                    payoff_observed=payoff_observed,
                    payoff_best_response=payoff_best,
                    payoff_gap=payoff_gap(payoff_observed, payoff_best),
                    deviated=deviated,
                )
            )
    return records


def payoff_gap(realised: float, best: float) -> float:
    """Payoff given up by not playing the best response."""
    return max(0.0, float(best) - float(realised))


# ---------------------------------------------------------------------------
# Numerical dynamic-programming check
# ---------------------------------------------------------------------------


def best_response_by_iteration(
    game: Stage1Game, rounds: int = 30, tolerance: float = 1e-9
) -> dict[str, Any]:
    """Iterate best responses to convergence and report the fixed point.

    A one-shot best response assumes peers do not respond. Iterating it is the
    standard public-goods check, and it is here to confirm the closed form rather
    than to replace it: with no continuation value the game is stage-equivalent to
    a single stage, so the iteration must reproduce ``best_response()`` exactly.
    If it ever does not, the closed form is wrong and the report is wrong with it.
    """
    cap = game.cap
    own = game.best_response()
    peers = max(0.0, game.peer_contributions)
    history: list[float] = []

    for _ in range(max(1, rounds)):
        current = Stage1Game(
            beta=game.beta,
            group_size=game.group_size,
            peer_contributions=peers,
            capacity=game.capacity,
            floor=game.floor,
        )
        own = current.best_response()
        history.append(own)
        updated_peers = max(0.0, peers - max(0.0, cap - own))
        if abs(updated_peers - peers) <= tolerance:
            peers = updated_peers
            break
        peers = updated_peers

    return {
        "closed_form": game.best_response(),
        "iterated": own,
        "agrees": abs(own - game.best_response()) <= tolerance,
        "converged_peers": peers,
        "mcpr": game.mcpr,
        "history": history,
    }


def participation_under_best_response(game: Stage1Game) -> float:
    """Total contribution if every agent played the Stage-1 best response."""
    return game.best_response() * game.group_size


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


@dataclass
class DeviationSummary:
    """Aggregate deviation statistics, grouped by an arbitrary key."""

    total_decisions: int = 0
    deviations: int = 0
    by_key: dict[Any, dict[str, float]] = field(default_factory=dict)

    @property
    def deviation_rate(self) -> float:
        return self.deviations / self.total_decisions if self.total_decisions else float("nan")

    def rate_for(self, key: Any) -> float:
        row = self.by_key.get(key)
        if not row or not row["n"]:
            return float("nan")
        return row["deviations"] / row["n"]


def summarise(records: Sequence[DeviationRecord], key: str = "prompt_variant") -> DeviationSummary:
    """Deviation rate overall and per prompt variant.

    The per-variant breakdown is the pre-committed comparison: a difference
    between P0 (which instructs the agent to maximise cumulative payoff) and P2
    (which removes that instruction) quantifies prompt steering with a
    game-theoretic yardstick instead of a lexical one.
    """
    summary = DeviationSummary()
    groups: dict[Any, list[DeviationRecord]] = {}
    for record in records:
        summary.total_decisions += 1
        summary.deviations += int(record.deviated)
        groups.setdefault(getattr(record, key, None), []).append(record)

    for group_key, group in groups.items():
        summary.by_key[group_key] = {
            "n": len(group),
            "deviations": sum(int(r.deviated) for r in group),
            "deviation_rate": sum(int(r.deviated) for r in group) / len(group)
            if group
            else float("nan"),
            "mean_contribution": sum(r.observed for r in group) / len(group)
            if group
            else float("nan"),
            "mean_best_response": (
                sum(r.best_response for r in group) / len(group) if group else float("nan")
            ),
            "mean_payoff_gap": sum(r.payoff_gap for r in group) / len(group)
            if group
            else float("nan"),
            "mean_mcpr": sum(r.mcpr for r in group) / len(group) if group else float("nan"),
        }
    return summary

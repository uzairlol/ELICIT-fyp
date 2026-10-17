"""Registry of named Loss & Damage Fund allocation rules.

The LDF's *allocation rule* — who is eligible, what the payout tracks, and how
much is covered — was a hardcoded constant. Eligibility was
``agent_group == "developing"``, the weight was damage, and the cap was 90%, in
seven lines of arithmetic with no agent input anywhere. Agents could nudge three
scalars; they could not choose the mechanism. For a repository named
*Endogenous Institutions*, that leaves the institution's distributional core
exogenous, and it is the mechanism — not the dial — that the burden-incidence
literature is about (Barrett 1994; Ostrom 2000).

This module supplies the menu. Each rule is a pure function of
``(eligible ids, damages, pool balance, parameters)`` returning desired weights,
and :func:`allocate` turns weights into an actual, constraint-respecting payout
vector. Three constraints hold regardless of what agents elect:

1. a payout never exceeds the available pool;
2. a payout never exceeds ``LDF_MAX_COVERAGE * damage_i``;
3. no agent is paid from their own contribution.

Constraints 1 and 2 are enforced here — in code — not in the prompt, which is the
same discipline the Stage-2 parser already uses. An agent cannot vote its way
into insolvency or over-coverage.

Under ``LDF_GOVERNANCE_MODE = "fixed"`` none of this is reachable:
:class:`~core.loss_damage_fund.LossDamageFund` calls
:func:`allocate` with the ``damage_proportional`` rule, which reproduces the
original arithmetic exactly. The default path is byte-identical by construction
and a regression test enforces it.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core import parameters

DEFAULT_RULE = "damage_proportional"


@dataclass(frozen=True)
class AllocationContext:
    """Everything a weight function may look at beyond damages and agents."""

    pool_balance: float
    coverage_cap: float
    damage_weight: float
    total_max_payout: float

    @property
    def pool_covers_all_damage(self) -> bool:
        """Whether the pool alone could pay every claimant its full cap."""
        return self.pool_balance >= self.total_max_payout


@dataclass(frozen=True)
class AllocationRule:
    """One named mechanism, with the weight it assigns to each claimant."""

    name: str
    description: str
    theory: str
    weight_fn: Callable[
        [Sequence[int], Mapping[int, float], Mapping[int, Any], AllocationContext], dict[int, float]
    ]
    needs_agents: bool = False
    board_discretion: bool = False

    def weights(
        self,
        claimant_ids: Sequence[int],
        damages: Mapping[int, float],
        pool_balance: float,
        agents_by_id: Mapping[int, Any] | None = None,
        coverage_cap: float | None = None,
        damage_weight: float | None = None,
    ) -> dict[int, float]:
        """Non-negative weight per claimant. A claimant with zero weight is unpaid."""
        eligible = [cid for cid in claimant_ids if cid in damages]
        if not eligible:
            return {}
        agent_map = agents_by_id or {}
        clean = {cid: max(0.0, float(damages.get(cid, 0.0))) for cid in eligible}
        cap = float(parameters.LDF_MAX_COVERAGE if coverage_cap is None else coverage_cap)
        weight = float(
            parameters.LDF_PAYOUT_DAMAGE_WEIGHT if damage_weight is None else damage_weight
        )
        context = AllocationContext(
            pool_balance=max(0.0, float(pool_balance)),
            coverage_cap=max(0.0, cap),
            damage_weight=weight,
            total_max_payout=sum(clean[cid] * max(0.0, cap) for cid in eligible),
        )
        raw = self.weight_fn(eligible, clean, agent_map, context)
        return {cid: max(0.0, float(raw.get(cid, 0.0))) for cid in eligible}


# ---------------------------------------------------------------------------
# Weight functions
# ---------------------------------------------------------------------------


def _mean_wealth(claimants: Sequence[int], agents: Mapping[int, Any]) -> float:
    """Mean wealth over claimants, floored at 1.0 as the fixed path always did."""
    wealths = [max(1.0, float(getattr(agents[cid], "wealth", 1.0))) for cid in claimants]
    return sum(wealths) / len(wealths) if wealths else 1.0


def _equity_multiplier(
    claimant_id: int,
    claimants: Sequence[int],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> float:
    """Reproduce the fixed path's equity multiplier exactly.

    The historical code short-circuited to 1.0 whenever the pool could cover
    every claimant's cap, and only consulted ``LDF_EQUITY_WEIGHT`` when the pool
    was short. Both branches are preserved so an elected change to
    ``LDF_EQUITY_WEIGHT`` still moves the fixed rule, as it always did.
    """
    if context.pool_covers_all_damage:
        return 1.0
    equity_weight = float(getattr(parameters, "LDF_EQUITY_WEIGHT", 0.0))
    mean_dev = _mean_wealth(claimants, agents)
    wealth = max(1.0, float(getattr(agents.get(claimant_id), "wealth", 1.0)))
    return max(0.0, 1.0 + (mean_dev / wealth - 1.0) * equity_weight)


def _w_damage(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Compensate in proportion to damage incurred. The original rule."""
    return {
        cid: damages[cid] * _equity_multiplier(cid, claimants, agents, context) for cid in claimants
    }


def _w_equal(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Equal per-capita shares within the affected group; ignores need."""
    return dict.fromkeys(claimants, 1.0)


def _w_poverty_tilted(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Welfare-maximising (max-min) tilt toward the poorest claimants.

    The equity index is ``e_i = mean_dev_wealth / wealth_i``, so a claimant one
    unit below the developing-group mean scores above 1 and one above it scores
    below 1. ``LDF_EQUITY_WEIGHT`` scales the tilt; at its default of 0.0 the rule
    degenerates to ``damage_proportional``, which is the honest statement that
    the equity lever is inert unless the assembly turns it up.
    """
    equity_weight = float(getattr(parameters, "LDF_EQUITY_WEIGHT", 0.0))
    mean_dev = _mean_wealth(claimants, agents)
    out: dict[int, float] = {}
    for cid in claimants:
        wealth = max(1.0, float(getattr(agents[cid], "wealth", 1.0)))
        index = max(0.0, mean_dev / wealth)
        multiplier = max(0.0, 1.0 + (index - 1.0) * equity_weight)
        out[cid] = max(0.0, damages[cid] * multiplier)
    return out


def _w_cbdr(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Common but differentiated responsibilities: weight damage by who emitted.

    Barrett (1994) treats international environmental agreements as stable
    contribution devices with modest net transfers. This rule is the direct
    mechanism test of that pattern: it makes ``HISTORICAL_EMISSIONS``
    load-bearing instead of decorative.
    """
    out: dict[int, float] = {}
    for cid in claimants:
        emissions = float(getattr(agents[cid], "historical_emissions", 1.0))
        out[cid] = max(0.0, damages[cid] * max(0.0, emissions))
    return out


def _w_capacity_pooled(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Solidarity: pay in proportion to capacity to pay.

    Makes ``CONTRIBUTION_CAPACITY`` load-bearing on the receiving side as well as
    the contributing side.
    """
    out: dict[int, float] = {}
    for cid in claimants:
        capacity = float(getattr(agents[cid], "contribution_capacity", 1.0))
        out[cid] = max(0.0, damages[cid] * max(0.0, capacity))
    return out


def _w_board_discretion(
    claimants: Sequence[int],
    damages: Mapping[int, float],
    agents: Mapping[int, Any],
    context: AllocationContext,
) -> dict[int, float]:
    """Placeholder weights.

    ``board_discretion`` has no formula: the elected board returns an explicit
    allocation vector and :func:`allocate` takes it verbatim (subject only to the
    hard constraints). This weight function is never reached with real agents; it
    exists so the registry can stay total.
    """
    return dict(damages)


#: Frozen registry. Insertion order is the documented menu order.
REGISTRY: dict[str, AllocationRule] = {
    rule.name: rule
    for rule in (
        AllocationRule(
            name="damage_proportional",
            description=(
                "Pay each eligible claimant in proportion to the climate damage it "
                "suffered in the shock."
            ),
            theory="Loss-of-damage compensation. The baseline mechanism.",
            weight_fn=_w_damage,
        ),
        AllocationRule(
            name="need_equality",
            description=(
                "Split the pool into equal per-capita shares among eligible claimants, "
                "regardless of how much damage each suffered."
            ),
            theory="Equal per-capita distribution within the affected group; ignores need.",
            weight_fn=_w_equal,
        ),
        AllocationRule(
            name="poverty_tilted",
            description=(
                "Weight damage by need, tilting payouts toward the poorest eligible "
                "claimants in proportion to the fund's equity setting."
            ),
            theory="Welfare-maximising (max-min) needs-based allocation.",
            weight_fn=_w_poverty_tilted,
            needs_agents=True,
        ),
        AllocationRule(
            name="cbdr",
            description=(
                "Weight damage by historical emissions, so the highest-emitting "
                "claimants draw the largest shares."
            ),
            theory=(
                "Common but differentiated responsibilities (Barrett 1994). Makes "
                "HISTORICAL_EMISSIONS load-bearing."
            ),
            weight_fn=_w_cbdr,
            needs_agents=True,
        ),
        AllocationRule(
            name="capacity_pooled",
            description=(
                "Weight damage by capacity to pay, so the agents with the most "
                "capacity draw the largest shares."
            ),
            theory="Solidarity / ability-to-pay. Makes CONTRIBUTION_CAPACITY load-bearing.",
            weight_fn=_w_capacity_pooled,
            needs_agents=True,
        ),
        AllocationRule(
            name="board_discretion",
            description=(
                "No formula: a rotating elected board allocates the pool case by case, "
                "one line of justification per claimant."
            ),
            theory="Discretionary administration by elected representatives.",
            weight_fn=_w_board_discretion,
            needs_agents=True,
            board_discretion=True,
        ),
    )
}

ALLOCATION_RULE_NAMES: tuple[str, ...] = tuple(REGISTRY)

#: Aliases so a proposal that says "damage" or "CBDR" still resolves.
NAME_ALIASES: dict[str, str] = {
    "damage": "damage_proportional",
    "damage_weighted": "damage_proportional",
    "proportional": "damage_proportional",
    "equal": "need_equality",
    "equality": "need_equality",
    "per_capita": "need_equality",
    "equity": "poverty_tilted",
    "need": "poverty_tilted",
    "needs": "poverty_tilted",
    "poverty": "poverty_tilted",
    "cbdr": "cbdr",
    "differentiated": "cbdr",
    "emissions": "cbdr",
    "capacity": "capacity_pooled",
    "solidarity": "capacity_pooled",
    "board": "board_discretion",
    "discretion": "board_discretion",
    "discretionary": "board_discretion",
}


class UnknownAllocationRule(ValueError):
    """Raised when a name does not resolve to a registry entry."""


def normalise_rule_name(name: str | None) -> str | None:
    """Resolve a possibly-abbreviated rule name, or return ``None``."""
    if name is None:
        return None
    key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if key in REGISTRY:
        return key
    if key in NAME_ALIASES:
        return NAME_ALIASES[key]
    compact = key.replace("_", "")
    for candidate in REGISTRY:
        if candidate.replace("_", "") == compact:
            return candidate
    return None


def resolve_rule(name: str | None = None) -> AllocationRule:
    """Return a registry entry, falling back to the default."""
    resolved = normalise_rule_name(name)
    if resolved is None:
        if name:
            raise UnknownAllocationRule(
                f"Unknown allocation rule {name!r}. Known: {', '.join(ALLOCATION_RULE_NAMES)}"
            )
        return REGISTRY[DEFAULT_RULE]
    return REGISTRY[resolved]


def describe_registry(order_seed: int | None = None) -> dict[str, str]:
    """Name -> description, optionally shuffled to avoid position bias.

    Deterministic for a given seed so a governance decision is reproducible.
    """
    pairs = [(name, rule.description) for name, rule in REGISTRY.items()]
    if order_seed is not None:
        random.Random(order_seed).shuffle(pairs)
    return dict(pairs)


def active_rule_name() -> str:
    """The rule currently in force, resolved through the alias table."""
    resolved = normalise_rule_name(getattr(parameters, "LDF_ALLOCATION_RULE", DEFAULT_RULE))
    return resolved or DEFAULT_RULE


def allocate(
    rule_name: str | None,
    claimant_ids: Iterable[int],
    damages: Mapping[int, float],
    pool_balance: float,
    agents_by_id: Mapping[int, Any] | None = None,
    board_allocation: Mapping[int, float] | None = None,
    damage_weight: float | None = None,
    coverage_cap: float | None = None,
) -> dict[int, float]:
    """Turn a rule into a constraint-respecting payout vector.

    Claims are served greedily in claimant order, each clipped to its own
    ``LDF_MAX_COVERAGE x damage`` cap and then to the remaining pool. Unspent
    balance stays in the fund rather than being redistributed afterwards: the
    fixed rule has always behaved that way, and changing it would move the
    reported coverage figures for governance level G0.

    Returns ``{agent_id: amount}`` and never raises on bad input: an empty or
    zero pool yields an empty vector, which is what the fixed path has always
    done.
    """
    pool = max(0.0, float(pool_balance))
    if pool <= 0.0:
        return {}

    claimants = [cid for cid in claimant_ids if float(damages.get(cid, 0.0)) > 0.0]
    if not claimants:
        return {}

    cap_fraction = float(parameters.LDF_MAX_COVERAGE if coverage_cap is None else coverage_cap)
    weight = float(parameters.LDF_PAYOUT_DAMAGE_WEIGHT if damage_weight is None else damage_weight)

    rule = resolve_rule(rule_name)
    agents = agents_by_id or {}

    # Hard cap (2): nobody is paid more than coverage_cap x their own damage.
    caps = {
        cid: max(0.0, float(damages.get(cid, 0.0))) * max(0.0, cap_fraction) for cid in claimants
    }

    if rule.board_discretion:
        if not board_allocation:
            return {}
        proposed = {cid: max(0.0, float(board_allocation.get(cid, 0.0))) for cid in claimants}
        # Constraint (3) has teeth here: the board is allocating pool money that
        # the developing group itself funded, so a board member's claim on the
        # board is self-dealing and is removed before the vector is applied.
        proposed = drop_self_payments(
            proposed,
            [
                cid
                for cid in claimants
                if bool(getattr(agents.get(cid), "board_member_allocating", False))
            ],
        )
    else:
        raw = rule.weights(
            claimants, damages, pool, agents, coverage_cap=cap_fraction, damage_weight=weight
        )
        total = sum(max(0.0, weight * raw.get(cid, 0.0)) for cid in claimants)
        if total <= 0.0:
            return {}
        proposed = {cid: max(0.0, weight * raw.get(cid, 0.0)) / total * pool for cid in claimants}

    # Constraints (1) and (2), applied in the historical order.
    payouts: dict[int, float] = {}
    remaining = pool
    for cid in claimants:
        if remaining <= 0.0:
            break
        amount = min(proposed.get(cid, 0.0), caps.get(cid, 0.0), remaining)
        if amount <= 0.0:
            continue
        payouts[cid] = amount
        remaining -= amount

    return {cid: value for cid, value in payouts.items() if value > 0.0}


def default_eligibility(agents: Sequence[Any]) -> list[int]:
    """Agents structurally eligible for a payout under the fixed criterion.

    Group membership stays exogenous even when the allocation rule does not —
    separating *who can claim* from *how the pool is split* keeps the mechanism
    attributable. Under ``full`` governance, claim adjudication adds a
    behavioural filter on top of this; see ``core.governance``.
    """
    return [
        int(agent.agent_id)
        for agent in agents
        if getattr(agent, "agent_group", "developing") == "developing"
    ]


def drop_self_payments(
    payouts: Mapping[int, float], allocating_members: Iterable[int]
) -> dict[int, float]:
    """Constraint (3): no agent is paid out of the pool it was itself allocating.

    This applies to agent-chosen allocations only. The formula rules are a
    function of damage, not of contribution, so they cannot route an agent's own
    money back to it; applying the filter there would suppress every developing
    agent's payout, since the whole developing group funds the pool.
    """
    allocating = {int(cid) for cid in allocating_members}
    return {cid: value for cid, value in payouts.items() if int(cid) not in allocating}

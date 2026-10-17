"""Governance analysis: which rule do agents elect, and does it matter?

This module makes the redistribution arm reportable. It is the object that makes
the repository's name true: the allocation *rule* becomes something participants
choose, rather than a constant the experimental design supplied.

Three quantities, each answering a distinct referee question:

* **elected rule frequency**, by governance level x model. A categorical outcome
  counted on 54 sessions per level, not a mean estimated from three points.
* **allocation concentration and realised distribution**, before and after each
  rule. This is what turns "they adopted a rule" into "the rule changed who was
  paid".
* **claim acceptance by group**, with reason codes. The breakdown by group is what
  pre-empts the obvious objection — that the board is rejecting claimants because
  it is biased, not because the claims are weak. G3c exists for that comparison and
  a rejection rate without it means nothing.

A deliberate refusal: rejection incidence is reported as adjudication, never
folded into a free-riding rate. Structural ineligibility and behavioural
rejection are different objects and the earlier clean separation is preserved.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd

from analysis.qwen_9seed.statistics import gini, hhi, percentile_ci

RULE_COLUMN_HINTS = ("allocation_rule", "elected_rule", "rule")


def _first_existing(frame: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    for column in candidates:
        if column in frame:
            return column
    return None


def constitutional_sessions(rounds: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One record per constitutional session, from the round history."""
    sessions: list[dict[str, Any]] = []
    for round_data in rounds:
        session = round_data.get("constitutional_change")
        if not isinstance(session, dict):
            continue
        sessions.append(
            {
                "round": int(round_data.get("round_number", 0) or 0),
                "governance_level": session.get("governance_level"),
                "allocation_rule": session.get("allocation_rule"),
                "winning_rule": (session.get("winning_proposal") or {}).get("rule"),
                "winning_value": (session.get("winning_proposal") or {}).get("new_value"),
                "proposals": session.get("proposals") or [],
                "tally": session.get("tally") or {},
                "votes": session.get("votes") or {},
                "applied": bool(session.get("applied", False)),
            }
        )
    return sessions


def elected_rule_table(sessions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Which rule was in force after each session, and which rule won each vote.

    A rule counts as *elected* only when the winning proposal was the categorical
    allocation-rule branch. Numeric parameter votes are recorded separately so the
    two are never conflated: "the assembly chose a rule" and "the assembly moved a
    dial" are different claims.
    """
    rows: list[dict[str, Any]] = []
    for session in sessions:
        for proposal in session.get("proposals") or []:
            rows.append(
                {
                    "round": session.get("round"),
                    "governance_level": session.get("governance_level"),
                    "proposed_rule": proposal.get("rule"),
                    "proposed_value": proposal.get("new_value"),
                    "proposer": proposal.get("proposer"),
                    "is_allocation_rule": proposal.get("rule") == "LDF_ALLOCATION_RULE",
                    "won": proposal.get("rule") == session.get("winning_rule")
                    and proposal.get("new_value") == session.get("winning_value"),
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "governance_level",
            "proposed_rule",
            "proposed_value",
            "proposer",
            "is_allocation_rule",
            "won",
        ],
    )


def rule_adoption(
    sessions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rule frequency among allocation-rule elections, with a concentration measure.

    The pre-committed readings, all of them publishable:

    * one rule wins in >= 80% of sessions *and* is the same across all three models
      -> agents converge on a shared normative rule;
    * one rule wins but differs by model family -> the preference is a property of
      the model prior, not of the decision context, which is itself the audit's
      second headline;
    * sessions are unstable -> the institution is unstable under its own
      governance.
    """
    elections = [
        s
        for s in sessions
        if s.get("winning_rule") == "LDF_ALLOCATION_RULE" and s.get("winning_value")
    ]
    if not elections:
        return {
            "n_sessions": len(sessions),
            "n_rule_elections": 0,
            "rule_shares": {},
            "modal_rule": None,
            "modal_share": float("nan"),
            "converges": False,
            "entropy": float("nan"),
            "per_level": {},
        }

    shares: dict[str, float] = {}
    for session in elections:
        value = str(session["winning_value"])
        shares[value] = shares.get(value, 0.0) + 1.0
    total = sum(shares.values())
    shares = {rule: count / total for rule, count in sorted(shares.items())}

    modal_rule = max(shares, key=lambda rule: shares[rule])
    modal_share = shares[modal_rule]

    per_level: dict[str, dict[str, Any]] = {}
    for level in sorted({str(s.get("governance_level")) for s in elections}):
        subset = [s for s in elections if str(s.get("governance_level")) == level]
        level_shares: dict[str, int] = {}
        for session in subset:
            value = str(session["winning_value"])
            level_shares[value] = level_shares.get(value, 0) + 1
        per_level[level] = {
            "n": len(subset),
            "counts": level_shares,
            "shares": {rule: count / len(subset) for rule, count in sorted(level_shares.items())},
            "modal_rule": max(level_shares, key=lambda rule: level_shares[rule]),
        }

    return {
        "n_sessions": len(sessions),
        "n_rule_elections": len(elections),
        "rule_shares": shares,
        "modal_rule": modal_rule,
        "modal_share": modal_share,
        "converges": bool(modal_share >= 0.80),
        "entropy": hhi(list(shares.values())),
        "per_level": per_level,
    }


def rule_stability(sessions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Per-round sequence of the rule in force, for the instability reading.

    ``changed`` marks a session where the in-force rule differs from the previous
    one. A high change rate with high rule entropy is the "the institution is
    unstable under its own governance" finding, stated rather than avoided.
    """
    rows: list[dict[str, Any]] = []
    previous: str | None = None
    for session in sessions:
        rule = session.get("allocation_rule")
        rows.append(
            {
                "round": session.get("round"),
                "governance_level": session.get("governance_level"),
                "allocation_rule": rule,
                "changed": bool(previous is not None and rule != previous),
                "winning_rule": session.get("winning_rule"),
                "n_proposals": len(session.get("proposals") or []),
                "n_votes": len(session.get("votes") or {}),
            }
        )
        if rule is not None:
            previous = str(rule)
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "governance_level",
            "allocation_rule",
            "changed",
            "winning_rule",
            "n_proposals",
            "n_votes",
        ],
    )


def claim_adjudication_table(rounds: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """One row per filed claim: verdict by group, with reason codes.

    The ``by_group`` split is the diagnostic. Reading only the aggregate rejection
    rate cannot distinguish a board that screens well from one that screens
    against a group, and that distinction is the first thing a referee will ask
    about a peer-adjudication mechanism.
    """
    rows: list[dict[str, Any]] = []
    for round_data in rounds:
        governance = round_data.get("governance") or {}
        adjudication = governance.get("adjudication")
        if not isinstance(adjudication, dict):
            continue
        round_number = int(round_data.get("round_number", 0) or 0)
        claims = adjudication.get("claims") or {}
        verdicts = adjudication.get("verdicts_by_adjudicator") or {}
        accepted = set(adjudication.get("accepted") or [])
        agents = round_data.get("agents") or {}

        for claimant, claim in claims.items():
            per_adjudicator = {
                str(adj): verdict_map.get(f"Agent {claimant}", "missing")
                for adj, verdict_map in verdicts.items()
            }
            accept_votes = sum(1 for v in per_adjudicator.values() if v == "accept")
            group = str((agents.get(str(claimant)) or {}).get("agent_group", "unknown"))
            rows.append(
                {
                    "round": round_number,
                    "claimant": int(claimant),
                    "group": group,
                    "damage_claimed": claim.get("damage_claimed"),
                    "damage_recorded": claim.get("mechanically_recorded_damage"),
                    "accepted": int(claimant) in accepted,
                    "reason_code": claim.get("reason_code"),
                    "accept_votes": accept_votes,
                    "n_adjudicators": len(per_adjudicator),
                    "acceptance_share": accept_votes / len(per_adjudicator)
                    if per_adjudicator
                    else float("nan"),
                    "per_adjudicator": per_adjudicator,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "claimant",
            "group",
            "damage_claimed",
            "damage_recorded",
            "accepted",
            "reason_code",
            "accept_votes",
            "n_adjudicators",
            "acceptance_share",
            "per_adjudicator",
        ],
    )


def rejection_by_group(claims: pd.DataFrame) -> dict[str, Any]:
    """Acceptance rate per group, plus the reason codes behind the rejections.

    Reported as its own quantity and never merged into any free-riding measure:
    a rejected claim is an adjudication outcome, not a behavioural finding.
    """
    if claims.empty:
        return {"available": False, "by_group": {}, "reason_codes": {}, "overall": {}}

    by_group: dict[str, Any] = {}
    for group, subset in claims.groupby("group"):
        accepted = int(subset["accepted"].sum())
        shares = percentile_ci(subset["acceptance_share"].tolist(), n_boot=5_000)
        by_group[str(group)] = {
            "claims": len(subset),
            "accepted": accepted,
            "rejected": int(len(subset) - accepted),
            "rejection_incidence": 1.0 - accepted / len(subset),
            "mean_acceptance_share": float(subset["acceptance_share"].mean()),
            "acceptance_share_ci": {"lower": shares["lower"], "upper": shares["upper"]},
        }

    reason_codes = (
        claims.loc[~claims["accepted"].astype(bool), "reason_code"]
        .fillna("unknown")
        .value_counts()
        .to_dict()
    )

    overall_accept = int(claims["accepted"].sum())
    return {
        "available": True,
        "by_group": by_group,
        "reason_codes": {str(k): int(v) for k, v in reason_codes.items()},
        "overall": {
            "claims": len(claims),
            "accepted": overall_accept,
            "rejection_incidence": 1.0 - overall_accept / len(claims),
        },
    }


def payout_allocation_table(rounds: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """One row per shock round: payout vector, its concentration, and the rule."""
    rows: list[dict[str, Any]] = []
    for round_data in rounds:
        if not round_data.get("shock_occurred"):
            continue
        payouts = {int(k): float(v or 0.0) for k, v in (round_data.get("payouts") or {}).items()}
        if not payouts:
            continue
        governance = round_data.get("governance") or {}
        agents = round_data.get("agents") or {}
        positive = [v for v in payouts.values() if v > 0]
        by_group: dict[str, float] = {}
        for agent_id, amount in payouts.items():
            group = str((agents.get(str(agent_id)) or {}).get("agent_group", "unknown"))
            by_group[group] = by_group.get(group, 0.0) + amount

        rows.append(
            {
                "round": int(round_data.get("round_number", 0) or 0),
                "severity": float(round_data.get("shock_severity", 0.0) or 0.0),
                "governance_level": governance.get("level"),
                "allocation_rule": governance.get("elected_rule"),
                "pool_before": float(round_data.get("ldf_pool_start", 0.0) or 0.0),
                "payout_total": sum(payouts.values()),
                "payout_gini": gini(positive) if positive else float("nan"),
                "payout_hhi": hhi(positive) if positive else float("nan"),
                "n_paid": len(positive),
                "payout_by_group": by_group,
                "payouts": payouts,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "severity",
            "governance_level",
            "allocation_rule",
            "pool_before",
            "payout_total",
            "payout_gini",
            "payout_hhi",
            "n_paid",
            "payout_by_group",
            "payouts",
        ],
    )


def wealth_gap_by_rule(rounds: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Terminal developed/developing wealth ratio per round, tagged with the rule.

    The economic headline of the governance arm: whether an elected rule actually
    moves the distribution, or whether participation rose without substantive
    redistribution regardless of who wrote the rule.
    """
    rows: list[dict[str, Any]] = []
    for round_data in rounds:
        governance = round_data.get("governance") or {}
        groups: dict[str, list[float]] = {}
        for data in (round_data.get("agents") or {}).values():
            group = str(data.get("agent_group", "unknown"))
            groups.setdefault(group, []).append(float(data.get("wealth", 0.0) or 0.0))
        if not groups:
            continue
        means = {g: sum(v) / len(v) for g, v in groups.items() if v}
        developed = means.get("developed", float("nan"))
        developing = means.get("developing", float("nan"))
        rows.append(
            {
                "round": int(round_data.get("round_number", 0) or 0),
                "governance_level": governance.get("level"),
                "allocation_rule": governance.get("elected_rule"),
                "mean_developed_wealth": developed,
                "mean_developing_wealth": developing,
                "wealth_ratio": developed / developing if developing else float("nan"),
                "gini": round_data.get("gini_wealth"),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "governance_level",
            "allocation_rule",
            "mean_developed_wealth",
            "mean_developing_wealth",
            "wealth_ratio",
            "gini",
        ],
    )


def board_concentration(board_records: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """How concentrated the elected board's allocations were, and how often they agreed.

    The elementwise median is meant to be robust to one outlier member. Measuring
    the spread of member proposals around the median is what checks that claim
    rather than asserting it.
    """
    rows: list[dict[str, Any]] = []
    for record in board_records:
        proposals = record.get("proposals") or {}
        median_allocation = record.get("median_allocation") or {}
        if not proposals:
            continue
        claimants = sorted({cid for proposal in proposals.values() for cid in proposal})
        spreads = []
        for claimant in claimants:
            values = [float(p.get(claimant, 0.0)) for p in proposals.values()]
            if values:
                spreads.append(max(values) - min(values))
        paid = [float(v) for v in median_allocation.values() if v > 0]
        rows.append(
            {
                "round": record.get("round"),
                "rule": record.get("rule"),
                "pool": float(record.get("pool", 0.0) or 0.0),
                "n_board": len(proposals),
                "median_gini": gini(paid) if paid else float("nan"),
                "median_hhi": hhi(paid) if paid else float("nan"),
                "mean_member_spread": sum(spreads) / len(spreads) if spreads else float("nan"),
                "max_member_spread": max(spreads) if spreads else float("nan"),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "round",
            "rule",
            "pool",
            "n_board",
            "median_gini",
            "median_hhi",
            "mean_member_spread",
            "max_member_spread",
        ],
    )


def build_governance_tables(rounds: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Every governance table plus the headline summaries, in one call."""
    rounds = list(rounds)
    sessions = constitutional_sessions(rounds)
    claims = claim_adjudication_table(rounds)
    allocations = payout_allocation_table(rounds)
    board_records = [
        record
        for round_data in rounds
        if isinstance((record := (round_data.get("governance") or {}).get("board")), dict)
    ]
    return {
        "sessions": sessions,
        "elections": elected_rule_table(sessions),
        "adoption": rule_adoption(sessions),
        "stability": rule_stability(sessions),
        "claims": claims,
        "rejection": rejection_by_group(claims),
        "allocations": allocations,
        "wealth_by_rule": wealth_gap_by_rule(rounds),
        "board_concentration": board_concentration(board_records),
    }

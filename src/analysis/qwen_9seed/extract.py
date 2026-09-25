"""Extract Qwen result JSONs into analysis-ready, provenance-preserving tables.

The extractor deliberately keeps the raw contribution, payoff, LDF, sanction,
belief, ToM, parser, and text ledgers separate.  It reconstructs the beginning
of each round from the previous logged end wealth (and from the first-round
payoff identity), because the JSON stores post-round wealth rather than the
pre-decision budget used by the climate contribution prompt.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io import as_rounds, discover_qwen_runs, load_json, parse_run_name

PG_MULTIPLIER = 1.6
DEFAULT_PARAMETERS: dict[str, int | float] = {
    "PUNISHMENT_EFFECT": 3,
    "REWARD_EFFECT": 1,
    "ENDOWMENT_STAGE_2": 20,
    "MAX_PUNISHMENT_TOKENS": 20,
    "SUBSIDY_FRACTION": 0.2,
    "SUBSIDY_TOP_N": 2,
    "LDF_PAYOUT_DAMAGE_WEIGHT": 1.0,
    "LDF_MAX_COVERAGE": 0.9,
    "LDF_EQUITY_WEIGHT": 0.0,
}
SHOCK_SEVERITY_BY_ROUND = {5: 0.10, 10: 0.20}
GOSSIP_TRIGGER_SCORE = 7.0
MAX_GOSSIP_ITEMS = 5


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _num(value: Any, default: float = float("nan")) -> float:
    try:
        if isinstance(value, bool):
            return default
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _int_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _label_counts(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, dict):
        return 0, 0, 0
    free = cooperative = 0
    for label in value.values():
        text = str(label).lower().replace("_", "-")
        free += int("free-rider" in text or "free rider" in text)
        cooperative += int("cooperat" in text)
    return len(value), free, cooperative


def _rule_family(rule: str) -> str:
    rule = str(rule)
    if rule.startswith("LDF_"):
        return "ldf"
    if rule.startswith("SUBSIDY"):
        return "subsidy"
    if "PUNISH" in rule:
        return "punishment"
    if "REWARD" in rule:
        return "reward"
    if "ENDOWMENT_STAGE_2" in rule or "MAX_PUNISHMENT" in rule:
        return "sanction_budget"
    return "other"


def _normalise_target_map(value: Any) -> dict[int, float]:
    result: dict[int, float] = {}
    if not isinstance(value, dict):
        return result
    for key, amount in value.items():
        target = _int_id(key)
        if target is not None:
            result[target] = _num(amount, 0.0)
    return result


def _extract_parser_flags(meta: Any) -> dict[str, Any]:
    meta = meta if isinstance(meta, dict) else {}
    return {
        "fallback_used": bool(meta.get("fallback_used", False)),
        "semantic_retry": bool(meta.get("semantic_retry", False)),
        "auto_fitted_to_budget": bool(meta.get("auto_fitted_to_budget", False)),
        "fallback_reason": str(meta.get("fallback_reason", "") or ""),
        "semantic_retry_reason": str(meta.get("semantic_retry_reason", "") or ""),
        "raw_shape": str(meta.get("raw_shape", "") or ""),
        "budget": _num(meta.get("budget"), float("nan")),
        "reported_total_spend": _num(meta.get("total_spend"), float("nan")),
    }


def _sum_map(value: Any) -> float:
    return float(sum(_normalise_target_map(value).values()))


def _extract_democracy(
    seed: int,
    filename: str,
    rounds: list[dict[str, Any]],
    initial_role_by_agent: dict[int, str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[int, dict[str, int | float]],
]:
    """Extract sessions, proposals, votes, and the live parameter trajectory."""
    sessions: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    votes: list[dict[str, Any]] = []
    trajectory: list[dict[str, Any]] = []
    params = dict(DEFAULT_PARAMETERS)
    params_by_round: dict[int, dict[str, int | float]] = {}

    for record in rounds:
        round_number = int(record["round_number"])
        params_by_round[round_number] = dict(params)
        for name, value in params.items():
            trajectory.append(
                {
                    "seed": seed,
                    "filename": filename,
                    "round_number": round_number,
                    "parameter": name,
                    "value_before_session": value,
                    "value_after_session": value,
                    "changed_at_round": np.nan,
                }
            )
        change = record.get("constitutional_change")
        if not isinstance(change, dict):
            continue
        raw_proposals = change.get("proposals") or []
        raw_votes = change.get("votes") or {}
        tally = {str(k): int(v) for k, v in (change.get("tally") or {}).items()}
        valid_vote_indices = [
            idx
            for idx, value in raw_votes.items()
            if isinstance(value, dict)
            and isinstance(value.get("vote"), (int, float))
            and int(value.get("vote")) in range(len(raw_proposals))
        ]
        winning = change.get("winning_proposal")
        winning_index = None
        if isinstance(winning, dict):
            for idx, proposal in enumerate(raw_proposals):
                if (
                    proposal.get("rule") == winning.get("rule")
                    and _num(proposal.get("new_value"), float("nan"))
                    == _num(winning.get("new_value"), float("nan"))
                    and _int_id(proposal.get("proposer")) == _int_id(winning.get("proposer"))
                ):
                    winning_index = idx
                    break
            if winning_index is None:
                for idx, proposal in enumerate(raw_proposals):
                    if proposal.get("rule") == winning.get("rule") and _num(
                        proposal.get("new_value"), float("nan")
                    ) == _num(winning.get("new_value"), float("nan")):
                        winning_index = idx
                        break
        valid_tally = [int(value) for value in tally.values() if isinstance(value, (int, float))]
        sorted_tally = sorted(valid_tally, reverse=True)
        top_tally = sorted_tally[0] if sorted_tally else 0
        second_tally = sorted_tally[1] if len(sorted_tally) > 1 else 0
        session_id = f"Q{seed}-D{round_number:02d}"
        session_row = {
            "session_id": session_id,
            "seed": seed,
            "filename": filename,
            "round_number": round_number,
            "n_proposals": len(raw_proposals),
            "n_vote_records": len(raw_votes),
            "n_valid_votes": len(valid_vote_indices),
            "participation_rate": len(valid_vote_indices) / 26 if raw_votes else 0.0,
            "n_tally_total": sum(valid_tally),
            "winning_index": winning_index,
            "winning_rule": winning.get("rule") if isinstance(winning, dict) else None,
            "winning_new_value": _num(winning.get("new_value"), float("nan"))
            if isinstance(winning, dict)
            else np.nan,
            "winning_proposer": _int_id(winning.get("proposer"))
            if isinstance(winning, dict)
            else None,
            "winning_rule_family": _rule_family(winning.get("rule"))
            if isinstance(winning, dict)
            else None,
            "winning_votes": top_tally,
            "plurality_margin": top_tally - second_tally,
            "plurality_share": top_tally / sum(valid_tally) if valid_tally else np.nan,
            "applied": bool(change.get("applied", False)),
            "winning_reason": winning.get("reason", "") if isinstance(winning, dict) else "",
            "tally_json": _json(change.get("tally") or {}),
        }
        sessions.append(session_row)
        for idx, proposal in enumerate(raw_proposals):
            if not isinstance(proposal, dict):
                continue
            rule = str(proposal.get("rule", ""))
            new_value = _num(proposal.get("new_value"), float("nan"))
            current = params.get(rule, np.nan)
            proposer = _int_id(proposal.get("proposer"))
            proposals.append(
                {
                    "session_id": session_id,
                    "seed": seed,
                    "filename": filename,
                    "round_number": round_number,
                    "proposal_index": idx,
                    "proposer": proposer,
                    "proposer_role": initial_role_by_agent.get(proposer, "unknown"),
                    "rule": rule,
                    "rule_family": _rule_family(rule),
                    "current_value": current,
                    "new_value": new_value,
                    "direction": "increase"
                    if new_value > current
                    else "decrease"
                    if new_value < current
                    else "same",
                    "reason": str(proposal.get("reason", "") or ""),
                    "is_winner": idx == winning_index,
                    "was_applied": bool(change.get("applied", False) and idx == winning_index),
                }
            )
        for voter_key, vote_record in raw_votes.items():
            if not isinstance(vote_record, dict):
                continue
            voter = _int_id(voter_key)
            vote_index = vote_record.get("vote")
            vote_index_int = int(vote_index) if isinstance(vote_index, (int, float)) else np.nan
            valid = (
                bool(vote_index_int in range(len(raw_proposals)))
                if np.isfinite(vote_index_int)
                else False
            )
            voted_proposal = raw_proposals[int(vote_index_int)] if valid else None
            votes.append(
                {
                    "session_id": session_id,
                    "seed": seed,
                    "filename": filename,
                    "round_number": round_number,
                    "voter": voter,
                    "voter_role": initial_role_by_agent.get(voter, "unknown"),
                    "vote_index": vote_index_int,
                    "valid_vote": valid,
                    "vote_rule": voted_proposal.get("rule")
                    if isinstance(voted_proposal, dict)
                    else None,
                    "vote_rule_family": _rule_family(voted_proposal.get("rule"))
                    if isinstance(voted_proposal, dict)
                    else None,
                    "reason": str(vote_record.get("reason", "") or ""),
                }
            )
        if isinstance(winning, dict) and change.get("applied", False):
            rule = str(winning.get("rule", ""))
            if rule in params:
                params[rule] = type(params[rule])(_num(winning.get("new_value"), params[rule]))
        for name, value in params.items():
            trajectory.append(
                {
                    "seed": seed,
                    "filename": filename,
                    "round_number": round_number,
                    "parameter": name,
                    "value_before_session": params_by_round[round_number][name],
                    "value_after_session": value,
                    "changed_at_round": round_number
                    if name == (winning.get("rule") if isinstance(winning, dict) else None)
                    else np.nan,
                }
            )
    # Keep one row per parameter and round, preferring the after-session value.
    if trajectory:
        traj = pd.DataFrame(trajectory)
        traj = (
            traj.sort_values(["seed", "round_number", "parameter", "value_after_session"])
            .drop_duplicates(["seed", "round_number", "parameter"], keep="last")
            .reset_index(drop=True)
        )
    else:
        traj = pd.DataFrame(
            columns=[
                "seed",
                "filename",
                "round_number",
                "parameter",
                "value_before_session",
                "value_after_session",
                "changed_at_round",
            ]
        )
    return sessions, proposals, votes, traj.to_dict("records"), params_by_round


def _gossip_tables(
    seed: int,
    filename: str,
    tom_edges: list[dict[str, Any]],
    n_agents: int = 26,
) -> list[dict[str, Any]]:
    """Reconstruct certain/possible bulletin exposure from stored ToM edges.

    The JSON does not store the live bulletin.  Edges with scores strictly
    below the fifth-lowest negative score are certain; ties at the cutoff are
    possible but not identifiable because concurrent completion order is not
    logged.  This table is therefore an exposure bound, not a false exact
    reconstruction.
    """
    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for edge in tom_edges:
        if edge["seed"] == seed:
            grouped[(edge["observation_round"], edge["action_round"])].append(edge)
    output: list[dict[str, Any]] = []
    for round_number in range(1, 31):
        edges = grouped.get((round_number, round_number), [])
        candidates = [edge for edge in edges if edge["score"] <= GOSSIP_TRIGGER_SCORE]
        candidates.sort(key=lambda edge: (edge["score"], edge["evaluator"], edge["target"]))
        n_candidates = len(candidates)
        if n_candidates > MAX_GOSSIP_ITEMS:
            cutoff = candidates[MAX_GOSSIP_ITEMS - 1]["score"]
        else:
            cutoff = candidates[-1]["score"] if candidates else np.nan
        certain = [
            edge
            for edge in candidates
            if n_candidates <= MAX_GOSSIP_ITEMS or edge["score"] < cutoff
        ]
        ambiguous = [
            edge
            for edge in candidates
            if n_candidates > MAX_GOSSIP_ITEMS and edge["score"] == cutoff
        ]
        for receiver in range(n_agents):
            certain_visible = [edge for edge in certain if edge["evaluator"] != receiver]
            possible_visible = certain_visible + [
                edge for edge in ambiguous if edge["evaluator"] != receiver
            ]
            certain_you = [
                edge
                for edge in certain
                if edge["target"] == receiver and edge["evaluator"] != receiver
            ]
            possible_you = [
                edge
                for edge in candidates
                if edge["target"] == receiver and edge["evaluator"] != receiver
            ]
            output.append(
                {
                    "seed": seed,
                    "filename": filename,
                    "round_number": round_number,
                    "receiver": receiver,
                    "n_tom_edges": len(edges),
                    "n_negative_candidates": n_candidates,
                    "cutoff_score": cutoff,
                    "n_certain_selected": len(certain),
                    "n_tie_ambiguous_selected": len(ambiguous),
                    "bulletin_nonempty_possible": bool(candidates),
                    "bulletin_receipt_guaranteed": bool(certain_visible),
                    "bulletin_receipt_possible": bool(possible_visible),
                    "visible_lines_guaranteed": len(certain_visible),
                    "visible_lines_possible": len(possible_visible),
                    "you_line_guaranteed": bool(certain_you),
                    "you_line_possible": bool(possible_you),
                    "named_in_visible_line_possible": any(
                        edge["target"] != receiver for edge in possible_visible
                    ),
                }
            )
    return output


def extract_results(results_dir: Path) -> dict[str, pd.DataFrame | list[dict[str, Any]]]:
    paths = discover_qwen_runs(results_dir)
    agent_rows: list[dict[str, Any]] = []
    round_rows: list[dict[str, Any]] = []
    text_rows: list[dict[str, Any]] = []
    fact_rows: list[dict[str, Any]] = []
    belief_rows: list[dict[str, Any]] = []
    belief_edge_rows: list[dict[str, Any]] = []
    tom_rows: list[dict[str, Any]] = []
    sanction_rows: list[dict[str, Any]] = []
    democracy_sessions: list[dict[str, Any]] = []
    democracy_proposals: list[dict[str, Any]] = []
    democracy_votes: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []
    run_metadata: list[dict[str, Any]] = []

    for path in paths:
        meta = parse_run_name(path)
        seed = int(meta["seed"])
        filename = meta["filename"]
        rounds = as_rounds(load_json(path))
        initial_wealth: dict[int, float] = {}
        initial_role: dict[int, str] = {}
        previous_end: dict[int, float] = {}
        tom_for_run: list[dict[str, Any]] = []
        params_by_round: dict[int, dict[str, int | float]] = {}

        # First pass establishes the exact initial profile and role assignment.
        first_agents = rounds[0]["agents"]
        for key, record in first_agents.items():
            aid = int(key)
            initial_wealth[aid] = _num(record.get("cumulative_payoff"), 0.0) - _num(
                record.get("payoff"), 0.0
            )
            initial_role[aid] = str(record.get("agent_group", "unknown"))

        sessions, proposals, votes, trajectory, params_by_round = _extract_democracy(
            seed, filename, rounds, initial_role
        )
        democracy_sessions.extend(sessions)
        democracy_proposals.extend(proposals)
        democracy_votes.extend(votes)
        parameter_rows.extend(trajectory)

        for record in rounds:
            round_number = int(record["round_number"])
            agents = record.get("agents", {})
            round_agent_rows: list[dict[str, Any]] = []
            for key in sorted(
                agents, key=lambda value: int(value) if str(value).isdigit() else str(value)
            ):
                agent = agents[key]
                aid = int(key)
                group = str(agent.get("agent_group", "unknown"))
                institution = str(agent.get("institution_choice", "unknown"))
                end_wealth = _num(agent.get("wealth"))
                start_wealth = (
                    initial_wealth[aid] if round_number == 1 else previous_end.get(aid, np.nan)
                )
                cap = max(0, int(start_wealth)) if math.isfinite(start_wealth) else 0
                contribution = _num(agent.get("contribution"), 0.0)
                positive = int(contribution > 0)
                zero = int(contribution == 0)
                pred_intensity = contribution / cap if cap > 0 else np.nan
                logged_intensity = contribution / int(end_wealth) if int(end_wealth) > 0 else 0.0
                trust_count, free_count, coop_count = _label_counts(
                    agent.get("belief_state", {}).get("trust_levels", {})
                )
                pm = _extract_parser_flags(agent.get("punishment_parser_meta"))
                cm = _extract_parser_flags(agent.get("contribution_parser_meta"))
                assigned_p = _normalise_target_map(agent.get("assigned_punishments"))
                assigned_r = _normalise_target_map(agent.get("assigned_rewards"))
                raw_p = _normalise_target_map(
                    (agent.get("punishment_parser_meta") or {}).get("raw_punishment_values")
                    if isinstance(agent.get("punishment_parser_meta"), dict)
                    else {}
                )
                if not raw_p:
                    raw_p = _normalise_target_map(
                        (agent.get("punishment_parser_meta") or {}).get(
                            "raw_punishment_allocations"
                        )
                        if isinstance(agent.get("punishment_parser_meta"), dict)
                        else {}
                    )
                raw_r = _normalise_target_map(
                    (agent.get("punishment_parser_meta") or {}).get("raw_reward_values")
                    if isinstance(agent.get("punishment_parser_meta"), dict)
                    else {}
                )
                if not raw_r:
                    raw_r = _normalise_target_map(
                        (agent.get("punishment_parser_meta") or {}).get("raw_reward_allocations")
                        if isinstance(agent.get("punishment_parser_meta"), dict)
                        else {}
                    )
                all_targets = sorted(set(assigned_p) | set(assigned_r) | set(raw_p) | set(raw_r))
                justification = agent.get("punishment_justifications") or {}
                for target in all_targets:
                    for kind, applied in (
                        ("punishment", assigned_p.get(target, 0.0)),
                        ("reward", assigned_r.get(target, 0.0)),
                    ):
                        requested = (
                            raw_p.get(target, applied)
                            if kind == "punishment"
                            else raw_r.get(target, applied)
                        )
                        params = params_by_round[round_number]
                        if kind == "punishment":
                            effect = _num(params.get("PUNISHMENT_EFFECT"), 3.0)
                            cost = _num(params.get("PUNISHMENT_COST"), 1.0)
                            applied_effect = -applied * effect
                        else:
                            effect = _num(params.get("REWARD_EFFECT"), 1.0)
                            cost = _num(params.get("REWARD_COST"), 1.0)
                            applied_effect = applied * effect
                        sanction_rows.append(
                            {
                                "seed": seed,
                                "filename": filename,
                                "round_number": round_number,
                                "source_agent": aid,
                                "target_agent": target,
                                "source_role": group,
                                "kind": kind,
                                "requested_amount": requested,
                                "applied_amount": applied,
                                "applied_effect": applied_effect,
                                "sender_cost": applied * cost,
                                "effect_multiplier": effect,
                                "cost_multiplier": cost,
                                "justification": str(
                                    justification.get(
                                        str(target), justification.get(f"Agent {target}", "")
                                    )
                                    or ""
                                ),
                                "auto_fitted_to_budget": pm["auto_fitted_to_budget"],
                                "fallback_used": pm["fallback_used"],
                                "semantic_retry": pm["semantic_retry"],
                                "raw_total_spend": pm["reported_total_spend"],
                                "budget": pm["budget"],
                                "evidence_id": f"Q{seed}-R{round_number:02d}-A{aid:02d}-SANCTION",
                            }
                        )
                # ToM scores in a result row were produced after the prior round
                # and are therefore available to this row's action prompt.
                for target_key, score in (agent.get("tom_scores") or {}).items():
                    target = _int_id(target_key)
                    if target is None:
                        continue
                    edge = {
                        "seed": seed,
                        "filename": filename,
                        "observation_round": round_number,
                        "action_round": round_number,
                        "score_round": round_number - 1,
                        "evaluator": aid,
                        "target": target,
                        "score": _num(score, float("nan")),
                        "negative_candidate": bool(_num(score, 10.0) <= GOSSIP_TRIGGER_SCORE),
                    }
                    tom_rows.append(edge)
                    tom_for_run.append(edge)
                belief = agent.get("belief_state") or {}
                belief_rows.append(
                    {
                        "seed": seed,
                        "filename": filename,
                        "round_number": round_number,
                        "agent_id": aid,
                        "role": group,
                        "trust_count": trust_count,
                        "free_rider_label_count": free_count,
                        "cooperative_label_count": coop_count,
                        "institutional_strategy": str(
                            belief.get("institutional_strategy", "") or ""
                        ),
                        "observations": str(belief.get("observations", "") or ""),
                    }
                )
                for target_key, label in (belief.get("trust_levels") or {}).items():
                    target = _int_id(target_key)
                    if target is not None:
                        belief_edge_rows.append(
                            {
                                "seed": seed,
                                "filename": filename,
                                "round_number": round_number,
                                "agent_id": aid,
                                "target_agent": target,
                                "trust_label": str(label),
                                "is_free_rider_label": "free-rider" in str(label).lower()
                                or "free rider" in str(label).lower(),
                                "is_cooperative_label": "cooperat" in str(label).lower(),
                            }
                        )
                for field in (
                    "institution_reasoning",
                    "contribution_reasoning",
                    "punishment_reasoning",
                    "deanonymized_punishment_reasoning",
                ):
                    text = str(agent.get(field, "") or "")
                    if text:
                        text_rows.append(
                            {
                                "seed": seed,
                                "filename": filename,
                                "round_number": round_number,
                                "agent_id": aid,
                                "role": group,
                                "field": field,
                                "evidence_id": f"Q{seed}-R{round_number:02d}-A{aid:02d}-{field.upper()}",
                                "text": text,
                            }
                        )
                for field in (
                    "institution_facts_used",
                    "contribution_facts_used",
                    "punishment_facts_used",
                ):
                    values = agent.get(field) or []
                    if isinstance(values, list):
                        for item_index, item in enumerate(values):
                            fact_rows.append(
                                {
                                    "seed": seed,
                                    "filename": filename,
                                    "round_number": round_number,
                                    "agent_id": aid,
                                    "field": field,
                                    "item_index": item_index,
                                    "text": str(item),
                                }
                            )
                row = {
                    "seed": seed,
                    "filename": filename,
                    "timestamp": meta["timestamp"],
                    "round_number": round_number,
                    "agent_id": aid,
                    "evidence_id": f"Q{seed}-R{round_number:02d}-A{aid:02d}",
                    "agent_group": group,
                    "institution_choice": institution,
                    "strategy": str(agent.get("strategy", "")),
                    "initial_wealth": initial_wealth[aid],
                    "start_wealth": start_wealth,
                    "decision_cap": cap,
                    "cap_is_zero": int(cap == 0),
                    "end_wealth": end_wealth,
                    "cumulative_payoff": _num(agent.get("cumulative_payoff")),
                    "vulnerability": _num(agent.get("vulnerability")),
                    "historical_emissions": _num(agent.get("historical_emissions")),
                    "contribution_capacity_profile": _num(agent.get("contribution_capacity")),
                    "contribution": contribution,
                    "positive_contribution": positive,
                    "zero_contribution": zero,
                    "pre_decision_intensity": pred_intensity,
                    "contribution_share_of_start_wealth": contribution / start_wealth
                    if start_wealth > 0
                    else np.nan,
                    "logged_intensity_using_end_wealth": logged_intensity,
                    "raw_round_cooperation_rate": _num(record.get("cooperation_rate")),
                    "stage1_payoff": _num(agent.get("stage1_payoff")),
                    "stage2_payoff": _num(agent.get("stage2_payoff")),
                    "payoff": _num(agent.get("payoff")),
                    "subsidy": _num(agent.get("subsidy"), 0.0),
                    "received_punishments_effect": _num(agent.get("received_punishments"), 0.0),
                    "received_rewards_effect": _num(agent.get("received_rewards"), 0.0),
                    "assigned_punishment_total": sum(assigned_p.values()),
                    "assigned_reward_total": sum(assigned_r.values()),
                    "assigned_punishment_count": int(
                        sum(value > 0 for value in assigned_p.values())
                    ),
                    "assigned_reward_count": int(sum(value > 0 for value in assigned_r.values())),
                    "raw_punishment_total": sum(raw_p.values()),
                    "raw_reward_total": sum(raw_r.values()),
                    "reputation_pre_action": _num(agent.get("reputation"), 5.0),
                    "tom_score_count": len(agent.get("tom_scores") or {}),
                    "tom_mean_outgoing": _num(
                        pd.Series(list((agent.get("tom_scores") or {}).values())).mean(), np.nan
                    ),
                    "tom_min_outgoing": _num(
                        pd.Series(list((agent.get("tom_scores") or {}).values())).min(), np.nan
                    ),
                    "tom_low_outgoing_count": sum(
                        _num(value, 10.0) <= GOSSIP_TRIGGER_SCORE
                        for value in (agent.get("tom_scores") or {}).values()
                    ),
                    "belief_trust_count": trust_count,
                    "belief_free_rider_label_count": free_count,
                    "belief_cooperative_label_count": coop_count,
                    "belief_strategy_length": len(
                        str(belief.get("institutional_strategy", "") or "")
                    ),
                    "belief_observations_length": len(str(belief.get("observations", "") or "")),
                    "climate_damage_round": _num(agent.get("climate_damage_taken_round"), 0.0),
                    "climate_damage_cumulative": _num(
                        agent.get("climate_damage_taken_cumulative"), 0.0
                    ),
                    "ldf_contribution": _num(agent.get("ldf_contribution_round"), 0.0),
                    "ldf_payout": _num(agent.get("ldf_payout_round"), 0.0),
                    "net_climate_transfer": _num(agent.get("net_climate_transfer_round"), 0.0),
                    "parsing_failures_logged": _num(agent.get("parsing_failures"), 0.0),
                    "rule_of_law_blocks": _num(agent.get("rule_of_law_blocks"), 0.0),
                    "contribution_fallback": cm["fallback_used"],
                    "contribution_semantic_retry": cm["semantic_retry"],
                    "contribution_auto_fit": cm["auto_fitted_to_budget"],
                    "punishment_fallback": pm["fallback_used"],
                    "punishment_semantic_retry": pm["semantic_retry"],
                    "punishment_auto_fit": pm["auto_fitted_to_budget"],
                    "punishment_fallback_reason": pm["fallback_reason"],
                    "punishment_semantic_retry_reason": pm["semantic_retry_reason"],
                    "punishment_budget": pm["budget"],
                    "punishment_reported_total_spend": pm["reported_total_spend"],
                    "tom_scores_json": _json(agent.get("tom_scores") or {}),
                }
                round_agent_rows.append(row)
                agent_rows.append(row)
            previous_end.update({row["agent_id"]: row["end_wealth"] for row in round_agent_rows})
            # Round-level values are filled after the agent table is assembled.
            round_rows.append(
                {
                    "seed": seed,
                    "filename": filename,
                    "timestamp": meta["timestamp"],
                    "round_number": round_number,
                    "raw_cooperation_rate": _num(record.get("cooperation_rate")),
                    "gini_wealth": _num(record.get("gini_wealth")),
                    "shock_occurred": bool(record.get("shock_occurred", False)),
                    "shock_severity": _num(record.get("shock_severity"), 0.0),
                    "gross_damage_total": _num(record.get("gross_damage_total"), 0.0),
                    "net_damage_total": _num(record.get("net_damage_total"), 0.0),
                    "ldf_pool_start": _num(record.get("ldf_pool_start"), 0.0),
                    "ldf_contributions_total": _num(record.get("ldf_contributions_total"), 0.0),
                    "ldf_payouts_total": _num(record.get("ldf_payouts_total"), 0.0),
                    "ldf_pool_end": _num(record.get("ldf_pool_end"), 0.0),
                    "si_total_contribution_raw": _num(record.get("si_total_contribution"), 0.0),
                    "sfi_total_contribution_raw": _num(record.get("sfi_total_contribution"), 0.0),
                    "si_avg_contribution_raw": _num(record.get("si_avg_contribution"), 0.0),
                    "sfi_avg_contribution_raw": _num(record.get("sfi_avg_contribution"), 0.0),
                    "is_democracy_round": "constitutional_change" in record,
                    "is_shock_round": bool(record.get("shock_occurred", False)),
                    "shock_event_offset": (round_number - 5) if round_number >= 5 else np.nan,
                }
            )
        run_metadata.append(
            {
                **meta,
                "initial_developed_agents": sum(
                    role == "developed" for role in initial_role.values()
                ),
                "initial_developing_agents": sum(
                    role == "developing" for role in initial_role.values()
                ),
                "initial_total_wealth": sum(initial_wealth.values()),
                "initial_developed_wealth": sum(
                    value
                    for role, value in zip(initial_role.values(), initial_wealth.values(), strict=True)
                    if role == "developed"
                ),
                "initial_developing_wealth": sum(
                    value
                    for role, value in zip(initial_role.values(), initial_wealth.values(), strict=True)
                    if role == "developing"
                ),
            }
        )
        # Reconstruct exposure bounds after all stored ToM edges are known.
        # The list is appended below after the per-run loop through a local list.
        # (The actual merge is performed after the loop to keep run boundaries clear.)
        run_tom_edges = [edge for edge in tom_rows if edge["seed"] == seed]
        # Store temporarily on the metadata object; it is removed before return.
        run_metadata[-1]["_tom_edges"] = run_tom_edges

    agent_df = pd.DataFrame(agent_rows)
    round_df = pd.DataFrame(round_rows)
    if not agent_df.empty:
        agent_df = agent_df.sort_values(["seed", "round_number", "agent_id"]).reset_index(drop=True)
        # Public-good share is calculated within each assigned institution.
        group = agent_df.groupby(["seed", "round_number", "institution_choice"], dropna=False)
        inst = group.agg(
            institution_n=("agent_id", "size"),
            institution_contribution=("contribution", "sum"),
        ).reset_index()
        inst["public_good_share"] = (
            PG_MULTIPLIER
            * inst["institution_contribution"]
            / inst["institution_n"].replace(0, np.nan)
        )
        inst = inst[
            [
                "seed",
                "round_number",
                "institution_choice",
                "institution_n",
                "institution_contribution",
                "public_good_share",
            ]
        ]
        # The all-agent aggregates are added after role-specific tables.
        role_tables = []
        for (seed, rn, role), part in agent_df.groupby(["seed", "round_number", "agent_group"]):
            role_tables.append(
                pd.DataFrame(
                    [
                        {
                            "seed": seed,
                            "round_number": rn,
                            "agent_group": role,
                            "role_n": len(part),
                            "role_total_contribution": part["contribution"].sum(),
                            "role_positive_share": part["positive_contribution"].mean(),
                            "role_zero_share": part["zero_contribution"].mean(),
                            "role_mean_intensity": part["pre_decision_intensity"].mean(),
                            "role_median_intensity": part["pre_decision_intensity"].median(),
                            "role_start_wealth": part["start_wealth"].sum(),
                            "role_end_wealth": part["end_wealth"].sum(),
                            "role_mean_end_wealth": part["end_wealth"].mean(),
                            "role_damage": part["climate_damage_round"].sum(),
                            "role_ldf_contribution": part["ldf_contribution"].sum(),
                            "role_ldf_payout": part["ldf_payout"].sum(),
                        }
                    ]
                )
            )
        role_df = pd.concat(role_tables, ignore_index=True) if role_tables else pd.DataFrame()
        if not role_df.empty:
            role_wide = role_df.pivot_table(
                index=["seed", "round_number"],
                columns="agent_group",
                values=[
                    "role_n",
                    "role_total_contribution",
                    "role_positive_share",
                    "role_zero_share",
                    "role_mean_intensity",
                    "role_median_intensity",
                    "role_start_wealth",
                    "role_end_wealth",
                    "role_mean_end_wealth",
                    "role_damage",
                    "role_ldf_contribution",
                    "role_ldf_payout",
                ],
                aggfunc="first",
            )
            role_wide.columns = [f"{col}_{role}" for col, role in role_wide.columns]
            role_wide = role_wide.reset_index()
            round_df = round_df.merge(role_wide, on=["seed", "round_number"], how="left")
        # Add public-good shares by institution to each agent row.
        inst_wide = (
            inst.pivot_table(
                index=["seed", "round_number"],
                columns="institution_choice",
                values="public_good_share",
                aggfunc="first",
            )
            .add_prefix("public_good_share_")
            .reset_index()
        )
        round_df = round_df.merge(inst_wide, on=["seed", "round_number"], how="left")
        agent_df = agent_df.merge(
            inst[["seed", "round_number", "institution_choice", "public_good_share"]],
            on=["seed", "round_number", "institution_choice"],
            how="left",
        )
        agent_df["stage1_payoff_reconstructed"] = (
            agent_df["public_good_share"] - agent_df["contribution"]
        )
        agent_df["stage1_reconciliation_error"] = (
            agent_df["stage1_payoff"] - agent_df["stage1_payoff_reconstructed"]
        )
        agent_df["end_wealth_reconstructed"] = (agent_df["start_wealth"] + agent_df["payoff"]).clip(
            lower=0
        )
        agent_df["wealth_rollforward_error"] = (
            agent_df["end_wealth"] - agent_df["end_wealth_reconstructed"]
        )
        agent_df["cumulative_payoff_change"] = agent_df.groupby(["seed", "agent_id"])[
            "cumulative_payoff"
        ].diff()
        agent_df["prior_contribution"] = agent_df.groupby(["seed", "agent_id"])[
            "contribution"
        ].shift(1)
        agent_df["prior_positive_contribution"] = agent_df.groupby(["seed", "agent_id"])[
            "positive_contribution"
        ].shift(1)
        agent_df["prior_pre_decision_intensity"] = agent_df.groupby(["seed", "agent_id"])[
            "pre_decision_intensity"
        ].shift(1)
        # Round-level totals and LDF incidence.
        round_df = round_df.merge(
            agent_df.groupby(["seed", "round_number"])
            .agg(
                total_contribution=("contribution", "sum"),
                mean_contribution=("contribution", "mean"),
                median_contribution=("contribution", "median"),
                positive_share=("positive_contribution", "mean"),
                zero_share=("zero_contribution", "mean"),
                mean_pre_decision_intensity=("pre_decision_intensity", "mean"),
                median_pre_decision_intensity=("pre_decision_intensity", "median"),
                contribution_gini=("contribution", "gini") if False else ("contribution", "sum"),
                total_ldf_contribution=("ldf_contribution", "sum"),
                total_ldf_payout=("ldf_payout", "sum"),
                total_damage=("climate_damage_round", "sum"),
                total_subsidy=("subsidy", "sum"),
                total_assigned_punishment=("assigned_punishment_total", "sum"),
                total_assigned_reward=("assigned_reward_total", "sum"),
                total_received_punishment_effect=("received_punishments_effect", "sum"),
                total_received_reward_effect=("received_rewards_effect", "sum"),
                total_raw_punishment=("raw_punishment_total", "sum"),
                total_raw_reward=("raw_reward_total", "sum"),
                auto_fit_agent_count=("punishment_auto_fit", "sum"),
                fallback_agent_count=("punishment_fallback", "sum"),
                semantic_retry_agent_count=("punishment_semantic_retry", "sum"),
                mean_reputation=("reputation_pre_action", "mean"),
                mean_tom_score=("tom_mean_outgoing", "mean"),
            )
            .reset_index(),
            on=["seed", "round_number"],
            how="left",
            suffixes=("_agent", ""),
        )

        # Correct contribution Gini after the aggregation (pandas has no gini).
        def contribution_gini(values: pd.Series) -> float:
            arr = values.to_numpy(dtype=float)
            arr = np.maximum(arr, 0)
            if len(arr) == 0 or arr.sum() == 0:
                return np.nan
            arr = np.sort(arr)
            n = len(arr)
            return float((2 * np.sum((np.arange(1, n + 1) * arr)) / (n * arr.sum())) - (n + 1) / n)

        round_df["contribution_gini"] = round_df.get("seed_round_placeholder", np.nan)
        for (seed, rn), part in agent_df.groupby(["seed", "round_number"]):
            mask = (round_df["seed"] == seed) & (round_df["round_number"] == rn)
            round_df.loc[mask, "contribution_gini"] = contribution_gini(part["contribution"])
        round_df["eligible_damage"] = round_df.get("role_damage_developing", np.nan)
        round_df["eligible_payout"] = round_df.get("role_ldf_payout_developing", np.nan)
        round_df["eligible_residual_damage"] = (
            round_df["eligible_damage"] - round_df["eligible_payout"]
        )
        round_df["eligible_coverage"] = np.where(
            round_df["eligible_damage"] > 0,
            round_df["eligible_payout"] / round_df["eligible_damage"],
            np.nan,
        )
        round_df["system_coverage"] = np.where(
            round_df["gross_damage_total"] > 0,
            round_df["ldf_payouts_total"] / round_df["gross_damage_total"],
            np.nan,
        )
        round_df["deposit_to_payout_ratio"] = np.where(
            round_df["ldf_contributions_total"] > 0,
            round_df["ldf_payouts_total"] / round_df["ldf_contributions_total"],
            np.nan,
        )
        round_df["pool_identity_error"] = round_df["ldf_pool_end"] - (
            round_df["ldf_pool_start"]
            + round_df["ldf_contributions_total"]
            - round_df["ldf_payouts_total"]
        )
        round_df["public_good_total"] = PG_MULTIPLIER * round_df["total_contribution"]
        round_df["stage1_net_transfer"] = (
            round_df["public_good_total"] - round_df["total_contribution"]
        )
        round_df["shock_response_eligible_round"] = round_df["is_shock_round"].astype(int)
        round_df["democracy_after_shock"] = round_df["is_democracy_round"].astype(int)

    # Gossip exposure reconstruction is run after the agent tables are complete.
    all_gossip_rows: list[dict[str, Any]] = []
    for path in paths:
        seed = int(parse_run_name(path)["seed"])
        all_gossip_rows.extend(_gossip_tables(seed, parse_run_name(path)["filename"], tom_rows))
    # Merge exposure onto agent-round rows for downstream models.
    gossip_df = pd.DataFrame(all_gossip_rows)
    if not agent_df.empty and not gossip_df.empty:
        agent_df = agent_df.merge(
            gossip_df.rename(columns={"round_number": "round_number", "receiver": "agent_id"}),
            on=["seed", "filename", "round_number", "agent_id"],
            how="left",
        )
    if not round_df.empty:
        round_df["eligible_damage"] = round_df["eligible_damage"].fillna(0.0)
        round_df["eligible_payout"] = round_df["eligible_payout"].fillna(0.0)
        round_df = round_df.sort_values(["seed", "round_number"]).reset_index(drop=True)

    # Remove temporary run-level internals.
    clean_run_metadata = [
        {k: v for k, v in row.items() if not k.startswith("_")} for row in run_metadata
    ]
    return {
        "agent_round": agent_df,
        "round_metrics": round_df,
        "tom_edges": pd.DataFrame(tom_rows),
        "gossip_exposure": gossip_df,
        "sanction_edges": pd.DataFrame(sanction_rows),
        "belief_snapshots": pd.DataFrame(belief_rows),
        "belief_edges": pd.DataFrame(belief_edge_rows),
        "democracy_sessions": pd.DataFrame(democracy_sessions),
        "democracy_proposals": pd.DataFrame(democracy_proposals),
        "democracy_votes": pd.DataFrame(democracy_votes),
        "parameter_trajectory": pd.DataFrame(parameter_rows),
        "reasoning_blocks": pd.DataFrame(text_rows),
        "facts_used": pd.DataFrame(fact_rows),
        "run_metadata": pd.DataFrame(clean_run_metadata),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables = extract_results(args.results_dir)
    for name, table in tables.items():
        table.to_csv(args.output_dir / f"{name}.csv", index=False)
    print(json.dumps({name: len(table) for name, table in tables.items()}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Extract analysis-ready tables from the locked 20260731 simulation JSON.

Run from repository root:
  python "docs/raw documentation/20260731/scripts/extract_20260731_results.py"

Does not modify the original results file.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_REL = Path(
    "results/To_Use/"
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json"
)
OUT_ROOT = Path("docs/raw documentation/20260731")
TABLES = OUT_ROOT / "tables"
EVIDENCE = OUT_ROOT / "evidence"

RUN_ID = "20260731_013853"
RUN_NAME = (
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853"
)
MIN_CONTRIBUTION = 0  # parameters.MIN_CONTRIBUTION for LDF climate budget

REQUIRED_ROUND_KEYS = {
    "round_number",
    "agents",
    "si_members",
    "sfi_members",
    "si_total_contribution",
    "sfi_total_contribution",
    "shock_occurred",
    "ldf_pool_start",
    "ldf_pool_end",
}

REQUIRED_AGENT_KEYS = {
    "agent_group",
    "institution_choice",
    "contribution",
    "wealth",
    "reputation",
    "payoff",
}


class ExtractionError(RuntimeError):
    pass


def fail(msg: str) -> None:
    raise ExtractionError(msg)


def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def stage1_cap_from_wealth(wealth: float | None) -> float | None:
    """LDF/climate: get_stage1_contribution_cap = max(MIN_CONTRIBUTION, int(wealth)).

    Note: results store end-of-round wealth. Cap at decision time used pre-contribution
    wealth; this reconstruction is approximate for validation / proportional columns.
    """
    if wealth is None:
        return None
    return float(max(MIN_CONTRIBUTION, int(wealth)))


def ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def sum_map(raw: Any) -> float:
    if not isinstance(raw, dict):
        return 0.0
    total = 0.0
    for v in raw.values():
        total += safe_float(v, 0.0) or 0.0
    return total


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fieldnames:
                val = row.get(key, "")
                if val is None:
                    out[key] = ""
                elif isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    out[key] = ""
                else:
                    out[key] = val
            writer.writerow(out)


def load_results(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        fail(f"Results file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or not data:
        fail("Results JSON must be a non-empty list of round objects")
    for i, round_data in enumerate(data):
        if not isinstance(round_data, dict):
            fail(f"Round index {i} is not an object")
        missing = REQUIRED_ROUND_KEYS - set(round_data.keys())
        if missing:
            fail(f"Round index {i} missing keys: {sorted(missing)}")
        agents = round_data.get("agents")
        if not isinstance(agents, dict) or not agents:
            fail(f"Round index {i} has empty/missing agents")
        for aid, agent in agents.items():
            if not isinstance(agent, dict):
                fail(f"Round {round_data.get('round_number')} agent {aid} is not an object")
            missing_a = REQUIRED_AGENT_KEYS - set(agent.keys())
            if missing_a:
                fail(
                    f"Round {round_data.get('round_number')} agent {aid} "
                    f"missing keys: {sorted(missing_a)}"
                )
    return data


def agent_sorted_items(agents: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    def key_fn(item: tuple[str, dict[str, Any]]) -> tuple[int, str]:
        aid = item[0]
        try:
            return (int(aid), aid)
        except ValueError:
            return (10**9, aid)

    return sorted(agents.items(), key=key_fn)


def extract(data: list[dict[str, Any]], source_rel: str) -> dict[str, Any]:
    issues: list[str] = []
    agent_meta: dict[int, dict[str, Any]] = {}
    round_agent_rows: list[dict[str, Any]] = []
    contribution_rows: list[dict[str, Any]] = []
    fund_rows: list[dict[str, Any]] = []
    reputation_rows: list[dict[str, Any]] = []
    proposal_rows: list[dict[str, Any]] = []
    vote_rows: list[dict[str, Any]] = []
    adopted_rows: list[dict[str, Any]] = []
    shock_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    payoff_rows: list[dict[str, Any]] = []
    redistrib_rows: list[dict[str, Any]] = []
    institutional_rows: list[dict[str, Any]] = []
    reasoning_rows: list[dict[str, Any]] = []
    gossip_rows: list[dict[str, Any]] = []  # intentionally empty schema

    prev_rep: dict[int, float | None] = {}
    prev_contrib: dict[int, float | None] = {}

    rounds_sorted = sorted(data, key=lambda r: safe_int(r.get("round_number"), -1) or -1)

    for round_data in rounds_sorted:
        rn = safe_int(round_data.get("round_number"))
        if rn is None:
            issues.append(
                f"Skipped round with non-integer round_number: {round_data.get('round_number')!r}"
            )
            continue

        shock_occurred = bool(round_data.get("shock_occurred", False))
        severity = safe_float(round_data.get("shock_severity"), 0.0)
        if shock_occurred and (severity is None or severity <= 0):
            issues.append(f"round={rn}: shock_occurred=True but severity={severity}")
        if (not shock_occurred) and severity not in (None, 0.0):
            issues.append(f"round={rn}: shock_occurred=False but severity={severity}")

        fund_rows.append(
            {
                "run": RUN_ID,
                "source_file": source_rel,
                "round_number": rn,
                "ldf_pool_start": safe_float(round_data.get("ldf_pool_start")),
                "ldf_contributions_total": safe_float(round_data.get("ldf_contributions_total")),
                "ldf_payouts_total": safe_float(round_data.get("ldf_payouts_total")),
                "ldf_pool_end": safe_float(round_data.get("ldf_pool_end")),
                "gross_damage_total": safe_float(round_data.get("gross_damage_total")),
                "net_damage_total": safe_float(round_data.get("net_damage_total")),
            }
        )

        shock_rows.append(
            {
                "run": RUN_ID,
                "source_file": source_rel,
                "round_number": rn,
                "shock_occurred": int(shock_occurred),
                "shock_severity": severity,
                "gross_damage_total": safe_float(round_data.get("gross_damage_total")),
                "net_damage_total": safe_float(round_data.get("net_damage_total")),
            }
        )

        si_members = [safe_int(x) for x in (round_data.get("si_members") or [])]
        sfi_members = [safe_int(x) for x in (round_data.get("sfi_members") or [])]
        institutional_rows.append(
            {
                "run": RUN_ID,
                "source_file": source_rel,
                "round_number": rn,
                "si_members": ";".join(str(x) for x in si_members if x is not None),
                "sfi_members": ";".join(str(x) for x in sfi_members if x is not None),
                "si_population": len(si_members),
                "sfi_population": len(sfi_members),
                "si_total_contribution": safe_float(round_data.get("si_total_contribution")),
                "sfi_total_contribution": safe_float(round_data.get("sfi_total_contribution")),
                "si_avg_contribution": safe_float(round_data.get("si_avg_contribution")),
                "sfi_avg_contribution": safe_float(round_data.get("sfi_avg_contribution")),
                "cooperation_rate": safe_float(round_data.get("cooperation_rate")),
                "gini_wealth": safe_float(round_data.get("gini_wealth")),
            }
        )

        cc = round_data.get("constitutional_change")
        if cc is not None and not isinstance(cc, dict):
            issues.append(f"round={rn}: constitutional_change is not an object")
            cc = None

        proposals: list[Any] = []
        if isinstance(cc, dict):
            proposals = cc.get("proposals") or []
            if not isinstance(proposals, list):
                issues.append(f"round={rn}: proposals is not a list")
                proposals = []
            for idx, prop in enumerate(proposals):
                if not isinstance(prop, dict):
                    issues.append(f"round={rn}: proposal[{idx}] not an object")
                    continue
                proposer = safe_int(prop.get("proposer"))
                proposal_rows.append(
                    {
                        "run": RUN_ID,
                        "source_file": source_rel,
                        "round_number": rn,
                        "proposal_index": idx,
                        "proposer": proposer,
                        "rule": prop.get("rule", ""),
                        "new_value": prop.get("new_value", ""),
                        "reason": prop.get("reason", ""),
                        "record_id": f"CC-R{rn:02d}-P{idx}",
                    }
                )
                reason = str(prop.get("reason") or "").strip()
                if reason:
                    reasoning_rows.append(
                        {
                            "evidence_id": (
                                f"RB-{rn:02d}-A"
                                f"{proposer if proposer is not None else 'NA'}"
                                f"-proposal_reason"
                            ),
                            "run": RUN_ID,
                            "source_file": source_rel,
                            "round_number": rn,
                            "agent_id": proposer if proposer is not None else "",
                            "agent_group": "",
                            "institution_choice": "",
                            "kind": "proposal_reason",
                            "action": f"propose:{prop.get('rule')}={prop.get('new_value')}",
                            "contribution": "",
                            "reputation": "",
                            "shock_occurred": int(shock_occurred),
                            "proposal_round": 1,
                            "source_path": (
                                f"rounds[{rn}].constitutional_change.proposals[{idx}].reason"
                            ),
                            "text": reason,
                            "text_length": len(reason),
                        }
                    )

            votes = cc.get("votes") or {}
            if not isinstance(votes, dict):
                issues.append(f"round={rn}: votes is not an object")
                votes = {}
            for voter, choice in votes.items():
                voter_id: Any
                if isinstance(voter, int) or str(voter).isdigit():
                    voter_id = safe_int(voter)
                else:
                    voter_id = voter
                vote_rows.append(
                    {
                        "run": RUN_ID,
                        "source_file": source_rel,
                        "round_number": rn,
                        "voter": voter_id,
                        "vote_choice": choice,
                        "n_proposals": len(proposals),
                        "record_id": f"CC-R{rn:02d}-V{voter}",
                    }
                )

            winning = cc.get("winning_proposal")
            applied = bool(cc.get("applied", False))
            if isinstance(winning, dict):
                adopted_rows.append(
                    {
                        "run": RUN_ID,
                        "source_file": source_rel,
                        "round_number": rn,
                        "applied": int(applied),
                        "rule": winning.get("rule", ""),
                        "new_value": winning.get("new_value", ""),
                        "proposer": safe_int(winning.get("proposer")),
                        "reason": winning.get("reason", ""),
                        "record_id": f"CC-R{rn:02d}-WIN",
                    }
                )
                if applied and proposals:
                    matched = any(
                        isinstance(p, dict)
                        and p.get("rule") == winning.get("rule")
                        and p.get("new_value") == winning.get("new_value")
                        and safe_int(p.get("proposer")) == safe_int(winning.get("proposer"))
                        for p in proposals
                    )
                    if not matched:
                        issues.append(
                            f"round={rn}: applied winning_proposal not found in proposals list"
                        )
            elif applied:
                issues.append(f"round={rn}: applied=True but winning_proposal missing")

        agents = round_data.get("agents") or {}
        for aid_str, agent in agent_sorted_items(agents):
            aid = safe_int(aid_str)
            if aid is None:
                issues.append(f"round={rn}: non-integer agent key {aid_str!r}")
                continue

            group = agent.get("agent_group", "")
            inst = agent.get("institution_choice", "")
            contrib = safe_float(agent.get("contribution"))
            wealth = safe_float(agent.get("wealth"))
            capacity = safe_float(agent.get("contribution_capacity"))
            rep = safe_float(agent.get("reputation"))
            stage1_cap = stage1_cap_from_wealth(wealth)

            if group == "developed" and inst != "SI":
                issues.append(f"round={rn} agent={aid}: developed but institution={inst}")
            if group == "developing" and inst != "SFI":
                issues.append(f"round={rn} agent={aid}: developing but institution={inst}")

            if contrib is not None and contrib < 0:
                issues.append(f"round={rn} agent={aid}: negative contribution {contrib}")

            if contrib is not None and stage1_cap is not None and contrib > stage1_cap + 1e-6:
                issues.append(
                    f"round={rn} agent={aid}: contribution {contrib} > reconstructed "
                    f"stage1_cap_from_end_wealth {stage1_cap} (approx; end-of-round wealth)"
                )

            if aid not in agent_meta:
                agent_meta[aid] = {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "agent_id": aid,
                    "agent_group": group,
                    "initial_round": rn,
                    "initial_wealth": wealth,
                    "contribution_capacity": capacity,
                    "vulnerability": safe_float(agent.get("vulnerability")),
                    "historical_emissions": safe_float(agent.get("historical_emissions")),
                }

            round_agent_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "in_si": int(inst == "SI"),
                    "in_sfi": int(inst == "SFI"),
                    "wealth": wealth,
                    "reputation": rep,
                    "rank": agent.get("rank", ""),
                    "strategy": agent.get("strategy", ""),
                    "contribution_capacity": capacity,
                    "vulnerability": safe_float(agent.get("vulnerability")),
                    "shock_occurred": int(shock_occurred),
                    "has_constitutional_change": int(isinstance(cc, dict)),
                }
            )

            contribution_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "contribution": contrib,
                    "wealth_end_of_round": wealth,
                    "contribution_capacity": capacity,
                    "stage1_cap_from_end_wealth": stage1_cap,
                    "prop_of_wealth": ratio(contrib, wealth),
                    "prop_of_capacity": ratio(contrib, capacity),
                    "prop_of_stage1_cap": ratio(contrib, stage1_cap),
                    "note": (
                        "proportional columns are analyst-derived; "
                        "stage1_cap uses end-of-round wealth (approx)"
                    ),
                }
            )

            rep_delta = None
            if aid in prev_rep and prev_rep[aid] is not None and rep is not None:
                rep_delta = rep - prev_rep[aid]
            reputation_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "reputation": rep,
                    "reputation_delta": rep_delta,
                    "tom_scores_count": len(agent.get("tom_scores") or {}),
                    "record_id": f"REP-R{rn:02d}-A{aid}",
                }
            )
            if rep is not None and (rep < 0 or rep > 10):
                issues.append(f"round={rn} agent={aid}: reputation {rep} outside [0,10]")
            prev_rep[aid] = rep

            assigned_p = sum_map(agent.get("assigned_punishments"))
            assigned_r = sum_map(agent.get("assigned_rewards"))
            action_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "contribution": contrib,
                    "assigned_punishments_total": assigned_p,
                    "assigned_rewards_total": assigned_r,
                    "received_punishments": safe_float(agent.get("received_punishments")),
                    "received_rewards": safe_float(agent.get("received_rewards")),
                    "subsidy": safe_float(agent.get("subsidy")),
                    "ldf_contribution_round": safe_float(agent.get("ldf_contribution_round")),
                    "ldf_payout_round": safe_float(agent.get("ldf_payout_round")),
                    "net_climate_transfer_round": safe_float(
                        agent.get("net_climate_transfer_round")
                    ),
                    "climate_damage_taken_round": safe_float(
                        agent.get("climate_damage_taken_round")
                    ),
                    "parsing_failures": agent.get("parsing_failures", ""),
                    "rule_of_law_blocks": agent.get("rule_of_law_blocks", ""),
                    "prior_contribution": prev_contrib.get(aid, ""),
                }
            )
            prev_contrib[aid] = contrib

            payoff_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "stage1_payoff": safe_float(agent.get("stage1_payoff")),
                    "stage2_payoff": safe_float(agent.get("stage2_payoff")),
                    "payoff": safe_float(agent.get("payoff")),
                    "cumulative_payoff": safe_float(agent.get("cumulative_payoff")),
                    "wealth": wealth,
                }
            )

            redistrib_rows.append(
                {
                    "run": RUN_ID,
                    "source_file": source_rel,
                    "round_number": rn,
                    "agent_id": aid,
                    "agent_group": group,
                    "institution_choice": inst,
                    "subsidy": safe_float(agent.get("subsidy")),
                    "ldf_payout_round": safe_float(agent.get("ldf_payout_round")),
                    "ldf_contribution_round": safe_float(agent.get("ldf_contribution_round")),
                    "net_climate_transfer_round": safe_float(
                        agent.get("net_climate_transfer_round")
                    ),
                }
            )

            belief = agent.get("belief_state") if isinstance(agent.get("belief_state"), dict) else {}
            blocks = [
                (
                    "institution",
                    "institution_reasoning",
                    agent.get("institution_reasoning"),
                    f"institution_choice={inst}",
                ),
                (
                    "contribution",
                    "contribution_reasoning",
                    agent.get("contribution_reasoning"),
                    f"contribution={contrib}",
                ),
                (
                    "punishment",
                    "punishment_reasoning",
                    agent.get("punishment_reasoning"),
                    f"assigned_punish_total={assigned_p}",
                ),
                (
                    "deanonymized_punishment",
                    "deanonymized_punishment_reasoning",
                    agent.get("deanonymized_punishment_reasoning"),
                    f"assigned_punish_total={assigned_p}",
                ),
                (
                    "belief_strategy",
                    "belief_state.institutional_strategy",
                    belief.get("institutional_strategy") if belief else "",
                    f"institution_choice={inst}",
                ),
                (
                    "belief_observations",
                    "belief_state.observations",
                    belief.get("observations") if belief else "",
                    f"institution_choice={inst}",
                ),
            ]
            for kind, path_suffix, text, action in blocks:
                text_s = str(text or "").strip()
                if not text_s:
                    continue
                eid = f"RB-{rn:02d}-A{aid}-{kind}"
                reasoning_rows.append(
                    {
                        "evidence_id": eid,
                        "run": RUN_ID,
                        "source_file": source_rel,
                        "round_number": rn,
                        "agent_id": aid,
                        "agent_group": group,
                        "institution_choice": inst,
                        "kind": kind,
                        "action": action,
                        "contribution": contrib,
                        "reputation": rep,
                        "shock_occurred": int(shock_occurred),
                        "proposal_round": int(isinstance(cc, dict)),
                        "source_path": f"rounds[{rn}].agents[{aid}].{path_suffix}",
                        "text": text_s,
                        "text_length": len(text_s),
                    }
                )

            c_reason = str(agent.get("contribution_reasoning") or "").strip()
            if contrib is not None and contrib > 0 and not c_reason:
                issues.append(
                    f"round={rn} agent={aid}: contribution={contrib} but empty contribution_reasoning"
                )

            pf = agent.get("parsing_failures")
            if pf not in (None, "", 0, "0", False):
                issues.append(f"round={rn} agent={aid}: parsing_failures={pf!r}")

            if not (agent.get("tom_scores") or {}):
                issues.append(f"round={rn} agent={aid}: empty tom_scores")

    issues.append(
        "GOSSIP_ABSENT: results JSON has no gossip / gossip_bulletin field; "
        "gossip_bulletins.csv emitted with header only"
    )

    meta_rows = [agent_meta[k] for k in sorted(agent_meta)]
    return {
        "agent_metadata": meta_rows,
        "round_agent_state": round_agent_rows,
        "contributions": contribution_rows,
        "fund_state": fund_rows,
        "reputation_events": reputation_rows,
        "proposals": proposal_rows,
        "votes": vote_rows,
        "adopted_rules": adopted_rows,
        "climatic_shocks": shock_rows,
        "agent_actions": action_rows,
        "payoffs": payoff_rows,
        "redistribution": redistrib_rows,
        "institutional_state": institutional_rows,
        "reasoning_blocks": reasoning_rows,
        "gossip_bulletins": gossip_rows,
        "issues": issues,
        "n_rounds": len(rounds_sorted),
        "n_agents": len(agent_meta),
    }


def validate_and_summarize(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = bundle["round_agent_state"]
    contrib = bundle["contributions"]
    issues = bundle["issues"]
    summary: list[dict[str, Any]] = []

    def add(check: str, value: Any, status: str, detail: str = "") -> None:
        summary.append({"check": check, "value": value, "status": status, "detail": detail})

    n_ar = len(rows)
    expected = bundle["n_agents"] * bundle["n_rounds"]
    add(
        "agent_round_rows",
        n_ar,
        "PASS" if n_ar == expected else "FAIL",
        f"expected {expected}",
    )
    add(
        "unique_agents",
        bundle["n_agents"],
        "PASS" if bundle["n_agents"] == 26 else "WARN",
        "filename says 26",
    )
    add(
        "n_rounds",
        bundle["n_rounds"],
        "PASS" if bundle["n_rounds"] == 30 else "WARN",
        "filename says 30",
    )

    pairs = [(r["round_number"], r["agent_id"]) for r in rows]
    add(
        "duplicate_round_agent",
        len(pairs) - len(set(pairs)),
        "PASS" if len(pairs) == len(set(pairs)) else "FAIL",
    )

    rounds = sorted({r["round_number"] for r in rows})
    add("round_min", min(rounds) if rounds else "", "INFO")
    add("round_max", max(rounds) if rounds else "", "INFO")
    add(
        "round_range_complete",
        int(rounds == list(range(1, 31))) if rounds else 0,
        "PASS" if rounds == list(range(1, 31)) else "WARN",
    )

    for field in ("contribution", "wealth", "reputation", "institution_choice", "agent_group"):
        if field == "contribution":
            missing = sum(1 for r in contrib if r.get("contribution") in ("", None))
            n = len(contrib)
        else:
            missing = sum(1 for r in rows if r.get(field) in ("", None))
            n = len(rows)
        rate = (missing / n) if n else 0
        add(
            f"missing_rate_{field}",
            round(rate, 6),
            "PASS" if rate == 0 else "WARN",
            f"{missing}/{n}",
        )

    neg = sum(
        1 for r in contrib if (r.get("contribution") is not None and r["contribution"] < 0)
    )
    add("invalid_negative_contribution", neg, "PASS" if neg == 0 else "FAIL")

    over = sum(
        1
        for issue in issues
        if "contribution" in issue and ">" in issue and "stage1_cap" in issue
    )
    add(
        "approx_over_stage1_cap_flags",
        over,
        "INFO",
        "uses end-of-round wealth; may false-positive",
    )

    rep_bad = sum(1 for issue in issues if "reputation" in issue and "outside" in issue)
    add("impossible_reputation_flags", rep_bad, "PASS" if rep_bad == 0 else "FAIL")

    routing = sum(
        1 for issue in issues if "developed but" in issue or "developing but" in issue
    )
    add("agent_type_institution_mismatches", routing, "PASS" if routing == 0 else "FAIL")

    shock_inconsist = sum(1 for issue in issues if "shock_occurred" in issue)
    add("shock_consistency_flags", shock_inconsist, "PASS" if shock_inconsist == 0 else "FAIL")

    prop_vote = sum(
        1 for issue in issues if "winning_proposal" in issue or "proposal[" in issue
    )
    add("proposal_vote_consistency_flags", prop_vote, "PASS" if prop_vote == 0 else "WARN")

    empty_tom = sum(1 for issue in issues if "empty tom_scores" in issue)
    add("empty_tom_scores_count", empty_tom, "INFO", "expected possibly early rounds")

    empty_creason = sum(1 for issue in issues if "empty contribution_reasoning" in issue)
    add("contrib_reasoning_action_gaps", empty_creason, "INFO")

    add("gossip_rows", len(bundle["gossip_bulletins"]), "INFO", "field absent from JSON")
    add("reasoning_blocks_extracted", len(bundle["reasoning_blocks"]), "INFO")
    add("proposals_extracted", len(bundle["proposals"]), "INFO")
    add("votes_extracted", len(bundle["votes"]), "INFO")
    add("adopted_rules_extracted", len(bundle["adopted_rules"]), "INFO")
    add("issue_log_lines", len(issues), "INFO")

    return summary


def write_reasoning_index(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reasoning Block Index",
        "",
        f"Run: `{RUN_NAME}`",
        f"Source: `{CANONICAL_REL.as_posix()}`",
        "",
        "Stable evidence IDs use the form `RB-{round:02d}-A{agent}-{kind}`.",
        "",
        f"Total blocks with non-empty text: **{len(rows)}**",
        "",
        "| evidence_id | round | agent | group | institution | kind | contribution | reputation | shock | chars | source_path |",
        "|---|---:|---:|---|---|---|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['evidence_id']}` | {r['round_number']} | {r['agent_id']} | "
            f"{r.get('agent_group', '')} | {r.get('institution_choice', '')} | {r['kind']} | "
            f"{r.get('contribution', '')} | {r.get('reputation', '')} | "
            f"{r.get('shock_occurred', '')} | {r.get('text_length', '')} | "
            f"`{r.get('source_path', '')}` |"
        )
    lines.append("")
    lines.append("Full verbatim text is in `tables/reasoning_blocks.csv`.")
    lines.append("")
    lines.append("## Selected excerpts (traceability samples)")
    lines.append("")
    samples = [r for r in rows if r["kind"] == "proposal_reason"][:6]
    samples += [r for r in rows if r["kind"] == "contribution"][:4]
    seen: set[str] = set()
    for r in samples:
        if r["evidence_id"] in seen:
            continue
        seen.add(r["evidence_id"])
        lines.append(f"### {r['evidence_id']}")
        lines.append("")
        lines.append(
            f"[Evidence: {CANONICAL_REL.as_posix()} | run={RUN_ID} | "
            f"round={r['round_number']} | agent={r['agent_id']} | record={r['source_path']}]"
        )
        lines.append("")
        lines.append(f"- action: `{r.get('action', '')}`")
        lines.append(f"- institution: `{r.get('institution_choice', '')}`")
        lines.append(f"- contribution: `{r.get('contribution', '')}`")
        lines.append(f"- reputation: `{r.get('reputation', '')}`")
        lines.append(f"- shock: `{r.get('shock_occurred', '')}`")
        lines.append("")
        excerpt = r["text"]
        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "…"
        lines.append(f"> {excerpt}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_malformed(
    issues: list[str], path: Path, summary: list[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Malformed or Missing Records",
        "",
        f"Run: `{RUN_NAME}`",
        f"Source: `{CANONICAL_REL.as_posix()}`",
        "",
        "## Summary checks",
        "",
        "| check | value | status | detail |",
        "|---|---|---|---|",
    ]
    for s in summary:
        lines.append(f"| {s['check']} | {s['value']} | {s['status']} | {s['detail']} |")

    lines.extend(["", "## Issue log", ""])
    if not issues:
        lines.append("_No issues logged._")
    else:
        counts = Counter(issues)
        empty_tom_rounds: dict[int, int] = defaultdict(int)
        other: list[str] = []
        for issue, n in counts.items():
            m = re.match(r"round=(\d+) agent=\d+: empty tom_scores", issue)
            if m:
                empty_tom_rounds[int(m.group(1))] += n
            else:
                other.append(f"- ({n}×) {issue}" if n > 1 else f"- {issue}")

        if empty_tom_rounds:
            lines.append("### Empty `tom_scores`")
            lines.append("")
            for rn in sorted(empty_tom_rounds):
                lines.append(f"- round {rn}: {empty_tom_rounds[rn]} agents")
            lines.append("")

        lines.append("### Other issues")
        lines.append("")
        lines.extend(sorted(other) if other else ["_None._"])
        lines.append("")

    lines.append("## Gossip")
    lines.append("")
    lines.append(
        "No `gossip` / `gossip_bulletin` field exists in the selected results JSON. "
        "`tables/gossip_bulletins.csv` is emitted with headers only."
    )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    source = REPO_ROOT / CANONICAL_REL
    if not source.is_file():
        alt = Path(CANONICAL_REL)
        if alt.is_file():
            source = alt.resolve()
            root = Path.cwd()
        else:
            print(f"ERROR: cannot find {CANONICAL_REL}", file=sys.stderr)
            return 1
    else:
        root = REPO_ROOT

    source_rel = CANONICAL_REL.as_posix()
    tables = root / TABLES
    evidence = root / EVIDENCE
    tables.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)

    print(f"Loading {source_rel} ...")
    data = load_results(source)
    print(f"Loaded {len(data)} rounds")

    bundle = extract(data, source_rel)
    summary = validate_and_summarize(bundle)

    schemas: dict[str, list[str]] = {
        "agent_metadata": [
            "run",
            "source_file",
            "agent_id",
            "agent_group",
            "initial_round",
            "initial_wealth",
            "contribution_capacity",
            "vulnerability",
            "historical_emissions",
        ],
        "round_agent_state": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "in_si",
            "in_sfi",
            "wealth",
            "reputation",
            "rank",
            "strategy",
            "contribution_capacity",
            "vulnerability",
            "shock_occurred",
            "has_constitutional_change",
        ],
        "contributions": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "contribution",
            "wealth_end_of_round",
            "contribution_capacity",
            "stage1_cap_from_end_wealth",
            "prop_of_wealth",
            "prop_of_capacity",
            "prop_of_stage1_cap",
            "note",
        ],
        "fund_state": [
            "run",
            "source_file",
            "round_number",
            "ldf_pool_start",
            "ldf_contributions_total",
            "ldf_payouts_total",
            "ldf_pool_end",
            "gross_damage_total",
            "net_damage_total",
        ],
        "reputation_events": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "reputation",
            "reputation_delta",
            "tom_scores_count",
            "record_id",
        ],
        "proposals": [
            "run",
            "source_file",
            "round_number",
            "proposal_index",
            "proposer",
            "rule",
            "new_value",
            "reason",
            "record_id",
        ],
        "votes": [
            "run",
            "source_file",
            "round_number",
            "voter",
            "vote_choice",
            "n_proposals",
            "record_id",
        ],
        "adopted_rules": [
            "run",
            "source_file",
            "round_number",
            "applied",
            "rule",
            "new_value",
            "proposer",
            "reason",
            "record_id",
        ],
        "climatic_shocks": [
            "run",
            "source_file",
            "round_number",
            "shock_occurred",
            "shock_severity",
            "gross_damage_total",
            "net_damage_total",
        ],
        "agent_actions": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "contribution",
            "assigned_punishments_total",
            "assigned_rewards_total",
            "received_punishments",
            "received_rewards",
            "subsidy",
            "ldf_contribution_round",
            "ldf_payout_round",
            "net_climate_transfer_round",
            "climate_damage_taken_round",
            "parsing_failures",
            "rule_of_law_blocks",
            "prior_contribution",
        ],
        "payoffs": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "stage1_payoff",
            "stage2_payoff",
            "payoff",
            "cumulative_payoff",
            "wealth",
        ],
        "redistribution": [
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "subsidy",
            "ldf_payout_round",
            "ldf_contribution_round",
            "net_climate_transfer_round",
        ],
        "institutional_state": [
            "run",
            "source_file",
            "round_number",
            "si_members",
            "sfi_members",
            "si_population",
            "sfi_population",
            "si_total_contribution",
            "sfi_total_contribution",
            "si_avg_contribution",
            "sfi_avg_contribution",
            "cooperation_rate",
            "gini_wealth",
        ],
        "reasoning_blocks": [
            "evidence_id",
            "run",
            "source_file",
            "round_number",
            "agent_id",
            "agent_group",
            "institution_choice",
            "kind",
            "action",
            "contribution",
            "reputation",
            "shock_occurred",
            "proposal_round",
            "source_path",
            "text",
            "text_length",
        ],
        "gossip_bulletins": [
            "run",
            "source_file",
            "round_number",
            "source_agent",
            "target_agent",
            "score",
            "reasoning",
            "note",
        ],
        "data_quality_summary": ["check", "value", "status", "detail"],
    }

    for name, fields in schemas.items():
        if name == "data_quality_summary":
            write_csv(tables / f"{name}.csv", fields, summary)
        elif name == "gossip_bulletins":
            write_csv(tables / f"{name}.csv", fields, [])
        else:
            write_csv(tables / f"{name}.csv", fields, bundle[name])

    write_reasoning_index(bundle["reasoning_blocks"], evidence / "reasoning_block_index.md")
    write_malformed(bundle["issues"], evidence / "malformed_or_missing_records.md", summary)

    print("Wrote tables to", tables)
    print("Wrote evidence to", evidence)
    print("Agent-round rows:", len(bundle["round_agent_state"]))
    print("Reasoning blocks:", len(bundle["reasoning_blocks"]))
    print("Issues logged:", len(bundle["issues"]))
    fails = [s for s in summary if s["status"] == "FAIL"]
    if fails:
        print("FAIL checks:", fails)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExtractionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

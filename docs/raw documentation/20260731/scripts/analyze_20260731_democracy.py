#!/usr/bin/env python3
"""
Prompt 5: democracy / proposals / enforcement / institutional adaptation analysis.

Run from repo root:
  python "docs/raw documentation/20260731/scripts/analyze_20260731_democracy.py"
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "docs" / "raw documentation" / "20260731"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"
RUN = "20260731_013853"

CATEGORY_MAP = {
    "SUBSIDY_FRACTION": "reward_subsidy",
    "SUBSIDY_TOP_N": "reward_subsidy",
    "PUNISHMENT_EFFECT": "punishment_weakening",  # in this run new_value < default 3
    "REWARD_EFFECT": "reward_strength",
    "ENDOWMENT_STAGE_2": "enforcement_budget",
    "MAX_PUNISHMENT_TOKENS": "punishment_capacity",
    "LDF_MAX_COVERAGE": "ldf_redistribution",
    "LDF_EQUITY_WEIGHT": "ldf_equity",
    "LDF_PAYOUT_DAMAGE_WEIGHT": "ldf_damage_weight",
}


def parse_vote_choice(raw):
    if isinstance(raw, dict):
        return raw
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return {"vote": None, "reason": str(raw)}


def load():
    props = pd.read_csv(TABLES / "proposals.csv")
    adopted = pd.read_csv(TABLES / "adopted_rules.csv")
    votes = pd.read_csv(TABLES / "votes.csv")
    profiles = pd.read_csv(TABLES / "agent_strategy_profiles.csv")
    contrib = pd.read_csv(TABLES / "contributions.csv")
    actions = pd.read_csv(TABLES / "agent_actions.csv")
    return props, adopted, votes, profiles, contrib, actions


def code_proposals(props: pd.DataFrame, adopted: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    win = adopted.set_index("round_number")
    rows = []
    for _, r in props.iterrows():
        rn = int(r["round_number"])
        proposer = int(r["proposer"])
        prof = profiles[profiles["agent_id"] == proposer].iloc[0]
        # pre-history: mean prop in previous 3 rounds
        # filled later
        category = CATEGORY_MAP.get(r["rule"], "other")
        direction = "increase" if float(r["new_value"]) > _default_for(r["rule"]) else (
            "decrease" if float(r["new_value"]) < _default_for(r["rule"]) else "unchanged"
        )
        # special-case: compared to previous adopted value if any
        adopted_row = win.loc[rn] if rn in win.index else None
        is_winner = False
        if adopted_row is not None:
            is_winner = (
                str(adopted_row["rule"]) == str(r["rule"])
                and float(adopted_row["new_value"]) == float(r["new_value"])
                and int(adopted_row["proposer"]) == proposer
            )
        rows.append(
            {
                "round_number": rn,
                "proposal_index": int(r["proposal_index"]),
                "proposer": proposer,
                "proposer_group": prof["agent_group"],
                "proposer_institution": prof["institution_choice"],
                "proposer_mean_prop": prof["mean_prop"],
                "proposer_zero_share": prof["zero_share"],
                "proposer_mean_rep": prof["mean_reputation"],
                "proposer_n_gossip": prof["n_gossip_target_rounds"],
                "rule": r["rule"],
                "new_value": float(r["new_value"]),
                "category": category,
                "direction_vs_param_default": direction,
                "reason": r["reason"],
                "adopted": int(is_winner),
                "shock_round": int(rn in (5, 10)),
                "record_id": r["record_id"],
            }
        )
    out = pd.DataFrame(rows)
    # attach pre-window contribution stats
    contrib = pd.read_csv(TABLES / "contributions.csv")
    pre_means = []
    for _, r in out.iterrows():
        pre = contrib[
            (contrib["agent_id"] == r["proposer"])
            & (contrib["round_number"] >= r["round_number"] - 3)
            & (contrib["round_number"] < r["round_number"])
        ]
        pre_means.append(pre["prop_of_wealth"].mean() if len(pre) else np.nan)
    out["proposer_prop_prev3"] = pre_means
    out.to_csv(TABLES / "proposals_coded.csv", index=False)
    return out


def _default_for(rule: str) -> float:
    defaults = {
        "SUBSIDY_FRACTION": 0.2,
        "SUBSIDY_TOP_N": 2,
        "PUNISHMENT_EFFECT": 3.0,
        "REWARD_EFFECT": 1.0,
        "ENDOWMENT_STAGE_2": 20,
        "MAX_PUNISHMENT_TOKENS": 10,  # may differ; used only for direction heuristic
        "LDF_MAX_COVERAGE": 0.90,
        "LDF_EQUITY_WEIGHT": 0.0,
        "LDF_PAYOUT_DAMAGE_WEIGHT": 1.0,
    }
    return float(defaults.get(rule, 0.0))


def parse_votes(votes: pd.DataFrame, props: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in votes.iterrows():
        choice = parse_vote_choice(r["vote_choice"])
        vote_idx = choice.get("vote")
        reason = choice.get("reason", "")
        rn = int(r["round_number"])
        voter = int(r["voter"])
        prof = profiles[profiles["agent_id"] == voter].iloc[0]
        # map vote to proposal
        match = props[(props["round_number"] == rn) & (props["proposal_index"] == vote_idx)]
        rule = match.iloc[0]["rule"] if len(match) else ""
        new_value = float(match.iloc[0]["new_value"]) if len(match) else np.nan
        proposer = int(match.iloc[0]["proposer"]) if len(match) else -1
        rows.append(
            {
                "round_number": rn,
                "voter": voter,
                "voter_group": prof["agent_group"],
                "voter_institution": prof["institution_choice"],
                "vote_index": vote_idx,
                "voted_rule": rule,
                "voted_new_value": new_value,
                "voted_proposer": proposer,
                "vote_reason": reason,
                "same_group_as_proposer": int(
                    proposer >= 0
                    and profiles.loc[profiles.agent_id == proposer, "agent_group"].iloc[0]
                    == prof["agent_group"]
                ),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "votes_parsed.csv", index=False)
    return out


def enforcement_stats(actions: pd.DataFrame, contrib: pd.DataFrame) -> pd.DataFrame:
    """Who pays for Stage-2 enforcement (SI only)."""
    si = actions[actions["institution_choice"] == "SI"].copy()
    si["enforcercost"] = si["assigned_punishments_total"] + si["assigned_rewards_total"]
    # join prop
    m = si.merge(
        contrib[["round_number", "agent_id", "prop_of_wealth", "contribution"]],
        on=["round_number", "agent_id"],
        how="left",
    )
    # correlation high contrib vs enforcement spend
    rows = []
    for rn, g in m.groupby("round_number"):
        if g["enforcercost"].sum() == 0:
            continue
        rows.append(
            {
                "round_number": rn,
                "n_si": len(g),
                "share_agents_with_positive_enforcement": (g["enforcercost"] > 0).mean(),
                "mean_cost_among_spenders": g.loc[g["enforcercost"] > 0, "enforcercost"].mean(),
                "corr_prop_vs_enforcement_cost": g["prop_of_wealth"].corr(g["enforcercost"]),
                "top_quartile_prop_share_of_cost": (
                    g.loc[g["prop_of_wealth"] >= g["prop_of_wealth"].quantile(0.75), "enforcercost"].sum()
                    / g["enforcercost"].sum()
                    if g["enforcercost"].sum()
                    else np.nan
                ),
                "total_enforcement_tokens": g["enforcercost"].sum(),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "enforcement_burden_by_round.csv", index=False)
    # agent totals
    ag = (
        m.groupby("agent_id")
        .agg(
            mean_prop=("prop_of_wealth", "mean"),
            total_enforcement_tokens=("enforcercost", "sum"),
            mean_enforcement=("enforcercost", "mean"),
            frac_rounds_enforcing=("enforcercost", lambda s: (s > 0).mean()),
        )
        .reset_index()
    )
    ag.to_csv(TABLES / "enforcement_burden_by_agent.csv", index=False)
    return out, ag


def post_adoption_behavior(adopted: pd.DataFrame, contrib: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in adopted.iterrows():
        rn = int(r["round_number"])
        for inst in ("SI", "SFI", "ALL"):
            sub = contrib if inst == "ALL" else contrib[contrib["institution_choice"] == inst]
            pre = sub[sub["round_number"].isin([rn - 2, rn - 1])]["prop_of_wealth"].mean()
            post = sub[sub["round_number"].isin([rn + 1, rn + 2])]["prop_of_wealth"].mean()
            rows.append(
                {
                    "round_number": rn,
                    "rule": r["rule"],
                    "new_value": r["new_value"],
                    "proposer": r["proposer"],
                    "institution_choice": inst,
                    "mean_prop_pre": pre,
                    "mean_prop_post": post,
                    "delta_prop": post - pre if pd.notna(pre) and pd.notna(post) else np.nan,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "post_adoption_prop_changes.csv", index=False)
    return out


def plots(coded, votes_p, enf_round, adopted):
    PLOTS.mkdir(parents=True, exist_ok=True)
    # proposal categories over rounds
    fig, ax = plt.subplots(figsize=(9, 4))
    cats = coded.groupby(["round_number", "category"]).size().unstack(fill_value=0)
    cats.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_xlabel("Democracy round")
    ax.set_ylabel("N proposals")
    ax.set_title("Proposal categories over time")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(PLOTS / "proposal_categories_timeline.png", dpi=150)
    plt.close(fig)

    # adopted rule timeline
    fig, ax = plt.subplots(figsize=(9, 3.5))
    for i, (_, r) in enumerate(adopted.sort_values("round_number").iterrows()):
        ax.scatter(r["round_number"], i, s=80)
        ax.text(r["round_number"] + 0.3, i, f"{r['rule']}={r['new_value']}", va="center", fontsize=8)
    ax.set_yticks([])
    ax.set_xlabel("Round")
    ax.set_title("Adopted rules timeline")
    fig.tight_layout()
    fig.savefig(PLOTS / "adopted_rules_timeline.png", dpi=150)
    plt.close(fig)

    # proposer SI vs SFI counts
    fig, ax = plt.subplots(figsize=(5, 4))
    counts = coded["proposer_institution"].value_counts()
    ax.bar(counts.index.astype(str), counts.values, color=["#5B4B8A", "#C47B2C"][: len(counts)])
    ax.set_ylabel("N proposals")
    ax.set_title("Who proposes? (by institution)")
    fig.tight_layout()
    fig.savefig(PLOTS / "proposers_by_institution.png", dpi=150)
    plt.close(fig)

    # enforcement burden
    if len(enf_round):
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(enf_round["round_number"], enf_round["share_agents_with_positive_enforcement"], label="share enforcing")
        ax.plot(enf_round["round_number"], enf_round["top_quartile_prop_share_of_cost"], label="top-quartile prop share of cost")
        ax.set_xlabel("Round")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8)
        ax.set_title("SI enforcement participation and burden concentration")
        fig.tight_layout()
        fig.savefig(PLOTS / "enforcement_burden.png", dpi=150)
        plt.close(fig)


def main() -> int:
    props, adopted, votes, profiles, contrib, actions = load()
    coded = code_proposals(props, adopted, profiles)
    votes_p = parse_votes(votes, props, profiles)
    enf_round, enf_agent = enforcement_stats(actions, contrib)
    post = post_adoption_behavior(adopted, contrib)
    plots(coded, votes_p, enf_round, adopted)

    summary = {
        "n_proposals": len(coded),
        "n_democracy_rounds": int(coded["round_number"].nunique()),
        "n_adopted": len(adopted),
        "proposals_by_category": coded["category"].value_counts().to_dict(),
        "proposals_by_institution": coded["proposer_institution"].value_counts().to_dict(),
        "adopted_by_category": [
            CATEGORY_MAP.get(r, "other") for r in adopted["rule"].tolist()
        ],
        "mean_proposer_prop": float(coded["proposer_mean_prop"].mean()),
        "mean_all_agent_prop": float(profiles["mean_prop"].mean()),
        "punishment_proposals": coded[coded["rule"] == "PUNISHMENT_EFFECT"][
            ["round_number", "proposer", "new_value", "adopted"]
        ].to_dict(orient="records"),
        "post_adoption_delta_all": post[post["institution_choice"] == "ALL"][
            ["round_number", "rule", "delta_prop"]
        ].to_dict(orient="records"),
        "enforcement_corr_mean": float(enf_round["corr_prop_vs_enforcement_cost"].mean())
        if len(enf_round)
        else None,
        "enforcement_topq_share_mean": float(enf_round["top_quartile_prop_share_of_cost"].mean())
        if len(enf_round)
        else None,
        "vote_same_group_rate": float(votes_p["same_group_as_proposer"].mean()),
    }
    with open(TABLES / "prompt5_numeric_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

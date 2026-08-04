#!/usr/bin/env python3
"""
Dashboard-dimension expansion + several additional research-question metrics
for the locked 20260804 run.

Run from repo root:
  python "docs/raw documentation/20260804/scripts/analyze_20260804_dashboard_dimensions.py"
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT = REPO_ROOT / "docs" / "raw documentation" / "20260804"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"
SOURCE = (
    "results/"
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json"
)
JSON_PATH = REPO_ROOT / SOURCE
RUN = "20260804_024555"
SHOCK = {5, 10}
DEMO = {5, 10, 15, 20, 25, 30}


def trust_class(level: str) -> str:
    if not level:
        return "default"
    l = str(level).lower()
    if "cooperative" in l or "similar" in l:
        return "cooperative"
    if "free-rider" in l or "uncooperative" in l or "untrustworthy" in l:
        return "free-rider"
    if "unreliable" in l or "inconsistent" in l or "cautious" in l:
        return "unreliable"
    if "strategic" in l or "opportunistic" in l or "aggressive" in l or "ambitious" in l:
        return "strategic"
    return "default"


def gini(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return float("nan")
    if np.allclose(v, 0):
        return 0.0
    v = np.sort(np.abs(v))
    n = len(v)
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * v) / (n * np.sum(v))) - (n + 1) / n)


def load_rounds():
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def wealth_gap_and_inst(rounds) -> pd.DataFrame:
    inst = pd.read_csv(TABLES / "institutional_state.csv")
    contrib = pd.read_csv(TABLES / "contributions.csv")
    rows = []
    for r in rounds:
        rn = int(r["round_number"])
        agents = r["agents"]
        dev = [float(a["wealth"]) for a in agents.values() if a.get("agent_group") == "developed"]
        dvg = [float(a["wealth"]) for a in agents.values() if a.get("agent_group") == "developing"]
        mean_dev, mean_dvg = float(np.mean(dev)), float(np.mean(dvg))
        gap = max(0.0, mean_dev - mean_dvg)
        csub = contrib[contrib["round_number"] == rn]
        abs_gini = gini(csub["contribution"].to_numpy())
        prop_gini = gini(csub["prop_of_wealth"].to_numpy())
        ir = inst[inst["round_number"] == rn].iloc[0]
        rows.append(
            {
                "round_number": rn,
                "gini_wealth": float(ir["gini_wealth"]),
                "cooperation_rate": float(ir["cooperation_rate"]),
                "mean_wealth_developed": mean_dev,
                "mean_wealth_developing": mean_dvg,
                "wealth_gap_dev_minus_dvg": gap,
                "gini_contribution_abs": abs_gini,
                "gini_prop_of_wealth": prop_gini,
                "shock_round": int(rn in SHOCK),
                "democracy_round": int(rn in DEMO),
            }
        )
    return pd.DataFrame(rows)


def ldf_coverage(rounds) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    fund = pd.read_csv(TABLES / "fund_state.csv")
    red = pd.read_csv(TABLES / "redistribution.csv")
    # need damage from JSON
    agent_cov = []
    for r in rounds:
        rn = int(r["round_number"])
        for aid, a in r["agents"].items():
            dmg = float(a.get("climate_damage_taken_round") or 0)
            pay = float(a.get("ldf_payout_round") or 0)
            contrib = float(a.get("ldf_contribution_round") or a.get("contribution") or 0)
            if dmg > 0 or pay > 0 or rn in SHOCK:
                agent_cov.append(
                    {
                        "round_number": rn,
                        "agent_id": int(aid),
                        "agent_group": a.get("agent_group"),
                        "institution_choice": a.get("institution_choice"),
                        "climate_damage": dmg,
                        "ldf_payout": pay,
                        "ldf_contribution": contrib,
                        "coverage_ratio": (pay / dmg) if dmg > 0 else (np.nan if pay == 0 else np.inf),
                        "net_transfer": pay - contrib,
                    }
                )
    agent_df = pd.DataFrame(agent_cov)
    round_rows = []
    for _, fr in fund.iterrows():
        rn = int(fr["round_number"])
        gross = float(fr["gross_damage_total"])
        payouts = float(fr["ldf_payouts_total"])
        round_rows.append(
            {
                "round_number": rn,
                "ldf_pool_end": float(fr["ldf_pool_end"]),
                "ldf_contributions_total": float(fr["ldf_contributions_total"]),
                "ldf_payouts_total": payouts,
                "gross_damage_total": gross,
                "net_damage_total": float(fr["net_damage_total"]),
                "coverage_ratio": (payouts / gross) if gross > 0 else np.nan,
            }
        )
    round_df = pd.DataFrame(round_rows)
    # lifetime net transfer by agent
    life = (
        red.groupby(["agent_id", "agent_group", "institution_choice"], as_index=False)
        .agg(
            sum_ldf_payout=("ldf_payout_round", "sum"),
            sum_ldf_contrib=("ldf_contribution_round", "sum"),
        )
    )
    life["net_ldf"] = life["sum_ldf_payout"] - life["sum_ldf_contrib"]
    # overall coverage across shock rounds
    shock_fund = round_df[round_df["round_number"].isin(SHOCK)]
    summary = {
        "shock_coverage_ratios": shock_fund[["round_number", "coverage_ratio", "gross_damage_total", "ldf_payouts_total"]].to_dict(
            orient="records"
        ),
        "cumulative_payouts": float(fund["ldf_payouts_total"].sum()),
        "cumulative_gross_damage": float(fund["gross_damage_total"].sum()),
        "overall_coverage_when_damage": float(
            fund["ldf_payouts_total"].sum() / fund["gross_damage_total"].sum()
            if fund["gross_damage_total"].sum() > 0
            else float("nan")
        ),
        "final_pool_end": float(fund["ldf_pool_end"].iloc[-1]),
    }
    return round_df, agent_df, summary, life


def beliefs_and_sanctions(rounds) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    bucket_counts = Counter()
    perception = defaultdict(lambda: {"coop": 0, "defector": 0})
    sanction_rounds = []
    edges_p = Counter()
    edges_r = Counter()
    giver_p = Counter()
    recv_p = Counter()

    for r in rounds:
        rn = int(r["round_number"])
        punish_tot = 0.0
        reward_tot = 0.0
        for aid, a in r["agents"].items():
            tl = (a.get("belief_state") or {}).get("trust_levels") or {}
            if isinstance(tl, dict):
                for target, label in tl.items():
                    cls = trust_class(label)
                    bucket_counts[cls] += 1
                    tid = str(target)
                    if cls in ("free-rider", "unreliable"):
                        perception[tid]["defector"] += 1
                    elif cls == "cooperative":
                        perception[tid]["coop"] += 1
            ap = a.get("assigned_punishments") or {}
            ar = a.get("assigned_rewards") or {}
            if isinstance(ap, dict):
                for t, v in ap.items():
                    v = float(v)
                    if v:
                        punish_tot += v
                        edges_p[(str(aid), str(t))] += v
                        giver_p[str(aid)] += v
                        recv_p[str(t)] += v
            if isinstance(ar, dict):
                for t, v in ar.items():
                    v = float(v)
                    if v:
                        reward_tot += v
                        edges_r[(str(aid), str(t))] += v
            rp = a.get("received_punishments")
            # sometimes scalar
        sanction_rounds.append(
            {
                "round_number": rn,
                "total_punishment_tokens": punish_tot,
                "total_reward_tokens": reward_tot,
                "n_punish_edges": sum(1 for (_, _), v in edges_p.items() if False),  # placeholder
            }
        )

    # recount edges per round properly
    sanction_rounds = []
    for r in rounds:
        rn = int(r["round_number"])
        punish_tot = reward_tot = 0.0
        n_pe = n_re = 0
        for aid, a in r["agents"].items():
            ap = a.get("assigned_punishments") or {}
            ar = a.get("assigned_rewards") or {}
            if isinstance(ap, dict):
                for t, v in ap.items():
                    v = float(v)
                    if v > 0:
                        punish_tot += v
                        n_pe += 1
            if isinstance(ar, dict):
                for t, v in ar.items():
                    v = float(v)
                    if v > 0:
                        reward_tot += v
                        n_re += 1
        sanction_rounds.append(
            {
                "round_number": rn,
                "total_punishment_tokens": punish_tot,
                "total_reward_tokens": reward_tot,
                "n_punish_edges": n_pe,
                "n_reward_edges": n_re,
            }
        )

    belief_df = pd.DataFrame(
        [{"trust_bucket": k, "count": v, "share": v / sum(bucket_counts.values())} for k, v in bucket_counts.items()]
    ).sort_values("count", ascending=False)

    perc_df = pd.DataFrame(
        [
            {"agent_id": int(aid), "perceived_coop_mentions": v["coop"], "perceived_defector_mentions": v["defector"]}
            for aid, v in perception.items()
            if aid.isdigit()
        ]
    ).sort_values("agent_id")

    sanc_df = pd.DataFrame(sanction_rounds)

    top_givers = pd.DataFrame(
        [{"agent_id": int(k), "punish_tokens_given": v} for k, v in giver_p.items()]
    ).sort_values("punish_tokens_given", ascending=False)
    top_recv = pd.DataFrame(
        [{"agent_id": int(k), "punish_tokens_received": v} for k, v in recv_p.items()]
    ).sort_values("punish_tokens_received", ascending=False)

    summary = {
        "belief_buckets": belief_df.to_dict(orient="records"),
        "top5_punish_givers": top_givers.head(5).to_dict(orient="records"),
        "top5_punish_receivers": top_recv.head(5).to_dict(orient="records"),
        "n_unique_punish_edges_lifetime": len(edges_p),
        "n_unique_reward_edges_lifetime": len(edges_r),
    }
    return belief_df, perc_df, sanc_df, summary, top_givers, top_recv


def tom_and_gossip_rq(rounds) -> dict:
    scores = []
    by_dir = defaultdict(list)
    le7 = 0
    total = 0
    # gossip target ranks
    contrib = pd.read_csv(TABLES / "contributions.csv")
    gossip = pd.read_csv(TABLES / "gossip_bulletins_reconstructed.csv")
    score_hist = Counter()

    for r in rounds:
        rn = int(r["round_number"])
        agents = r["agents"]
        # institution map
        inst = {str(aid): a.get("institution_choice") for aid, a in agents.items()}
        for aid, a in agents.items():
            tom = a.get("tom_scores") or {}
            if not isinstance(tom, dict):
                continue
            for tid, payload in tom.items():
                if isinstance(payload, dict):
                    sc = payload.get("score")
                else:
                    sc = payload
                try:
                    sc = float(sc)
                except (TypeError, ValueError):
                    continue
                scores.append(sc)
                score_hist[sc] += 1
                total += 1
                if sc <= 7.0:
                    le7 += 1
                si = inst.get(str(aid), "?")
                ti = inst.get(str(tid), "?")
                by_dir[f"{si}->{ti}"].append(sc)

    # gossip target prop ranks
    rank_rows = []
    tcol = None
    for c in ("target", "target_id", "about_agent"):
        if c in gossip.columns:
            tcol = c
            break
    if tcol and "round_number" in gossip.columns:
        for _, g in gossip.iterrows():
            rn = int(g["round_number"])
            tid = int(g[tcol])
            sub = contrib[contrib["round_number"] == rn].copy()
            sub["rank"] = sub["prop_of_wealth"].rank(ascending=False, method="min")
            hit = sub[sub["agent_id"] == tid]
            if len(hit):
                rank_rows.append(
                    {
                        "round_number": rn,
                        "target_id": tid,
                        "prop": float(hit["prop_of_wealth"].iloc[0]),
                        "prop_rank": float(hit["rank"].iloc[0]),
                        "n_agents": len(sub),
                    }
                )
    rank_df = pd.DataFrame(rank_rows)
    if len(rank_df):
        rank_df.to_csv(TABLES / "gossip_target_prop_ranks.csv", index=False)

    dir_means = {k: float(np.mean(v)) if v else None for k, v in by_dir.items()}
    return {
        "n_tom_scores": total,
        "frac_score_le_7": (le7 / total) if total else None,
        "score_value_counts_top": dict(score_hist.most_common(15)),
        "score_min": float(min(scores)) if scores else None,
        "score_max": float(max(scores)) if scores else None,
        "mean_by_direction": dir_means,
        "gossip_target_mean_prop_rank": float(rank_df["prop_rank"].mean()) if len(rank_df) else None,
        "gossip_target_frac_top_half": float((rank_df["prop_rank"] <= rank_df["n_agents"] / 2).mean())
        if len(rank_df)
        else None,
        "n_gossip_rank_rows": int(len(rank_df)),
    }


def payout_next_prop() -> pd.DataFrame:
    c = pd.read_csv(TABLES / "contributions.csv")
    r = pd.read_csv(TABLES / "redistribution.csv")
    df = c.merge(r[["round_number", "agent_id", "ldf_payout_round"]], on=["round_number", "agent_id"])
    df = df[df["agent_group"] == "developing"].sort_values(["agent_id", "round_number"])
    rows = []
    for aid, g in df.groupby("agent_id"):
        g = g.reset_index(drop=True)
        for i, row in g.iterrows():
            if row["ldf_payout_round"] <= 0:
                continue
            if i + 1 >= len(g):
                continue
            nxt = g.iloc[i + 1]
            pre = g.iloc[max(0, i - 3) : i]
            baseline = float(pre["prop_of_wealth"].mean()) if len(pre) else float("nan")
            rows.append(
                {
                    "agent_id": aid,
                    "payout_round": int(row["round_number"]),
                    "payout": float(row["ldf_payout_round"]),
                    "next_round": int(nxt["round_number"]),
                    "next_prop": float(nxt["prop_of_wealth"]),
                    "baseline_prev3_prop": baseline,
                    "delta_vs_baseline": float(nxt["prop_of_wealth"]) - baseline if baseline == baseline else np.nan,
                }
            )
    return pd.DataFrame(rows)


def conditional_coop_corr() -> dict:
    c = pd.read_csv(TABLES / "contributions.csv")
    out = {}
    for inst in ("SI", "SFI"):
        g = c[c["institution_choice"] == inst].copy()
        # leave-one-out peer mean prev round
        pairs = []
        for rn in range(2, 31):
            cur = g[g["round_number"] == rn]
            prev = g[g["round_number"] == rn - 1]
            if cur.empty or prev.empty:
                continue
            peer_mean = prev["prop_of_wealth"].mean()
            for _, row in cur.iterrows():
                # exclude self from prev mean if present
                prev_others = prev[prev["agent_id"] != row["agent_id"]]
                pm = prev_others["prop_of_wealth"].mean() if len(prev_others) else peer_mean
                pairs.append((pm, row["prop_of_wealth"]))
        if pairs:
            x, y = zip(*pairs)
            out[inst] = {
                "n": len(pairs),
                "corr_peer_prev_mean_vs_own_prop": float(np.corrcoef(x, y)[0, 1]),
            }
    return out


def shock_absorber_2x2() -> pd.DataFrame:
    d = pd.read_csv(TABLES / "shock_agent_deltas.csv")
    # expect columns with shock round deltas
    # fall back: compute from contributions
    c = pd.read_csv(TABLES / "contributions.csv")
    rows = []
    for aid, g in c.groupby("agent_id"):
        inst = g["institution_choice"].iloc[0]
        def delta(shock):
            pre = g[g["round_number"] == shock - 1]["prop_of_wealth"]
            post = g[g["round_number"] == shock + 1]["prop_of_wealth"]
            if len(pre) and len(post):
                return float(post.iloc[0] - pre.iloc[0])
            return np.nan
        d5, d10 = delta(5), delta(10)
        rows.append(
            {
                "agent_id": aid,
                "institution_choice": inst,
                "delta_r5": d5,
                "delta_r10": d10,
                "r5_up": int(d5 > 0) if d5 == d5 else None,
                "r10_up": int(d10 > 0) if d10 == d10 else None,
                "cell": (
                    f"{'up' if d5 > 0 else 'down'}_{'up' if d10 > 0 else 'down'}"
                    if d5 == d5 and d10 == d10
                    else "na"
                ),
            }
        )
    return pd.DataFrame(rows)


def fund_language_mcpr_scan() -> dict:
    rb = pd.read_csv(TABLES / "reasoning_blocks.csv")
    contrib = rb[rb["kind"] == "contribution"]
    fund_re = contrib["text"].fillna("").str.contains(
        r"pool|fund|sufficient|covered|enough|remaining|ldf|damage", case=False, regex=True
    )
    mcpr_re = contrib["text"].fillna("").str.contains(
        r"mcpr|marginal return|multiplier|1\.6|efficiency", case=False, regex=True
    )
    return {
        "n_contribution_blocks": int(len(contrib)),
        "n_fund_language": int(fund_re.sum()),
        "share_fund_language": float(fund_re.mean()),
        "n_mcpr_language": int(mcpr_re.sum()),
        "share_mcpr_language": float(mcpr_re.mean()),
        "examples_fund": contrib.loc[fund_re, ["evidence_id", "round_number", "agent_id", "text"]].head(8).to_dict(
            orient="records"
        ),
        "examples_mcpr": contrib.loc[mcpr_re, ["evidence_id", "round_number", "agent_id", "text"]].head(8).to_dict(
            orient="records"
        ),
    }


def make_plots(gap_df: pd.DataFrame, sanc_df: pd.DataFrame, fund_round: pd.DataFrame) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gap_df["round_number"], gap_df["gini_wealth"], label="gini_wealth", color="#2563eb")
    ax.plot(gap_df["round_number"], gap_df["cooperation_rate"], label="cooperation_rate", color="#059669")
    for s in SHOCK:
        ax.axvline(s, color="#dc2626", ls="--", alpha=0.5)
    ax.set_xlabel("Round")
    ax.set_title("Stored gini_wealth and cooperation_rate")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "gini_wealth_cooperation_rate.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gap_df["round_number"], gap_df["wealth_gap_dev_minus_dvg"], color="#7c3aed")
    for s in SHOCK:
        ax.axvline(s, color="#dc2626", ls="--", alpha=0.5)
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean wealth gap (developed âˆ’ developing)")
    ax.set_title("Developedâ€“developing wealth gap")
    fig.tight_layout()
    fig.savefig(PLOTS / "wealth_gap_developed_developing.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gap_df["round_number"], gap_df["gini_contribution_abs"], label="Gini(abs contrib)")
    ax.plot(gap_df["round_number"], gap_df["gini_prop_of_wealth"], label="Gini(prop)")
    ax.plot(gap_df["round_number"], gap_df["gini_wealth"], label="Gini(wealth)", ls=":")
    for s in SHOCK:
        ax.axvline(s, color="#dc2626", ls="--", alpha=0.4)
    ax.legend()
    ax.set_title("Contribution vs wealth inequality")
    fig.tight_layout()
    fig.savefig(PLOTS / "gini_contribution_vs_wealth.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(sanc_df["round_number"] - 0.15, sanc_df["total_punishment_tokens"], width=0.3, label="punish", color="#dc2626")
    ax.bar(sanc_df["round_number"] + 0.15, sanc_df["total_reward_tokens"], width=0.3, label="reward", color="#059669")
    ax.legend()
    ax.set_title("Sanction token totals by round")
    fig.tight_layout()
    fig.savefig(PLOTS / "sanction_punish_reward_timeline.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(fund_round["round_number"], fund_round["ldf_pool_end"], label="pool_end")
    ax.plot(fund_round["round_number"], fund_round["ldf_contributions_total"], label="contrib_total")
    ax.plot(fund_round["round_number"], fund_round["ldf_payouts_total"], label="payouts_total")
    ax.legend()
    ax.set_title("LDF pool dynamics")
    ax.set_yscale("log")
    fig.tight.layout() if False else fig.tight_layout()
    fig.savefig(PLOTS / "ldf_pool_dynamics.png", dpi=140)
    plt.close(fig)


def main() -> None:
    rounds = load_rounds()
    gap_df = wealth_gap_and_inst(rounds)
    gap_df.to_csv(TABLES / "dashboard_macro_series.csv", index=False)

    fund_round, agent_cov, fund_summary, life = ldf_coverage(rounds)
    fund_round.to_csv(TABLES / "ldf_coverage_by_round.csv", index=False)
    agent_cov.to_csv(TABLES / "ldf_coverage_by_agent_round.csv", index=False)
    life.to_csv(TABLES / "ldf_lifetime_net_transfers.csv", index=False)

    belief_df, perc_df, sanc_df, belief_summary, top_g, top_r = beliefs_and_sanctions(rounds)
    belief_df.to_csv(TABLES / "belief_trust_buckets.csv", index=False)
    perc_df.to_csv(TABLES / "belief_agent_perception_counts.csv", index=False)
    sanc_df.to_csv(TABLES / "sanction_timeline.csv", index=False)
    top_g.to_csv(TABLES / "sanction_top_givers.csv", index=False)
    top_r.to_csv(TABLES / "sanction_top_receivers.csv", index=False)

    tom = tom_and_gossip_rq(rounds)
    payout = payout_next_prop()
    payout.to_csv(TABLES / "ldf_payout_next_prop.csv", index=False)
    cc = conditional_coop_corr()
    shock2 = shock_absorber_2x2()
    shock2.to_csv(TABLES / "shock_absorber_2x2.csv", index=False)
    lang = fund_language_mcpr_scan()

    make_plots(gap_df, sanc_df, fund_round)

    summary = {
        "run": RUN,
        "fund": fund_summary,
        "beliefs_sanctions": belief_summary,
        "tom_gossip": tom,
        "conditional_coop": cc,
        "payout_next_prop": {
            "n_events": int(len(payout)),
            "mean_delta_vs_baseline": float(payout["delta_vs_baseline"].mean()) if len(payout) else None,
            "median_delta_vs_baseline": float(payout["delta_vs_baseline"].median()) if len(payout) else None,
        },
        "shock_2x2_counts": shock2["cell"].value_counts().to_dict() if len(shock2) else {},
        "fund_mcpr_language": {k: v for k, v in lang.items() if not k.startswith("examples")},
        "fund_mcpr_examples": {k: lang[k] for k in ("examples_fund", "examples_mcpr")},
        "wealth_gap_r1": float(gap_df.iloc[0]["wealth_gap_dev_minus_dvg"]),
        "wealth_gap_r30": float(gap_df.iloc[-1]["wealth_gap_dev_minus_dvg"]),
        "gini_wealth_r1": float(gap_df.iloc[0]["gini_wealth"]),
        "gini_wealth_r30": float(gap_df.iloc[-1]["gini_wealth"]),
    }
    (TABLES / "prompt_dashboard_rq_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()

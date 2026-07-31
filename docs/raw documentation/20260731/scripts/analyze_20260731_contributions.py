#!/usr/bin/env python3
"""
Prompt 3 quantitative analysis: contribution trajectories, SI vs SFI comparison,
and climatic-shock event study for the locked 20260731 run.

Run from repo root:
  python "docs/raw documentation/20260731/scripts/analyze_20260731_contributions.py"
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT = REPO_ROOT / "docs" / "raw documentation" / "20260731"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"
RUN = "20260731_013853"
SOURCE = (
    "results/To_Use/"
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json"
)
SHOCK_ROUNDS = (5, 10)
RNG = np.random.default_rng(20260731)


def load() -> pd.DataFrame:
    df = pd.read_csv(TABLES / "contributions.csv")
    df["prop"] = df["prop_of_wealth"].astype(float)
    df["contribution"] = df["contribution"].astype(float)
    df["wealth"] = df["wealth_end_of_round"].astype(float)
    # Primary proportional metric; clip display extremes for plots only
    df["prop_plot"] = df["prop"].clip(upper=np.nanpercentile(df["prop"].dropna(), 99))
    return df


def round_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (rn, inst), g in df.groupby(["round_number", "institution_choice"]):
        c = g["contribution"]
        p = g["prop"]
        rows.append(
            {
                "round_number": rn,
                "institution_choice": inst,
                "n": len(g),
                "mean_contribution": c.mean(),
                "median_contribution": c.median(),
                "std_contribution": c.std(ddof=1),
                "iqr_contribution": c.quantile(0.75) - c.quantile(0.25),
                "zero_share": (c <= 0).mean(),
                "mean_prop_wealth": p.mean(),
                "median_prop_wealth": p.median(),
                "std_prop_wealth": p.std(ddof=1),
                "iqr_prop_wealth": p.quantile(0.75) - p.quantile(0.25),
                "zero_prop_share": (p <= 0).mean(),
            }
        )
    # all-agents aggregate
    for rn, g in df.groupby("round_number"):
        c = g["contribution"]
        p = g["prop"]
        rows.append(
            {
                "round_number": rn,
                "institution_choice": "ALL",
                "n": len(g),
                "mean_contribution": c.mean(),
                "median_contribution": c.median(),
                "std_contribution": c.std(ddof=1),
                "iqr_contribution": c.quantile(0.75) - c.quantile(0.25),
                "zero_share": (c <= 0).mean(),
                "mean_prop_wealth": p.mean(),
                "median_prop_wealth": p.median(),
                "std_prop_wealth": p.std(ddof=1),
                "iqr_prop_wealth": p.quantile(0.75) - p.quantile(0.25),
                "zero_prop_share": (p <= 0).mean(),
            }
        )
    out = pd.DataFrame(rows).sort_values(["institution_choice", "round_number"])
    out.to_csv(TABLES / "contribution_round_summary.csv", index=False)
    return out


def persistence(df: pd.DataFrame) -> pd.DataFrame:
    """Agent-level autocorrelation of prop and contribution; movement vs group mean."""
    rows = []
    for aid, g in df.sort_values("round_number").groupby("agent_id"):
        g = g.copy()
        inst = g["institution_choice"].iloc[0]
        group = g["agent_group"].iloc[0]
        # peer mean same institution each round
        peer_means = []
        for _, row in g.iterrows():
            peers = df[
                (df["round_number"] == row["round_number"])
                & (df["institution_choice"] == row["institution_choice"])
                & (df["agent_id"] != aid)
            ]["prop"]
            peer_means.append(peers.mean() if len(peers) else np.nan)
        g["peer_mean_prop"] = peer_means
        g["dev_from_peer"] = g["prop"] - g["peer_mean_prop"]
        # persistence: corr of lag1
        prop = g["prop"].to_numpy()
        contrib = g["contribution"].to_numpy()
        if len(prop) > 2:
            ac_prop = np.corrcoef(prop[:-1], prop[1:])[0, 1]
            ac_c = np.corrcoef(contrib[:-1], contrib[1:])[0, 1]
        else:
            ac_prop = ac_c = np.nan
        # mean abs change toward peer (negative delta_|dev| = convergence)
        abs_dev = np.abs(g["dev_from_peer"].to_numpy())
        if len(abs_dev) > 1:
            conv = np.nanmean(abs_dev[1:] - abs_dev[:-1])
        else:
            conv = np.nan
        rows.append(
            {
                "agent_id": aid,
                "agent_group": group,
                "institution_choice": inst,
                "mean_contribution": contrib.mean(),
                "mean_prop_wealth": prop.mean(),
                "median_prop_wealth": np.median(prop),
                "std_prop_wealth": np.std(prop, ddof=1),
                "zero_share": float(np.mean(contrib <= 0)),
                "autocorr_prop_lag1": ac_prop,
                "autocorr_contrib_lag1": ac_c,
                "mean_abs_dev_from_peer_prop": np.nanmean(abs_dev),
                "mean_change_abs_dev_prop": conv,  # <0 => converging toward peer mean
                "n_rounds": len(g),
            }
        )
    out = pd.DataFrame(rows).sort_values("agent_id")
    out.to_csv(TABLES / "contribution_agent_persistence.csv", index=False)
    return out


def bootstrap_mean_ci(x: np.ndarray, n_boot: int = 2000, alpha: float = 0.05):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    boots = RNG.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


def hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    va, vb = a.var(ddof=1), b.var(ddof=1)
    sp = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if sp == 0:
        return 0.0
    d = (a.mean() - b.mean()) / sp
    # small-sample correction
    J = 1 - (3 / (4 * (na + nb) - 9))
    return float(J * d)


def si_sfi_comparison(df: pd.DataFrame, agent_pers: pd.DataFrame) -> dict:
    si = df[df["institution_choice"] == "SI"]
    sfi = df[df["institution_choice"] == "SFI"]

    results = {"metric": "prop_of_wealth", "notes": []}
    results["notes"].append(
        "In this run institution_choice is perfectly collinear with agent_group "
        "(developed=SI, developing=SFI). Differences are not identifiable as "
        "institution effects separate from group/wealth differences."
    )
    results["notes"].append(
        "Agents do not observe numeric LDF pool balance; interpret contributions "
        "without assuming optimisation against fund stock."
    )

    # agent-round weighted (all rows)
    for label, sub in [("SI", si), ("SFI", sfi)]:
        mean, lo, hi = bootstrap_mean_ci(sub["prop"].to_numpy())
        results[f"{label}_agent_round_mean_prop"] = mean
        results[f"{label}_agent_round_mean_prop_ci95"] = [lo, hi]
        results[f"{label}_agent_round_median_prop"] = float(sub["prop"].median())
        results[f"{label}_agent_round_std_prop"] = float(sub["prop"].std(ddof=1))
        results[f"{label}_agent_round_n"] = int(len(sub))
        results[f"{label}_zero_share"] = float((sub["contribution"] <= 0).mean())
        results[f"{label}_mean_abs_contribution"] = float(sub["contribution"].mean())
        results[f"{label}_median_abs_contribution"] = float(sub["contribution"].median())

    # mean of individual-agent means
    si_am = agent_pers[agent_pers["institution_choice"] == "SI"]["mean_prop_wealth"].to_numpy()
    sfi_am = agent_pers[agent_pers["institution_choice"] == "SFI"]["mean_prop_wealth"].to_numpy()
    for label, arr in [("SI", si_am), ("SFI", sfi_am)]:
        mean, lo, hi = bootstrap_mean_ci(arr)
        results[f"{label}_mean_of_agent_means_prop"] = mean
        results[f"{label}_mean_of_agent_means_prop_ci95"] = [lo, hi]
        results[f"{label}_n_agents"] = int(len(arr))

    results["effect_size_hedges_g_SI_minus_SFI_agent_round"] = hedges_g(
        si["prop"].to_numpy(), sfi["prop"].to_numpy()
    )
    results["effect_size_hedges_g_SI_minus_SFI_agent_means"] = hedges_g(si_am, sfi_am)

    # leave-one-agent-out sensitivity on agent-round mean prop
    sens = []
    for aid in sorted(df["agent_id"].unique()):
        sub = df[df["agent_id"] != aid]
        si_m = sub.loc[sub["institution_choice"] == "SI", "prop"].mean()
        sfi_m = sub.loc[sub["institution_choice"] == "SFI", "prop"].mean()
        sens.append(
            {
                "left_out_agent": aid,
                "SI_mean_prop": si_m,
                "SFI_mean_prop": sfi_m,
                "diff_SI_minus_SFI": si_m - sfi_m,
            }
        )
    sens_df = pd.DataFrame(sens)
    sens_df.to_csv(TABLES / "si_sfi_leave_one_out.csv", index=False)
    results["loo_diff_min"] = float(sens_df["diff_SI_minus_SFI"].min())
    results["loo_diff_max"] = float(sens_df["diff_SI_minus_SFI"].max())
    results["loo_diff_full"] = float(
        results["SI_agent_round_mean_prop"] - results["SFI_agent_round_mean_prop"]
    )

    # round-specific means
    by_round = (
        df.groupby(["round_number", "institution_choice"])["prop"]
        .agg(["mean", "median", "std", "count"])
        .reset_index()
    )
    by_round.to_csv(TABLES / "si_sfi_prop_by_round.csv", index=False)

    # democracy rounds proximity
    demo_rounds = {5, 10, 15, 20, 25, 30}
    df = df.copy()
    df["near_demo"] = df["round_number"].isin(demo_rounds)
    demo_cmp = (
        df.groupby(["institution_choice", "near_demo"])["prop"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )
    demo_cmp.to_csv(TABLES / "si_sfi_prop_democracy_rounds.csv", index=False)

    with open(TABLES / "si_sfi_comparison_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results


def event_study(df: pd.DataFrame) -> pd.DataFrame:
    """Windows around each shock: pre[-3,-1], during[0], post1[+1], post2[+2,+3]."""
    rows = []
    for shock in SHOCK_ROUNDS:
        windows = {
            "pre": list(range(shock - 3, shock)),
            "during": [shock],
            "post_immediate": [shock + 1],
            "post_later": list(range(shock + 2, shock + 4)),
        }
        # also wider post
        windows["post_wide"] = list(range(shock + 1, shock + 5))
        for inst in ("SI", "SFI", "ALL"):
            sub = df if inst == "ALL" else df[df["institution_choice"] == inst]
            for wname, rounds in windows.items():
                valid = [r for r in rounds if 1 <= r <= 30]
                g = sub[sub["round_number"].isin(valid)]
                if g.empty:
                    continue
                p = g["prop"]
                c = g["contribution"]
                rows.append(
                    {
                        "shock_round": shock,
                        "window": wname,
                        "rounds": ",".join(map(str, valid)),
                        "institution_choice": inst,
                        "n_agent_rounds": len(g),
                        "n_agents": g["agent_id"].nunique(),
                        "mean_prop_wealth": p.mean(),
                        "median_prop_wealth": p.median(),
                        "std_prop_wealth": p.std(ddof=1),
                        "iqr_prop_wealth": p.quantile(0.75) - p.quantile(0.25),
                        "zero_share": (c <= 0).mean(),
                        "mean_contribution": c.mean(),
                        "median_contribution": c.median(),
                        "std_contribution": c.std(ddof=1),
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "shock_event_study.csv", index=False)

    # agent-level pre vs post change (within-agent) for each shock
    delta_rows = []
    for shock in SHOCK_ROUNDS:
        pre_r = [shock - 2, shock - 1]
        post_r = [shock + 1, shock + 2]
        for aid, g in df.groupby("agent_id"):
            pre = g[g["round_number"].isin(pre_r)]["prop"].mean()
            post = g[g["round_number"].isin(post_r)]["prop"].mean()
            during = g[g["round_number"] == shock]["prop"].mean()
            delta_rows.append(
                {
                    "shock_round": shock,
                    "agent_id": aid,
                    "institution_choice": g["institution_choice"].iloc[0],
                    "agent_group": g["agent_group"].iloc[0],
                    "mean_prop_pre": pre,
                    "mean_prop_during": during,
                    "mean_prop_post": post,
                    "delta_post_minus_pre": post - pre,
                    "delta_during_minus_pre": during - pre,
                }
            )
    deltas = pd.DataFrame(delta_rows)
    deltas.to_csv(TABLES / "shock_agent_deltas.csv", index=False)
    return out, deltas


def make_plots(df: pd.DataFrame, round_sum: pd.DataFrame, deltas: pd.DataFrame) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)

    # 1. Mean prop trajectories SI/SFI/ALL
    fig, ax = plt.subplots(figsize=(10, 5))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C"), ("ALL", "#444444")]:
        sub = round_sum[round_sum["institution_choice"] == inst]
        ax.plot(sub["round_number"], sub["mean_prop_wealth"], label=inst, color=color, lw=2)
        ax.fill_between(
            sub["round_number"],
            sub["mean_prop_wealth"] - sub["std_prop_wealth"].fillna(0),
            sub["mean_prop_wealth"] + sub["std_prop_wealth"].fillna(0),
            color=color,
            alpha=0.12,
        )
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.8)
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean prop_of_wealth")
    ax.set_title("Mean proportional contribution by institution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_mean_prop_trajectories.png", dpi=150)
    plt.close(fig)

    # 2. Median + IQR prop
    fig, ax = plt.subplots(figsize=(10, 5))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = round_sum[round_sum["institution_choice"] == inst]
        ax.plot(sub["round_number"], sub["median_prop_wealth"], label=f"{inst} median", color=color)
        # approximate band using mean± not IQR center; plot IQR half around median
        ax.fill_between(
            sub["round_number"],
            sub["median_prop_wealth"] - sub["iqr_prop_wealth"] / 2,
            sub["median_prop_wealth"] + sub["iqr_prop_wealth"] / 2,
            color=color,
            alpha=0.15,
            label=f"{inst} ±IQR/2",
        )
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1)
    ax.set_xlabel("Round")
    ax.set_ylabel("Median prop_of_wealth")
    ax.set_title("Median proportional contribution (± IQR/2 band)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_median_prop_iqr.png", dpi=150)
    plt.close(fig)

    # 3. Absolute mean contribution (log scale) — wealth confound visible
    fig, ax = plt.subplots(figsize=(10, 5))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = round_sum[round_sum["institution_choice"] == inst]
        ax.plot(sub["round_number"], sub["mean_contribution"], label=inst, color=color)
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1)
    ax.set_yscale("log")
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean contribution (log scale)")
    ax.set_title("Mean absolute contribution (SI vs SFI; wealth-confounded)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_mean_absolute_log.png", dpi=150)
    plt.close(fig)

    # 4. Zero contribution frequency
    fig, ax = plt.subplots(figsize=(10, 4))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = round_sum[round_sum["institution_choice"] == inst]
        ax.plot(sub["round_number"], sub["zero_share"], label=inst, color=color)
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Round")
    ax.set_ylabel("Share with contribution == 0")
    ax.set_title("Zero-contribution frequency")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_zero_frequency.png", dpi=150)
    plt.close(fig)

    # 5. Individual agent prop trajectories (small multiples by institution)
    for inst in ("SI", "SFI"):
        sub = df[df["institution_choice"] == inst]
        fig, ax = plt.subplots(figsize=(10, 5))
        for aid, g in sub.groupby("agent_id"):
            ax.plot(g["round_number"], g["prop"], alpha=0.35, lw=1)
        mean_line = (
            round_sum[round_sum["institution_choice"] == inst]
            .set_index("round_number")["mean_prop_wealth"]
        )
        ax.plot(mean_line.index, mean_line.values, color="black", lw=2.5, label="group mean")
        for s in SHOCK_ROUNDS:
            ax.axvline(s, color="#AA2222", ls="--", lw=1)
        ax.set_xlabel("Round")
        ax.set_ylabel("prop_of_wealth")
        ax.set_title(f"Individual prop trajectories — {inst}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(PLOTS / f"contrib_individual_prop_{inst}.png", dpi=150)
        plt.close(fig)

    # 6. Smoothed group trajectories (rolling mean of mean prop)
    fig, ax = plt.subplots(figsize=(10, 5))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = round_sum[round_sum["institution_choice"] == inst].sort_values("round_number")
        smooth = sub["mean_prop_wealth"].rolling(3, center=True, min_periods=1).mean()
        ax.plot(sub["round_number"], smooth, label=f"{inst} (3-round roll)", color=color, lw=2)
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1)
    ax.set_xlabel("Round")
    ax.set_ylabel("Smoothed mean prop_of_wealth")
    ax.set_title("Smoothed group proportional contribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_smoothed_prop.png", dpi=150)
    plt.close(fig)

    # 7. Shock deltas boxplot
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, shock in zip(axes, SHOCK_ROUNDS):
        d = deltas[deltas["shock_round"] == shock]
        data = [
            d.loc[d["institution_choice"] == "SI", "delta_post_minus_pre"].dropna(),
            d.loc[d["institution_choice"] == "SFI", "delta_post_minus_pre"].dropna(),
        ]
        ax.boxplot(data, labels=["SI", "SFI"])
        ax.axhline(0, color="#888", lw=1)
        ax.set_title(f"Shock R{shock}: post−pre prop")
        ax.set_ylabel("Δ prop_of_wealth")
    fig.suptitle("Within-agent proportional contribution change after shocks")
    fig.tight_layout()
    fig.savefig(PLOTS / "shock_delta_boxplot.png", dpi=150)
    plt.close(fig)

    # 8. Dispersion over time
    fig, ax = plt.subplots(figsize=(10, 4))
    for inst, color in [("SI", "#5B4B8A"), ("SFI", "#C47B2C")]:
        sub = round_sum[round_sum["institution_choice"] == inst]
        ax.plot(sub["round_number"], sub["std_prop_wealth"], label=inst, color=color)
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1)
    ax.set_xlabel("Round")
    ax.set_ylabel("Std of prop_of_wealth")
    ax.set_title("Dispersion of proportional contributions")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "contrib_dispersion_prop.png", dpi=150)
    plt.close(fig)


def write_numbers_sidecar(cmp: dict, event: pd.DataFrame, deltas: pd.DataFrame, pers: pd.DataFrame):
    """Compact numbers file for markdown authors / verification."""
    summary = {
        "run": RUN,
        "source": SOURCE,
        "shock_rounds": list(SHOCK_ROUNDS),
        "si_sfi": cmp,
        "persistence": {
            "SI_mean_autocorr_prop": float(
                pers.loc[pers["institution_choice"] == "SI", "autocorr_prop_lag1"].mean()
            ),
            "SFI_mean_autocorr_prop": float(
                pers.loc[pers["institution_choice"] == "SFI", "autocorr_prop_lag1"].mean()
            ),
            "SI_mean_change_abs_dev": float(
                pers.loc[pers["institution_choice"] == "SI", "mean_change_abs_dev_prop"].mean()
            ),
            "SFI_mean_change_abs_dev": float(
                pers.loc[pers["institution_choice"] == "SFI", "mean_change_abs_dev_prop"].mean()
            ),
        },
        "shock_delta_means": {},
    }
    for shock in SHOCK_ROUNDS:
        d = deltas[deltas["shock_round"] == shock]
        summary["shock_delta_means"][str(shock)] = {
            inst: {
                "mean_delta_post_minus_pre": float(
                    d.loc[d["institution_choice"] == inst, "delta_post_minus_pre"].mean()
                ),
                "median_delta_post_minus_pre": float(
                    d.loc[d["institution_choice"] == inst, "delta_post_minus_pre"].median()
                ),
                "frac_positive_delta": float(
                    (d.loc[d["institution_choice"] == inst, "delta_post_minus_pre"] > 0).mean()
                ),
                "n": int((d["institution_choice"] == inst).sum()),
            }
            for inst in ("SI", "SFI")
        }
    with open(TABLES / "prompt3_numeric_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def main() -> int:
    df = load()
    assert len(df) == 780, len(df)
    round_sum = round_summary(df)
    pers = persistence(df)
    cmp = si_sfi_comparison(df, pers)
    event, deltas = event_study(df)
    make_plots(df, round_sum, deltas)
    write_numbers_sidecar(cmp, event, deltas, pers)
    print("Wrote Prompt 3 tables and plots")
    print("SI mean prop:", cmp["SI_agent_round_mean_prop"])
    print("SFI mean prop:", cmp["SFI_agent_round_mean_prop"])
    print("Hedges g (agent-round):", cmp["effect_size_hedges_g_SI_minus_SFI_agent_round"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

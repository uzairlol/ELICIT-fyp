#!/usr/bin/env python3
"""
Cross-seed comparison: seed1 (20260731) vs seed2 (20260804) Full LDF runs.

Primary metric: prop_of_wealth = contribution / wealth_end_of_round
(already present in contributions.csv when extract scripts created it).

Run from repo root:
  python "docs/raw documentation/20260804/scripts/cross_seed_comparison.py"

Does not require the raw JSON results files (tables packs are primary);
JSON paths are recorded in the summary when found.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy import stats as scipy_stats
except ImportError:  # pragma: no cover
    scipy_stats = None  # type: ignore

try:
    from statsmodels.tsa.stattools import adfuller as _adfuller
except ImportError:  # pragma: no cover
    _adfuller = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[4]
SEED1_TABLES = REPO_ROOT / "docs" / "raw documentation" / "20260731" / "tables"
SEED2_TABLES = REPO_ROOT / "docs" / "raw documentation" / "20260804" / "tables"
OUT_TABLES = SEED2_TABLES
OUT_PLOTS = REPO_ROOT / "docs" / "raw documentation" / "20260804" / "plots" / "cross_seed"

SEED1_JSON_CANDIDATES = [
    REPO_ROOT
    / "results"
    / "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json",
    REPO_ROOT
    / "results"
    / "To_Use"
    / "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json",
]
SEED2_JSON = (
    REPO_ROOT
    / "results"
    / "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json"
)

SHOCK_ROUNDS = (5, 10)
SEED_LABELS = {"seed1": "seed1 (20260731)", "seed2": "seed2 (20260804)"}
COLORS = {"seed1": "#2C5F8A", "seed2": "#C47B2C"}
INST_COLORS = {"SI": "#5B4B8A", "SFI": "#C47B2C", "ALL": "#444444"}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _find_json(candidates: list[Path]) -> Optional[str]:
    for p in candidates:
        if p.exists():
            try:
                return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
            except ValueError:
                return str(p)
    return None


def load_contributions(tables: Path, seed_key: str) -> pd.DataFrame:
    path = tables / "contributions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required table: {path}")
    df = pd.read_csv(path)
    if "prop_of_wealth" not in df.columns:
        wealth = df["wealth_end_of_round"].astype(float)
        contrib = df["contribution"].astype(float)
        df["prop_of_wealth"] = np.where(wealth > 0, contrib / wealth, np.nan)
    df["prop"] = df["prop_of_wealth"].astype(float)
    df["contribution"] = df["contribution"].astype(float)
    df["wealth"] = df["wealth_end_of_round"].astype(float)
    df["seed"] = seed_key
    return df


def ensure_dirs() -> None:
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)
    OUT_TABLES.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Core aggregates
# ---------------------------------------------------------------------------


def round_mean_prop(df: pd.DataFrame) -> pd.DataFrame:
    """Mean/median/std prop by round for ALL / SI / SFI."""
    rows = []
    for seed, sdf in df.groupby("seed"):
        for rn, g in sdf.groupby("round_number"):
            rows.append(
                {
                    "seed": seed,
                    "round_number": int(rn),
                    "institution_choice": "ALL",
                    "n": len(g),
                    "mean_prop": float(g["prop"].mean()),
                    "median_prop": float(g["prop"].median()),
                    "std_prop": float(g["prop"].std(ddof=1)),
                    "mean_contribution": float(g["contribution"].mean()),
                    "mean_wealth": float(g["wealth"].mean()),
                }
            )
        for (rn, inst), g in sdf.groupby(["round_number", "institution_choice"]):
            rows.append(
                {
                    "seed": seed,
                    "round_number": int(rn),
                    "institution_choice": inst,
                    "n": len(g),
                    "mean_prop": float(g["prop"].mean()),
                    "median_prop": float(g["prop"].median()),
                    "std_prop": float(g["prop"].std(ddof=1)),
                    "mean_contribution": float(g["contribution"].mean()),
                    "mean_wealth": float(g["wealth"].mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(["seed", "institution_choice", "round_number"])


def wealth_gap_series(df: pd.DataFrame) -> pd.DataFrame:
    """Developed - developing mean wealth by round, both seeds."""
    rows = []
    for seed, sdf in df.groupby("seed"):
        for rn, g in sdf.groupby("round_number"):
            by_group = g.groupby("agent_group")["wealth"].mean()
            developed = float(by_group.get("developed", np.nan))
            developing = float(by_group.get("developing", np.nan))
            rows.append(
                {
                    "seed": seed,
                    "round_number": int(rn),
                    "mean_wealth_developed": developed,
                    "mean_wealth_developing": developing,
                    "wealth_gap_dev_minus_developing": developed - developing,
                    "wealth_ratio_dev_over_developing": (
                        developed / developing if developing and developing > 0 else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["seed", "round_number"])


def load_fund_pool(tables: Path, seed_key: str) -> Optional[pd.DataFrame]:
    fund = _read_csv(tables / "fund_state.csv")
    if fund is None:
        return None
    out = fund[["round_number", "ldf_pool_end"]].copy()
    out["seed"] = seed_key
    return out


def agent_mean_prop(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (seed, aid), g in df.groupby(["seed", "agent_id"]):
        rows.append(
            {
                "seed": seed,
                "agent_id": int(aid),
                "agent_group": g["agent_group"].iloc[0],
                "institution_choice": g["institution_choice"].iloc[0],
                "mean_prop": float(g["prop"].mean()),
                "median_prop": float(g["prop"].median()),
                "n_rounds": int(len(g)),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------


def _corr_with_pvalue(x: np.ndarray, y: np.ndarray, method: str) -> dict[str, Any]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = int(len(x))
    out: dict[str, Any] = {"n": n, "r": np.nan, "p": np.nan, "method": method}
    if n < 3 or scipy_stats is None:
        if scipy_stats is None:
            out["note"] = "scipy unavailable"
        return out
    if method == "pearson":
        r, p = scipy_stats.pearsonr(x, y)
    else:
        r, p = scipy_stats.spearmanr(x, y)
    out["r"] = float(r)
    out["p"] = float(p)
    return out


def mann_whitney_si_sfi(df: pd.DataFrame, seed_key: str) -> dict[str, Any]:
    sub = df[df["seed"] == seed_key]
    si = sub.loc[sub["institution_choice"] == "SI", "prop"].to_numpy(dtype=float)
    sfi = sub.loc[sub["institution_choice"] == "SFI", "prop"].to_numpy(dtype=float)
    result: dict[str, Any] = {
        "seed": seed_key,
        "metric": "prop_of_wealth",
        "unit": "agent-round",
        "n_SI": int(np.isfinite(si).sum()),
        "n_SFI": int(np.isfinite(sfi).sum()),
        "mean_SI": float(np.nanmean(si)),
        "mean_SFI": float(np.nanmean(sfi)),
        "median_SI": float(np.nanmedian(si)),
        "median_SFI": float(np.nanmedian(sfi)),
    }
    # also agent-means
    am = agent_mean_prop(sub)
    si_am = am.loc[am["institution_choice"] == "SI", "mean_prop"].to_numpy(dtype=float)
    sfi_am = am.loc[am["institution_choice"] == "SFI", "mean_prop"].to_numpy(dtype=float)
    result["n_agents_SI"] = int(len(si_am))
    result["n_agents_SFI"] = int(len(sfi_am))
    result["mean_of_agent_means_SI"] = float(np.nanmean(si_am))
    result["mean_of_agent_means_SFI"] = float(np.nanmean(sfi_am))

    if scipy_stats is None:
        result["note"] = "scipy unavailable; Mann-Whitney skipped"
        return result

    si_c = si[np.isfinite(si)]
    sfi_c = sfi[np.isfinite(sfi)]
    if len(si_c) and len(sfi_c):
        u, p = scipy_stats.mannwhitneyu(si_c, sfi_c, alternative="two-sided")
        result["mannwhitney_U_agent_round"] = float(u)
        result["mannwhitney_p_agent_round"] = float(p)
    if len(si_am) and len(sfi_am):
        u2, p2 = scipy_stats.mannwhitneyu(si_am, sfi_am, alternative="two-sided")
        result["mannwhitney_U_agent_means"] = float(u2)
        result["mannwhitney_p_agent_means"] = float(p2)
    result["note"] = (
        "institution_choice is collinear with agent_group "
        "(developed=SI, developing=SFI) in these runs."
    )
    return result


def shock_within_agent_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Within-agent pre→post prop deltas around R5 and R10."""
    rows = []
    for seed, sdf in df.groupby("seed"):
        for shock in SHOCK_ROUNDS:
            pre_r = [shock - 2, shock - 1]
            post_r = [shock + 1, shock + 2]
            for aid, g in sdf.groupby("agent_id"):
                pre = g.loc[g["round_number"].isin(pre_r), "prop"].mean()
                post = g.loc[g["round_number"].isin(post_r), "prop"].mean()
                during = g.loc[g["round_number"] == shock, "prop"].mean()
                rows.append(
                    {
                        "seed": seed,
                        "shock_round": int(shock),
                        "agent_id": int(aid),
                        "institution_choice": g["institution_choice"].iloc[0],
                        "agent_group": g["agent_group"].iloc[0],
                        "mean_prop_pre": float(pre) if pd.notna(pre) else np.nan,
                        "mean_prop_during": float(during) if pd.notna(during) else np.nan,
                        "mean_prop_post": float(post) if pd.notna(post) else np.nan,
                        "delta_post_minus_pre": (
                            float(post - pre) if pd.notna(pre) and pd.notna(post) else np.nan
                        ),
                        "delta_during_minus_pre": (
                            float(during - pre)
                            if pd.notna(pre) and pd.notna(during)
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def wilcoxon_shock_summary(deltas: pd.DataFrame) -> list[dict[str, Any]]:
    results = []
    for (seed, shock), g in deltas.groupby(["seed", "shock_round"]):
        d = g["delta_post_minus_pre"].to_numpy(dtype=float)
        d = d[np.isfinite(d)]
        row: dict[str, Any] = {
            "seed": seed,
            "shock_round": int(shock),
            "n_agents": int(len(d)),
            "mean_delta_post_minus_pre": float(np.mean(d)) if len(d) else np.nan,
            "median_delta_post_minus_pre": float(np.median(d)) if len(d) else np.nan,
        }
        if scipy_stats is None:
            row["wilcoxon_note"] = "scipy unavailable"
        elif len(d) < 5:
            row["wilcoxon_note"] = "too few observations"
        else:
            # drop exact zeros for Wilcoxon signed-rank
            nonzero = d[d != 0]
            if len(nonzero) < 5:
                row["wilcoxon_note"] = "too few non-zero deltas"
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        w, p = scipy_stats.wilcoxon(nonzero, alternative="two-sided")
                        row["wilcoxon_stat"] = float(w)
                        row["wilcoxon_p"] = float(p)
                    except ValueError as exc:
                        row["wilcoxon_note"] = str(exc)
        results.append(row)
    return results


def mann_kendall_simple(x: np.ndarray) -> dict[str, Any]:
    """
    Mann-Kendall trend via Kendall's tau on (time, value).
    Requires scipy; returns skip note otherwise.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    out: dict[str, Any] = {"n": int(len(x))}
    if scipy_stats is None:
        out["skipped"] = True
        out["note"] = "scipy unavailable; Mann-Kendall skipped"
        return out
    if len(x) < 4:
        out["skipped"] = True
        out["note"] = "series too short"
        return out
    t = np.arange(len(x), dtype=float)
    tau, p = scipy_stats.kendalltau(t, x)
    # Sen's slope (median of pairwise slopes)
    slopes = []
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dt = j - i
            if dt:
                slopes.append((x[j] - x[i]) / dt)
    out.update(
        {
            "skipped": False,
            "kendall_tau": float(tau) if pd.notna(tau) else np.nan,
            "p_value": float(p) if pd.notna(p) else np.nan,
            "sens_slope": float(np.median(slopes)) if slopes else np.nan,
            "trend": (
                "increasing"
                if pd.notna(p) and p < 0.05 and tau > 0
                else "decreasing"
                if pd.notna(p) and p < 0.05 and tau < 0
                else "no significant trend"
            ),
        }
    )
    return out


def adf_test(x: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if _adfuller is None:
        return {"skipped": True, "note": "statsmodels unavailable; ADF skipped"}
    if len(x) < 8:
        return {"skipped": True, "note": "series too short for ADF"}
    try:
        stat, p, usedlag, nobs, crit, icbest = _adfuller(x, autolag="AIC")
        return {
            "skipped": False,
            "adf_stat": float(stat),
            "p_value": float(p),
            "usedlag": int(usedlag),
            "nobs": int(nobs),
            "critical_values": {k: float(v) for k, v in crit.items()},
            "icbest": float(icbest) if icbest is not None else None,
            "reject_unit_root_5pct": bool(p < 0.05),
        }
    except Exception as exc:  # pragma: no cover
        return {"skipped": True, "note": f"ADF failed: {exc}"}


# ---------------------------------------------------------------------------
# Reputation / rules
# ---------------------------------------------------------------------------


def compare_reputation_summaries() -> tuple[Optional[pd.DataFrame], dict[str, Any]]:
    s1 = _read_csv(SEED1_TABLES / "reputation_gossip_event_summary.csv")
    s2 = _read_csv(SEED2_TABLES / "reputation_gossip_event_summary.csv")
    meta: dict[str, Any] = {}
    if s1 is None and s2 is None:
        meta["note"] = "reputation_gossip_event_summary.csv missing for both seeds"
        return None, meta
    frames = []
    if s1 is not None:
        a = s1.copy()
        a["seed"] = "seed1"
        frames.append(a)
    else:
        meta["seed1_missing"] = True
    if s2 is not None:
        b = s2.copy()
        b["seed"] = "seed2"
        frames.append(b)
    else:
        meta["seed2_missing"] = True
    both = pd.concat(frames, ignore_index=True)
    # focus immediate horizon mean delta by event family
    imm = both[both.get("horizon", pd.Series(dtype=str)) == "imm"].copy() if "horizon" in both.columns else both.copy()
    return both, {"immediate_rows": int(len(imm)), **meta}


def compare_adopted_rules() -> tuple[Optional[pd.DataFrame], dict[str, Any]]:
    s1 = _read_csv(SEED1_TABLES / "adopted_rules.csv")
    s2 = _read_csv(SEED2_TABLES / "adopted_rules.csv")
    meta: dict[str, Any] = {}
    if s1 is None and s2 is None:
        return None, {"note": "adopted_rules.csv missing for both seeds"}
    frames = []
    if s1 is not None:
        a = s1.copy()
        a["seed"] = "seed1"
        frames.append(a)
        meta["seed1_n_rules"] = int(len(a))
        meta["seed1_rules"] = [
            {"round": int(r.round_number), "rule": str(r.rule), "new_value": r.new_value}
            for r in a.itertuples()
        ]
    else:
        meta["seed1_missing"] = True
    if s2 is not None:
        b = s2.copy()
        b["seed"] = "seed2"
        frames.append(b)
        meta["seed2_n_rules"] = int(len(b))
        meta["seed2_rules"] = [
            {"round": int(r.round_number), "rule": str(r.rule), "new_value": r.new_value}
            for r in b.itertuples()
        ]
    else:
        meta["seed2_missing"] = True

    both = pd.concat(frames, ignore_index=True)
    if s1 is not None and s2 is not None:
        keys1 = set(zip(s1["round_number"].astype(int), s1["rule"].astype(str)))
        keys2 = set(zip(s2["round_number"].astype(int), s2["rule"].astype(str)))
        meta["shared_round_rule_pairs"] = sorted(
            [{"round": r, "rule": rule} for r, rule in (keys1 & keys2)],
            key=lambda x: (x["round"], x["rule"]),
        )
        meta["only_seed1"] = sorted(
            [{"round": r, "rule": rule} for r, rule in (keys1 - keys2)],
            key=lambda x: (x["round"], x["rule"]),
        )
        meta["only_seed2"] = sorted(
            [{"round": r, "rule": rule} for r, rule in (keys2 - keys1)],
            key=lambda x: (x["round"], x["rule"]),
        )
    return both, meta


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def plot_mean_prop_trajectories(round_sum: pd.DataFrame) -> None:
    """One figure with three panels: ALL, SI, SFI — seed1 vs seed2."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    for ax, inst in zip(axes, ("ALL", "SI", "SFI")):
        for seed, color in COLORS.items():
            sub = round_sum[
                (round_sum["seed"] == seed) & (round_sum["institution_choice"] == inst)
            ].sort_values("round_number")
            if sub.empty:
                continue
            ax.plot(
                sub["round_number"],
                sub["mean_prop"],
                label=SEED_LABELS[seed],
                color=color,
                lw=2,
            )
        for s in SHOCK_ROUNDS:
            ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.7)
        ax.set_title(inst)
        ax.set_xlabel("Round")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Mean prop_of_wealth")
    axes[0].legend(fontsize=8)
    fig.suptitle("Mean proportional contribution: seed1 vs seed2", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "mean_prop_trajectories_by_institution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # overlay all three institutions per seed (two panels)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, seed in zip(axes, ("seed1", "seed2")):
        for inst, color in INST_COLORS.items():
            sub = round_sum[
                (round_sum["seed"] == seed) & (round_sum["institution_choice"] == inst)
            ].sort_values("round_number")
            ax.plot(sub["round_number"], sub["mean_prop"], label=inst, color=color, lw=2)
        for s in SHOCK_ROUNDS:
            ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.7)
        ax.set_title(SEED_LABELS[seed])
        ax.set_xlabel("Round")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Mean prop_of_wealth")
    fig.suptitle("Mean prop trajectories within each seed", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "mean_prop_trajectories_within_seed.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_wealth_gap(gap: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, seed in zip(axes, ("seed1", "seed2")):
        sub = gap[gap["seed"] == seed].sort_values("round_number")
        ax.plot(
            sub["round_number"],
            sub["mean_wealth_developed"],
            label="developed",
            color="#2C5F8A",
            lw=2,
        )
        ax.plot(
            sub["round_number"],
            sub["mean_wealth_developing"],
            label="developing",
            color="#C47B2C",
            lw=2,
        )
        ax.set_yscale("log")
        ax.set_title(SEED_LABELS[seed])
        ax.set_xlabel("Round")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25, which="both")
        for s in SHOCK_ROUNDS:
            ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.7)
    axes[0].set_ylabel("Mean wealth (log)")
    fig.suptitle("Wealth by group (developed vs developing)", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "wealth_by_group.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seed, color in COLORS.items():
        sub = gap[gap["seed"] == seed].sort_values("round_number")
        ax.plot(
            sub["round_number"],
            sub["wealth_gap_dev_minus_developing"],
            label=SEED_LABELS[seed],
            color=color,
            lw=2,
        )
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.7)
    ax.set_xlabel("Round")
    ax.set_ylabel("Mean wealth gap (developed - developing)")
    ax.set_title("Wealth gap: developed - developing")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "wealth_gap_developed_minus_developing.png", dpi=150)
    plt.close(fig)


def plot_ldf_pool(fund: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seed, color in COLORS.items():
        sub = fund[fund["seed"] == seed].sort_values("round_number")
        ax.plot(
            sub["round_number"],
            sub["ldf_pool_end"],
            label=SEED_LABELS[seed],
            color=color,
            lw=2,
        )
    for s in SHOCK_ROUNDS:
        ax.axvline(s, color="#AA2222", ls="--", lw=1, alpha=0.7)
    ax.set_xlabel("Round")
    ax.set_ylabel("LDF pool end")
    ax.set_title("LDF pool end by round")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "ldf_pool_end_by_round.png", dpi=150)
    plt.close(fig)


def plot_agent_mean_scatter(agent_join: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    for group, marker in (("developed", "o"), ("developing", "s")):
        # colour by seed2 group (or same-group marker if matched)
        sub = agent_join[agent_join["agent_group_seed2"] == group]
        ax.scatter(
            sub["mean_prop_seed1"],
            sub["mean_prop_seed2"],
            label=f"seed2 group={group}",
            marker=marker,
            alpha=0.8,
            s=50,
        )
    lims = [
        min(agent_join["mean_prop_seed1"].min(), agent_join["mean_prop_seed2"].min()),
        max(agent_join["mean_prop_seed1"].max(), agent_join["mean_prop_seed2"].max()),
    ]
    pad = 0.05 * (lims[1] - lims[0] + 1e-9)
    lims = [lims[0] - pad, lims[1] + pad]
    ax.plot(lims, lims, "k--", lw=1, alpha=0.5)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("Mean prop_of_wealth (seed1)")
    ax.set_ylabel("Mean prop_of_wealth (seed2)")
    ax.set_title("Per-agent mean prop across seeds (matched by agent_id)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "agent_mean_prop_scatter.png", dpi=150)
    plt.close(fig)


def plot_reputation_imm(rep: pd.DataFrame) -> None:
    imm = rep[rep["horizon"] == "imm"].copy() if "horizon" in rep.columns else rep.copy()
    if imm.empty:
        return
    # aggregate across institution for a compact bar chart, or facet
    pivot = (
        imm.groupby(["seed", "event_family"])["mean_delta_prop"]
        .mean()
        .reset_index()
    )
    families = sorted(pivot["event_family"].unique())
    x = np.arange(len(families))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (seed, color) in enumerate(COLORS.items()):
        vals = [
            float(
                pivot.loc[
                    (pivot["seed"] == seed) & (pivot["event_family"] == fam),
                    "mean_delta_prop",
                ].mean()
            )
            if not pivot.loc[
                (pivot["seed"] == seed) & (pivot["event_family"] == fam)
            ].empty
            else np.nan
            for fam in families
        ]
        ax.bar(x + (i - 0.5) * width, vals, width, label=SEED_LABELS[seed], color=color)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(families, rotation=20, ha="right")
    ax.set_ylabel("Mean immediate delta prop")
    ax.set_title("Reputation event mean immediate delta prop (avg over institutions)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "reputation_imm_delta_prop_by_family.png", dpi=150)
    plt.close(fig)


def plot_shock_deltas(deltas: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, shock in zip(axes, SHOCK_ROUNDS):
        data, labels, colors = [], [], []
        for seed, color in COLORS.items():
            d = deltas[
                (deltas["seed"] == seed) & (deltas["shock_round"] == shock)
            ]["delta_post_minus_pre"].dropna()
            data.append(d.to_numpy())
            labels.append(SEED_LABELS[seed])
            colors.append(color)
        bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.55)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.45)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"Shock R{shock}: post-pre prop")
        ax.set_ylabel("delta prop_of_wealth" if shock == SHOCK_ROUNDS[0] else "")
        ax.grid(True, axis="y", alpha=0.25)
    fig.suptitle("Within-agent shock event-study deltas", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "shock_delta_boxplot_cross_seed.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ensure_dirs()
    notes: list[str] = []

    c1 = load_contributions(SEED1_TABLES, "seed1")
    c2 = load_contributions(SEED2_TABLES, "seed2")
    contrib = pd.concat([c1, c2], ignore_index=True)

    # agent_id group alignment note
    meta1 = c1.groupby("agent_id").agg(
        agent_group=("agent_group", "first"), institution_choice=("institution_choice", "first")
    )
    meta2 = c2.groupby("agent_id").agg(
        agent_group=("agent_group", "first"), institution_choice=("institution_choice", "first")
    )
    aligned = meta1.join(meta2, lsuffix="_seed1", rsuffix="_seed2", how="inner")
    n_same_group = int((aligned["agent_group_seed1"] == aligned["agent_group_seed2"]).sum())
    notes.append(
        f"agent_id group match across seeds: {n_same_group}/{len(aligned)} "
        "(seeds reshuffle developed/developing assignment; correlations by agent_id "
        "are not persona-matched)."
    )

    round_sum = round_mean_prop(contrib)
    round_sum.to_csv(OUT_TABLES / "cross_seed_round_mean_prop.csv", index=False)

    gap = wealth_gap_series(contrib)
    gap.to_csv(OUT_TABLES / "cross_seed_wealth_gap.csv", index=False)

    fund_parts = []
    for key, tables in (("seed1", SEED1_TABLES), ("seed2", SEED2_TABLES)):
        f = load_fund_pool(tables, key)
        if f is None:
            notes.append(f"fund_state.csv missing for {key}")
        else:
            fund_parts.append(f)
    fund = pd.concat(fund_parts, ignore_index=True) if fund_parts else None
    if fund is not None:
        fund.to_csv(OUT_TABLES / "cross_seed_ldf_pool.csv", index=False)

    # Round-level mean prop correlation / summary
    round_corr_rows = []
    round_summary_stats = []
    for inst in ("ALL", "SI", "SFI"):
        s1 = round_sum[
            (round_sum["seed"] == "seed1") & (round_sum["institution_choice"] == inst)
        ].set_index("round_number")["mean_prop"]
        s2 = round_sum[
            (round_sum["seed"] == "seed2") & (round_sum["institution_choice"] == inst)
        ].set_index("round_number")["mean_prop"]
        joined = pd.concat([s1.rename("seed1"), s2.rename("seed2")], axis=1).dropna()
        pear = _corr_with_pvalue(joined["seed1"].to_numpy(), joined["seed2"].to_numpy(), "pearson")
        spear = _corr_with_pvalue(joined["seed1"].to_numpy(), joined["seed2"].to_numpy(), "spearman")
        round_corr_rows.append(
            {
                "level": "round_mean_prop",
                "institution_choice": inst,
                "n_rounds": pear["n"],
                "pearson_r": pear["r"],
                "pearson_p": pear["p"],
                "spearman_r": spear["r"],
                "spearman_p": spear["p"],
                "mean_seed1": float(joined["seed1"].mean()) if len(joined) else np.nan,
                "mean_seed2": float(joined["seed2"].mean()) if len(joined) else np.nan,
                "std_seed1": float(joined["seed1"].std(ddof=1)) if len(joined) > 1 else np.nan,
                "std_seed2": float(joined["seed2"].std(ddof=1)) if len(joined) > 1 else np.nan,
                "rmse": float(np.sqrt(np.mean((joined["seed1"] - joined["seed2"]) ** 2)))
                if len(joined)
                else np.nan,
            }
        )
        for seed_col, seed_key in (("seed1", "seed1"), ("seed2", "seed2")):
            series = joined[seed_col]
            round_summary_stats.append(
                {
                    "seed": seed_key,
                    "institution_choice": inst,
                    "n_rounds": int(len(series)),
                    "mean_of_round_means": float(series.mean()),
                    "median_of_round_means": float(series.median()),
                    "std_of_round_means": float(series.std(ddof=1)) if len(series) > 1 else np.nan,
                    "min_round_mean": float(series.min()),
                    "max_round_mean": float(series.max()),
                }
            )
    round_corr_df = pd.DataFrame(round_corr_rows)
    round_corr_df.to_csv(OUT_TABLES / "cross_seed_round_prop_correlation.csv", index=False)
    pd.DataFrame(round_summary_stats).to_csv(
        OUT_TABLES / "cross_seed_round_prop_summary_stats.csv", index=False
    )

    # Per-agent mean prop correlation
    am = agent_mean_prop(contrib)
    am1 = am[am["seed"] == "seed1"].set_index("agent_id")
    am2 = am[am["seed"] == "seed2"].set_index("agent_id")
    agent_join = am1[["mean_prop", "agent_group", "institution_choice"]].join(
        am2[["mean_prop", "agent_group", "institution_choice"]],
        lsuffix="_seed1",
        rsuffix="_seed2",
        how="inner",
    )
    agent_join = agent_join.reset_index()
    agent_join["same_group"] = agent_join["agent_group_seed1"] == agent_join["agent_group_seed2"]
    agent_join.to_csv(OUT_TABLES / "cross_seed_agent_mean_prop.csv", index=False)

    pear_a = _corr_with_pvalue(
        agent_join["mean_prop_seed1"].to_numpy(),
        agent_join["mean_prop_seed2"].to_numpy(),
        "pearson",
    )
    spear_a = _corr_with_pvalue(
        agent_join["mean_prop_seed1"].to_numpy(),
        agent_join["mean_prop_seed2"].to_numpy(),
        "spearman",
    )
    same = agent_join[agent_join["same_group"]]
    pear_s = _corr_with_pvalue(
        same["mean_prop_seed1"].to_numpy(), same["mean_prop_seed2"].to_numpy(), "pearson"
    )
    spear_s = _corr_with_pvalue(
        same["mean_prop_seed1"].to_numpy(), same["mean_prop_seed2"].to_numpy(), "spearman"
    )
    agent_corr_df = pd.DataFrame(
        [
            {
                "match": "agent_id",
                "subset": "all",
                "n": pear_a["n"],
                "pearson_r": pear_a["r"],
                "pearson_p": pear_a["p"],
                "spearman_r": spear_a["r"],
                "spearman_p": spear_a["p"],
            },
            {
                "match": "agent_id",
                "subset": "same_group_only",
                "n": pear_s["n"],
                "pearson_r": pear_s["r"],
                "pearson_p": pear_s["p"],
                "spearman_r": spear_s["r"],
                "spearman_p": spear_s["p"],
            },
        ]
    )
    agent_corr_df.to_csv(OUT_TABLES / "cross_seed_agent_prop_correlation.csv", index=False)

    # Mann-Whitney SI vs SFI within each seed
    mw_rows = [mann_whitney_si_sfi(contrib, "seed1"), mann_whitney_si_sfi(contrib, "seed2")]
    pd.DataFrame(mw_rows).to_csv(OUT_TABLES / "cross_seed_mannwhitney_si_sfi.csv", index=False)

    # Shock event study
    deltas = shock_within_agent_deltas(contrib)
    deltas.to_csv(OUT_TABLES / "cross_seed_shock_agent_deltas.csv", index=False)
    wilcox_rows = wilcoxon_shock_summary(deltas)
    pd.DataFrame(wilcox_rows).to_csv(OUT_TABLES / "cross_seed_shock_wilcoxon.csv", index=False)

    # Reputation
    rep, rep_meta = compare_reputation_summaries()
    if rep is not None:
        rep.to_csv(OUT_TABLES / "cross_seed_reputation_event_summary.csv", index=False)
        imm = rep[rep["horizon"] == "imm"] if "horizon" in rep.columns else rep
        imm_wide = imm.pivot_table(
            index=["event_family", "institution_choice"],
            columns="seed",
            values="mean_delta_prop",
            aggfunc="mean",
        ).reset_index()
        imm_wide.to_csv(OUT_TABLES / "cross_seed_reputation_imm_delta_prop.csv", index=False)

    # Adopted rules
    rules, rules_meta = compare_adopted_rules()
    if rules is not None:
        rules.to_csv(OUT_TABLES / "cross_seed_adopted_rules.csv", index=False)

    # Trend / stationarity on ALL round-mean prop
    trend_block: dict[str, Any] = {}
    for seed in ("seed1", "seed2"):
        series = (
            round_sum[
                (round_sum["seed"] == seed) & (round_sum["institution_choice"] == "ALL")
            ]
            .sort_values("round_number")["mean_prop"]
            .to_numpy(dtype=float)
        )
        trend_block[seed] = {
            "mann_kendall": mann_kendall_simple(series),
            "adf": adf_test(series),
        }

    # Plots
    plot_mean_prop_trajectories(round_sum)
    plot_wealth_gap(gap)
    if fund is not None:
        plot_ldf_pool(fund)
    plot_agent_mean_scatter(agent_join)
    plot_shock_deltas(deltas)
    if rep is not None:
        plot_reputation_imm(rep)

    # JSON summary
    json_seed1 = _find_json(SEED1_JSON_CANDIDATES)
    json_seed2 = (
        str(SEED2_JSON.relative_to(REPO_ROOT)).replace("\\", "/")
        if SEED2_JSON.exists()
        else None
    )

    # Key scalars for print + json
    all_corr = round_corr_df[round_corr_df["institution_choice"] == "ALL"].iloc[0]
    gap_end = {
        seed: float(
            gap[gap["seed"] == seed].sort_values("round_number").iloc[-1][
                "wealth_gap_dev_minus_developing"
            ]
        )
        for seed in ("seed1", "seed2")
    }
    pool_end = {}
    if fund is not None:
        for seed in ("seed1", "seed2"):
            sub = fund[fund["seed"] == seed].sort_values("round_number")
            if not sub.empty:
                pool_end[seed] = float(sub.iloc[-1]["ldf_pool_end"])

    summary: dict[str, Any] = {
        "metric": "prop_of_wealth",
        "seeds": {
            "seed1": {
                "tables": str(SEED1_TABLES.relative_to(REPO_ROOT)).replace("\\", "/"),
                "run_label": "20260731",
                "json": json_seed1,
            },
            "seed2": {
                "tables": str(SEED2_TABLES.relative_to(REPO_ROOT)).replace("\\", "/"),
                "run_label": "20260804",
                "json": json_seed2,
            },
        },
        "shock_rounds": list(SHOCK_ROUNDS),
        "notes": notes,
        "agent_id_same_group_count": n_same_group,
        "agent_id_n": int(len(aligned)),
        "round_mean_prop_correlation_ALL": {
            "pearson_r": float(all_corr["pearson_r"])
            if pd.notna(all_corr["pearson_r"])
            else None,
            "pearson_p": float(all_corr["pearson_p"])
            if pd.notna(all_corr["pearson_p"])
            else None,
            "spearman_r": float(all_corr["spearman_r"])
            if pd.notna(all_corr["spearman_r"])
            else None,
            "spearman_p": float(all_corr["spearman_p"])
            if pd.notna(all_corr["spearman_p"])
            else None,
            "mean_seed1": float(all_corr["mean_seed1"]),
            "mean_seed2": float(all_corr["mean_seed2"]),
            "rmse": float(all_corr["rmse"]),
        },
        "round_mean_prop_correlation_by_institution": round_corr_rows,
        "agent_mean_prop_correlation": agent_corr_df.to_dict(orient="records"),
        "mannwhitney_si_vs_sfi": mw_rows,
        "shock_wilcoxon": wilcox_rows,
        "wealth_gap_final_round": gap_end,
        "ldf_pool_end_final_round": pool_end,
        "reputation": rep_meta,
        "adopted_rules": rules_meta,
        "cooperation_trend": trend_block,
        "outputs": {
            "plots_dir": str(OUT_PLOTS.relative_to(REPO_ROOT)).replace("\\", "/"),
            "tables_glob": "docs/raw documentation/20260804/tables/cross_seed_*.csv",
            "summary_json": "docs/raw documentation/20260804/tables/cross_seed_summary.json",
        },
        "scipy_available": scipy_stats is not None,
        "statsmodels_adf_available": _adfuller is not None,
    }

    # scrub NaN for JSON
    def _json_safe(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_json_safe(v) for v in obj]
        if isinstance(obj, (np.floating, float)):
            if np.isnan(obj):
                return None
            return float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    summary_path = OUT_TABLES / "cross_seed_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(summary), f, indent=2)

    # Short text summary
    print("=" * 64)
    print("Cross-seed comparison: seed1 (20260731) vs seed2 (20260804)")
    print("=" * 64)
    print(
        f"Round-mean prop (ALL): seed1={all_corr['mean_seed1']:.4f}  "
        f"seed2={all_corr['mean_seed2']:.4f}  "
        f"Pearson r={all_corr['pearson_r']:.3f} (p={all_corr['pearson_p']:.3g})  "
        f"Spearman r={all_corr['spearman_r']:.3f} (p={all_corr['spearman_p']:.3g})"
    )
    print(
        f"Agent-mean prop (agent_id): Pearson r={pear_a['r']:.3f} "
        f"(p={pear_a['p']:.3g}), Spearman r={spear_a['r']:.3f} "
        f"(p={spear_a['p']:.3g}); same-group n={pear_s['n']}"
    )
    for row in mw_rows:
        p_ar = row.get("mannwhitney_p_agent_round")
        p_am = row.get("mannwhitney_p_agent_means")
        print(
            f"Mann-Whitney SI vs SFI [{row['seed']}]: "
            f"mean SI={row['mean_SI']:.4f} SFI={row['mean_SFI']:.4f}  "
            f"p_agent-round={p_ar if p_ar is not None else 'n/a'}  "
            f"p_agent-means={p_am if p_am is not None else 'n/a'}"
        )
    for row in wilcox_rows:
        print(
            f"Shock R{row['shock_round']} [{row['seed']}]: "
            f"mean delta(post-pre)={row['mean_delta_post_minus_pre']:.4f}  "
            f"Wilcoxon p={row.get('wilcoxon_p', row.get('wilcoxon_note', 'n/a'))}"
        )
    print(
        f"Final wealth gap (dev-developing): "
        f"seed1={gap_end.get('seed1', float('nan')):.3g}  "
        f"seed2={gap_end.get('seed2', float('nan')):.3g}"
    )
    if pool_end:
        print(
            f"Final LDF pool end: "
            f"seed1={pool_end.get('seed1', float('nan')):.3g}  "
            f"seed2={pool_end.get('seed2', float('nan')):.3g}"
        )
    for seed, blk in trend_block.items():
        mk = blk["mann_kendall"]
        if mk.get("skipped"):
            print(f"Mann-Kendall [{seed}]: skipped ({mk.get('note')})")
        else:
            print(
                f"Mann-Kendall [{seed}]: tau={mk['kendall_tau']:.3f} "
                f"p={mk['p_value']:.3g} slope={mk['sens_slope']:.4g} "
                f"→ {mk['trend']}"
            )
        adf = blk["adf"]
        if adf.get("skipped"):
            print(f"ADF [{seed}]: skipped ({adf.get('note')})")
        else:
            print(
                f"ADF [{seed}]: stat={adf['adf_stat']:.3f} p={adf['p_value']:.3g} "
                f"reject_unit_root_5pct={adf['reject_unit_root_5pct']}"
            )
    if rules_meta:
        print(
            f"Adopted rules: seed1 n={rules_meta.get('seed1_n_rules', 'missing')}  "
            f"seed2 n={rules_meta.get('seed2_n_rules', 'missing')}  "
            f"shared round-rule pairs={len(rules_meta.get('shared_round_rule_pairs', []))}"
        )
    print(f"Wrote summary → {summary_path.relative_to(REPO_ROOT)}")
    print(f"Plots → {OUT_PLOTS.relative_to(REPO_ROOT)}")
    print("=" * 64)


if __name__ == "__main__":
    main()

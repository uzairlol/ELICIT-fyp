#!/usr/bin/env python3
"""Bootstrap CIs, Cohen's d, and permutation tests for reputation event study."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
TABLES = REPO / "docs" / "raw documentation" / "20260731" / "tables"
OUT = Path(__file__).resolve().parents[1] / "tables"
SEED = 20260731
N_BOOT = 5000
N_PERM = 5000


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    pooled = np.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
    if pooled == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled)


def cohens_d_vs_zero(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return float("nan")
    s = x.std(ddof=1)
    if s == 0:
        return float("nan")
    return float(x.mean() / s)


def bootstrap_mean_ci(x: np.ndarray, rng: np.random.Generator, n_boot: int = N_BOOT):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    boots = x[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return float(x.mean()), float(lo), float(hi)


def event_study_stats(events: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    imm = events[events["horizon"] == "imm"].copy()
    rows = []
    for fam in ("bad_rep", "rep_drop", "gossip_target"):
        sub = imm[imm["event_types"].str.contains(fam, regex=False)]
        for inst in ("SI", "SFI", "ALL"):
            gg = (
                sub["delta_prop"].to_numpy()
                if inst == "ALL"
                else sub.loc[sub["institution_choice"] == inst, "delta_prop"].to_numpy()
            )
            mean, lo, hi = bootstrap_mean_ci(gg, rng)
            rows.append(
                {
                    "event_family": fam,
                    "institution": inst,
                    "n": int(np.sum(~np.isnan(gg))),
                    "mean_delta": mean,
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "frac_positive": float(np.nanmean(gg > 0)) if len(gg) else float("nan"),
                    "cohens_d_vs_zero": cohens_d_vs_zero(gg),
                }
            )
    return pd.DataFrame(rows)


def build_agent_round_deltas(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.sort_values(["agent_id", "round_number"]).copy()
    p["prop_next"] = p.groupby("agent_id")["prop"].shift(-1)
    p["delta"] = p["prop_next"] - p["prop"]
    p = p[p["prop_next"].notna()].copy()
    if "gossip_target" not in p.columns:
        p["gossip_target"] = p["in_gossip_bulletin"].astype(int)
    return p


def round_dids(day: pd.DataFrame, col: str) -> np.ndarray:
    dids = []
    for _, g in day.groupby("round_number"):
        aff = g.loc[g[col] == 1, "delta"].to_numpy()
        ctrl = g.loc[g[col] == 0, "delta"].to_numpy()
        if len(aff) == 0 or len(ctrl) == 0:
            continue
        dids.append(aff.mean() - ctrl.mean())
    return np.asarray(dids, dtype=float)


def permute_round_did(deltas: np.ndarray, flags: np.ndarray, rng: np.random.Generator) -> float:
    """Within one round: shuffle flags, return DiD."""
    n_aff = int(flags.sum())
    if n_aff == 0 or n_aff == len(flags):
        return float("nan")
    perm = rng.permutation(len(flags))
    f = flags[perm]  # equivalent to shuffling assignment onto fixed deltas? better shuffle flags
    # Correct: shuffle flags in place relative to fixed deltas
    f = flags.copy()
    rng.shuffle(f)
    return float(deltas[f == 1].mean() - deltas[f == 0].mean())


def did_stats(panel: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    day = build_agent_round_deltas(panel)
    rows = []
    for fam, col in [
        ("bad_rep", "bad_rep"),
        ("gossip_target", "gossip_target"),
        ("rep_drop", "rep_drop"),
    ]:
        round_stats = round_dids(day, col)
        mean_did = float(round_stats.mean())
        # Bootstrap over rounds (vectorized)
        boot_idx = rng.integers(0, len(round_stats), size=(N_BOOT, len(round_stats)))
        boots = round_stats[boot_idx].mean(axis=1)
        lo, hi = np.quantile(boots, [0.025, 0.975])

        # Precompute per-round arrays for fast permutation
        round_arrays = []
        for _, g in day.groupby("round_number"):
            dlt = g["delta"].to_numpy(dtype=float)
            flg = g[col].to_numpy(dtype=int)
            if flg.sum() == 0 or flg.sum() == len(flg):
                continue
            round_arrays.append((dlt, flg))

        null = np.empty(N_PERM)
        for i in range(N_PERM):
            dids = [permute_round_did(dlt, flg, rng) for dlt, flg in round_arrays]
            null[i] = np.nanmean(dids)

        p_perm = float(np.mean(np.abs(null) >= abs(mean_did)))

        aff_deltas = day.loc[day[col] == 1, "delta"].to_numpy()
        ctrl_deltas = day.loc[day[col] == 0, "delta"].to_numpy()
        d_effect = cohens_d(aff_deltas, ctrl_deltas)
        aff_mean = float(np.nanmean(aff_deltas))
        ctrl_mean = float(np.nanmean(ctrl_deltas))

        rows.append(
            {
                "event_family": fam,
                "affected_mean_delta": aff_mean,
                "control_mean_delta": ctrl_mean,
                "did_round_mean": mean_did,
                "did_ci_lo": float(lo),
                "did_ci_hi": float(hi),
                "did_pooled": aff_mean - ctrl_mean,
                "cohens_d_aff_vs_ctrl": d_effect,
                "perm_p_two_sided": p_perm,
                "n_rounds": int(len(round_stats)),
                "n_affected_agent_rounds": int(len(aff_deltas)),
                "n_control_agent_rounds": int(len(ctrl_deltas)),
            }
        )
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    events = pd.read_csv(TABLES / "reputation_gossip_events.csv")
    panel = pd.read_csv(TABLES / "reputation_gossip_panel.csv")

    es = event_study_stats(events, rng)
    es.to_csv(OUT / "event_study_bootstrap.csv", index=False)

    did = did_stats(panel, rng)
    did.to_csv(OUT / "did_bootstrap_permutation.csv", index=False)

    summary = {
        "seed": SEED,
        "n_boot": N_BOOT,
        "n_perm": N_PERM,
        "event_study": es.to_dict(orient="records"),
        "did": did.to_dict(orient="records"),
    }
    (OUT / "inference_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(es.to_string(index=False))
    print("---")
    print(did.to_string(index=False))


if __name__ == "__main__":
    main()

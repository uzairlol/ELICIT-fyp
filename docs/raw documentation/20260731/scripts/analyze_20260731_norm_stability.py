#!/usr/bin/env python3
"""Prompt 7 support metrics: norm/stability numbers for 20260731."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
TABLES = REPO / "docs" / "raw documentation" / "20260731" / "tables"


def main() -> int:
    c = pd.read_csv(TABLES / "contributions.csv")
    c["prop"] = c["prop_of_wealth"].astype(float)
    rs = (
        c.groupby("round_number")
        .agg(
            mean_prop=("prop", "mean"),
            median_prop=("prop", "median"),
            std_prop=("prop", "std"),
            iqr_prop=("prop", lambda s: s.quantile(0.75) - s.quantile(0.25)),
            zero_share=("contribution", lambda s: (s <= 0).mean()),
        )
        .reset_index()
    )
    # early vs late dispersion
    early = rs[rs["round_number"] <= 10]
    late = rs[rs["round_number"] >= 21]
    # agent polarisation: share near-zero specialists
    am = c.groupby("agent_id")["prop"].mean()
    # thresholds disclosed a priori relative to analysis: 0.05 near-zero, 0.25+ high
    near_zero_agents = int((am < 0.05).sum())
    high_agents = int((am >= 0.25).sum())

    # contribution autocorrelation mean across agents
    acs = []
    for _, g in c.sort_values("round_number").groupby("agent_id"):
        p = g["prop"].to_numpy()
        if len(p) > 2 and np.std(p[:-1]) > 1e-12 and np.std(p[1:]) > 1e-12:
            acs.append(float(np.corrcoef(p[:-1], p[1:])[0, 1]))
    # recovery: rounds to return to pre-shock mean after R5/R10
    recoveries = {}
    for shock in (5, 10):
        pre = rs.loc[rs["round_number"].isin([shock - 2, shock - 1]), "mean_prop"].mean()
        recover = None
        for r in range(shock + 1, 31):
            if rs.loc[rs["round_number"] == r, "mean_prop"].iloc[0] >= pre:
                recover = r - shock
                break
        recoveries[str(shock)] = {"pre_mean": float(pre), "rounds_to_regain_pre_mean": recover}

    out = {
        "group_mean_prop_autocorr_lag1": float(rs["mean_prop"].autocorr(1)),
        "agent_mean_prop_autocorr_lag1": float(np.nanmean(acs)),
        "early_mean_std_prop": float(early["std_prop"].mean()),
        "late_mean_std_prop": float(late["std_prop"].mean()),
        "early_mean_iqr_prop": float(early["iqr_prop"].mean()),
        "late_mean_iqr_prop": float(late["iqr_prop"].mean()),
        "early_mean_zero_share": float(early["zero_share"].mean()),
        "late_mean_zero_share": float(late["zero_share"].mean()),
        "overall_mean_prop": float(c["prop"].mean()),
        "overall_median_prop": float(c["prop"].median()),
        "near_zero_agents_mean_prop_lt_0.05": near_zero_agents,
        "high_agents_mean_prop_ge_0.25": high_agents,
        "n_agents": int(am.shape[0]),
        "threshold_rounds": {
            "0.1": int((rs["mean_prop"] >= 0.1).sum()),
            "0.2": int((rs["mean_prop"] >= 0.2).sum()),
            "0.3": int((rs["mean_prop"] >= 0.3).sum()),
        },
        "shock_recoveries": recoveries,
        "thresholds_disclosed": {
            "near_zero_agent": 0.05,
            "high_agent": 0.25,
            "group_mean_levels": [0.1, 0.2, 0.3],
        },
    }
    rs.to_csv(TABLES / "norm_stability_round_series.csv", index=False)
    with open(TABLES / "prompt7_numeric_summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Zero-contribution episode analysis for the locked 20260804 run.
Also supports R2 spike, warm-glow flags, and burst timing correlates.

Run from repo root:
  python "docs/raw documentation/20260804/scripts/analyze_20260804_zero_contributions.py"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT = REPO_ROOT / "docs" / "raw documentation" / "20260804"
TABLES = OUT / "tables"
RUN = "20260804_024555"
SOURCE = (
    "results/"
    "simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json"
)
JSON_PATH = REPO_ROOT / SOURCE
COOP_PAT = re.compile(
    r"cooperat|collective|fair|reciproc|together|common.?good|contribute.?back|"
    r"maintain.?cooper|encourage.?cooper|group.?cooper",
    re.I,
)
MCPR_PAT = re.compile(r"mcpr|marginal.?return|multiplier|payoff.?maxim", re.I)
CONSERVE_PAT = re.compile(r"conserv|budget|wealth|resourc|liquidity|cannot|can't|afford", re.I)
FREE_PAT = re.compile(r"free.?rid|zero.?contrib|contribute.?nothing|not to contribute", re.I)


def load_panel() -> pd.DataFrame:
    c = pd.read_csv(TABLES / "contributions.csv")
    st = pd.read_csv(TABLES / "round_agent_state.csv")[
        ["round_number", "agent_id", "wealth", "reputation", "vulnerability", "shock_occurred"]
    ]
    red = pd.read_csv(TABLES / "redistribution.csv")[
        ["round_number", "agent_id", "ldf_payout_round", "ldf_contribution_round", "subsidy"]
    ]
    pay = pd.read_csv(TABLES / "payoffs.csv")
    # optional punishment columns
    for col in ("received_punishments_sum", "assigned_punishments_sum"):
        if col not in pay.columns:
            # try alternate names
            pass
    df = c.merge(st, on=["round_number", "agent_id"], how="left", suffixes=("", "_st"))
    df = df.merge(red, on=["round_number", "agent_id"], how="left")
    if "wealth_end_of_round" in df.columns and "wealth" in df.columns:
        df["wealth_eor"] = df["wealth_end_of_round"]
    else:
        df["wealth_eor"] = df["wealth"]
    df["is_zero"] = df["contribution"].astype(float) <= 0
    # Liquidity-forced: stage1 cap from END wealth is 0 (approx; true decision uses start wealth)
    # Better: wealth before contribution unavailable; use stage1_cap_from_end_wealth==0 OR
    # contribution==0 and wealth_eor < 1
    df["stage1_cap"] = df["stage1_cap_from_end_wealth"].astype(float)
    df["liquidity_forced_approx"] = df["is_zero"] & (df["stage1_cap"] <= 0)
    df["voluntary_zero_approx"] = df["is_zero"] & (df["stage1_cap"] > 0)
    return df


def load_reasoning() -> pd.DataFrame:
    rb = pd.read_csv(TABLES / "reasoning_blocks.csv")
    return rb[rb["kind"] == "contribution"].copy()


def attach_reasoning(zeros: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    r = rb[["round_number", "agent_id", "evidence_id", "text"]].rename(
        columns={"text": "contribution_reasoning", "evidence_id": "evidence_id"}
    )
    return zeros.merge(r, on=["round_number", "agent_id"], how="left")


def theme_flags(text: str) -> dict:
    t = text or ""
    return {
        "mentions_coop": int(bool(COOP_PAT.search(t))),
        "mentions_mcpr": int(bool(MCPR_PAT.search(t))),
        "mentions_conserve": int(bool(CONSERVE_PAT.search(t))),
        "mentions_free_ride": int(bool(FREE_PAT.search(t))),
    }


def inventory(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for inst, g in df.groupby("institution_choice"):
        z = g[g["is_zero"]]
        rows.append(
            {
                "institution_choice": inst,
                "n_agent_rounds": len(g),
                "n_zeros": len(z),
                "zero_share": len(z) / len(g),
                "n_liquidity_forced_approx": int(z["liquidity_forced_approx"].sum()),
                "n_voluntary_zero_approx": int(z["voluntary_zero_approx"].sum()),
                "n_agents_ever_zero": z["agent_id"].nunique(),
            }
        )
    zall = df[df["is_zero"]]
    rows.append(
        {
            "institution_choice": "ALL",
            "n_agent_rounds": len(df),
            "n_zeros": len(zall),
            "zero_share": len(zall) / len(df),
            "n_liquidity_forced_approx": int(zall["liquidity_forced_approx"].sum()),
            "n_voluntary_zero_approx": int(zall["voluntary_zero_approx"].sum()),
            "n_agents_ever_zero": zall["agent_id"].nunique(),
        }
    )
    return pd.DataFrame(rows)


def zero_by_round(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (rn, inst), g in df.groupby(["round_number", "institution_choice"]):
        rows.append(
            {
                "round_number": rn,
                "institution_choice": inst,
                "n": len(g),
                "zero_share": g["is_zero"].mean(),
                "n_zeros": int(g["is_zero"].sum()),
                "mean_prop": g["prop_of_wealth"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(["round_number", "institution_choice"])


def episode_table(df: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    z = df[df["is_zero"]].copy()
    z = attach_reasoning(z, rb)
    themes = z["contribution_reasoning"].fillna("").map(theme_flags).apply(pd.Series)
    z = pd.concat([z.reset_index(drop=True), themes], axis=1)
    # prior round context
    df_sorted = df.sort_values(["agent_id", "round_number"])
    prev = df_sorted[
        ["agent_id", "round_number", "contribution", "prop_of_wealth", "reputation", "ldf_payout_round"]
    ].copy()
    prev["round_number"] = prev["round_number"] + 1
    prev = prev.rename(
        columns={
            "contribution": "prev_contribution",
            "prop_of_wealth": "prev_prop",
            "reputation": "prev_reputation",
            "ldf_payout_round": "prev_ldf_payout",
        }
    )
    z = z.merge(prev, on=["agent_id", "round_number"], how="left")
    cols = [
        "round_number",
        "agent_id",
        "agent_group",
        "institution_choice",
        "contribution",
        "prop_of_wealth",
        "wealth_eor",
        "stage1_cap",
        "liquidity_forced_approx",
        "voluntary_zero_approx",
        "reputation",
        "shock_occurred",
        "ldf_payout_round",
        "prev_contribution",
        "prev_prop",
        "prev_reputation",
        "prev_ldf_payout",
        "mentions_coop",
        "mentions_mcpr",
        "mentions_conserve",
        "mentions_free_ride",
        "evidence_id",
        "contribution_reasoning",
    ]
    return z[cols].sort_values(["institution_choice", "round_number", "agent_id"])


def si_r6_focus(df: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    """SI agents around shock R5 / zero spike R6."""
    rows = []
    si = df[df["institution_choice"] == "SI"]
    for aid in sorted(si["agent_id"].unique()):
        for rn in range(4, 8):
            g = si[(si["agent_id"] == aid) & (si["round_number"] == rn)]
            if g.empty:
                continue
            row = g.iloc[0].to_dict()
            reason = rb[(rb["agent_id"] == aid) & (rb["round_number"] == rn)]
            text = reason["text"].iloc[0] if len(reason) else ""
            eid = reason["evidence_id"].iloc[0] if len(reason) else ""
            rows.append(
                {
                    "agent_id": aid,
                    "round_number": rn,
                    "contribution": row["contribution"],
                    "prop_of_wealth": row["prop_of_wealth"],
                    "wealth_eor": row["wealth_eor"],
                    "is_zero": row["is_zero"],
                    "reputation": row["reputation"],
                    "shock_occurred": row["shock_occurred"],
                    "ldf_payout_round": row.get("ldf_payout_round", 0),
                    "evidence_id": eid,
                    "contribution_reasoning": text,
                }
            )
    return pd.DataFrame(rows)


def r1_r2_spike(df: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for aid in sorted(df["agent_id"].unique()):
        r1 = df[(df["agent_id"] == aid) & (df["round_number"] == 1)].iloc[0]
        r2 = df[(df["agent_id"] == aid) & (df["round_number"] == 2)].iloc[0]
        t1 = rb[(rb["agent_id"] == aid) & (rb["round_number"] == 1)]
        t2 = rb[(rb["agent_id"] == aid) & (rb["round_number"] == 2)]
        rows.append(
            {
                "agent_id": aid,
                "institution_choice": r1["institution_choice"],
                "r1_contribution": r1["contribution"],
                "r1_prop": r1["prop_of_wealth"],
                "r1_zero": bool(r1["is_zero"]),
                "r2_contribution": r2["contribution"],
                "r2_prop": r2["prop_of_wealth"],
                "r2_zero": bool(r2["is_zero"]),
                "delta_prop": r2["prop_of_wealth"] - r1["prop_of_wealth"],
                "doubled_or_more": (r1["prop_of_wealth"] > 0)
                and (r2["prop_of_wealth"] >= 2 * r1["prop_of_wealth"]),
                "r1_reasoning": t1["text"].iloc[0] if len(t1) else "",
                "r2_reasoning": t2["text"].iloc[0] if len(t2) else "",
                "r1_evidence_id": t1["evidence_id"].iloc[0] if len(t1) else "",
                "r2_evidence_id": t2["evidence_id"].iloc[0] if len(t2) else "",
            }
        )
    return pd.DataFrame(rows)


def warm_glow(df: pd.DataFrame, rb: pd.DataFrame) -> pd.DataFrame:
    z = df[df["is_zero"]].copy()
    z = attach_reasoning(z, rb)
    z["text"] = z["contribution_reasoning"].fillna("")
    z["coop_lang"] = z["text"].map(lambda t: bool(COOP_PAT.search(t)))
    z["text_len"] = z["text"].str.len()
    glow = z[z["coop_lang"]].copy()
    # also compare lengths vs positive contrib with coop
    pos = df[~df["is_zero"]].copy()
    pos = attach_reasoning(pos, rb)
    pos["text"] = pos["contribution_reasoning"].fillna("")
    pos["coop_lang"] = pos["text"].map(lambda t: bool(COOP_PAT.search(t)))
    pos_coop = pos[pos["coop_lang"]]
    summary = {
        "n_zero_with_coop_lang": int(len(glow)),
        "n_zero_total": int(len(z)),
        "mean_text_len_zero_coop": float(glow["text_len"].mean()) if len(glow) else None,
        "mean_text_len_pos_coop": float(pos_coop["text"].str.len().mean()) if len(pos_coop) else None,
        "n_pos_with_coop_lang": int(len(pos_coop)),
        "top_agents_zero_coop": glow.groupby("agent_id").size().sort_values(ascending=False).head(10).to_dict(),
    }
    (TABLES / "warm_glow_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    cols = [
        "round_number",
        "agent_id",
        "institution_choice",
        "contribution",
        "prop_of_wealth",
        "text_len",
        "evidence_id",
        "contribution_reasoning",
    ]
    return glow[cols].sort_values(["agent_id", "round_number"])


def burst_timing(df: pd.DataFrame) -> pd.DataFrame:
    """For high-variance SFI agents, flag bursts > mean+1.5*std."""
    profiles = pd.read_csv(TABLES / "agent_strategy_profiles.csv")
    sfi = profiles[profiles["institution_choice"] == "SFI"]
    # bursty: zero_share > 0.1 and mean_prop > 0.2
    bursty_ids = sfi[(sfi["zero_share"] > 0.1) & (sfi["mean_prop"] > 0.15)]["agent_id"].tolist()
    rows = []
    for aid in bursty_ids:
        g = df[df["agent_id"] == aid].sort_values("round_number")
        mu, sd = g["contribution"].mean(), g["contribution"].std(ddof=1)
        thr = mu + 1.5 * (sd if sd and not np.isnan(sd) else 0)
        for _, row in g.iterrows():
            if row["contribution"] > thr and thr > 0:
                prev = g[g["round_number"] == row["round_number"] - 1]
                prev_payout = float(prev["ldf_payout_round"].iloc[0]) if len(prev) else 0.0
                rows.append(
                    {
                        "agent_id": aid,
                        "round_number": int(row["round_number"]),
                        "contribution": row["contribution"],
                        "prop_of_wealth": row["prop_of_wealth"],
                        "threshold": thr,
                        "prev_ldf_payout": prev_payout,
                        "is_democracy_round": int(row["round_number"]) % 5 == 0,
                        "shock_occurred": int(row["shock_occurred"]),
                        "after_payout": int(prev_payout > 0),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df = load_panel()
    rb = load_reasoning()

    inv = inventory(df)
    inv.to_csv(TABLES / "zero_contribution_inventory.csv", index=False)

    zbr = zero_by_round(df)
    zbr.to_csv(TABLES / "zero_contribution_by_round.csv", index=False)

    ep = episode_table(df, rb)
    ep.to_csv(TABLES / "zero_contribution_episodes.csv", index=False)

    si6 = si_r6_focus(df, rb)
    si6.to_csv(TABLES / "zero_si_r4_r7_window.csv", index=False)

    spike = r1_r2_spike(df, rb)
    spike.to_csv(TABLES / "r1_r2_spike_by_agent.csv", index=False)

    glow = warm_glow(df, rb)
    glow.to_csv(TABLES / "warm_glow_zero_coop_cases.csv", index=False)

    bursts = burst_timing(df)
    bursts.to_csv(TABLES / "sfi_burst_rounds.csv", index=False)

    # numeric summary
    si_r6 = df[(df["institution_choice"] == "SI") & (df["round_number"] == 6)]
    sfi_r1 = df[(df["institution_choice"] == "SFI") & (df["round_number"] == 1)]
    summary = {
        "run": RUN,
        "source": SOURCE,
        "inventory": inv.to_dict(orient="records"),
        "si_r6_zero_share": float(si_r6["is_zero"].mean()),
        "si_r6_zero_agents": si_r6[si_r6["is_zero"]]["agent_id"].tolist(),
        "sfi_r1_zero_share": float(sfi_r1["is_zero"].mean()),
        "sfi_r1_zero_agents": sfi_r1[sfi_r1["is_zero"]]["agent_id"].tolist(),
        "all_r1_mean_prop": float(df[df["round_number"] == 1]["prop_of_wealth"].mean()),
        "all_r2_mean_prop": float(df[df["round_number"] == 2]["prop_of_wealth"].mean()),
        "sfi_r1_mean_prop": float(sfi_r1["prop_of_wealth"].mean()),
        "sfi_r2_mean_prop": float(
            df[(df["institution_choice"] == "SFI") & (df["round_number"] == 2)]["prop_of_wealth"].mean()
        ),
        "n_warm_glow_cases": int(len(glow)),
        "n_burst_rounds": int(len(bursts)),
        "liquidity_note": (
            "liquidity_forced_approx uses stage1_cap_from_end_wealth==0; "
            "true decision-time wealth may differ â€” treat as approximate."
        ),
    }
    (TABLES / "prompt_zero_numeric_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

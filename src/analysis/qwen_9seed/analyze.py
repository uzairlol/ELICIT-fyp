"""Run-level statistical analysis for the nine Qwen Full-LDF trajectories."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .statistics import (
    cliffs_delta,
    cohen_dz,
    exact_sign_flip_pvalue,
    paired_percentile_ci,
    percentile_ci,
)

RNG_SEED = 20260925
BOOTSTRAP_N = 20_000
GOSSIP_TRIGGER_SCORE = 7.0

MOTIFS: dict[str, re.Pattern[str]] = {
    "payoff_or_marginal_return": re.compile(
        r"\b(payoff|profit|marginal|benefit|cost|self[- ]interest|maximi[sz]|rational|return)\b",
        re.I,
    ),
    "peer_matching": re.compile(
        r"\b(other agents?|peers?|others?|contributors?|match|free[- ]?rider|free[- ]?ride|defect\w*)\b",
        re.I,
    ),
    "reciprocity_or_future": re.compile(
        r"\b(recipro\w*|return|mutual|future round|next round|reward|repeat\w*|ongoing)\b", re.I
    ),
    "fairness_or_equity": re.compile(
        r"\b(fair\w*|equit\w*|justice|equal\w*|distribution|burden|deserv\w*)\b", re.I
    ),
    "climate_or_ldf": re.compile(
        r"\b(climate|shock|damage|loss|adapt\w*|fund|vulnerab\w*|emission\w*)\b", re.I
    ),
    "enforcement_or_sanction": re.compile(
        r"\b(punish\w*|sanction\w*|enforc\w*|penalt\w*|reward\w*|rule of law)\b", re.I
    ),
    "constraint_or_liquidity": re.compile(
        r"\b(wealth|resource|cannot|unable|afford|capacity|limit\w*|budget|poor|needy)\b", re.I
    ),
    "institution_or_governance": re.compile(
        r"\b(institution\w*|treaty|agreement|\bSI\b|\bSFI\b|vote\w*|proposal|govern\w*|constitution\w*)\b",
        re.I,
    ),
}

EARLY_ROUNDS = [1, 2, 3, 4]
LATE_ROUNDS = [27, 28, 29, 30]
EARLY_ROUNDS_NO_COLD_START = [2, 3, 4]
LATE_ROUNDS_NO_COLD_START = [28, 29, 30]


def _finite(values: Any) -> np.ndarray:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    return arr[np.isfinite(arr)]


def _mean(values: Any) -> float:
    arr = _finite(values)
    return float(arr.mean()) if len(arr) else float("nan")


def _median(values: Any) -> float:
    arr = _finite(values)
    return float(np.median(arr)) if len(arr) else float("nan")


def _sd(values: Any) -> float:
    arr = _finite(values)
    return float(arr.std(ddof=1)) if len(arr) > 1 else float("nan")


def _summary(values: Any, label: str, unit: str = "run", seed_offset: int = 0) -> dict[str, Any]:
    arr = _finite(values)
    result: dict[str, Any] = {
        "metric": label,
        "unit": unit,
        "n": len(arr),
        "mean": float(arr.mean()) if len(arr) else np.nan,
        "median": float(np.median(arr)) if len(arr) else np.nan,
        "sd": float(arr.std(ddof=1)) if len(arr) > 1 else np.nan,
        "min": float(arr.min()) if len(arr) else np.nan,
        "max": float(arr.max()) if len(arr) else np.nan,
    }
    if len(arr):
        ci = percentile_ci(arr, np.mean, n_boot=BOOTSTRAP_N, seed=RNG_SEED + seed_offset)
        result.update(
            {
                "ci_lower": ci["lower"],
                "ci_upper": ci["upper"],
                "bootstrap_n": ci["n_boot"],
            }
        )
    else:
        result.update({"ci_lower": np.nan, "ci_upper": np.nan, "bootstrap_n": 0})
    return result


def _paired_summary(
    frame: pd.DataFrame,
    before_col: str,
    after_col: str,
    label: str,
    role: str = "all",
    seed_offset: int = 0,
) -> dict[str, Any]:
    valid = frame[[before_col, after_col]].replace([np.inf, -np.inf], np.nan).dropna()
    before = valid[before_col].to_numpy(dtype=float)
    after = valid[after_col].to_numpy(dtype=float)
    diff = after - before
    ci = paired_percentile_ci(before, after, n_boot=BOOTSTRAP_N, seed=RNG_SEED + seed_offset)
    return {
        "contrast": label,
        "role": role,
        "n_runs": len(diff),
        "mean_before": float(before.mean()) if len(before) else np.nan,
        "mean_after": float(after.mean()) if len(after) else np.nan,
        "mean_change": float(diff.mean()) if len(diff) else np.nan,
        "ci_lower": ci["lower"],
        "ci_upper": ci["upper"],
        "exact_sign_flip_p": exact_sign_flip_pvalue(diff) if len(diff) else np.nan,
        "n_positive_change": int(np.sum(diff > 0)),
        "n_zero_change": int(np.sum(diff == 0)),
        "n_negative_change": int(np.sum(diff < 0)),
        "cliffs_delta_paired": cliffs_delta(before, after) if len(diff) else np.nan,
        "cohen_dz_paired": cohen_dz(diff) if len(diff) else np.nan,
    }


def _safe_divide(a: Any, b: Any) -> float:
    try:
        return float(a) / float(b) if float(b) != 0 else np.nan
    except (TypeError, ValueError):
        return np.nan


def _gini(values: Any) -> float:
    arr = _finite(values)
    arr = np.maximum(arr, 0)
    if len(arr) == 0 or arr.sum() == 0:
        return np.nan
    arr = np.sort(arr)
    n = len(arr)
    return float((2 * np.sum(np.arange(1, n + 1) * arr) / (n * arr.sum())) - (n + 1) / n)


def _hhi(values: Any) -> float:
    arr = _finite(values)
    arr = np.maximum(arr, 0)
    if len(arr) == 0 or arr.sum() == 0:
        return np.nan
    return float(np.sum((arr / arr.sum()) ** 2))


def _top_share(values: Any, fraction: float = 0.1) -> float:
    arr = _finite(values)
    arr = np.maximum(arr, 0)
    if len(arr) == 0 or arr.sum() == 0:
        return np.nan
    k = max(1, math.ceil(len(arr) * fraction))
    return float(np.sort(arr)[-k:].sum() / arr.sum())


def _add_window_metrics(
    frame: pd.DataFrame,
    rounds: list[int],
    prefix: str,
    role: str | None = None,
) -> pd.DataFrame:
    """Add mean outcomes for one round window to a per-run frame."""
    frame = frame.copy()
    subset = frame[frame["round_number"].isin(rounds)]
    if role is not None:
        subset = subset[subset["agent_group"] == role]
    if subset.empty:
        return frame
    grouped = subset.groupby("seed")
    for outcome, source in {
        "positive_share": "positive_contribution",
        "zero_share": "zero_contribution",
        "mean_intensity": "pre_decision_intensity",
        "mean_contribution": "contribution",
        "mean_start_wealth": "start_wealth",
        "mean_end_wealth": "end_wealth",
    }.items():
        values = grouped[source].mean()
        frame[f"{prefix}_{outcome}"] = frame["seed"].map(values)
    eligible = subset[subset["decision_cap"] > 0]
    eligible_grouped = eligible.groupby("seed")
    frame[f"{prefix}_eligible_positive_share"] = frame["seed"].map(
        eligible_grouped["positive_contribution"].mean()
    )
    frame[f"{prefix}_eligible_zero_share"] = frame["seed"].map(
        eligible_grouped["zero_contribution"].mean()
    )
    # A zero-cap record is structurally ineligible, so the all-agent zero share
    # is supplemented with an eligible-only denominator.
    return frame


def _prepare_agent_metrics(
    agent: pd.DataFrame, tom: pd.DataFrame, belief: pd.DataFrame
) -> pd.DataFrame:
    df = agent.copy()
    df["intensity_zero_as_zero"] = df["pre_decision_intensity"].fillna(0.0)
    df["eligible"] = (df["decision_cap"] > 0).astype(int)
    df["eligible_positive"] = df["positive_contribution"] * df["eligible"]
    df["eligible_zero"] = df["zero_contribution"] * df["eligible"]
    df = df.sort_values(["seed", "agent_id", "round_number"]).reset_index(drop=True)
    # Shift belief state to the next action, since row-t belief is post-outcome.
    df["next_pre_decision_intensity"] = df.groupby(["seed", "agent_id"])[
        "pre_decision_intensity"
    ].shift(-1)
    df["next_positive_contribution"] = df.groupby(["seed", "agent_id"])[
        "positive_contribution"
    ].shift(-1)
    df["belief_next_action"] = df["belief_free_rider_label_count"].shift(-1)
    df["belief_next_coop_label"] = df["belief_cooperative_label_count"].shift(-1)
    # Prospective ToM target summaries: row-t incoming scores were available
    # before action t, although generated after t-1.
    if not tom.empty:
        target = (
            tom.groupby(["seed", "action_round", "target"])
            .agg(
                incoming_tom_n=("score", "count"),
                incoming_tom_mean=("score", "mean"),
                incoming_tom_min=("score", "min"),
                incoming_tom_low_count=("score", lambda s: int((s <= GOSSIP_TRIGGER_SCORE).sum())),
            )
            .reset_index()
            .rename(columns={"action_round": "round_number", "target": "agent_id"})
        )
        df = df.merge(target, on=["seed", "round_number", "agent_id"], how="left")
    else:
        for col in [
            "incoming_tom_n",
            "incoming_tom_mean",
            "incoming_tom_min",
            "incoming_tom_low_count",
        ]:
            df[col] = np.nan
    # Primary event definition: a low peer-average consistency score.  The
    # edge-count alternative is retained in robustness outputs rather than
    # combined here, because nearly every target has several scores <= 7.
    df["low_incoming_consistency_event"] = (df["incoming_tom_mean"] < 4).astype(int)
    return df


def _run_level_table(
    agent: pd.DataFrame, round_df: pd.DataFrame, tom: pd.DataFrame, sanction: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sanction_positive = (
        sanction[sanction["applied_amount"] > 0].copy() if not sanction.empty else sanction
    )
    sanction_requested = (
        sanction[sanction["requested_amount"] > 0].copy() if not sanction.empty else sanction
    )
    for seed in sorted(agent["seed"].unique()):
        a = agent[agent["seed"] == seed].copy()
        r = round_df[round_df["seed"] == seed].copy()
        s = (
            sanction_positive[sanction_positive["seed"] == seed]
            if not sanction_positive.empty
            else sanction_positive
        )
        sr = (
            sanction_requested[sanction_requested["seed"] == seed]
            if not sanction_requested.empty
            else sanction_requested
        )
        si = a[a["institution_choice"] == "SI"]
        row: dict[str, Any] = {
            "seed": int(seed),
            "n_rounds": int(r["round_number"].nunique()),
            "n_agent_records": len(a),
            "mean_positive_share": _mean(a["positive_contribution"]),
            "mean_eligible_positive_share": _mean(
                a.loc[a["eligible"] == 1, "positive_contribution"]
            ),
            "mean_zero_share": _mean(a["zero_contribution"]),
            "mean_eligible_zero_share": _mean(a.loc[a["eligible"] == 1, "zero_contribution"]),
            "mean_intensity": _mean(a["pre_decision_intensity"]),
            "mean_intensity_zero_as_zero": _mean(a["intensity_zero_as_zero"]),
            "median_intensity": _median(a["pre_decision_intensity"]),
            "mean_contribution": _mean(a["contribution"]),
            "median_contribution": _median(a["contribution"]),
            "mean_public_good_share": _mean(a["public_good_share"]),
            "mean_stage1_payoff": _mean(a["stage1_payoff"]),
            "stage1_positive_payoff_share": _mean(a["stage1_payoff"] > 0),
            "mean_stage1_net_from_contribution": _mean(a["public_good_share"] - a["contribution"]),
            "mean_total_payoff": _mean(a["payoff"]),
            "positive_total_payoff_share": _mean(a["payoff"] > 0),
            "peer_positive_zero_share": _mean(
                a["zero_contribution"]
                & (
                    a.groupby(["seed", "round_number"])["positive_contribution"].transform("mean")
                    > 0
                )
            ),
            "zero_cap_agent_share": _mean(a["cap_is_zero"]),
            "total_contribution": float(a["contribution"].sum()),
            "total_public_good_benefit": float(a["public_good_share"].sum()),
            "total_stage1_net_from_contribution": float(
                (a["public_good_share"] - a["contribution"]).sum()
            ),
            "total_stage1_payoff": float(a["stage1_payoff"].sum()),
            "total_stage2_payoff": float(a["stage2_payoff"].sum()),
            "total_subsidy": float(a["subsidy"].sum()),
            "total_payoff": float(a["payoff"].sum()),
            "mean_gini_round": _mean(r["gini_wealth"]),
            "early_gini": _mean(r[r["round_number"].isin(EARLY_ROUNDS)]["gini_wealth"]),
            "late_gini": _mean(r[r["round_number"].isin(LATE_ROUNDS)]["gini_wealth"]),
            "final_gini": float(r.iloc[-1]["gini_wealth"]),
            "mean_contribution_gini": _mean(r["contribution_gini"]),
            "low_incoming_event_share": _mean(a["low_incoming_consistency_event"]),
            "mean_incoming_tom": _mean(a["incoming_tom_mean"]),
            "mean_reputation": _mean(a["reputation_pre_action"]),
            "mean_belief_free_label_count": _mean(a["belief_free_rider_label_count"]),
            "mean_belief_coop_label_count": _mean(a["belief_cooperative_label_count"]),
            "gossip_you_possible_share": _mean(a["you_line_possible"]),
            "gossip_you_guaranteed_share": _mean(a["you_line_guaranteed"]),
            "gossip_bulletin_possible_share": _mean(a["bulletin_nonempty_possible"]),
            "gossip_receipt_guaranteed_share": _mean(a["bulletin_receipt_guaranteed"]),
            "si_mean_positive_share": _mean(si["positive_contribution"]),
            "sfi_mean_positive_share": _mean(
                a[a["institution_choice"] == "SFI"]["positive_contribution"]
            ),
            "si_mean_intensity": _mean(si["pre_decision_intensity"]),
            "sfi_mean_intensity": _mean(
                a[a["institution_choice"] == "SFI"]["pre_decision_intensity"]
            ),
            "si_mean_zero_share": _mean(si["zero_contribution"]),
            "sfi_mean_zero_share": _mean(a[a["institution_choice"] == "SFI"]["zero_contribution"]),
            "si_total_contribution": float(si["contribution"].sum()),
            "sfi_total_contribution": float(
                a[a["institution_choice"] == "SFI"]["contribution"].sum()
            ),
            "auto_fit_records": int(si["punishment_auto_fit"].sum()),
            "fallback_records": int(si["punishment_fallback"].sum()),
            "semantic_retry_records": int(si["punishment_semantic_retry"].sum()),
            "si_agent_rounds": len(si),
            "auto_fit_agent_share": _mean(si["punishment_auto_fit"]),
            "fallback_agent_share": _mean(si["punishment_fallback"]),
            "semantic_retry_agent_share": _mean(si["punishment_semantic_retry"]),
            "sanction_final_tokens": float(s["applied_amount"].sum()) if not s.empty else 0.0,
            "sanction_requested_tokens": float(sr["requested_amount"].sum())
            if not sr.empty
            else 0.0,
            "sanction_requested_reward_tokens": float(
                sr.loc[sr["kind"] == "reward", "requested_amount"].sum()
            )
            if not sr.empty
            else 0.0,
            "sanction_final_reward_tokens": float(
                s.loc[s["kind"] == "reward", "applied_amount"].sum()
            )
            if not s.empty
            else 0.0,
            "sanction_discard_ratio": _safe_divide(
                float(sr["requested_amount"].sum() - s["applied_amount"].sum())
                if not sr.empty
                else 0.0,
                float(sr["requested_amount"].sum()) if not sr.empty else 0.0,
            ),
            "sanction_participant_share": _mean(
                si["assigned_punishment_count"].gt(0) | si["assigned_reward_count"].gt(0)
            )
            if not si.empty
            else np.nan,
            "sanction_target_hhi": _hhi(s.groupby("target_agent")["applied_amount"].sum())
            if not s.empty
            else np.nan,
            "sanction_target_top10_share": _top_share(
                s.groupby("target_agent")["applied_amount"].sum()
            )
            if not s.empty
            else np.nan,
            "received_punishment_effect_total": float(a["received_punishments_effect"].sum()),
            "received_reward_effect_total": float(a["received_rewards_effect"].sum()),
            "total_ldf_deposit": float(a["ldf_contribution"].sum()),
            "total_ldf_payout": float(a["ldf_payout"].sum()),
            "total_climate_damage": float(a["climate_damage_round"].sum()),
            "total_net_climate_transfer": float(a["net_climate_transfer"].sum()),
            "final_ldf_pool": float(r.iloc[-1]["ldf_pool_end"]),
            "eligible_damage_total": float(r["eligible_damage"].sum()),
            "eligible_payout_total": float(r["eligible_payout"].sum()),
            "gross_damage_total": float(r["gross_damage_total"].sum()),
            "eligible_coverage": _safe_divide(
                float(r["eligible_payout"].sum()), float(r["eligible_damage"].sum())
            ),
            "system_coverage": _safe_divide(
                float(r["ldf_payouts_total"].sum()), float(r["gross_damage_total"].sum())
            ),
            "payout_to_deposit": _safe_divide(
                float(r["ldf_payouts_total"].sum()), float(r["ldf_contributions_total"].sum())
            ),
            "final_pool_to_deposit": _safe_divide(
                float(r.iloc[-1]["ldf_pool_end"]), float(r["ldf_contributions_total"].sum())
            ),
            "si_ldf_deposit": float(si["ldf_contribution"].sum()),
            "sfi_ldf_deposit": float(a[a["institution_choice"] == "SFI"]["ldf_contribution"].sum()),
            "sfi_ldf_payout": float(a[a["institution_choice"] == "SFI"]["ldf_payout"].sum()),
            "si_ldf_payout": float(si["ldf_payout"].sum()),
        }
        # Paired persistence over eligible consecutive decisions.
        eligible_pairs = (
            a[(a["eligible"] == 1) & a["prior_contribution"].notna() & (a["prior_cap"] > 0)]
            if "prior_cap" in a
            else a[(a["eligible"] == 1) & a["prior_contribution"].notna()]
        )
        if not eligible_pairs.empty:
            row["p_positive_after_positive"] = _mean(
                eligible_pairs.loc[
                    eligible_pairs["prior_contribution"] > 0, "positive_contribution"
                ]
            )
            row["p_positive_after_zero"] = _mean(
                eligible_pairs.loc[
                    eligible_pairs["prior_contribution"] == 0, "positive_contribution"
                ]
            )
            row["lag_intensity_corr"] = _safe_corr(
                eligible_pairs["prior_pre_decision_intensity"],
                eligible_pairs["pre_decision_intensity"],
            )
        else:
            row["p_positive_after_positive"] = row["p_positive_after_zero"] = row[
                "lag_intensity_corr"
            ] = np.nan
        # Wealth incidence relative to each role's initial endowment.
        first = a[a["round_number"] == 1]
        final = a[a["round_number"] == 30]
        for role in ["developed", "developing"]:
            first_role = first[first["agent_group"] == role]
            final_role = final[final["agent_group"] == role]
            initial_mean = _mean(first_role["start_wealth"])
            final_mean = _mean(final_role["end_wealth"])
            row[f"{role}_initial_mean_wealth"] = initial_mean
            row[f"{role}_final_mean_wealth"] = final_mean
            row[f"{role}_wealth_ratio_to_initial"] = _safe_divide(final_mean, initial_mean)
            row[f"{role}_initial_total_wealth"] = float(first_role["start_wealth"].sum())
            row[f"{role}_final_total_wealth"] = float(final_role["end_wealth"].sum())
            row[f"{role}_final_share_total_wealth"] = _safe_divide(
                float(final_role["end_wealth"].sum()), float(final["end_wealth"].sum())
            )
        row["final_group_mean_ratio"] = _safe_divide(
            row["developed_final_mean_wealth"], row["developing_final_mean_wealth"]
        )
        row["initial_group_mean_ratio"] = _safe_divide(
            row["developed_initial_mean_wealth"], row["developing_initial_mean_wealth"]
        )
        row["group_ratio_change"] = row["final_group_mean_ratio"] - row["initial_group_mean_ratio"]
        row["mean_log_end_wealth"] = _mean(np.log1p(a["end_wealth"].clip(lower=0)))
        row["final_top10_wealth_share"] = _top_share(final["end_wealth"])
        row["final_wealth_hhi"] = _hhi(final["end_wealth"])
        # Add window metrics for all and each assigned role.
        for rounds, prefix in [
            (EARLY_ROUNDS, "early"),
            (LATE_ROUNDS, "late"),
            (EARLY_ROUNDS_NO_COLD_START, "early_no_cold"),
            (LATE_ROUNDS_NO_COLD_START, "late_no_cold"),
        ]:
            for role in [None, "developed", "developing"]:
                tmp = pd.DataFrame({"seed": [seed]})
                if role is None:
                    tmp = _add_window_metrics(a, rounds, prefix, role)
                else:
                    tmp = _add_window_metrics(
                        a[a["agent_group"] == role], rounds, f"{prefix}_{role}", role
                    )
                    # The helper returns a frame with only the role subset; map
                    # its one value back to the run row.
                    for col in [c for c in tmp.columns if c.startswith(prefix + "_")]:
                        row[col] = (
                            float(tmp[col].iloc[0])
                            if len(tmp) and pd.notna(tmp[col].iloc[0])
                            else np.nan
                        )
                    continue
                for col in [c for c in tmp.columns if c.startswith(prefix + "_")]:
                    row[col] = (
                        float(tmp[col].iloc[0])
                        if len(tmp) and pd.notna(tmp[col].iloc[0])
                        else np.nan
                    )
        # Shock-specific descriptive windows, with round t excluded because
        # actions precede the shock and the associated constitutional session.
        for shock, pre_rounds, post_rounds in [
            (5, [2, 3, 4], [6, 7, 8]),
            (10, [7, 8, 9], [11, 12, 13]),
        ]:
            for outcome, source in [
                ("positive", "positive_contribution"),
                ("intensity", "pre_decision_intensity"),
                ("zero", "zero_contribution"),
            ]:
                row[f"shock{shock}_pre_{outcome}"] = _mean(
                    a[a["round_number"].isin(pre_rounds)][source]
                )
                row[f"shock{shock}_post_{outcome}"] = _mean(
                    a[a["round_number"].isin(post_rounds)][source]
                )
        rows.append(row)
    result = pd.DataFrame(rows).sort_values("seed").reset_index(drop=True)
    return result


def _safe_corr(x: Any, y: Any) -> float:
    xa = _finite(x)
    ya = _finite(y)
    if len(xa) != len(ya) or len(xa) < 3:
        return np.nan
    if np.std(xa) == 0 or np.std(ya) == 0:
        return np.nan
    return float(np.corrcoef(xa, ya)[0, 1])


def _role_summary(agent: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role, part in agent.groupby("agent_group"):
        for outcome, source in [
            ("positive_share", "positive_contribution"),
            ("zero_share", "zero_contribution"),
            ("pre_decision_intensity", "pre_decision_intensity"),
            ("contribution", "contribution"),
            ("stage1_payoff", "stage1_payoff"),
        ]:
            seed_values = part.groupby("seed")[source].mean()
            rows.append(
                {
                    "role": role,
                    "outcome": outcome,
                    "n_agent_rounds": len(part),
                    "n_runs": part["seed"].nunique(),
                    **_summary(seed_values, f"{role}:{outcome}", seed_offset=700 + len(rows)),
                }
            )
        early = (
            part[part["round_number"].isin(EARLY_ROUNDS)]
            .groupby("seed")["positive_contribution"]
            .mean()
        )
        late = (
            part[part["round_number"].isin(LATE_ROUNDS)]
            .groupby("seed")["positive_contribution"]
            .mean()
        )
        rows.append(
            {
                "role": role,
                "outcome": "positive_share_early",
                "n_agent_rounds": len(part[part["round_number"].isin(EARLY_ROUNDS)]),
                "n_runs": part["seed"].nunique(),
                **_summary(early, f"{role}:early positive", seed_offset=800 + len(rows)),
            }
        )
        rows.append(
            {
                "role": role,
                "outcome": "positive_share_late",
                "n_agent_rounds": len(part[part["round_number"].isin(LATE_ROUNDS)]),
                "n_runs": part["seed"].nunique(),
                **_summary(late, f"{role}:late positive", seed_offset=900 + len(rows)),
            }
        )
    return pd.DataFrame(rows)


def _public_goods_summary(agent: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role, part in [
        ("all", agent),
        ("developed", agent[agent["agent_group"] == "developed"]),
        ("developing", agent[agent["agent_group"] == "developing"]),
    ]:
        for metric, values in [
            ("stage1_positive_payoff_share", part["stage1_payoff"] > 0),
            ("positive_total_payoff_share", part["payoff"] > 0),
            (
                "peer_positive_zero_share",
                part["zero_contribution"]
                & (
                    part.groupby(["seed", "round_number"])["positive_contribution"].transform(
                        "mean"
                    )
                    > 0
                ),
            ),
            ("mean_stage1_net", part["public_good_share"] - part["contribution"]),
        ]:
            seed_values = part.assign(_value=values).groupby("seed")["_value"].mean()
            rows.append(
                {
                    "role": role,
                    "metric": metric,
                    "n_agent_rounds": len(part),
                    **_summary(seed_values, f"{role}:{metric}", seed_offset=1000 + len(rows)),
                }
            )
    return pd.DataFrame(rows)


def _round_summary(round_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = [
        "positive_share",
        "zero_share",
        "mean_pre_decision_intensity",
        "median_pre_decision_intensity",
        "mean_contribution",
        "contribution_gini",
        "gini_wealth",
        "ldf_pool_end",
        "total_ldf_payout",
        "role_positive_share_developed",
        "role_positive_share_developing",
        "role_mean_intensity_developed",
        "role_mean_intensity_developing",
    ]
    for rn, part in round_df.groupby("round_number"):
        for metric in metrics:
            if metric not in part:
                continue
            rows.append(
                {
                    "round_number": int(rn),
                    "metric": metric,
                    **_summary(part[metric], metric, unit="run", seed_offset=rn * 100 + len(rows)),
                }
            )
    return pd.DataFrame(rows)


def _primary_contrasts(run_metrics: pd.DataFrame) -> pd.DataFrame:
    specs = [
        (
            "positive_share",
            "early_positive_share",
            "late_positive_share",
            "positive-contribution share",
            "all",
        ),
        (
            "eligible_positive_share",
            "early_eligible_positive_share",
            "late_eligible_positive_share",
            "eligible positive-contribution share",
            "all",
        ),
        (
            "positive_share",
            "early_no_cold_positive_share",
            "late_no_cold_positive_share",
            "positive-contribution share (excluding cold start)",
            "all",
        ),
        (
            "mean_intensity",
            "early_mean_intensity",
            "late_mean_intensity",
            "pre-decision intensity",
            "all",
        ),
        (
            "mean_intensity",
            "early_no_cold_mean_intensity",
            "late_no_cold_mean_intensity",
            "pre-decision intensity (excluding cold start)",
            "all",
        ),
        ("zero_share", "early_zero_share", "late_zero_share", "zero-contribution share", "all"),
        ("gini_wealth", "early_gini", "late_gini", "wealth Gini", "all"),
        (
            "positive_share",
            "early_developed_positive_share",
            "late_developed_positive_share",
            "positive-contribution share",
            "developed/SI",
        ),
        (
            "mean_intensity",
            "early_developed_mean_intensity",
            "late_developed_mean_intensity",
            "pre-decision intensity",
            "developed/SI",
        ),
        (
            "positive_share",
            "early_developing_positive_share",
            "late_developing_positive_share",
            "positive-contribution share",
            "developing/SFI",
        ),
        (
            "mean_intensity",
            "early_developing_mean_intensity",
            "late_developing_mean_intensity",
            "pre-decision intensity",
            "developing/SFI",
        ),
    ]
    rows = []
    for i, (_, before, after, label, role) in enumerate(specs):
        rows.append(
            _paired_summary(run_metrics, before, after, f"late minus early: {label}", role, i + 10)
        )
    for i, shock in enumerate([5, 10]):
        for outcome in ["positive", "intensity", "zero"]:
            rows.append(
                _paired_summary(
                    run_metrics,
                    f"shock{shock}_pre_{outcome}",
                    f"shock{shock}_post_{outcome}",
                    f"shock {shock}: post minus pre {outcome}",
                    "all",
                    100 + i * 10 + len(rows),
                )
            )
    return pd.DataFrame(rows)


def _event_associations(agent: pd.DataFrame, run_metrics: pd.DataFrame) -> pd.DataFrame:
    """Estimate prospective event associations within common time/role cells.

    A raw exposed-minus-unexposed comparison is dominated by the fact that
    events become more common after the early rounds.  For each seed, round,
    and assigned role, this function compares exposed and unexposed eligible
    agents within the same cell, averages those cell differences within the
    seed, and bootstraps the nine seed-level averages.  This is still an
    associational diagnostic: exposure is generated by the same model and is
    not randomized.
    """
    definitions = [
        ("low_incoming_consistency_event", "Low incoming consistency event (peer mean <4)"),
        ("you_line_possible", "Possible visible gossip line about agent"),
        ("you_line_guaranteed", "Guaranteed visible gossip line about agent"),
        ("bulletin_receipt_possible", "Possible bulletin receipt"),
    ]
    rows = []
    for flag, label in definitions:
        for role in ["all", "developed", "developing"]:
            run_rows = []
            for seed, seed_part in agent.groupby("seed"):
                part = seed_part[seed_part["eligible"] == 1]
                if role != "all":
                    part = part[part["agent_group"] == role]
                # Round 1 has no preceding ToM audit.  Restrict event analyses
                # to rows with a measured incoming score, avoiding a mechanical
                # early/late exposure contrast.
                if "incoming_tom_n" in part:
                    part = part[part["incoming_tom_n"].notna()]
                cell_diffs = []
                cell_positive_diffs = []
                n_exposed = 0
                n_unexposed = 0
                n_cells = 0
                for _, cell in part.groupby(["round_number", "agent_group"]):
                    exposed = cell[cell[flag] == 1]
                    unexposed = cell[cell[flag] == 0]
                    if exposed.empty or unexposed.empty:
                        continue
                    n_cells += 1
                    n_exposed += len(exposed)
                    n_unexposed += len(unexposed)
                    cell_diffs.append(
                        _mean(exposed["pre_decision_intensity"])
                        - _mean(unexposed["pre_decision_intensity"])
                    )
                    cell_positive_diffs.append(
                        _mean(exposed["positive_contribution"])
                        - _mean(unexposed["positive_contribution"])
                    )
                run_rows.append(
                    {
                        "seed": int(seed),
                        "n_cells": n_cells,
                        "n_exposed": n_exposed,
                        "n_unexposed": n_unexposed,
                        "difference": _mean(cell_diffs),
                        "positive_share_difference": _mean(cell_positive_diffs),
                    }
                )
            frame = pd.DataFrame(run_rows)
            for outcome, diff_col in [
                ("intensity", "difference"),
                ("positive_share", "positive_share_difference"),
            ]:
                differences = frame[diff_col]
                ci = percentile_ci(
                    differences, np.mean, n_boot=BOOTSTRAP_N, seed=RNG_SEED + len(rows)
                )
                rows.append(
                    {
                        "event": label,
                        "role": role,
                        "outcome": outcome,
                        "method": "within-seed-round-role cell difference; run-level bootstrap",
                        "n_runs": int(differences.notna().sum()),
                        "n_cells_total": int(frame["n_cells"].sum()),
                        "n_exposed_total": int(frame["n_exposed"].sum()),
                        "n_unexposed_total": int(frame["n_unexposed"].sum()),
                        "mean_difference": _mean(differences),
                        "ci_lower": ci["lower"],
                        "ci_upper": ci["upper"],
                        "n_positive_run_differences": int((differences > 0).sum()),
                    }
                )
    return pd.DataFrame(rows)


def _sanction_summary(
    agent: pd.DataFrame, sanction: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    si = agent[agent["institution_choice"] == "SI"].copy()
    run_rows = []
    for seed, part in si.groupby("seed"):
        run_rows.append(
            {
                "seed": int(seed),
                "si_agent_rounds": len(part),
                "auto_fit_records": int(part["punishment_auto_fit"].sum()),
                "fallback_records": int(part["punishment_fallback"].sum()),
                "semantic_retry_records": int(part["punishment_semantic_retry"].sum()),
                "auto_fit_share": _mean(part["punishment_auto_fit"]),
                "fallback_share": _mean(part["punishment_fallback"]),
                "retry_share": _mean(part["punishment_semantic_retry"]),
                "final_punishment_tokens": float(part["assigned_punishment_total"].sum()),
                "final_reward_tokens": float(part["assigned_reward_total"].sum()),
                "raw_punishment_tokens": float(part["raw_punishment_total"].sum()),
                "raw_reward_tokens": float(part["raw_reward_total"].sum()),
                "final_to_raw_punishment_ratio": _safe_divide(
                    part["assigned_punishment_total"].sum(), part["raw_punishment_total"].sum()
                ),
                "final_to_raw_reward_ratio": _safe_divide(
                    part["assigned_reward_total"].sum(), part["raw_reward_total"].sum()
                ),
                "sender_participation_share": _mean(
                    (part["assigned_punishment_count"] > 0) | (part["assigned_reward_count"] > 0)
                ),
                "received_punishment_effect": float(part["received_punishments_effect"].sum()),
                "received_reward_effect": float(part["received_rewards_effect"].sum()),
                "subsidy_total": float(part["subsidy"].sum()),
            }
        )
    run_df = pd.DataFrame(run_rows)
    edge_rows = []
    if not sanction.empty:
        for seed, part in sanction.groupby("seed"):
            for kind, sub in part.groupby("kind"):
                requested = float(sub.loc[sub["requested_amount"] > 0, "requested_amount"].sum())
                applied = float(sub.loc[sub["applied_amount"] > 0, "applied_amount"].sum())
                edge_rows.append(
                    {
                        "seed": int(seed),
                        "kind": kind,
                        "requested_tokens": requested,
                        "applied_tokens": applied,
                        "discarded_tokens": requested - applied,
                        "discard_ratio": _safe_divide(requested - applied, requested),
                        "positive_edge_count": int((sub["applied_amount"] > 0).sum()),
                        "requested_edge_count": int((sub["requested_amount"] > 0).sum()),
                    }
                )
    return run_df, pd.DataFrame(edge_rows)


def _democracy_summary(
    sessions: pd.DataFrame, proposals: pd.DataFrame, votes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    session_rows = []
    for seed, part in sessions.groupby("seed"):
        session_rows.append(
            {
                "seed": int(seed),
                "sessions": len(part),
                "proposals": int(part["n_proposals"].sum()),
                "valid_votes": int(part["n_valid_votes"].sum()),
                "vote_records": int(part["n_vote_records"].sum()),
                "valid_vote_share": _mean(part["participation_rate"]),
                "mean_plurality_share": _mean(part["plurality_share"]),
                "mean_plurality_margin": _mean(part["plurality_margin"]),
                "applied_sessions": int(part["applied"].sum()),
                "post_final_shock_applied": int(
                    ((part["round_number"] > 10) & part["applied"]).sum()
                ),
                "ldf_rule_wins": int(part["winning_rule_family"].eq("ldf").sum()),
                "subsidy_rule_wins": int(part["winning_rule_family"].eq("subsidy").sum()),
                "punishment_rule_wins": int(part["winning_rule_family"].eq("punishment").sum()),
                "reward_rule_wins": int(part["winning_rule_family"].eq("reward").sum()),
            }
        )
    winner = proposals[proposals["is_winner"]].copy() if not proposals.empty else proposals
    rule_counts = []
    if not winner.empty:
        for (family, direction), part in winner.groupby(["rule_family", "direction"]):
            rule_counts.append(
                {
                    "rule_family": family,
                    "direction": direction,
                    "winner_sessions": len(part),
                    "unique_seeds": part["seed"].nunique(),
                    "mean_new_value": _mean(part["new_value"]),
                }
            )
    vote_summary = []
    if not votes.empty:
        for (seed, rn), part in votes.groupby(["seed", "round_number"]):
            vote_summary.append(
                {
                    "seed": int(seed),
                    "round_number": int(rn),
                    "n_votes": len(part),
                    "valid_vote_share": _mean(part["valid_vote"]),
                    "distinct_vote_choices": int(
                        part.loc[part["valid_vote"], "vote_index"].nunique()
                    ),
                    "winner_choice_share": _mean(
                        part.loc[part["valid_vote"], "vote_index"]
                        == part.loc[part["valid_vote"], "vote_index"].mode().iloc[0]
                    )
                    if part["valid_vote"].any()
                    else np.nan,
                }
            )
    return pd.DataFrame(session_rows), pd.DataFrame(rule_counts), pd.DataFrame(vote_summary)


def _wealth_summary(run_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("mean_gini_round", "Mean round wealth Gini"),
        ("early_gini", "Opening-window wealth Gini"),
        ("late_gini", "Closing-window wealth Gini"),
        ("final_gini", "Terminal wealth Gini"),
        ("developed_wealth_ratio_to_initial", "Developed mean wealth / initial developed mean"),
        ("developing_wealth_ratio_to_initial", "Developing mean wealth / initial developing mean"),
        ("final_group_mean_ratio", "Terminal developed/developing mean-wealth ratio"),
        ("initial_group_mean_ratio", "Initial developed/developing mean-wealth ratio"),
        ("group_ratio_change", "Change in developed/developing mean-wealth ratio"),
        ("final_top10_wealth_share", "Terminal top-10% wealth share"),
        ("final_wealth_hhi", "Terminal wealth HHI"),
    ]
    for i, (col, label) in enumerate(specs):
        rows.append(
            {
                "metric": col,
                "label": label,
                **_summary(run_metrics[col], label, seed_offset=300 + i),
            }
        )
    return pd.DataFrame(rows)


def _reasoning_profile(reasoning: pd.DataFrame, agent: pd.DataFrame) -> pd.DataFrame:
    """Describe how much reasoning text the model actually produces.

    The lexical motif analysis below is only interpretable alongside the
    length and repetition structure of the same field.  This profile makes
    that structure auditable: a one-line justification template produces
    motif prevalences that measure template wording, not deliberation.
    """
    if reasoning.empty:
        return pd.DataFrame()
    keys = [
        "seed",
        "round_number",
        "agent_id",
        "agent_group",
        "positive_contribution",
        "zero_contribution",
    ]
    context = agent[keys] if all(key in agent.columns for key in keys) else None
    rows: list[dict[str, Any]] = []

    def describe(part: pd.DataFrame, field: str, stratum: str) -> None:
        text = part["text"].fillna("").astype(str)
        words = text.str.split().str.len()
        per_run = part.assign(_words=words).groupby("seed")["_words"].mean()
        ci = percentile_ci(per_run, np.mean, n_boot=BOOTSTRAP_N, seed=RNG_SEED + 1500 + len(rows))
        counts = text.value_counts()
        rows.append(
            {
                "field": field,
                "stratum": stratum,
                "n_documents": len(text),
                "n_unique_texts": int(text.nunique()),
                "unique_text_share": float(text.nunique() / len(text)) if len(text) else np.nan,
                "most_common_text_count": int(counts.iloc[0]) if len(counts) else 0,
                "most_common_text_share": float(counts.iloc[0] / len(text))
                if len(text)
                else np.nan,
                "mean_words": float(words.mean()) if len(words) else np.nan,
                "sd_words": float(words.std(ddof=1)) if len(words) > 1 else np.nan,
                "median_words": float(words.median()) if len(words) else np.nan,
                "p90_words": float(words.quantile(0.90)) if len(words) else np.nan,
                "mean_characters": float(text.str.len().mean()) if len(text) else np.nan,
                "mean_words_run_level": ci["estimate"],
                "mean_words_ci_lower": ci["lower"],
                "mean_words_ci_upper": ci["upper"],
            }
        )

    contribution = reasoning[reasoning["field"] == "contribution_reasoning"]
    if context is not None:
        contribution = contribution.merge(
            context, on=["seed", "round_number", "agent_id"], how="left"
        )
        describe(contribution, "contribution_reasoning", "all")
        for group, part in contribution.groupby("agent_group"):
            describe(part, "contribution_reasoning", str(group))
        for label, part in [
            ("positive_action", contribution[contribution["positive_contribution"] == 1]),
            ("zero_action", contribution[contribution["zero_contribution"] == 1]),
        ]:
            describe(part, "contribution_reasoning", label)
        describe(
            contribution[contribution["round_number"].isin(EARLY_ROUNDS)],
            "contribution_reasoning",
            "early_window",
        )
        describe(
            contribution[contribution["round_number"].isin(LATE_ROUNDS)],
            "contribution_reasoning",
            "late_window",
        )
    else:
        describe(contribution, "contribution_reasoning", "all")
    for field, part in reasoning[reasoning["field"] != "contribution_reasoning"].groupby("field"):
        describe(part, str(field), "all")
    return pd.DataFrame(rows)


def _qualitative_summary(
    reasoning: pd.DataFrame, agent: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if reasoning.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    corpus = reasoning[reasoning["field"] == "contribution_reasoning"].merge(
        agent[
            [
                "seed",
                "round_number",
                "agent_id",
                "agent_group",
                "institution_choice",
                "positive_contribution",
                "zero_contribution",
            ]
        ],
        on=["seed", "round_number", "agent_id"],
        how="left",
    )
    rows = []
    for motif, pattern in MOTIFS.items():
        corpus[f"motif_{motif}"] = (
            corpus["text"]
            .fillna("")
            .map(lambda value, pattern=pattern: bool(pattern.search(str(value))))
        )
        for role, part in [
            ("all", corpus),
            ("developed", corpus[corpus["agent_group"] == "developed"]),
            ("developing", corpus[corpus["agent_group"] == "developing"]),
            ("positive_action", corpus[corpus["positive_contribution"] == 1]),
            ("zero_action", corpus[corpus["zero_contribution"] == 1]),
        ]:
            seed_values = part.groupby("seed")[f"motif_{motif}"].mean()
            rows.append(
                {
                    "motif": motif,
                    "role_or_action": role,
                    "n_documents": len(part),
                    "n_seed_document_units": int(part["seed"].nunique()),
                    "mean_prevalence": _mean(seed_values),
                    "ci_lower": percentile_ci(
                        seed_values, np.mean, n_boot=BOOTSTRAP_N, seed=RNG_SEED + len(rows)
                    )["lower"],
                    "ci_upper": percentile_ci(
                        seed_values, np.mean, n_boot=BOOTSTRAP_N, seed=RNG_SEED + len(rows)
                    )["upper"],
                    "n_positive_documents": int(part[f"motif_{motif}"].sum()),
                }
            )
    # Belief labels are a separate descriptive vocabulary audit.
    belief = (
        pd.read_csv(Path("analysis_outputs/qwen2_5_14b_9seed/tables/belief_edges.csv"))
        if Path("analysis_outputs/qwen2_5_14b_9seed/tables/belief_edges.csv").exists()
        else pd.DataFrame()
    )
    label_rows = []
    if not belief.empty:
        for label, part in belief.groupby("trust_label"):
            label_rows.append(
                {
                    "trust_label": label,
                    "n": len(part),
                    "n_seeds": part["seed"].nunique(),
                    "free_rider_flag": int(part["is_free_rider_label"].sum()),
                    "cooperative_flag": int(part["is_cooperative_label"].sum()),
                }
            )
    # Deterministic examples: at most one per motif/role/action/seed, sorted by
    # evidence ID. They are illustrative excerpts, not a prevalence sample.
    examples = []
    for motif, _pattern in MOTIFS.items():
        matches = corpus[corpus[f"motif_{motif}"]].sort_values("evidence_id")
        selected = matches.drop_duplicates(
            ["seed", "agent_group", "positive_contribution"], keep="first"
        ).head(18)
        for _, item in selected.iterrows():
            examples.append(
                {
                    "motif": motif,
                    "evidence_id": item["evidence_id"],
                    "seed": item["seed"],
                    "round_number": item["round_number"],
                    "agent_id": item["agent_id"],
                    "role": item["agent_group"],
                    "action": "positive" if item["positive_contribution"] == 1 else "zero",
                    "text": item["text"],
                    "selection_rule": "first evidence_id per seed-role-action stratum, capped at 18",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(label_rows), pd.DataFrame(examples)


def analyze(tables_dir: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = pd.read_csv(tables_dir / "agent_round.csv")
    round_df = pd.read_csv(tables_dir / "round_metrics.csv")
    tom = pd.read_csv(tables_dir / "tom_edges.csv")
    sanction = pd.read_csv(tables_dir / "sanction_edges.csv")
    reasoning = pd.read_csv(tables_dir / "reasoning_blocks.csv")
    sessions = pd.read_csv(tables_dir / "democracy_sessions.csv")
    proposals = pd.read_csv(tables_dir / "democracy_proposals.csv")
    votes = pd.read_csv(tables_dir / "democracy_votes.csv")
    agent = _prepare_agent_metrics(agent, tom, pd.read_csv(tables_dir / "belief_snapshots.csv"))
    # Add the pre-action cap used for eligible transition checks.
    agent["prior_cap"] = agent.groupby(["seed", "agent_id"])["decision_cap"].shift(1)
    run_metrics = _run_level_table(agent, round_df, tom, sanction)
    round_summary = _round_summary(round_df)
    role_summary = _role_summary(agent)
    public_goods_summary = _public_goods_summary(agent)
    primary = _primary_contrasts(run_metrics)
    events = _event_associations(agent, run_metrics)
    sanction_runs, sanction_edges = _sanction_summary(agent, sanction)
    dem_runs, dem_rules, vote_summary = _democracy_summary(sessions, proposals, votes)
    wealth = _wealth_summary(run_metrics)
    motif_summary, belief_labels, motif_examples = _qualitative_summary(reasoning, agent)
    reasoning_profile = _reasoning_profile(reasoning, agent)
    # Save all derived tables.
    outputs = {
        "run_metrics": run_metrics,
        "round_summary": round_summary,
        "role_summary": role_summary,
        "public_goods_summary": public_goods_summary,
        "primary_contrasts": primary,
        "event_associations": events,
        "sanction_runs": sanction_runs,
        "sanction_edges": sanction_edges,
        "democracy_runs": dem_runs,
        "democracy_rule_counts": dem_rules,
        "democracy_vote_summary": vote_summary,
        "wealth_summary": wealth,
        "motif_summary": motif_summary,
        "belief_label_summary": belief_labels,
        "motif_examples": motif_examples,
        "reasoning_profile": reasoning_profile,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)
    # A compact machine-readable claim registry with source artifact pointers.
    claim_registry = {
        "scope": {
            "model_alias": "qwen2.5-14b",
            "condition": "Full_scnldf_sh1_ldf1",
            "independent_runs": 9,
            "rounds_per_run": 30,
            "agents_per_round": 26,
            "agent_round_records": len(agent),
            "round_records": len(round_df),
        },
        "definitions": {
            "positive_contribution_share": "mean(contribution > 0)",
            "pre_decision_intensity": "contribution / max(0, floor(start-of-round wealth)); cap-zero records are structurally ineligible and excluded from the mean",
            "zero_contribution_share": "mean(contribution == 0), with an eligible-only companion measure",
            "early_window": EARLY_ROUNDS,
            "late_window": LATE_ROUNDS,
            "shock_timing": "actions at shock round precede shock; post windows begin at t+1; shock rounds coincide with democracy",
            "eligible_ldf_coverage": "developing-agent LDF payout / developing-agent gross damage",
            "system_ldf_coverage": "all-agent LDF payout / all-agent gross damage",
            "reputation": "peer-average same-model intent-action consistency score, not a moral or human reputation measure",
        },
        "run_metrics_file": str((output_dir / "run_metrics.csv").resolve()),
        "primary_contrasts_file": str((output_dir / "primary_contrasts.csv").resolve()),
        "event_associations_file": str((output_dir / "event_associations.csv").resolve()),
        "motif_summary_file": str((output_dir / "motif_summary.csv").resolve()),
        "reasoning_profile_file": str((output_dir / "reasoning_profile.csv").resolve()),
    }
    (output_dir / "claim_registry.json").write_text(
        json.dumps(claim_registry, indent=2), encoding="utf-8"
    )
    return {
        "run_metrics": run_metrics,
        "round_summary": round_summary,
        "role_summary": role_summary,
        "public_goods_summary": public_goods_summary,
        "primary_contrasts": primary,
        "event_associations": events,
        "sanction_runs": sanction_runs,
        "democracy_runs": dem_runs,
        "wealth_summary": wealth,
        "motif_summary": motif_summary,
        "motif_examples": motif_examples,
        "reasoning_profile": reasoning_profile,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/analysis")
    )
    args = parser.parse_args()
    result = analyze(args.tables_dir, args.output_dir)
    print(json.dumps({name: len(frame) for name, frame in result.items()}, indent=2))


if __name__ == "__main__":
    main()

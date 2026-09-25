"""Robustness and sensitivity checks for the Qwen nine-seed analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .statistics import paired_percentile_ci

RNG_SEED = 20260925


def _paired(values_before: pd.Series, values_after: pd.Series) -> dict[str, float]:
    frame = pd.DataFrame({"before": values_before, "after": values_after}).dropna()
    diff = frame["after"] - frame["before"]
    ci = paired_percentile_ci(frame["before"], frame["after"], n_boot=10_000, seed=RNG_SEED)
    return {
        "n": len(diff),
        "mean_before": float(frame["before"].mean()) if len(frame) else np.nan,
        "mean_after": float(frame["after"].mean()) if len(frame) else np.nan,
        "mean_change": float(diff.mean()) if len(diff) else np.nan,
        "ci_lower": ci["lower"],
        "ci_upper": ci["upper"],
        "n_positive": int((diff > 0).sum()),
        "n_negative": int((diff < 0).sum()),
    }


def _window_run_metric(
    agent: pd.DataFrame, rounds: list[int], metric: str, role: str | None = None
) -> pd.Series:
    part = agent[agent["round_number"].isin(rounds)]
    if role:
        part = part[part["agent_group"] == role]
    return part.groupby("seed")[metric].mean()


def run_robustness(
    tables_dir: Path, analysis_dir: Path, output_dir: Path
) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = pd.read_csv(tables_dir / "agent_round.csv")
    run = pd.read_csv(analysis_dir / "run_metrics.csv")
    outputs: dict[str, pd.DataFrame] = {}

    # Leave-one-seed-out estimates for the headline run-level outcomes.
    loo_rows = []
    headline = [
        "mean_positive_share",
        "mean_zero_share",
        "mean_intensity",
        "mean_gini_round",
        "early_gini",
        "late_gini",
        "final_group_mean_ratio",
        "auto_fit_agent_share",
        "fallback_agent_share",
        "sanction_target_hhi",
    ]
    for omitted in sorted(run.seed.unique()):
        keep = run[run.seed != omitted]
        for metric in headline:
            loo_rows.append(
                {
                    "omitted_seed": int(omitted),
                    "metric": metric,
                    "estimate_without_seed": float(keep[metric].mean()),
                    "full_estimate": float(run[metric].mean()),
                    "difference_from_full": float(keep[metric].mean() - run[metric].mean()),
                    "n_remaining": len(keep),
                }
            )
    outputs["leave_one_seed_out"] = pd.DataFrame(loo_rows)

    # Window sensitivity, including windows that contain a shock/democracy
    # session so the report can show the effect of that design choice.
    windows = [
        ("opening_1_4_vs_closing_27_30", [1, 2, 3, 4], [27, 28, 29, 30]),
        ("no_cold_start_2_4_vs_28_30", [2, 3, 4], [28, 29, 30]),
        ("opening_1_3_vs_closing_28_30", [1, 2, 3], [28, 29, 30]),
        ("broader_1_5_vs_26_30", [1, 2, 3, 4, 5], [26, 27, 28, 29, 30]),
    ]
    window_rows = []
    for name, early, late in windows:
        for metric, source, role in [
            ("positive_share", "positive_contribution", None),
            ("mean_intensity", "pre_decision_intensity", None),
            ("zero_share", "zero_contribution", None),
            ("positive_share", "positive_contribution", "developed"),
            ("mean_intensity", "pre_decision_intensity", "developed"),
            ("positive_share", "positive_contribution", "developing"),
            ("mean_intensity", "pre_decision_intensity", "developing"),
        ]:
            before = _window_run_metric(agent, early, source, role)
            after = _window_run_metric(agent, late, source, role)
            result = _paired(before, after)
            window_rows.append(
                {
                    "window": name,
                    "metric": metric,
                    "role": role or "all",
                    "early_rounds": str(early),
                    "late_rounds": str(late),
                    **result,
                }
            )
    outputs["window_sensitivity"] = pd.DataFrame(window_rows)

    # Denominator sensitivity: correct pre-decision intensity versus the raw
    # logged end-wealth intensity.  The latter is shown only as a measurement
    # robustness diagnostic, not as an alternative primary estimand.
    denom_rows = []
    for label, metric in [
        ("pre_decision_budget", "pre_decision_intensity"),
        ("end_wealth_proxy", "logged_intensity_using_end_wealth"),
    ]:
        early = agent[agent["round_number"].isin([1, 2, 3, 4])].groupby("seed")[metric].mean()
        late = agent[agent["round_number"].isin([27, 28, 29, 30])].groupby("seed")[metric].mean()
        denom_rows.append({"denominator": label, **_paired(early, late)})
    outputs["denominator_sensitivity"] = pd.DataFrame(denom_rows)

    # Parser sensitivity: compare all SI records with records whose Stage-2
    # parser metadata has no auto-fit, fallback, or semantic retry.
    si = agent[agent["institution_choice"] == "SI"].copy()
    clean_mask = (
        (si["punishment_auto_fit"] == 0)
        & (si["punishment_fallback"] == 0)
        & (si["punishment_semantic_retry"] == 0)
    )
    clean = si[clean_mask]
    parser_rows = []
    for seed in sorted(si.seed.unique()):
        all_part = si[si.seed == seed]
        clean_part = clean[clean.seed == seed]
        parser_rows.append(
            {
                "seed": int(seed),
                "all_si_records": len(all_part),
                "clean_si_records": len(clean_part),
                "clean_record_share": len(clean_part) / len(all_part),
                "all_final_punishment": float(all_part["assigned_punishment_total"].sum()),
                "clean_final_punishment": float(clean_part["assigned_punishment_total"].sum()),
                "all_received_punishment_effect": float(
                    all_part["received_punishments_effect"].sum()
                ),
                "clean_received_punishment_effect": float(
                    clean_part["received_punishments_effect"].sum()
                ),
                "all_sender_participation": float(
                    (
                        (all_part["assigned_punishment_count"] > 0)
                        | (all_part["assigned_reward_count"] > 0)
                    ).mean()
                ),
                "clean_sender_participation": float(
                    (
                        (clean_part["assigned_punishment_count"] > 0)
                        | (clean_part["assigned_reward_count"] > 0)
                    ).mean()
                ),
            }
        )
    outputs["parser_sensitivity"] = pd.DataFrame(parser_rows)

    # ToM event threshold sensitivity, using within-round-role cells and the
    # same run-level aggregation as the main event table.
    # Reconstruct incoming score summaries from the stored ToM edge table.
    tom = pd.read_csv(tables_dir / "tom_edges.csv")
    target = (
        tom.groupby(["seed", "action_round", "target"])["score"]
        .agg(["count", "mean", "min"])
        .reset_index()
        .rename(columns={"action_round": "round_number", "target": "agent_id"})
    )
    low = (
        tom.assign(low=tom["score"] <= 7)
        .groupby(["seed", "action_round", "target"], as_index=False)["low"]
        .sum()
        .rename(columns={"action_round": "round_number", "target": "agent_id", "low": "low_count"})
    )
    target = target.merge(low, on=["seed", "round_number", "agent_id"], how="left")
    a = agent.merge(target, on=["seed", "round_number", "agent_id"], how="left")
    event_rows = []
    for threshold in [3, 4, 5, 6, 7]:
        a["event"] = (a["mean"] < threshold).astype(int)
        for role in ["all", "developed", "developing"]:
            run_values = []
            for _seed, part in a.groupby("seed"):
                if role != "all":
                    part = part[part["agent_group"] == role]
                part = part[(part["decision_cap"] > 0) & part["mean"].notna()]
                diffs = []
                for _, cell in part.groupby(["round_number", "agent_group"]):
                    ex = cell[cell.event == 1]
                    un = cell[cell.event == 0]
                    if len(ex) and len(un):
                        diffs.append(
                            ex["pre_decision_intensity"].mean()
                            - un["pre_decision_intensity"].mean()
                        )
                run_values.append(np.mean(diffs) if diffs else np.nan)
            vals = pd.Series(run_values).dropna()
            event_rows.append(
                {
                    "threshold": threshold,
                    "role": role,
                    "n_runs": len(vals),
                    "mean_within_cell_difference": float(vals.mean()) if len(vals) else np.nan,
                    "n_positive_runs": int((vals > 0).sum()),
                    "n_negative_runs": int((vals < 0).sum()),
                }
            )
    outputs["event_threshold_sensitivity"] = pd.DataFrame(event_rows)

    for name, frame in outputs.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)
    (output_dir / "robustness_summary.json").write_text(
        json.dumps(
            {
                "n_runs": int(run.seed.nunique()),
                "headline_metrics_loo": len(outputs["leave_one_seed_out"]),
                "window_contrasts": len(outputs["window_sensitivity"]),
                "parser_clean_definition": "SI agent-round with punishment_auto_fit=0, punishment_fallback=0, punishment_semantic_retry=0",
                "event_threshold_definition": "incoming ToM peer-average consistency mean below threshold; the edge-count alternative is reported separately in the main ToM table",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    parser.add_argument(
        "--analysis-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/analysis")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/robustness")
    )
    args = parser.parse_args()
    outputs = run_robustness(args.tables_dir, args.analysis_dir, args.output_dir)
    print(json.dumps({name: len(frame) for name, frame in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()

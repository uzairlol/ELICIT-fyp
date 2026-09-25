"""Freeze a machine-readable claim ledger for the final Qwen report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _f(value: Any) -> float | None:
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _row(frame: pd.DataFrame, **conditions: Any) -> dict[str, Any] | None:
    part = frame
    for key, value in conditions.items():
        part = part[part[key] == value]
    return part.iloc[0].to_dict() if len(part) else None


def _clean_dict(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_dict(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _f(value)
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def build_claims(
    tables_dir: Path, analysis_dir: Path, robustness_dir: Path, persistence_dir: Path
) -> dict[str, Any]:
    run = pd.read_csv(analysis_dir / "run_metrics.csv")
    primary = pd.read_csv(analysis_dir / "primary_contrasts.csv")
    rounds = pd.read_csv(tables_dir / "round_metrics.csv")
    public = pd.read_csv(analysis_dir / "public_goods_summary.csv")
    wealth = pd.read_csv(analysis_dir / "wealth_summary.csv")
    sanctions = pd.read_csv(analysis_dir / "sanction_runs.csv")
    democracy = pd.read_csv(analysis_dir / "democracy_runs.csv")
    rules = pd.read_csv(analysis_dir / "democracy_rule_counts.csv")
    events = pd.read_csv(analysis_dir / "event_associations.csv")
    motifs = pd.read_csv(analysis_dir / "motif_summary.csv")
    profile = pd.read_csv(analysis_dir / "reasoning_profile.csv")
    belief = pd.read_csv(analysis_dir / "belief_label_summary.csv")
    reasoning_profile = pd.read_csv(analysis_dir / "reasoning_profile.csv")
    transitions = pd.read_csv(persistence_dir / "transition_summary.csv")
    window = pd.read_csv(robustness_dir / "window_sensitivity.csv")
    loo = pd.read_csv(robustness_dir / "leave_one_seed_out.csv")
    parser = pd.read_csv(robustness_dir / "parser_sensitivity.csv")

    trajectory = {}
    for rn in [1, 2, 3, 4, 5, 6, 8, 10, 11, 15, 20, 25, 27, 30]:
        part = rounds[rounds.round_number == rn]
        trajectory[str(rn)] = {
            metric: {
                "mean": _f(part[metric].mean()),
                "sd": _f(part[metric].std(ddof=1)),
                "min": _f(part[metric].min()),
                "max": _f(part[metric].max()),
            }
            for metric in [
                "positive_share",
                "zero_share",
                "mean_pre_decision_intensity",
                "mean_contribution",
                "gini_wealth",
                "ldf_pool_end",
            ]
        }

    headline = {
        "overall_positive_share": _f(run.mean_positive_share.mean()),
        "overall_eligible_positive_share": _f(run.mean_eligible_positive_share.mean()),
        "overall_zero_share": _f(run.mean_zero_share.mean()),
        "overall_pre_decision_intensity": _f(run.mean_intensity.mean()),
        "early_positive_share": _f(run.early_positive_share.mean()),
        "late_positive_share": _f(run.late_positive_share.mean()),
        "early_intensity": _f(run.early_mean_intensity.mean()),
        "late_intensity": _f(run.late_mean_intensity.mean()),
        "early_gini": _f(run.early_gini.mean()),
        "late_gini": _f(run.late_gini.mean()),
        "mean_round_gini": _f(run.mean_gini_round.mean()),
        "p_positive_after_positive": _f(run.p_positive_after_positive.mean()),
        "p_positive_after_zero": _f(run.p_positive_after_zero.mean()),
        "lag_intensity_correlation": _f(run.lag_intensity_corr.mean()),
    }
    for label, col in [
        ("early_positive_share", "early_positive_share"),
        ("late_positive_share", "late_positive_share"),
        ("early_intensity", "early_mean_intensity"),
        ("late_intensity", "late_mean_intensity"),
        ("early_gini", "early_gini"),
        ("late_gini", "late_gini"),
        ("mean_round_gini", "mean_gini_round"),
        ("p_positive_after_positive", "p_positive_after_positive"),
        ("p_positive_after_zero", "p_positive_after_zero"),
        ("lag_intensity_correlation", "lag_intensity_corr"),
    ]:
        headline[label + "_range"] = [_f(run[col].min()), _f(run[col].max())]

    contrasts = {}
    for _, row in primary.iterrows():
        contrasts[row["contrast"] + "|" + row["role"]] = {
            key: _f(row[key]) if key not in {"contrast", "role"} else row[key]
            for key in [
                "mean_before",
                "mean_after",
                "mean_change",
                "ci_lower",
                "ci_upper",
                "exact_sign_flip_p",
                "n_positive_change",
                "n_negative_change",
            ]
        }

    role_summary = {}
    # Pull role-level estimates from the role summary artifact.
    role_table = pd.read_csv(analysis_dir / "role_summary.csv")
    for role in ["developed", "developing"]:
        role_summary[role] = {}
        for outcome in [
            "positive_share",
            "pre_decision_intensity",
            "contribution",
            "positive_share_early",
            "positive_share_late",
        ]:
            item = role_table[(role_table.role == role) & (role_table.outcome == outcome)]
            if len(item):
                row = item.iloc[0]
                role_summary[role][outcome] = {
                    k: _f(row[k]) for k in ["mean", "ci_lower", "ci_upper", "sd", "min", "max"]
                }

    public_goods = {}
    for _, row in public.iterrows():
        public_goods[row.role + "|" + row.metric] = {
            k: _f(row[k]) for k in ["mean", "ci_lower", "ci_upper", "sd", "min", "max"]
        }

    ldf = {
        "deposits_total_mean": _f(run.total_ldf_deposit.mean()),
        "deposits_total_range": [_f(run.total_ldf_deposit.min()), _f(run.total_ldf_deposit.max())],
        "payouts_total": _f(run.total_ldf_payout.mean()),
        "final_pool_mean": _f(run.final_ldf_pool.mean()),
        "final_pool_range": [_f(run.final_ldf_pool.min()), _f(run.final_ldf_pool.max())],
        "eligible_coverage": _f(run.eligible_coverage.mean()),
        "system_coverage": _f(run.system_coverage.mean()),
        "payout_to_deposit_range": [
            _f(run.payout_to_deposit.min()),
            _f(run.payout_to_deposit.max()),
        ],
        "si_deposit_share_of_total_range": [
            _f((run.si_ldf_deposit / run.total_ldf_deposit).min()),
            _f((run.si_ldf_deposit / run.total_ldf_deposit).max()),
        ],
    }

    wealth_claims = {}
    for _, row in wealth.iterrows():
        wealth_claims[row.metric] = {
            k: _f(row[k]) for k in ["mean", "ci_lower", "ci_upper", "sd", "min", "max"]
        }

    sanction_claims = {
        "auto_fit_share_mean": _f(sanctions.auto_fit_share.mean()),
        "auto_fit_share_range": [
            _f(sanctions.auto_fit_share.min()),
            _f(sanctions.auto_fit_share.max()),
        ],
        "fallback_share_mean": _f(sanctions.fallback_share.mean()),
        "fallback_share_range": [
            _f(sanctions.fallback_share.min()),
            _f(sanctions.fallback_share.max()),
        ],
        "sender_participation_mean": _f(sanctions.sender_participation_share.mean())
        if "sender_participation_share" in sanctions
        else _f(sanctions.final_to_raw_punishment_ratio.mean()),
        "final_to_raw_punishment_ratio_range": [
            _f(sanctions.final_to_raw_punishment_ratio.min()),
            _f(sanctions.final_to_raw_punishment_ratio.max()),
        ],
        "target_hhi_range": [_f(run.sanction_target_hhi.min()), _f(run.sanction_target_hhi.max())],
        "clean_record_share_range": [
            _f(parser.clean_record_share.min()),
            _f(parser.clean_record_share.max()),
        ],
    }
    # The run-level sanction table uses sanction_participant_share.
    sanction_claims["sender_participation_mean"] = _f(sanctions.sender_participation_share.mean())

    democracy_claims = {
        "sessions": int(democracy.sessions.sum()),
        "valid_vote_share": _f(democracy.valid_vote_share.mean()),
        "mean_plurality_share": _f(democracy.mean_plurality_share.mean()),
        "applied_sessions": int(democracy.applied_sessions.sum()),
        "post_final_shock_applied": int(democracy.post_final_shock_applied.sum()),
        "winner_rule_counts": rules.groupby("rule_family")["winner_sessions"].sum().to_dict(),
        "winner_direction_counts": rules.groupby("direction")["winner_sessions"].sum().to_dict(),
    }

    event_claims = []
    for _, row in events.iterrows():
        if row.outcome == "intensity" and row.n_runs > 0:
            event_claims.append(
                {
                    "event": row.event,
                    "role": row.role,
                    "mean_difference": _f(row.mean_difference),
                    "ci_lower": _f(row.ci_lower),
                    "ci_upper": _f(row.ci_upper),
                    "n_runs": int(row.n_runs),
                    "n_cells": int(row.n_cells_total),
                    "n_exposed": int(row.n_exposed_total),
                    "n_unexposed": int(row.n_unexposed_total),
                }
            )

    motif_claims = []
    for _, row in motifs[(motifs.role_or_action == "all")].iterrows():
        motif_claims.append(
            {
                "motif": row.motif,
                "prevalence": _f(row.mean_prevalence),
                "ci_lower": _f(row.ci_lower),
                "ci_upper": _f(row.ci_upper),
                "n_documents": int(row.n_documents),
                "n_positive_documents": int(row.n_positive_documents),
            }
        )

    belief_total = int(belief.n.sum()) if len(belief) else 0
    belief_claims = {
        "n_sparse_belief_edges": belief_total,
        "free_rider_label_count": int(belief.free_rider_flag.sum()) if len(belief) else 0,
        "cooperative_label_count": int(belief.cooperative_flag.sum()) if len(belief) else 0,
        "top_labels": belief.sort_values("n", ascending=False)
        .head(12)[["trust_label", "n", "free_rider_flag", "cooperative_flag"]]
        .to_dict("records"),
    }

    reasoning_claims = {
        str(row.field) + "|" + str(row.stratum): {
            key: _f(row[key])
            for key in [
                "n_documents",
                "n_unique_texts",
                "unique_text_share",
                "most_common_text_share",
                "mean_words",
                "median_words",
                "p90_words",
                "mean_characters",
                "mean_words_ci_lower",
                "mean_words_ci_upper",
            ]
        }
        for _, row in profile.iterrows()
    }

    reasoning_claims = []
    for _, row in reasoning_profile.iterrows():
        reasoning_claims.append({key: _f(row[key]) if key not in {"field", "stratum"} else row[key] for key in ["field", "stratum", "n_documents", "n_unique_texts", "unique_text_share", "most_common_text_count", "most_common_text_share", "mean_words", "sd_words", "median_words", "p90_words"]})

    transition_claims = [
        {
            k: _f(row[k]) if k not in {"transition"} else row[k]
            for k in [
                "transition",
                "n_transition_observations",
                "pooled_positive_rate",
                "mean_run_level_rate",
                "ci_lower",
                "ci_upper",
                "n_seeds_all_positive",
                "n_seeds_not_all_positive",
            ]
        }
        for _, row in transitions.iterrows()
    ]

    robustness_claims = {
        "window_rows": len(window),
        "primary_window_changes": window[window.role == "all"][
            ["window", "metric", "mean_change", "ci_lower", "ci_upper"]
        ].to_dict("records"),
        "loo_metric_ranges": loo.groupby("metric")["estimate_without_seed"]
        .agg(["min", "max"])
        .reset_index()
        .to_dict("records"),
        "parser_clean_definition": "SI agent-rounds with no auto-fit, fallback, or semantic retry",
    }

    claims = {
        "scope": {
            "n_runs": 9,
            "n_rounds": 270,
            "n_agents_per_round": 26,
            "n_agent_rounds": 7020,
            "model_alias": "qwen2.5-14b",
            "condition": "Full_scnldf_sh1_ldf1",
            "shock_rounds": [5, 10],
            "democracy_rounds": [5, 10, 15, 20, 25, 30],
        },
        "headline": headline,
        "trajectory": trajectory,
        "primary_contrasts": contrasts,
        "roles": role_summary,
        "public_goods": public_goods,
        "ldf": ldf,
        "wealth": wealth_claims,
        "sanctions": sanction_claims,
        "democracy": democracy_claims,
        "events": event_claims,
        "motifs": motif_claims,
        "reasoning": reasoning_claims,
        "beliefs": belief_claims,
        "reasoning_profile": reasoning_claims,
        "transitions": transition_claims,
        "robustness": robustness_claims,
        "source_artifacts": {
            "raw": "results/simulation_qwen2.5-14b_Full_scnldf_sh1_ldf1_seed{1..9}_26agents_30rounds_*.json",
            "audit": "analysis_outputs/qwen2_5_14b_9seed/audit/data_quality_checks.csv",
            "agent_round_table": "analysis_outputs/qwen2_5_14b_9seed/tables/agent_round.csv",
            "round_table": "analysis_outputs/qwen2_5_14b_9seed/tables/round_metrics.csv",
            "run_metrics": "analysis_outputs/qwen2_5_14b_9seed/analysis/run_metrics.csv",
            "primary_contrasts": "analysis_outputs/qwen2_5_14b_9seed/analysis/primary_contrasts.csv",
            "figures": "analysis_outputs/qwen2_5_14b_9seed/figures/",
        },
    }
    return _clean_dict(claims)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    parser.add_argument(
        "--analysis-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/analysis")
    )
    parser.add_argument(
        "--robustness-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/robustness")
    )
    parser.add_argument(
        "--persistence-dir",
        type=Path,
        default=Path("analysis_outputs/qwen2_5_14b_9seed/persistence"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/key_claims.json")
    )
    args = parser.parse_args()
    claims = build_claims(
        args.tables_dir, args.analysis_dir, args.robustness_dir, args.persistence_dir
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(claims, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

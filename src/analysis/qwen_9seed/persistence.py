"""Persistence and transition diagnostics for repeated Qwen decisions."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .statistics import percentile_ci


def _boot(values, seed):
    return percentile_ci(values, np.mean, n_boot=10_000, seed=seed)


def build(tables_dir: Path, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    agent = pd.read_csv(tables_dir / "agent_round.csv")
    agent = agent.sort_values(["seed", "agent_id", "round_number"]).copy()
    agent["prior_cap"] = agent.groupby(["seed", "agent_id"])["decision_cap"].shift(1)
    agent["prior_positive"] = agent.groupby(["seed", "agent_id"])["positive_contribution"].shift(1)
    valid = agent[
        (agent["decision_cap"] > 0) & (agent["prior_cap"] > 0) & agent["prior_positive"].notna()
    ].copy()
    valid["transition"] = np.where(
        valid["prior_positive"] == 1, "positive_after_positive", "positive_after_zero"
    )
    rows = []
    for transition, part in valid.groupby("transition"):
        per_run = part.groupby("seed")["positive_contribution"].mean()
        ci = _boot(per_run, 20260925 + len(rows))
        rows.append(
            {
                "transition": transition,
                "n_transition_observations": len(part),
                "n_runs": part.seed.nunique(),
                "pooled_positive_rate": float(part.positive_contribution.mean()),
                "mean_run_level_rate": float(per_run.mean()),
                "ci_lower": ci["lower"],
                "ci_upper": ci["upper"],
                "n_seeds_all_positive": int((per_run == 1).sum()),
                "n_seeds_not_all_positive": int((per_run < 1).sum()),
            }
        )
    transitions = pd.DataFrame(rows)

    round_positive = agent.groupby(["seed", "round_number"])["positive_contribution"].mean()
    episode_rows = []
    for (seed, aid), part in agent.groupby(["seed", "agent_id"]):
        part = part.sort_values("round_number")
        zero = part["positive_contribution"].eq(0).to_numpy()
        starts = np.flatnonzero(zero & np.r_[True, ~zero[:-1]])
        ends = np.flatnonzero(zero & np.r_[~zero[1:], True])
        for start, end in zip(starts, ends, strict=True):
            start_round = int(part.iloc[start]["round_number"])
            episode_rows.append(
                {
                    "seed": int(seed),
                    "agent_id": int(aid),
                    "role": part.iloc[0]["agent_group"],
                    "start_round": start_round,
                    "end_round": int(part.iloc[end]["round_number"]),
                    "duration_rounds": int(end - start + 1),
                    "has_positive_peer_action": bool(
                        round_positive.get((seed, start_round), 0.0) > 0
                    ),
                }
            )
    episodes = pd.DataFrame(episode_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    transitions.to_csv(output_dir / "transition_summary.csv", index=False)
    episodes.to_csv(output_dir / "zero_episodes.csv", index=False)
    if not episodes.empty:
        summary = (
            episodes.groupby("seed")
            .agg(
                zero_episodes=("duration_rounds", "size"),
                mean_zero_episode_length=("duration_rounds", "mean"),
                max_zero_episode_length=("duration_rounds", "max"),
                zero_episode_total_rounds=("duration_rounds", "sum"),
            )
            .reset_index()
        )
    else:
        summary = pd.DataFrame(
            columns=[
                "seed",
                "zero_episodes",
                "mean_zero_episode_length",
                "max_zero_episode_length",
                "zero_episode_total_rounds",
            ]
        )
    summary.to_csv(output_dir / "zero_episode_summary.csv", index=False)
    return transitions, episodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/persistence")
    )
    args = parser.parse_args()
    transitions, episodes = build(args.tables_dir, args.output_dir)
    print({"transition_rows": len(transitions), "zero_episodes": len(episodes)})


if __name__ == "__main__":
    main()

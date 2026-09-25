"""Publication-oriented figures for the Qwen nine-seed analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SEEDS = list(range(1, 10))
RUN_COLORS = plt.cm.tab10(np.linspace(0, 1, 9))
SHOCKS = [5, 10]


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _boot_band(
    values: np.ndarray, n_boot: int = 5000, seed: int = 20260925
) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    return float(values.mean()), float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def _shock_marks(ax: plt.Axes) -> None:
    for shock in SHOCKS:
        ax.axvline(shock, color="#b44b4b", linestyle="--", linewidth=1, alpha=0.75)
    ax.text(
        5.15,
        0.97,
        "shock + vote",
        transform=ax.get_xaxis_transform(),
        rotation=90,
        va="top",
        ha="left",
        fontsize=8,
        color="#8b2e2e",
    )
    ax.text(
        10.15,
        0.97,
        "shock + vote",
        transform=ax.get_xaxis_transform(),
        rotation=90,
        va="top",
        ha="left",
        fontsize=8,
        color="#8b2e2e",
    )


def cooperation_figure(rounds: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    metrics = [
        ("positive_share", "Positive-contribution share"),
        ("mean_pre_decision_intensity", "Mean pre-decision intensity"),
    ]
    for ax, (metric, label) in zip(axes, metrics, strict=True):
        for color, seed in zip(RUN_COLORS, SEEDS, strict=True):
            part = rounds[rounds.seed == seed].sort_values("round_number")
            ax.plot(part.round_number, part[metric], color=color, alpha=0.28, linewidth=0.8)
        by_round = rounds.groupby("round_number")[metric]
        means = by_round.mean().reindex(range(1, 31))
        los, his = [], []
        for rn, part in rounds.groupby("round_number"):
            _, lo, hi = _boot_band(part[metric].to_numpy(), seed=20260925 + rn)
            los.append(lo)
            his.append(hi)
        ax.plot(
            means.index, means.values, color="#111111", linewidth=2.4, label="Mean across 9 runs"
        )
        ax.fill_between(
            means.index, los, his, color="#111111", alpha=0.12, label="Run bootstrap 95% interval"
        )
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.2)
        _shock_marks(ax)
    axes[0].legend(frameon=False, loc="upper left", ncol=2)
    axes[1].set_xlabel("Round")
    axes[1].set_xticks(range(1, 31))
    fig.suptitle(
        "Qwen2.5-14B Full-LDF trajectories: participation rises while intensity declines",
        fontsize=14,
        y=0.995,
    )
    fig.tight_layout()
    _save(fig, out / "fig01_cooperation_trajectories.png")


def role_figure(rounds: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    panels = [
        (
            "role_positive_share_developed",
            "role_positive_share_developing",
            "Positive-contribution share",
            "Developed / SI",
            "Developing / SFI",
        ),
        (
            "role_mean_intensity_developed",
            "role_mean_intensity_developing",
            "Mean pre-decision intensity",
            "Developed / SI",
            "Developing / SFI",
        ),
    ]
    for row, (dev, sfi, ylabel, lab1, lab2) in enumerate(panels):
        for col, (metric, label, color) in enumerate(
            [(dev, lab1, "#1f77b4"), (sfi, lab2, "#d95f02")]
        ):
            ax = axes[row, col]
            for color_run, seed in zip(RUN_COLORS, SEEDS, strict=True):
                part = rounds[rounds.seed == seed].sort_values("round_number")
                ax.plot(part.round_number, part[metric], color=color_run, alpha=0.18, linewidth=0.7)
            by = rounds.groupby("round_number")[metric].mean().reindex(range(1, 31))
            los, his = [], []
            for rn, part in rounds.groupby("round_number"):
                _, lo, hi = _boot_band(part[metric].to_numpy(), seed=5000 + rn)
                los.append(lo)
                his.append(hi)
            ax.plot(by.index, by.values, color=color, linewidth=2.3, label="Mean")
            ax.fill_between(by.index, los, his, color=color, alpha=0.13)
            ax.set_title(label)
            ax.set_ylabel(ylabel)
            ax.grid(axis="y", alpha=0.2)
            _shock_marks(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Round")
        ax.set_xticks(range(1, 31))
    axes[0, 0].legend(frameon=False, loc="upper left")
    fig.suptitle(
        "Assigned-role trajectories are descriptive: role, wealth, and institution are confounded",
        fontsize=14,
        y=0.995,
    )
    fig.tight_layout()
    _save(fig, out / "fig02_role_trajectories.png")


def ldf_figure(rounds: pd.DataFrame, runs: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    shocks = rounds[rounds.is_shock_round].copy()
    x = np.arange(len(SEEDS))
    width = 0.36
    axes[0].bar(
        x - width / 2,
        shocks[shocks.round_number == 5].system_coverage,
        width,
        label="System-wide",
        color="#756bb1",
    )
    axes[0].bar(
        x + width / 2,
        shocks[shocks.round_number == 5].eligible_coverage,
        width,
        label="Developing-only",
        color="#31a354",
    )
    axes[0].set_xticks(x, SEEDS)
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("Payout / damage")
    axes[0].set_title("Coverage at the first shock")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    for color, seed in zip(RUN_COLORS, SEEDS, strict=True):
        part = rounds[rounds.seed == seed].sort_values("round_number")
        axes[1].plot(part.round_number, part.ldf_pool_end, color=color, alpha=0.35, linewidth=0.8)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("LDF pool (model units, log scale)")
    axes[1].set_title("Persistent reserve after shocks")
    axes[1].grid(alpha=0.2)
    _shock_marks(axes[1])

    axes[2].scatter(
        runs.total_ldf_deposit,
        runs.final_ldf_pool,
        c=RUN_COLORS,
        s=55,
        edgecolor="white",
        linewidth=0.6,
    )
    for _, row in runs.iterrows():
        axes[2].annotate(
            str(int(row.seed)),
            (row.total_ldf_deposit, row.final_ldf_pool),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=8,
        )
    lim = max(runs.total_ldf_deposit.max(), runs.final_ldf_pool.max()) * 1.08
    axes[2].plot([0, lim], [0, lim], color="#777777", linestyle="--", linewidth=1)
    axes[2].set_xlim(0, lim)
    axes[2].set_ylim(0, lim)
    axes[2].set_xlabel("Cumulative deposits")
    axes[2].set_ylabel("Terminal pool")
    axes[2].set_title("Deposits accumulate; payouts are small")
    axes[2].grid(alpha=0.2)
    fig.suptitle(
        "Loss and Damage Fund accounting: high eligible coverage is mechanically capped",
        fontsize=14,
        y=1.02,
    )
    fig.tight_layout()
    _save(fig, out / "fig03_ldf_accounting.png")


def wealth_figure(rounds: pd.DataFrame, runs: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for color, seed in zip(RUN_COLORS, SEEDS, strict=True):
        part = rounds[rounds.seed == seed].sort_values("round_number")
        axes[0].plot(part.round_number, part.gini_wealth, color=color, alpha=0.35, linewidth=0.8)
    by = rounds.groupby("round_number").gini_wealth.mean().reindex(range(1, 31))
    axes[0].plot(by.index, by.values, color="#111111", linewidth=2.3)
    axes[0].set_xlabel("Round")
    axes[0].set_ylabel("Gini of end-round wealth")
    axes[0].set_title("Inequality falls from a high cold-start baseline")
    axes[0].grid(axis="y", alpha=0.2)
    _shock_marks(axes[0])

    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(runs)))
    axes[1].bar(runs.seed, runs.final_group_mean_ratio, color=colors)
    axes[1].axhline(
        runs.initial_group_mean_ratio.iloc[0],
        color="#b44b4b",
        linestyle="--",
        label="Initial ratio",
    )
    axes[1].set_xlabel("Seed")
    axes[1].set_ylabel("Developed / developing mean wealth")
    axes[1].set_title("Terminal group ratio remains seed-dependent")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="y", alpha=0.2)

    for _, row in runs.iterrows():
        axes[2].scatter(
            row.developed_wealth_ratio_to_initial,
            row.developing_wealth_ratio_to_initial,
            color=RUN_COLORS[int(row.seed) - 1],
            s=55,
            edgecolor="white",
        )
        axes[2].annotate(
            str(int(row.seed)),
            (row.developed_wealth_ratio_to_initial, row.developing_wealth_ratio_to_initial),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=8,
        )
    axes[2].plot(
        [
            0,
            max(
                runs.developed_wealth_ratio_to_initial.max(),
                runs.developing_wealth_ratio_to_initial.max(),
            )
            + 0.5,
        ]
        * 2,
        [
            0,
            max(
                runs.developed_wealth_ratio_to_initial.max(),
                runs.developing_wealth_ratio_to_initial.max(),
            )
            + 0.5,
        ]
        * 2,
        color="#777777",
        linestyle="--",
    )
    axes[2].set_xlabel("Developed mean wealth / initial")
    axes[2].set_ylabel("Developing mean wealth / initial")
    axes[2].set_title("Relative group outcomes")
    axes[2].grid(alpha=0.2)
    fig.suptitle(
        "Wealth dynamics: convergence in aggregate Gini does not imply equal group outcomes",
        fontsize=14,
        y=1.02,
    )
    fig.tight_layout()
    _save(fig, out / "fig04_wealth_distribution.png")


def event_figure(events: pd.DataFrame, out: Path) -> None:
    part = events[(events.outcome == "intensity") & (events.n_runs > 0)].copy()
    labels = []
    for _, row in part.iterrows():
        labels.append(f"{row.event.split('(')[0].strip()}\n{row.role}")
    y = np.arange(len(part))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = [
        "#756bb1" if "developed" in label else "#d95f02" if "developing" in label else "#444444"
        for label in part.role
    ]
    means = part.mean_difference.to_numpy(dtype=float)
    center_for_missing = part.mean_difference
    lower = means - part.ci_lower.fillna(center_for_missing).to_numpy(dtype=float)
    upper = part.ci_upper.fillna(center_for_missing).to_numpy(dtype=float) - means
    for idx, (mean, lo, hi, color) in enumerate(zip(means, lower, upper, colors, strict=True)):
        if np.isfinite(mean):
            ax.errorbar(
                mean,
                y[idx],
                xerr=[[max(0, mean - lo)], [max(0, hi - mean)]],
                fmt="o",
                color=color,
                ecolor=color,
                capsize=3,
                markersize=5,
            )
    ax.axvline(0, color="#111111", linewidth=1)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Within-cell exposed minus unexposed pre-decision intensity")
    ax.set_title("Prospective consistency/gossip associations are heterogeneous and non-causal")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    _save(fig, out / "fig05_event_associations.png")


def governance_figure(sessions: pd.DataFrame, out: Path) -> None:
    sessions = sessions.sort_values(["seed", "round_number"])
    family_map = {
        "subsidy": "#31a354",
        "punishment": "#de2d26",
        "reward": "#3182bd",
        "ldf": "#756bb1",
        "other": "#969696",
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    # Build an RGB image from the family palette.
    rgb = np.zeros((9, 6, 3))
    palette = {k: matplotlib.colors.to_rgb(v) for k, v in family_map.items()}
    for i, seed in enumerate(SEEDS):
        for j, rn in enumerate([5, 10, 15, 20, 25, 30]):
            row = sessions[(sessions.seed == seed) & (sessions.round_number == rn)].iloc[0]
            family = row.winning_rule_family if pd.notna(row.winning_rule_family) else "other"
            rgb[i, j] = palette.get(family, palette["other"])
    ax.imshow(rgb, aspect="auto")
    for i, seed in enumerate(SEEDS):
        for j, rn in enumerate([5, 10, 15, 20, 25, 30]):
            rule = (
                str(
                    sessions[(sessions.seed == seed) & (sessions.round_number == rn)]
                    .iloc[0]
                    .winning_rule
                )
                .replace("SUBSIDY_", "S_")
                .replace("PUNISHMENT_", "P_")
                .replace("REWARD_", "R_")
                .replace("LDF_", "L_")
            )
            val = (
                sessions[(sessions.seed == seed) & (sessions.round_number == rn)]
                .iloc[0]
                .winning_new_value
            )
            ax.text(
                j,
                i,
                f"r{rn}\n{rule}\n{val:g}",
                ha="center",
                va="center",
                fontsize=7,
                color="white"
                if family_map.get(
                    str(
                        sessions[(sessions.seed == seed) & (sessions.round_number == rn)]
                        .iloc[0]
                        .winning_rule_family
                    ),
                    "#969696",
                )
                not in ["#31a354"]
                else "#111111",
            )
    ax.set_xticks(range(6), ["r5", "r10", "r15", "r20", "r25", "r30"])
    ax.set_yticks(range(9), SEEDS)
    ax.set_xlabel("Constitutional session (rule effective next round)")
    ax.set_ylabel("Seed")
    ax.set_title("Oracle-guided plurality rule changes: heterogeneous, often post-shock")
    fig.tight_layout()
    _save(fig, out / "fig06_governance_rules.png")


def sanction_figure(sanctions: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    x = np.arange(len(sanctions))
    axes[0].bar(
        x - 0.18,
        sanctions.auto_fit_share * 100,
        width=0.36,
        label="Auto-fit to budget",
        color="#fd8d3c",
    )
    axes[0].bar(
        x + 0.18,
        sanctions.fallback_share * 100,
        width=0.36,
        label="Final fallback",
        color="#e31a1c",
    )
    axes[0].set_xticks(x, sanctions.seed)
    axes[0].set_ylabel("Share of SI agent-rounds")
    axes[0].set_title("Parser/safety-net intervention")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)
    axes[1].scatter(
        sanctions.raw_punishment_tokens,
        sanctions.final_punishment_tokens,
        color=RUN_COLORS,
        s=55,
        edgecolor="white",
    )
    for _, row in sanctions.iterrows():
        axes[1].annotate(
            str(int(row.seed)),
            (row.raw_punishment_tokens, row.final_punishment_tokens),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=8,
        )
    lim = max(sanctions.raw_punishment_tokens.max(), sanctions.final_punishment_tokens.max()) * 1.08
    axes[1].plot([0, lim], [0, lim], color="#777777", linestyle="--")
    axes[1].set_xlim(0, lim)
    axes[1].set_ylim(0, lim)
    axes[1].set_xlabel("Raw requested punishment tokens")
    axes[1].set_ylabel("Final applied punishment tokens")
    axes[1].set_title("Enforcement after validation/rescaling")
    axes[1].grid(alpha=0.2)
    fig.suptitle(
        "Stage-2 outputs are model-mediated by parser and safety-net intervention",
        fontsize=14,
        y=1.02,
    )
    fig.tight_layout()
    _save(fig, out / "fig07_parser_sanctions.png")


def motif_figure(motifs: pd.DataFrame, out: Path) -> None:
    part = motifs[
        motifs.role_or_action.isin(["all", "developed", "developing", "zero_action"])
    ].copy()
    motif_order = list(part.motif.drop_duplicates())
    fig, ax = plt.subplots(figsize=(12, 10))
    positions = []
    labels = []
    colors = []
    pos = 0
    for motif in motif_order:
        for j, stratum in enumerate(["all", "developed", "developing", "zero_action"]):
            row = part[(part.motif == motif) & (part.role_or_action == stratum)]
            if row.empty:
                continue
            row = row.iloc[0]
            mean = row.mean_prevalence
            lo, hi = row.ci_lower, row.ci_upper
            color = ["#444444", "#1f77b4", "#d95f02", "#b44b4b"][j]
            ax.errorbar(
                mean,
                pos,
                xerr=[[max(0, mean - lo)], [max(0, hi - mean)]],
                fmt="o",
                color=color,
                capsize=2,
            )
            short_stratum = {
                "all": "all",
                "developed": "SI",
                "developing": "SFI",
                "zero_action": "zero",
            }[stratum]
            positions.append(pos)
            labels.append(motif.replace("_", " ") + "\n" + short_stratum)
            colors.append(color)
            pos += 1
        pos += 0.5
    ax.axvline(0, color="#111111", linewidth=0.8)
    ax.set_yticks(positions, labels, fontsize=7)
    ax.set_xlabel("Share of contribution rationales containing motif")
    ax.set_title(
        "Rationale language is payoff-heavy; lexical motifs are descriptive, not mental-state measures"
    )
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    _save(fig, out / "fig08_rationale_motifs.png")


def make_figures(tables_dir: Path, analysis_dir: Path, out_dir: Path) -> None:
    rounds = pd.read_csv(tables_dir / "round_metrics.csv")
    runs = pd.read_csv(analysis_dir / "run_metrics.csv")
    events = pd.read_csv(analysis_dir / "event_associations.csv")
    sessions = pd.read_csv(analysis_dir / "democracy_runs.csv")  # placeholder overwritten below
    # Governance needs session-level rows, not run-level aggregates.
    sessions = pd.read_csv(tables_dir / "democracy_sessions.csv")
    sanctions = pd.read_csv(analysis_dir / "sanction_runs.csv")
    motifs = pd.read_csv(analysis_dir / "motif_summary.csv")
    cooperation_figure(rounds, out_dir)
    role_figure(rounds, out_dir)
    ldf_figure(rounds, runs, out_dir)
    wealth_figure(rounds, runs, out_dir)
    event_figure(events, out_dir)
    governance_figure(sessions, out_dir)
    sanction_figure(sanctions, out_dir)
    motif_figure(motifs, out_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/tables")
    )
    parser.add_argument(
        "--analysis-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/analysis")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/figures")
    )
    args = parser.parse_args()
    make_figures(args.tables_dir, args.analysis_dir, args.output_dir)
    print(f"Wrote figures to {args.output_dir}")


if __name__ == "__main__":
    main()

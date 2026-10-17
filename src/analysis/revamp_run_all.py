"""Phase-4 pipeline: the four headline artefacts of the revamp.

    python -m analysis.revamp_run_all --results-dir results --out analysis_outputs/revamp

Four objects, each pre-committed with its interpretation in advance:

1. **Variance decomposition** — the share of outcome variance attributable to
   model family, prompt variant, condition and seed. If
   ``sigma^2_prompt + sigma^2_model > sigma^2_seed`` the result is a property of
   the instrument rather than of the institution.
2. **MCPR response curve** — participation and intensity against
   ``beta / n_G``, with MCPR = 1 marked. Either a discontinuity at the
   canonical threshold or cooperation persisting far below it; both were
   pre-registered as publishable.
3. **Best-response deviation rate** — the share of agent-rounds where the observed
   action is not the Stage-1 best response, by prompt variant. Costs zero
   GPU-hours and measures prompt steering with a game-theoretic yardstick.
4. **Governance tables** — elected rule by level x model, allocation
   concentration, and claim acceptance *by group*.

What already exists is preserved, not replaced: the nine-module
``analysis.qwen_9seed`` pipeline, the manifest, the audit, the run-level inference
and the claim ledger all carry over unchanged. This module adds to them.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from analysis.best_response import best_response_by_iteration, deviation_records, summarise
from analysis.governance import build_governance_tables
from analysis.qwen_9seed.io import as_rounds, load_json
from analysis.variance import (
    VarianceDecompositionError,
    decomposition_table,
    mcpr_response_curve,
    summarise_decomposition,
    threshold_discontinuity,
    variance_decomposition,
)

#: Cell-name grammar produced by the CLI:
#:   arm_<arm>_<condition tokens>_<model short>_<seed index>
#: e.g. arm_a_p0_qwen_s3, arm_c_beta14_llama_s2, arm_d_g3_mistral_s1
CELL_PATTERN = re.compile(
    r"^simulation_(?P<model>[^_]+)_(?P<cell>arm_[a-e]_[a-z0-9_]+)_seed(?P<seed>\d+)_"
    r"(?P<agents>\d+)agents_(?P<rounds>\d+)rounds_(?P<stamp>\d{8}_\d{6})\.json$"
)

ARMS = {"arm_a", "arm_b", "arm_c", "arm_d", "arm_e"}


def _normalise_arms(arms: set[str] | None) -> set[str] | None:
    """Accept ``{"A"}``, ``{"a"}`` or ``{"arm_a"}`` and return the cell-name form."""
    if arms is None:
        return None
    out: set[str] = set()
    for arm in arms:
        text = str(arm).strip().lower()
        out.add(text if text.startswith("arm_") else f"arm_{text}")
    return out


def discover_cells(results_dir: Path, arms: set[str] | None = None) -> list[dict[str, Any]]:
    """Find every CLI-produced cell in a results directory.

    Only cells whose provenance envelope is present are used. That is the point of
    writing the envelope: a run without a seed vector, a checkpoint and a
    prompt-variant hash cannot enter a decomposition that attributes variance to
    those factors.
    """
    cells: list[dict[str, Any]] = []
    wanted = _normalise_arms(arms)
    for path in sorted(results_dir.glob("simulation_*.json")):
        match = CELL_PATTERN.match(path.name)
        if not match:
            continue
        cell_name = match.group("cell")
        if wanted is not None and not cell_name.startswith(tuple(wanted)):
            continue
        try:
            payload = load_json(path)
        except (OSError, ValueError):
            continue
        provenance = payload.get("provenance") if isinstance(payload, dict) else None
        if not isinstance(provenance, dict):
            continue
        try:
            rounds = as_rounds(payload)
        except (ValueError, TypeError):
            continue
        cells.append(
            {
                "path": path,
                "run": cell_name,
                "cell": cell_name,
                "arm": cell_name.split("_")[1].upper(),
                "model": provenance.get("model", {}).get("alias", match.group("model")),
                "prompt_variant": provenance.get("prompt_variant", {}).get("name", ""),
                "condition": _condition_from(cell_name),
                "seed": f"{cell_name}_seed{match.group('seed')}",
                "governance_mode": provenance.get("governance", {}).get("mode", ""),
                "seed_fingerprint": payload.get("seed_fingerprint", ""),
                "rounds": rounds,
            }
        )
    return cells


def _condition_from(cell_name: str) -> str:
    """The treatment a cell implements, independent of model and seed.

    ``arm_a_p0_qwen_s3`` -> ``p0``; ``arm_c_beta14_llama_s2`` -> ``beta14``;
    ``arm_d_g3_mistral_s1`` -> ``g3``.
    """
    tokens = cell_name.split("_")
    if len(tokens) >= 3:
        return tokens[2]
    return cell_name


def run_level_frame(cells: list[dict[str, Any]]) -> pd.DataFrame:
    """One row per run: the cell's factors and its headline outcomes.

    Run-level, not agent-round-level. The protocol's central methodological
    commitment is that 7,020 agent-rounds are not 7,020 replications, and it
    applies here too: a variance decomposition computed over rows would report the
    within-run variance of a design whose replication unit is the run.
    """
    rows: list[dict[str, Any]] = []
    for cell in cells:
        rounds = cell["rounds"]
        if not rounds:
            continue
        intensities: list[float] = []
        cooperation: list[float] = []
        gini_end = float("nan")
        for index, round_data in enumerate(rounds):
            value = round_data.get("contribution_intensity")
            if isinstance(value, (int, float)):
                intensities.append(float(value))
            value = round_data.get("cooperation_rate")
            if isinstance(value, (int, float)):
                cooperation.append(float(value))
            if index == len(rounds) - 1:
                gini_end = float(round_data.get("gini_wealth", float("nan")) or float("nan"))

        positive_contributors = 0
        agent_rounds = 0
        for round_data in rounds:
            for data in (round_data.get("agents") or {}).values():
                agent_rounds += 1
                if float(data.get("contribution", 0.0) or 0.0) > 0:
                    positive_contributors += 1

        parameters = _cell_parameters(cell)
        rows.append(
            {
                "run": cell["run"],
                "arm": cell["arm"],
                "model": cell["model"],
                "prompt_variant": cell["prompt_variant"],
                "condition": cell["condition"],
                "seed": cell["seed"],
                "governance_mode": cell["governance_mode"],
                "seed_fingerprint": cell["seed_fingerprint"],
                "beta": parameters.get("PUBLIC_GOOD_MULTIPLIER", float("nan")),
                "group_size": parameters.get("NUM_AGENTS", float("nan")),
                "n_rounds": len(rounds),
                "contribution_intensity": _mean(intensities),
                "participation_rate": (
                    positive_contributors / agent_rounds if agent_rounds else float("nan")
                ),
                "cooperation_rate": _mean(cooperation),
                "final_gini": gini_end,
                "total_ldf_deposits": _sum_field(rounds, "ldf_contributions_total"),
                "total_ldf_payouts": _sum_field(rounds, "ldf_payouts_total"),
            }
        )
    return pd.DataFrame(rows)


def _cell_parameters(cell: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = load_json(cell["path"])
    except (OSError, ValueError):
        return {}
    if isinstance(payload, dict):
        snapshot = payload.get("effective_parameters")
        if isinstance(snapshot, dict):
            return snapshot
    return {}


def _mean(values: list[float]) -> float:
    finite = [v for v in values if v == v]
    return sum(finite) / len(finite) if finite else float("nan")


def _sum_field(rounds: list[dict[str, Any]], field: str) -> float:
    total = 0.0
    for round_data in rounds:
        value = round_data.get(field)
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def run_deviation_analysis(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Deviation rate by prompt variant, plus the iteration cross-check."""
    all_records = []
    for cell in cells:
        parameters = _cell_parameters(cell)
        all_records.extend(
            deviation_records(
                cell["rounds"],
                run=cell["run"],
                beta=parameters.get("PUBLIC_GOOD_MULTIPLIER"),
                prompt_variant=cell["prompt_variant"],
                model=cell["model"],
            )
        )
    summary = summarise(all_records, key="prompt_variant")

    # Cross-check the closed form against best-response iteration at the design's
    # own beta and group size. If these ever disagree, the closed form is wrong.
    frame = run_level_frame(cells)
    checks = []
    if not frame.empty:
        for beta, group_size in (
            frame[["beta", "group_size"]].dropna().drop_duplicates().itertuples(index=False)
        ):
            from analysis.best_response import Stage1Game

            game = Stage1Game(
                beta=float(beta),
                group_size=int(group_size),
                peer_contributions=0.0,
                capacity=1.0,
                floor=1.0,
            )
            iterated = best_response_by_iteration(game)
            checks.append(
                {
                    "beta": float(beta),
                    "group_size": int(group_size),
                    "mcpr": game.mcpr,
                    "closed_form_best_response": game.best_response(),
                    "iterated_best_response": iterated["iterated"],
                    "agrees": iterated["agrees"],
                }
            )

    return {
        "deviation_rate": summary.deviation_rate,
        "total_decisions": summary.total_decisions,
        "by_prompt_variant": summary.by_key,
        "by_model": _grouped_rate(all_records, "model"),
        "by_arm": _grouped_rate(all_records, "arm"),
        "iteration_cross_check": checks,
        "rows": [r.as_row() for r in all_records],
    }


def _grouped_rate(records: list[Any], key: str) -> dict[str, dict[str, float]]:
    groups: dict[str, list[Any]] = {}
    for record in records:
        groups.setdefault(str(getattr(record, key, "")), []).append(record)
    return {
        name: {
            "n": len(items),
            "deviations": sum(int(r.deviated) for r in items),
            "deviation_rate": sum(int(r.deviated) for r in items) / len(items)
            if items
            else float("nan"),
        }
        for name, items in sorted(groups.items())
    }


def run_variance_analysis(frame: pd.DataFrame) -> dict[str, Any]:
    """Decompose the primary outcomes across model, prompt, condition and seed."""
    outcomes = [
        name
        for name in (
            "contribution_intensity",
            "participation_rate",
            "final_gini",
            "cooperation_rate",
        )
        if name in frame
    ]
    results: dict[str, Any] = {}
    for outcome in outcomes:
        try:
            results[outcome] = variance_decomposition(frame, outcome)
        except VarianceDecompositionError as exc:
            results[outcome] = {"error": str(exc)}

    usable = {k: v for k, v in results.items() if "error" not in v}
    if not usable:
        # Never let an empty frame masquerade as a substantive verdict. The
        # instrument/seed comparison needs at least two runs per factor level,
        # and saying "seed dominates" on zero data would be a claim, not a result.
        return {
            "decompositions": {},
            "summary": [],
            "table": decomposition_table(frame, outcomes).to_dict("records"),
            "headline": (
                "not estimable: no runs with a provenance envelope were found. "
                "A run without a seed vector, checkpoint and prompt-variant hash "
                "cannot enter a decomposition that attributes variance to those factors."
            ),
        }
    return {
        "decompositions": usable,
        "summary": [summarise_decomposition(v) for v in usable.values()],
        "table": decomposition_table(frame, outcomes).to_dict("records"),
        "headline": (
            "instrument variance exceeds seed variance"
            if any(v["artifact_threshold_exceeded"] for v in usable.values())
            else "seed variance dominates the instrument factors"
        ),
    }


def run_mcpr_analysis(frame: pd.DataFrame) -> dict[str, Any]:
    """The Arm C prediction test."""
    curve = mcpr_response_curve(frame)
    return {
        "curve": curve.to_dict("records"),
        "participation_discontinuity": threshold_discontinuity(
            curve, "participation_rate", group_column="model"
        ),
        "intensity_discontinuity": threshold_discontinuity(
            curve, "contribution_intensity", group_column="model"
        ),
        "n_cells_above_threshold": int(curve["above_threshold"].sum()) if not curve.empty else 0,
        "n_cells_below_threshold": int((~curve["above_threshold"]).sum()) if not curve.empty else 0,
    }


def run_governance_analysis(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Rule adoption, stability, claim adjudication and payout concentration."""
    merged_rounds: list[dict[str, Any]] = []
    for cell in cells:
        for round_data in cell["rounds"]:
            merged = dict(round_data)
            if "governance_level" not in (merged.get("governance") or {}):
                merged["governance"] = {
                    **(merged.get("governance") or {}),
                    "level": cell["governance_mode"],
                    "elected_rule": _elected_rule(round_data),
                    "model": cell["model"],
                }
            merged_rounds.append(merged)

    tables = build_governance_tables(merged_rounds)
    by_model = _adoption_by_model(cells)
    return {
        "adoption": tables["adoption"],
        "adoption_by_model": by_model,
        "stability": tables["stability"].to_dict("records"),
        "elections": tables["elections"].to_dict("records"),
        "rejection": tables["rejection"],
        "claims": tables["claims"].to_dict("records"),
        "allocations": tables["allocations"].to_dict("records"),
        "wealth_by_rule": tables["wealth_by_rule"].to_dict("records"),
        "board_concentration": tables["board_concentration"].to_dict("records"),
    }


def _elected_rule(round_data: dict[str, Any]) -> str | None:
    session = round_data.get("constitutional_change") or {}
    return session.get("allocation_rule")


def _adoption_by_model(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Rule adoption split by model family — the cross-family stability question."""
    from analysis.governance import constitutional_sessions, rule_adoption

    by_model: dict[str, Any] = {}
    for cell in cells:
        sessions = constitutional_sessions(cell["rounds"])
        if not sessions:
            continue
        by_model.setdefault(cell["model"], rule_adoption(sessions))

    modal = {
        model: result.get("modal_rule")
        for model, result in by_model.items()
        if result.get("n_rule_elections")
    }
    distinct = {rule for rule in modal.values() if rule}
    return {
        "by_model": by_model,
        "modal_rule_by_model": modal,
        "single_modal_rule_across_models": len(distinct) <= 1,
        "interpretation": (
            "one rule is adopted by every model family -> a shared normative preference"
            if len(distinct) <= 1
            else f"the adopted rule differs by model family ({sorted(distinct)}): the "
            "preference is a property of the model prior, not of the decision context"
        ),
    }


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def make_figures(
    frame: pd.DataFrame,
    variance: dict[str, Any],
    mcpr: dict[str, Any],
    governance: dict[str, Any],
    out_dir: Path,
) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # 1. Variance decomposition.
    usable = variance.get("decompositions", {})
    if usable:
        outcome = (
            "contribution_intensity" if "contribution_intensity" in usable else next(iter(usable))
        )
        shares = usable[outcome]["variance_shares"]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(list(shares), [shares[k] for k in shares], color="#3b6ea5")
        ax.set_ylabel("Share of outcome variance")
        ax.set_title(f"Variance decomposition — {outcome}")
        ax.axhline(
            usable[outcome]["seed_share"], color="#c0392b", linestyle="--", label="sigma^2_seed"
        )
        ax.legend()
        path = out_dir / "fig_variance_decomposition.png"
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        written.append(str(path))

    # 2. MCPR response curve with the threshold marked.
    curve = pd.DataFrame(mcpr.get("curve") or [])
    if not curve.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for model, subset in curve.groupby("model"):
            ax.plot(subset["mcpr"], subset["participation_rate"], marker="o", label=model)
        ax.axvline(1.0, color="#c0392b", linestyle="--", label="MCPR = 1")
        ax.set_xscale("log")
        ax.set_xlabel("MCPR = beta / n")
        ax.set_ylabel("Participation rate")
        ax.set_title("Cooperation against the marginal return to contributing")
        ax.legend()
        path = out_dir / "fig_mcpr_response.png"
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        written.append(str(path))

    # 3. Model x prompt heatmap of the primary outcome.
    if not frame.empty and "model" in frame and "prompt_variant" in frame:
        pivot = frame.pivot_table(
            index="model", columns="prompt_variant", values="contribution_intensity", aggfunc="mean"
        )
        if not pivot.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            image = ax.imshow(pivot.to_numpy(dtype=float), cmap="viridis", aspect="auto")
            ax.set_xticks(range(pivot.shape[1]), pivot.columns, rotation=30, ha="right")
            ax.set_yticks(range(pivot.shape[0]), pivot.index)
            ax.set_title("Contribution intensity: model x prompt variant")
            fig.colorbar(image, ax=ax, label="mean contribution intensity")
            path = out_dir / "fig_model_prompt_heatmap.png"
            fig.tight_layout()
            fig.savefig(path, dpi=200)
            plt.close(fig)
            written.append(str(path))

    # 4. Elected allocation rule by governance level and model.
    adoption = governance.get("adoption", {})
    if adoption.get("n_rule_elections"):
        shares = adoption["rule_shares"]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(list(shares), [shares[k] for k in shares], color="#2e8b57")
        ax.set_ylabel("Share of rule elections")
        ax.set_title(
            f"Which redistribution rule the assembly elects "
            f"({adoption['n_rule_elections']} elections, {adoption['n_sessions']} sessions)"
        )
        path = out_dir / "fig_elected_rule.png"
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        written.append(str(path))

    return written


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_all(results_dir: Path, out_dir: Path, arms: set[str] | None = None) -> dict[str, Any]:
    cells = discover_cells(results_dir, arms=_normalise_arms(arms))
    tables = out_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    frame = run_level_frame(cells)
    frame.to_csv(tables / "run_level.csv", index=False)

    variance = run_variance_analysis(frame)
    mcpr = run_mcpr_analysis(frame)
    deviations = run_deviation_analysis(cells)
    governance = run_governance_analysis(cells)

    if deviations["rows"]:
        pd.DataFrame(deviations["rows"]).to_csv(
            tables / "best_response_deviations.csv", index=False
        )
    pd.DataFrame(governance.get("elections") or []).to_csv(
        tables / "governance_elections.csv", index=False
    )
    pd.DataFrame(governance.get("claims") or []).to_csv(
        tables / "governance_claims.csv", index=False
    )

    figures = make_figures(frame, variance, mcpr, governance, out_dir / "figures")

    summary = {
        "results_dir": str(results_dir),
        "n_cells": len(cells),
        "arms": sorted({c["arm"] for c in cells}),
        "models": sorted({c["model"] for c in cells}),
        "prompt_variants": sorted({c["prompt_variant"] for c in cells}),
        "seed_fingerprints_distinct": len({c["seed_fingerprint"] for c in cells}),
        "variance_headline": variance.get("headline"),
        "mcpr_cells_above_threshold": mcpr["n_cells_above_threshold"],
        "deviation_rate": deviations.get("deviation_rate"),
        "iteration_cross_check_ok": all(
            check["agrees"] for check in deviations.get("iteration_cross_check", [])
        ),
        "governance_rule_elections": governance.get("adoption", {}).get("n_rule_elections"),
        "figures": figures,
    }
    payload = {
        "summary": summary,
        "variance": {k: v for k, v in variance.items() if k != "table"},
        "mcpr": mcpr,
        "deviations": {k: v for k, v in deviations.items() if k != "rows"},
        "governance": governance,
    }
    (out_dir / "revamp_findings.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("analysis_outputs/revamp"))
    parser.add_argument("--arm", action="append", help="Restrict to these arms.")
    args = parser.parse_args()
    run_all(args.results_dir, args.out, arms={a.upper() for a in args.arm} if args.arm else None)


if __name__ == "__main__":
    main()

"""Run the complete reproducible Qwen2.5-14B nine-seed analysis pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import analyze as analysis
from . import claims as claim_builder
from . import figures as figure_builder
from . import persistence as persistence_analysis
from . import robustness as robustness_analysis
from .audit import run_audit
from .extract import extract_results
from .io import discover_qwen_runs
from .manifest import build_manifest


def run_all(results_dir: Path, output_dir: Path) -> None:
    tables_dir = output_dir / "tables"
    analysis_dir = output_dir / "analysis"
    robustness_dir = output_dir / "robustness"
    persistence_dir = output_dir / "persistence"
    figures_dir = output_dir / "figures"
    for directory in [
        output_dir,
        tables_dir,
        analysis_dir,
        robustness_dir,
        persistence_dir,
        figures_dir,
        output_dir / "audit",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(results_dir)
    (output_dir / "input_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    run_table, checks, schema = run_audit(results_dir)
    run_table.to_csv(output_dir / "audit" / "run_audit.csv", index=False)
    checks.to_csv(output_dir / "audit" / "data_quality_checks.csv", index=False)
    (output_dir / "audit" / "schema_inventory.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8"
    )
    failed = checks[(~checks["passed"]) & (checks["severity"] == "error")]
    if not failed.empty:
        raise RuntimeError(
            f"Data audit failed: {failed[['check_id', 'seed', 'scope']].to_dict('records')}"
        )

    tables = extract_results(results_dir)
    for name, frame in tables.items():
        frame.to_csv(tables_dir / f"{name}.csv", index=False)

    analysis.analyze(tables_dir, analysis_dir)
    persistence_analysis.build(tables_dir, persistence_dir)
    robustness_analysis.run_robustness(tables_dir, analysis_dir, robustness_dir)
    claims = claim_builder.build_claims(tables_dir, analysis_dir, robustness_dir, persistence_dir)
    (output_dir / "key_claims.json").write_text(
        json.dumps(claims, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    figure_builder.make_figures(tables_dir, analysis_dir, figures_dir)

    summary = {
        "input_files": len(discover_qwen_runs(results_dir)),
        "rounds": int(schema["selection"]["n_rounds"]),
        "agent_round_records": int(schema["selection"]["n_agent_records"]),
        "audit_error_failures": len(failed),
        "tables": {name: len(frame) for name, frame in tables.items()},
        "analysis_outputs": sorted(path.name for path in analysis_dir.glob("*.csv")),
        "figures": sorted(path.name for path in figures_dir.glob("*.png")),
    }
    (output_dir / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed")
    )
    args = parser.parse_args()
    run_all(args.results_dir, args.output_dir)


if __name__ == "__main__":
    main()

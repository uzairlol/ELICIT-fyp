"""Create a provenance manifest for the Qwen nine-seed input set."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .io import discover_qwen_runs, parse_run_name, sha256_file


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_manifest(results_dir: Path) -> dict:
    paths = discover_qwen_runs(results_dir)
    files = []
    for path in paths:
        files.append(
            {
                **parse_run_name(path),
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "created_utc": datetime.now(UTC).isoformat(),
        "results_dir": str(results_dir),
        "selection_rule": "qwen2.5-14b Full scnldf sh1 ldf1 seed1..9; 26 agents; 30 rounds",
        "selection_metadata_source": "filename; raw JSON has no embedded run manifest",
        "n_files": len(files),
        "files": files,
        "python": sys.version,
        "python_executable": sys.executable,
        "conda_prefix": os.environ.get("CONDA_PREFIX"),
        "platform": platform.platform(),
        "analysis_git_commit": _git_commit(),
        "package_versions": {
            name: _package_version(name)
            for name in [
                "numpy",
                "pandas",
                "scipy",
                "matplotlib",
                "seaborn",
                "statsmodels",
                "wordcloud",
            ]
        },
        "model_provenance_caveat": "The result files identify the model alias qwen2.5-14b but do not encode checkpoint revision, quantization, vLLM version, server flags, or inference commit.",
        "inference_manifest_caveat": "The analysis commit is recorded for the analysis code only; it cannot prove the code revision used to generate the result JSON files.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_outputs/qwen2_5_14b_9seed/input_manifest.json"),
    )
    args = parser.parse_args()
    manifest = build_manifest(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

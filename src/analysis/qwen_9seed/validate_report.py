"""Validate that the Markdown report points to real artifacts and headline claims."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TOKENS = [
    "0.926",
    "0.297",
    "0.235 to 0.358",
    "0.061",
    "-0.094 to -0.028",
    "0.077",
    "-0.111 to -0.043",
    "0.954",
    "0.768",
    "0.900",
    "2.775",
    "0.292",
    "-0.364 to -0.213",
    "29.7%",
    "2.2%",
    "0.387",
    "54 sessions",
    "1,404",
    "0.018",
    "0.062",
    "56.5%",
    "27,812",
    "39,632",
]


def validate(report_path: Path, claims_path: Path, root: Path) -> dict:
    report = report_path.read_text(encoding="utf-8")
    normalized_report = report.replace(chr(0x2212), "-").replace(chr(0x2013), "-")
    missing_tokens = [token for token in REQUIRED_TOKENS if token not in normalized_report]
    image_links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", report)
    missing_images = [link for link in image_links if not (report_path.parent / link).exists()]
    artifact_links = re.findall(r"`(analysis_outputs/[^`]+)`", report)
    missing_artifacts = [link for link in artifact_links if not (root / link).exists()]
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    scope_ok = claims["scope"]["n_runs"] == 9 and claims["scope"]["n_agent_rounds"] == 7020
    result = {
        "report": str(report_path),
        "claim_ledger": str(claims_path),
        "required_token_count": len(REQUIRED_TOKENS),
        "missing_tokens": missing_tokens,
        "image_links": len(image_links),
        "missing_images": missing_images,
        "artifact_links": len(artifact_links),
        "missing_artifacts": missing_artifacts,
        "scope_ledger_consistent": scope_ok,
        "passed": not missing_tokens and not missing_images and not missing_artifacts and scope_ok,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=Path("docs/paper/qwen_2_5_14b_9seed_results_report.md")
    )
    parser.add_argument(
        "--claims", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/key_claims.json")
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_outputs/qwen2_5_14b_9seed/report_validation.json"),
    )
    args = parser.parse_args()
    result = validate(args.report, args.claims, args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

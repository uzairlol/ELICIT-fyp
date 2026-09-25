"""Validate the nine Qwen JSON files and emit an auditable schema inventory."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from .io import as_rounds, discover_qwen_runs, load_json, parse_run_name, sha256_file

ROUND_REQUIRED = {
    "round_number",
    "agents",
    "si_members",
    "sfi_members",
    "si_total_contribution",
    "sfi_total_contribution",
    "si_avg_contribution",
    "sfi_avg_contribution",
    "shock_occurred",
    "shock_severity",
    "gross_damage_total",
    "net_damage_total",
    "ldf_pool_start",
    "ldf_contributions_total",
    "ldf_payouts_total",
    "ldf_pool_end",
    "cooperation_rate",
    "gini_wealth",
}
AGENT_REQUIRED = {
    "institution_choice",
    "institution_reasoning",
    "institution_parser_meta",
    "contribution",
    "contribution_reasoning",
    "contribution_facts_used",
    "contribution_parser_meta",
    "stage1_payoff",
    "stage2_payoff",
    "payoff",
    "cumulative_payoff",
    "strategy",
    "agent_group",
    "wealth",
    "vulnerability",
    "historical_emissions",
    "contribution_capacity",
    "received_punishments",
    "received_rewards",
    "assigned_punishments",
    "assigned_rewards",
    "punishment_reasoning",
    "reputation",
    "tom_scores",
    "rank",
    "subsidy",
    "climate_damage_taken_round",
    "climate_damage_taken_cumulative",
    "ldf_contribution_round",
    "ldf_payout_round",
    "net_climate_transfer_round",
    "parsing_failures",
    "rule_of_law_blocks",
    "belief_state",
    "round_number",
}


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(a: Any, b: Any, atol: float = 1e-7, rtol: float = 1e-7) -> bool:
    if not is_number(a) or not is_number(b):
        return False
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def gini(values: list[float]) -> float:
    arr = sorted(float(value) for value in values if value >= 0)
    n = len(arr)
    total = sum(arr)
    if n == 0 or total == 0:
        return float("nan")
    return (2 * sum((i + 1) * value for i, value in enumerate(arr)) / (n * total)) - ((n + 1) / n)


def run_audit(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    paths = discover_qwen_runs(results_dir)
    checks: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    round_types: defaultdict[str, Counter[str]] = defaultdict(Counter)
    agent_types: defaultdict[str, Counter[str]] = defaultdict(Counter)
    round_key_presence: Counter[str] = Counter()
    agent_key_presence: Counter[str] = Counter()
    total_agent_records = 0
    total_parser_failures = 0

    def add_check(
        check_id: str,
        seed: int,
        scope: str,
        passed: bool,
        observed: Any,
        expected: Any,
        severity: str = "error",
        details: str = "",
    ) -> None:
        checks.append(
            {
                "check_id": check_id,
                "seed": seed,
                "scope": scope,
                "severity": severity,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
                "details": details,
            }
        )

    for path in paths:
        meta = parse_run_name(path)
        seed = meta["seed"]
        payload = load_json(path)
        rounds = as_rounds(payload)
        round_numbers = [record.get("round_number") for record in rounds]
        shock_rounds = [
            record.get("round_number") for record in rounds if record.get("shock_occurred") is True
        ]
        shock_severities = [
            record.get("shock_severity")
            for record in rounds
            if record.get("shock_occurred") is True
        ]
        rounds_cooperation = [record.get("cooperation_rate") for record in rounds]
        run_agent_records = 0
        run_parser_failures = 0
        run_auto_fit = 0
        run_fallback = 0
        run_semantic_retry = 0
        run_ldf_same_contribution = 0
        run_damage_formula_errors: list[float] = []
        run_constitutional_sessions = 0
        run_vote_errors = 0
        run_agent_ids: set[str] = set()
        run_groups: Counter[str] = Counter()
        run_institutions: Counter[str] = Counter()
        run_strategies: Counter[str] = Counter()
        run_missing_round_keys: Counter[str] = Counter()
        run_missing_agent_keys: Counter[str] = Counter()
        agent_record_counts: list[int] = []
        cumulative_damage: defaultdict[str, list[float]] = defaultdict(list)
        pool_balance_errors: list[float] = []
        ldf_total_errors: list[float] = []
        cooperation_errors: list[float] = []
        gini_errors: list[float] = []
        group_total_errors: list[float] = []
        group_membership_errors = 0
        negative_values = 0
        internal_round_errors = 0

        add_check("one_file_per_seed", seed, "run", path.exists(), True, True)
        add_check("root_is_round_list", seed, "run", isinstance(payload, list), True, True)
        add_check("thirty_rounds", seed, "run", len(rounds) == 30, len(rounds), 30)
        add_check(
            "round_numbers_contiguous",
            seed,
            "run",
            round_numbers == list(range(1, 31)),
            round_numbers,
            list(range(1, 31)),
        )
        add_check("at_least_one_shock", seed, "run", bool(shock_rounds), True, True)

        for position, record in enumerate(rounds, start=1):
            round_number = record.get("round_number")
            scope = f"round={round_number}"
            if "constitutional_change" in record:
                run_constitutional_sessions += 1
                change = record.get("constitutional_change") or {}
                votes = change.get("votes") or {}
                tally = change.get("tally") or {}
                vote_total = sum(
                    1
                    for value in votes.values()
                    if isinstance(value, dict) and isinstance(value.get("vote"), (int, float))
                )
                tally_total = sum(
                    int(value) for value in tally.values() if isinstance(value, (int, float))
                )
                if len(votes) != 26 or vote_total != 26 or tally_total != 26:
                    run_vote_errors += 1
            missing_rounds = ROUND_REQUIRED - set(record)
            for key in missing_rounds:
                run_missing_round_keys[key] += 1
            round_key_presence.update(record.keys())
            for key, value in record.items():
                round_types[key][json_type(value)] += 1
            if round_number != position:
                add_check(
                    "round_position_matches_number",
                    seed,
                    scope,
                    False,
                    round_number,
                    position,
                )

            agents = record.get("agents")
            if not isinstance(agents, dict):
                add_check("agents_mapping", seed, scope, False, json_type(agents), "object")
                continue
            agent_ids = {str(key) for key in agents}
            run_agent_ids.update(agent_ids)
            agent_record_counts.append(len(agents))
            add_check("agents_per_round", seed, scope, len(agents) == 26, len(agents), 26)
            if agent_ids != {str(i) for i in range(26)}:
                add_check(
                    "stable_agent_ids",
                    seed,
                    scope,
                    agent_ids == {str(i) for i in range(26)},
                    sorted(agent_ids, key=lambda x: int(x) if x.isdigit() else x),
                    list(range(26)),
                )

            contributions: list[float] = []
            wealth: list[float] = []
            ldf_contributions: list[float] = []
            ldf_payouts: list[float] = []
            si_total = 0.0
            sfi_total = 0.0
            si_members: set[str] = set()
            sfi_members: set[str] = set()
            for agent_id, agent in agents.items():
                run_agent_records += 1
                total_agent_records += 1
                missing_agents = AGENT_REQUIRED - set(agent)
                for key in missing_agents:
                    run_missing_agent_keys[key] += 1
                agent_key_presence.update(agent.keys())
                for key, value in agent.items():
                    agent_types[key][json_type(value)] += 1
                if agent.get("round_number") != round_number:
                    internal_round_errors += 1

                group = str(agent.get("agent_group"))
                institution = str(agent.get("institution_choice"))
                run_groups[group] += 1
                run_institutions[institution] += 1
                run_strategies[str(agent.get("strategy"))] += 1

                contribution = agent.get("contribution")
                agent_wealth = agent.get("wealth")
                ldf_contribution = agent.get("ldf_contribution_round")
                ldf_payout = agent.get("ldf_payout_round")
                if all(
                    is_number(value)
                    for value in (contribution, agent_wealth, ldf_contribution, ldf_payout)
                ):
                    contributions.append(float(contribution))
                    wealth.append(float(agent_wealth))
                    ldf_contributions.append(float(ldf_contribution))
                    ldf_payouts.append(float(ldf_payout))
                    negative_values += sum(
                        value < 0
                        for value in (
                            float(contribution),
                            float(agent_wealth),
                            float(ldf_contribution),
                            float(ldf_payout),
                        )
                    )
                    if group == "developed":
                        si_members.add(str(agent_id))
                        si_total += float(contribution)
                    elif group == "developing":
                        sfi_members.add(str(agent_id))
                        sfi_total += float(contribution)

                parser_failures = agent.get("parsing_failures")
                if is_number(parser_failures):
                    run_parser_failures += int(parser_failures)
                    total_parser_failures += int(parser_failures)
                punishment_meta = agent.get("punishment_parser_meta") or {}
                run_auto_fit += int(bool(punishment_meta.get("auto_fitted_to_budget", False)))
                run_fallback += int(bool(punishment_meta.get("fallback_used", False)))
                run_semantic_retry += int(bool(punishment_meta.get("semantic_retry", False)))
                if is_number(contribution) and is_number(ldf_contribution):
                    run_ldf_same_contribution += int(float(contribution) == float(ldf_contribution))
                if bool(record.get("shock_occurred")) and is_number(
                    agent.get("climate_damage_taken_round")
                ):
                    expected_damage = (
                        150000.0
                        * float(record.get("shock_severity", 0.0))
                        * max(0.0, float(agent.get("vulnerability", 0.0)))
                    )
                    run_damage_formula_errors.append(
                        abs(expected_damage - float(agent.get("climate_damage_taken_round")))
                    )
                cumulative_damage[str(agent_id)].append(
                    float(agent.get("climate_damage_taken_cumulative", 0))
                )

            # The environment labels mean(contribution / int(wealth)) as
            # ``cooperation_rate``.  It is a contribution-intensity index, not
            # the fraction of agents making a positive contribution.
            intensity_ratios = [
                contribution_value / int(wealth_value) if int(wealth_value) > 0 else 0.0
                for contribution_value, wealth_value in zip(contributions, wealth, strict=True)
            ]
            logged_intensity = (
                sum(intensity_ratios) / len(intensity_ratios) if intensity_ratios else 0.0
            )
            intensity_error = abs(
                logged_intensity - float(record.get("cooperation_rate", float("nan")))
            )
            if math.isfinite(intensity_error):
                cooperation_errors.append(intensity_error)
            logged_gini = record.get("gini_wealth")
            calculated_gini = gini(wealth)
            if is_number(logged_gini) and math.isfinite(calculated_gini):
                gini_errors.append(abs(float(logged_gini) - calculated_gini))

            raw_si_members = {str(value) for value in record.get("si_members", [])}
            raw_sfi_members = {str(value) for value in record.get("sfi_members", [])}
            if si_members != raw_si_members or sfi_members != raw_sfi_members:
                group_membership_errors += 1
            group_error = max(
                abs(si_total - float(record.get("si_total_contribution", float("nan")))),
                abs(sfi_total - float(record.get("sfi_total_contribution", float("nan")))),
            )
            if math.isfinite(group_error):
                group_total_errors.append(group_error)

            ldf_total_error = max(
                abs(
                    sum(ldf_contributions)
                    - float(record.get("ldf_contributions_total", float("nan")))
                ),
                abs(sum(ldf_payouts) - float(record.get("ldf_payouts_total", float("nan")))),
            )
            if math.isfinite(ldf_total_error):
                ldf_total_errors.append(ldf_total_error)
            pool_identity_error = abs(
                float(record.get("ldf_pool_end", float("nan")))
                - (
                    float(record.get("ldf_pool_start", float("nan")))
                    + float(record.get("ldf_contributions_total", float("nan")))
                    - float(record.get("ldf_payouts_total", float("nan")))
                )
            )
            if math.isfinite(pool_identity_error):
                pool_balance_errors.append(pool_identity_error)

        add_check(
            "no_missing_round_keys",
            seed,
            "run",
            not run_missing_round_keys,
            dict(run_missing_round_keys),
            {},
        )
        add_check(
            "no_missing_agent_keys",
            seed,
            "run",
            not run_missing_agent_keys,
            dict(run_missing_agent_keys),
            {},
        )
        add_check(
            "stable_agent_ids_across_rounds",
            seed,
            "run",
            run_agent_ids == {str(i) for i in range(26)},
            sorted(run_agent_ids, key=lambda x: int(x) if x.isdigit() else x),
            list(range(26)),
        )
        add_check(
            "agent_round_records",
            seed,
            "run",
            run_agent_records == 26 * 30,
            run_agent_records,
            26 * 30,
        )
        add_check(
            "internal_round_numbers",
            seed,
            "run",
            internal_round_errors == 0,
            internal_round_errors,
            0,
        )
        add_check(
            "group_membership_maps_to_agent_group",
            seed,
            "run",
            group_membership_errors == 0,
            group_membership_errors,
            0,
        )
        add_check("nonnegative_core_values", seed, "run", negative_values == 0, negative_values, 0)
        add_check(
            "group_totals_reconcile",
            seed,
            "run",
            max(group_total_errors, default=0) <= 1e-7,
            max(group_total_errors, default=0),
            0,
        )
        add_check(
            "logged_contribution_intensity_range",
            seed,
            "run",
            all(0 <= float(value) <= 1 for value in rounds_cooperation),
            {"min": min(rounds_cooperation), "max": max(rounds_cooperation)},
            "all values in [0, 1]",
        )
        add_check(
            "logged_contribution_intensity_reconciles",
            seed,
            "run",
            max(cooperation_errors, default=0) <= 1e-12,
            max(cooperation_errors, default=0),
            0,
        )
        add_check(
            "logged_gini_recomputes",
            seed,
            "run",
            max(gini_errors, default=0) <= 1e-6,
            max(gini_errors, default=0),
            0,
        )
        add_check(
            "ldf_agent_totals_reconcile",
            seed,
            "run",
            max(ldf_total_errors, default=0) <= 1e-7,
            max(ldf_total_errors, default=0),
            0,
        )
        add_check(
            "ldf_pool_identity",
            seed,
            "run",
            max(pool_balance_errors, default=0) <= 1e-7,
            max(pool_balance_errors, default=0),
            0,
        )
        add_check(
            "parser_failures",
            seed,
            "run",
            run_parser_failures == 0,
            run_parser_failures,
            0,
            severity="warning",
        )
        add_check(
            "ldf_contribution_equals_stage1_contribution",
            seed,
            "run",
            run_ldf_same_contribution == run_agent_records,
            run_ldf_same_contribution,
            run_agent_records,
        )
        add_check(
            "shock_damage_formula",
            seed,
            "run",
            max(run_damage_formula_errors, default=0) <= 1e-7,
            max(run_damage_formula_errors, default=0),
            0,
        )
        add_check(
            "six_democracy_sessions",
            seed,
            "run",
            run_constitutional_sessions == 6,
            run_constitutional_sessions,
            6,
        )
        add_check(
            "democracy_vote_records_reconcile",
            seed,
            "run",
            run_vote_errors == 0,
            run_vote_errors,
            0,
        )
        add_check(
            "cumulative_damage_monotone",
            seed,
            "run",
            all(
                a <= b + 1e-9
                for sequence in cumulative_damage.values()
                for a, b in pairwise(sequence)
            ),
            "record-order check",
            "nondecreasing within agent trajectories",
        )

        run_rows.append(
            {
                **meta,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "n_rounds": len(rounds),
                "n_agent_records": run_agent_records,
                "agent_count_min": min(agent_record_counts),
                "agent_count_max": max(agent_record_counts),
                "shock_rounds": json.dumps(shock_rounds),
                "shock_severities": json.dumps(shock_severities),
                "groups": json.dumps(dict(run_groups), sort_keys=True),
                "institutions": json.dumps(dict(run_institutions), sort_keys=True),
                "strategies": json.dumps(dict(run_strategies), sort_keys=True),
                "parser_failures": run_parser_failures,
                "punishment_auto_fit_records": run_auto_fit,
                "punishment_fallback_records": run_fallback,
                "punishment_semantic_retry_records": run_semantic_retry,
                "constitutional_sessions": run_constitutional_sessions,
                "democracy_vote_errors": run_vote_errors,
                "ldf_contribution_same_records": run_ldf_same_contribution,
                "shock_damage_formula_max_error": max(
                    run_damage_formula_errors, default=float("nan")
                ),
                "missing_round_key_instances": sum(run_missing_round_keys.values()),
                "missing_agent_key_instances": sum(run_missing_agent_keys.values()),
                "max_cooperation_identity_error": max(cooperation_errors, default=float("nan")),
                "max_gini_recompute_error": max(gini_errors, default=float("nan")),
                "max_ldf_total_error": max(ldf_total_errors, default=float("nan")),
                "max_ldf_pool_identity_error": max(pool_balance_errors, default=float("nan")),
            }
        )

    add_check("nine_files", 0, "dataset", len(paths), 9, True)
    add_check(
        "all_rounds",
        0,
        "dataset",
        sum(row["n_rounds"] for row in run_rows) == 270,
        sum(row["n_rounds"] for row in run_rows),
        270,
    )
    add_check(
        "all_agent_records",
        0,
        "dataset",
        total_agent_records == 7020,
        total_agent_records,
        7020,
    )
    add_check(
        "all_parser_failures",
        0,
        "dataset",
        total_parser_failures == 0,
        total_parser_failures,
        0,
        severity="warning",
    )

    schema = {
        "selection": {
            "pattern": "simulation_qwen2.5-14b_Full_scnldf_sh1_ldf1_seed{1..9}_26agents_30rounds_*.json",
            "n_files": len(paths),
            "n_rounds": sum(row["n_rounds"] for row in run_rows),
            "n_agent_records": total_agent_records,
        },
        "required_round_keys": sorted(ROUND_REQUIRED),
        "required_agent_keys": sorted(AGENT_REQUIRED),
        "round_key_presence": dict(sorted(round_key_presence.items())),
        "agent_key_presence": dict(sorted(agent_key_presence.items())),
        "round_field_types": {
            key: dict(sorted(counter.items())) for key, counter in sorted(round_types.items())
        },
        "agent_field_types": {
            key: dict(sorted(counter.items())) for key, counter in sorted(agent_types.items())
        },
        "extra_round_keys": sorted(set(round_key_presence) - ROUND_REQUIRED),
        "extra_agent_keys": sorted(set(agent_key_presence) - AGENT_REQUIRED),
    }
    return pd.DataFrame(run_rows), pd.DataFrame(checks), schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_outputs/qwen2_5_14b_9seed/audit")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_table, checks, schema = run_audit(args.results_dir)
    run_table.to_csv(args.output_dir / "run_audit.csv", index=False)
    checks.to_csv(args.output_dir / "data_quality_checks.csv", index=False)
    (args.output_dir / "schema_inventory.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8"
    )
    failed = checks[(~checks["passed"]) & (checks["severity"] == "error")]
    warnings = checks[(~checks["passed"]) & (checks["severity"] == "warning")]
    print(
        json.dumps(
            {
                "runs": len(run_table),
                "rounds": int(run_table["n_rounds"].sum()),
                "agent_records": int(run_table["n_agent_records"].sum()),
                "failed_error_checks": len(failed),
                "warning_checks": len(warnings),
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )
    if not failed.empty:
        print(failed[["check_id", "seed", "scope", "observed", "expected"]].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()

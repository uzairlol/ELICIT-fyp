"""End-to-end: grid cell -> result file -> headline artefacts.

The grid is 164 runs of real compute. If the handover between a finished run and
the four headline artefacts is broken, that is discovered only after the quota is
spent. These tests build synthetic result files in exactly the envelope shape
``Environment.save_results`` writes, run the Phase-4 pipeline over them, and check
that each pre-committed finding is reachable.

Nothing here asserts a *result* — the findings are pre-registered, not pre-known.
What is asserted is that each one is *measurable* from the artefacts the grid
produces, which is the property that has to hold before the compute is spent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.revamp_run_all import discover_cells, run_all


def _round(round_number: int, agents: list[dict], *, shock: bool = False, governance=None):
    return {
        "round_number": round_number,
        "si_members": [a["agent_id"] for a in agents],
        "sfi_members": [],
        "shock_occurred": shock,
        "shock_severity": 0.10 if shock else 0.0,
        "payouts": {a["agent_id"]: a.get("payout", 0.0) for a in agents if a.get("payout", 0.0)},
        "ldf_contributions_total": 1_000_000.0,
        "ldf_payouts_total": sum(a.get("payout", 0.0) for a in agents),
        "ldf_pool_start": 5_000_000.0,
        "contribution_intensity": sum(a["contribution"] for a in agents) / len(agents),
        "cooperation_rate": 0.5,
        "gini_wealth": 0.4,
        "governance": governance or {},
        "agents": {str(a["agent_id"]): a for a in agents},
    }


def _agent(agent_id, *, group, contribution, wealth, capacity, emissions):
    return {
        "agent_id": agent_id,
        "agent_group": group,
        "contribution": contribution,
        "start_of_round_wealth": wealth,
        "stage1_contribution_cap": wealth,
        "contribution_intensity": contribution / wealth if wealth else 0.0,
        "contribution_capacity": capacity,
        "historical_emissions": emissions,
        "wealth": wealth,
        "payout": 0.0,
    }


def _session(round_number, rule, level):
    return {
        "constitutional_change": {
            "round": round_number,
            "governance_level": level,
            "allocation_rule": rule,
            "proposals": [
                {
                    "rule": "LDF_ALLOCATION_RULE",
                    "new_value": rule,
                    "proposer": 0,
                    "reason": "test",
                }
            ],
            "winning_proposal": {"rule": "LDF_ALLOCATION_RULE", "new_value": rule},
            "tally": {0: 5},
            "votes": {"0": {"vote": 0}},
            "applied": True,
        }
    }


def write_cell(
    results_dir: Path,
    *,
    arm: str,
    condition: str,
    model: str,
    variant: str,
    seed: int,
    agents: int,
    beta: float,
    intensity: float,
    governance_mode: str,
    elected_rule: str,
    level: str = "G0",
    rounds: int = 6,
) -> Path:
    """Write one envelope-shaped result file, as ``save_results`` would.

    The filename mirrors the real one: ``simulation_{model}_{cell}_seed{python
    seed}_{n}agents_{n}rounds_{stamp}.json``, where the cell name is
    ``arm_{A..E}_{condition}_{model short}_s{seed index}``.
    """
    round_rows = []
    for round_number in range(1, rounds + 1):
        population = []
        for index in range(agents):
            group = "developed" if index < agents // 3 else "developing"
            wealth = 1_000_000.0 if group == "developed" else 100_000.0
            capacity = 1.0 if group == "developed" else 0.10
            emissions = 1.50 if group == "developed" else 0.30
            contribution = wealth * intensity * (capacity if capacity < 1.0 else 1.0)
            population.append(
                _agent(
                    index,
                    group=group,
                    contribution=contribution,
                    wealth=wealth,
                    capacity=capacity,
                    emissions=emissions,
                )
            )
        governance = (
            {"level": level, "elected_rule": elected_rule} if governance_mode != "fixed" else {}
        )
        row = _round(round_number, population, shock=round_number in (7, 17), governance=governance)
        if round_number % 5 == 0:
            row.update(_session(round_number, elected_rule, level))
        round_rows.append(row)

    envelope = {
        "provenance": {
            "model": {"alias": model, "checkpoint": f"org/{model}", "quantization": "test"},
            "prompt_variant": {"name": variant, "hash": "deadbeef"},
            "governance": {"mode": governance_mode},
            "seed_vector": {"python": 1000 + seed, "llm_seed": 2000 + seed},
        },
        "effective_parameters": {"PUBLIC_GOOD_MULTIPLIER": beta, "NUM_AGENTS": agents},
        "seed_fingerprint": f"fp-{arm}-{condition}-{model}-{variant}-{seed}",
        "run": {"model_name": model, "batch_name": condition},
        "rounds": round_rows,
    }
    short = model.split("-")[0].split(".")[0]
    cell = f"arm_{arm.lower()}_{condition}_{short}_s{seed}"
    name = (
        f"simulation_{model}_{cell}_seed{1000 + seed}"
        f"_{agents}agents_{rounds}rounds_20260101_000000.json"
    )
    path = results_dir / name
    path.write_text(json.dumps(envelope), encoding="utf-8")
    return path


@pytest.fixture
def synthetic_results(tmp_path):
    """A miniature grid: 3 models x 3 variants x 3 seeds, plus MCPR and governance."""
    results = tmp_path / "results"
    results.mkdir()

    # Arm A, the audit: intensity is driven mainly by the prompt, then the model.
    for model, model_level in (("qwen2.5-14b", 0.55), ("llama-3.1-8b", 0.45), ("mistral-7b", 0.35)):
        for variant, variant_level in (
            ("P0_canonical", 0.20),
            ("P1_lexical", 0.15),
            ("P2_minimal_control", 0.10),
        ):
            for seed in (1, 2, 3):
                write_cell(
                    results,
                    arm="A",
                    model=model,
                    variant=variant,
                    condition=variant.split("_")[0].lower(),
                    seed=seed,
                    agents=6,
                    beta=1.6,
                    intensity=model_level + variant_level + seed * 0.001,
                    governance_mode="fixed",
                    elected_rule="damage_proportional",
                )

    # Arm C: a participation discontinuity at MCPR = 1.
    for model in ("qwen2.5-14b", "llama-3.1-8b"):
        for beta, intensity in ((0.4, 0.50), (1.6, 0.50), (14.0, 0.10), (20.0, 0.05)):
            for seed in (1, 2, 3):
                write_cell(
                    results,
                    arm="C",
                    model=model,
                    variant="P0_canonical",
                    condition=f"beta{str(beta).replace('.', 'p')}",
                    seed=seed,
                    agents=6,
                    beta=beta,
                    intensity=intensity,
                    governance_mode="fixed",
                    elected_rule="damage_proportional",
                )

    # Arm D: rule elections at three governance levels.
    for level, mode, label in (
        ("g1", "election", "G1"),
        ("g2", "election+board", "G2"),
        ("g3", "full", "G3"),
    ):
        for model in ("qwen2.5-14b", "llama-3.1-8b", "mistral-7b"):
            for seed in (1, 2, 3):
                write_cell(
                    results,
                    arm="D",
                    model=model,
                    variant="P0_canonical",
                    condition=level,
                    seed=seed,
                    agents=6,
                    beta=1.6,
                    intensity=0.45,
                    governance_mode=mode,
                    elected_rule="cbdr",
                    level=label,
                )
    return results


@pytest.fixture(scope="module")
def _pipeline_cache():
    return {}


@pytest.fixture
def findings(synthetic_results):
    """Run the whole Phase-4 pipeline once per test module session."""
    out = synthetic_results.parent / "out"
    summary = run_all(synthetic_results, out)
    payload = json.loads((out / "revamp_findings.json").read_text(encoding="utf-8"))
    return summary, payload, out


class TestCellDiscovery:
    def test_discovers_every_cli_produced_cell(self, synthetic_results):
        cells = discover_cells(synthetic_results)
        assert len(cells) == 27 + 24 + 27

    def test_reads_the_factors_out_of_the_provenance_envelope(self, synthetic_results):
        cells = discover_cells(synthetic_results)
        first = cells[0]
        assert first["model"]
        assert first["prompt_variant"].startswith("P")
        assert first["seed_fingerprint"]
        assert first["arm"] in {"A", "B", "C", "D", "E"}

    def test_ignores_cells_without_a_provenance_envelope(self, tmp_path):
        """A run with no seed vector cannot enter a decomposition that uses one."""
        results = tmp_path / "results"
        results.mkdir()
        (
            results / "simulation_qwen_arm_a_p0_qwen_s1_seed1_6agents_6rounds_20260101_000000.json"
        ).write_text(json.dumps([{"round_number": 1, "agents": {}}]), encoding="utf-8")
        assert discover_cells(results) == []

    def test_arms_can_be_restricted(self, synthetic_results):
        arm_a = discover_cells(synthetic_results, arms={"A"})
        assert arm_a and all(c["arm"] == "A" for c in arm_a)

    def test_every_seed_fingerprint_is_distinct(self, synthetic_results):
        cells = discover_cells(synthetic_results)
        assert len({c["seed_fingerprint"] for c in cells}) == len(cells)


class TestHeadlineArtefacts:
    def test_the_four_artefacts_are_all_produced(self, findings):
        summary, payload, _out = findings
        assert summary["n_cells"] > 0
        assert payload["variance"]["decompositions"], "no decomposition"
        assert payload["mcpr"]["curve"], "no MCPR curve"
        assert "by_prompt_variant" in payload["deviations"]
        assert "adoption" in payload["governance"]

    def test_variance_decomposition_is_measurable(self, findings):
        _summary, payload, _out = findings
        result = payload["variance"]["decompositions"]["contribution_intensity"]
        assert 0.0 <= result["instrument_share"] <= 1.0
        assert 0.0 <= result["seed_share"] <= 1.0
        assert set(result["variance_shares"]) >= {"model", "prompt_variant", "condition", "seed"}

    def test_deviation_rate_is_measurable_per_variant(self, findings):
        _summary, payload, _out = findings
        by_variant = payload["deviations"]["by_prompt_variant"]
        assert set(by_variant) >= {"P0_canonical", "P1_lexical", "P2_minimal_control"}
        for row in by_variant.values():
            assert row["n"] > 0
            assert 0.0 <= row["deviation_rate"] <= 1.0

    def test_iteration_cross_check_passes(self, findings):
        summary, payload, _out = findings
        assert summary["iteration_cross_check_ok"] is True
        assert payload["deviations"]["iteration_cross_check"]

    def test_mcpr_curve_brackets_the_threshold(self, findings):
        _summary, payload, _out = findings
        assert payload["mcpr"]["n_cells_below_threshold"] > 0
        assert payload["mcpr"]["n_cells_above_threshold"] > 0
        curve = payload["mcpr"]["curve"]
        assert any(row["above_threshold"] for row in curve)

    def test_governance_rule_elections_are_counted(self, findings):
        _summary, payload, _out = findings
        adoption = payload["governance"]["adoption"]
        assert adoption["n_rule_elections"] > 0
        assert adoption["rule_shares"]

    def test_rule_adoption_is_summarised_per_model(self, findings):
        _summary, payload, _out = findings
        by_model = payload["governance"]["adoption_by_model"]
        assert by_model["modal_rule_by_model"]
        # Every family elected the same rule here, so the cross-family reading is
        # the "shared normative preference" branch.
        assert by_model["single_modal_rule_across_models"] is True

    def test_figures_are_written(self, findings):
        summary, _payload, _out = findings
        assert summary["figures"], "no figures were produced"
        for path in summary["figures"]:
            assert Path(path).exists()

    def test_tables_are_written(self, findings):
        _summary, _payload, out = findings
        tables = out / "tables"
        assert (tables / "run_level.csv").exists()
        assert (tables / "best_response_deviations.csv").exists()
        assert (tables / "governance_elections.csv").exists()


class TestGovernanceTables:
    def test_rejection_rate_is_reported_by_group(self, synthetic_results):
        """The breakdown by group is what pre-empts the obvious referee objection."""
        import pandas as pd

        from analysis.governance import rejection_by_group

        claims = pd.DataFrame(
            [
                {
                    "group": "developing",
                    "accepted": True,
                    "reason_code": "damage_substantiated",
                    "acceptance_share": 1.0,
                },
                {
                    "group": "developing",
                    "accepted": False,
                    "reason_code": "damage_inflated",
                    "acceptance_share": 0.0,
                },
                {
                    "group": "developed",
                    "accepted": True,
                    "reason_code": "damage_substantiated",
                    "acceptance_share": 1.0,
                },
            ]
        )
        result = rejection_by_group(claims)
        assert result["available"] is True
        assert set(result["by_group"]) == {"developing", "developed"}
        assert result["by_group"]["developing"]["rejection_incidence"] == pytest.approx(0.5)
        assert result["reason_codes"]["damage_inflated"] == 1

    def test_empty_claim_ledger_reports_unavailable_not_zero(self):
        import pandas as pd

        from analysis.governance import rejection_by_group

        assert rejection_by_group(pd.DataFrame())["available"] is False

    def test_wealth_gap_is_tagged_with_the_rule_in_force(self, synthetic_results):
        from analysis.governance import wealth_gap_by_rule
        from analysis.qwen_9seed.io import as_rounds, load_json

        cells = discover_cells(synthetic_results, arms={"D"})
        table = wealth_gap_by_rule(as_rounds(load_json(cells[0]["path"])))
        assert not table.empty
        assert "allocation_rule" in table.columns
        assert table["wealth_ratio"].notna().any()

    def test_payout_concentration_is_computable(self, synthetic_results):
        from analysis.governance import payout_allocation_table
        from analysis.qwen_9seed.io import as_rounds, load_json

        cells = discover_cells(synthetic_results, arms={"A"})
        table = payout_allocation_table(as_rounds(load_json(cells[0]["path"])))
        assert "payout_hhi" in table.columns

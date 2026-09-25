# Qwen2.5-14B nine-seed analysis package

This package analyzes only the nine root-level result files matching:

`simulation_qwen2.5-14b_Full_scnldf_sh1_ldf1_seed{1..9}_26agents_30rounds_*.json`

The raw JSON files are never modified. The independent replication unit is the run/seed (`n=9`); the 7,020 agent-round records are treated as nested, serially dependent observations.

## Reproduce everything

From the repository root, using the requested conda environment:

```powershell
$env:PYTHONPATH = "src"
& "C:\Users\uzii1\miniconda3\Scripts\conda.exe" run -n ml python -m analysis.qwen_9seed.run_all `
  --results-dir results `
  --output-dir analysis_outputs/qwen2_5_14b_9seed
```

The runner writes the input manifest, structural audit, tidy tables, run-level statistics, robustness checks, persistence diagnostics, machine-readable claim ledger, and figures. It fails before analysis if a structural accounting check fails.

After writing or editing the manuscript report, validate its links and headline values with:

```powershell
$env:PYTHONPATH = "src"
& "C:\Users\uzii1\miniconda3\Scripts\conda.exe" run -n ml python -m analysis.qwen_9seed.validate_report
```

## Main definitions

- `positive_contribution_share` is the proportion of agent-round records with `contribution > 0`.
- `pre_decision_intensity` is `contribution / floor(previous-round end wealth)`; round 1 uses `cumulative_payoff - payoff` to reconstruct the initial endowment. A zero cap is marked structurally ineligible and is excluded from the eligible-only intensity denominator.
- The JSON field `cooperation_rate` is retained as a source diagnostic. The implementation computes it from contribution divided by the post-payoff end-wealth cap, so it is not the positive-contributor rate.
- `eligible_ldf_coverage` is developing-agent payout divided by developing-agent gross damage. `system_ldf_coverage` uses all-agent damage and should not be interpreted as eligible-recipient coverage.
- LDF contribution is the same Stage-1 contribution credited to the fund, not an independent second contribution.
- ToM scores are same-model intent/action-consistency ratings. Gossip exposure is reconstructed as certain/possible bounds because the live bulletin and completion order were not serialized.
- SI/SFI is an assigned role in climate mode: developed agents are SI and developing agents are SFI. Role comparisons are descriptive, not causal institution effects.

## Important outputs

- `audit/run_audit.csv` and `audit/data_quality_checks.csv`: provenance, hashes, structural checks, accounting identities, parser flags, and shock/democracy checks.
- `tables/agent_round.csv` and `tables/round_metrics.csv`: tidy analysis tables.
- `analysis/run_metrics.csv`: one row per seed, the primary inferential table.
- `analysis/primary_contrasts.csv`: paired late-minus-early and shock-window contrasts with run-bootstrap intervals and exact sign-flip sensitivity.
- `analysis/event_associations.csv`: prospective ToM/gossip associations estimated within common seed-round-role cells; these are not causal effects.
- `analysis/reasoning_profile.csv`: text length, distinct-text counts, and template concentration for every reasoning field. Read this before interpreting `motif_summary.csv`, because a short templated rationale makes motif prevalence a measure of wording.
- `robustness/`: leave-one-seed-out, window, denominator, parser-clean, and event-threshold checks.
- `persistence/`: transition and zero-episode diagnostics.
- `key_claims.json`: machine-readable claim ledger used to cross-check the Markdown report.
- `report_validation.json`: automated checks for report headline tokens, figure links, artifact links, and scope consistency.
- `figures/`: publication-oriented PNG figures generated from the derived tables.

## Report

The paper-oriented write-up is `docs/paper/qwen2_5_14b_9seed_results_report.md`. Every number in it is a value in `key_claims.json` or one of the analysis tables.

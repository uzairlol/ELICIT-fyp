# 01 — Repository Inventory (20260804)

Inventory for analyzing `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json`.

## Simulation outputs

| Path | Role |
|------|------|
| `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json` | Canonical seed2 Full LDF run |
| `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` | Seed1 baseline |
| `docs/raw documentation/20260731/` | Seed1 analysis pack |
| `docs/raw documentation/20260804/` | This pack |

## Engine surfaces used

| Path | Role |
|------|------|
| `src/core/` | Environment, institutions, LDF, parameters |
| `src/modules/` | ToM, gossip, democracy |
| `src/prompts/` | Decision prompts |
| `src/parsing/` | Response parsers (incl. Stage-2 semantic retries) |
| `src/analysis/` | Flatten/plot utilities |
| `dashboard/` | Interactive visualizer patterns |

## Analysis scripts (this pack)

| Script | Purpose |
|--------|---------|
| `scripts/extract_20260804_results.py` | Flatten JSON → tables + evidence IDs |
| `scripts/analyze_20260804_contributions.py` | Contribution / SI–SFI / shock plots |
| `scripts/analyze_20260804_reputation_gossip.py` | Event study + motifs |
| `scripts/analyze_20260804_democracy.py` | Proposals, votes, adopted rules |
| `scripts/analyze_20260804_language.py` | Wordclouds + keyness |
| `scripts/analyze_20260804_norm_stability.py` | Cooperation stability diagnostics |
| `scripts/analyze_20260804_zero_contributions.py` | Zero episodes |
| `scripts/analyze_20260804_dashboard_dimensions.py` | Wealth/Gini/LDF/enforcement |
| `scripts/cross_seed_comparison.py` | Seed1 vs seed2 statistics + plots |

[Evidence: `tables/extraction_issues.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=inventory]

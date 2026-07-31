# 01 — Repository Inventory (20260731)

Prompt 0 inventory: candidate datasets, selection rationale, reusable code, and access limitations.
No behavioural analysis.

---

## Candidate `20260731` result files

| # | Path | Size (bytes) | SHA256 | Notes |
|---|------|--------------|--------|-------|
| A | `results/To_Use/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` | 4,753,997 | `14FDCECAFBFAAAC6367FA2BE1E9441C439D911C1D5AAE5AA3A47C3C9507D9757` | Curated copy under `To_Use/` |
| B | `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` | 4,753,997 | `14FDCECAFBFAAAC6367FA2BE1E9441C439D911C1D5AAE5AA3A47C3C9507D9757` | Root-level duplicate |

Search coverage: repository-wide glob for `*20260731*`. No other matching result files, logs, configs, checkpoints, or spill dumps found.

Filename decode (consistent with `run_experiments` naming conventions):

- Model tag: `llama3.1_8b` → `llama3.1:8b`
- Condition: `Full`
- Scenario: `scnldf`
- Shocks: `sh1`
- LDF: `ldf1`
- Seed: `seed1`
- Agents: `26agents`
- Rounds: `30rounds`
- Timestamp: `20260731_013853`

---

## Why the selected dataset was chosen

**Selected:** Candidate A — `results/To_Use/...20260731_013853.json`

Reasons:

1. It is the only unique `20260731` run content in the repository (A and B are identical bytes).
2. Placement under `results/To_Use/` indicates intentional curation for analysis use.
3. JSON structure validates as a 30-round, 26-agent LDF Full run with shocks and democracy fields present.
4. No competing `20260731` timestamp or alternate seed/condition exists to create a choice conflict.

---

## Excluded datasets and reasons

| Path / pattern | Reason excluded |
|----------------|-----------------|
| Candidate B (root duplicate) | Identical SHA256 to A; excluded as working copy to avoid double-counting |
| `results/Baseline/*` (e.g. `20260603` abstract 7-agent run) | Different date, scenario (`scnabstract`), agent count, shock/LDF flags |
| Any other `results/**` files without `20260731` | Outside the requested analysis date lock |
| `results/_spill/` | Directory exists, but **zero** files matching `20260731` |
| `src/debug_logs/` | No durable run log tied to this timestamp in-repo |
| Current `src/core/parameters.py` defaults | Not a dataset; also mismatch this run’s agent/scenario/LDF flags |

---

## Reusable analysis scripts

| Path | Reuse potential for later prompts |
|------|-----------------------------------|
| `src/analysis/export_ablation_metrics.py` | Filename parse + round/agent flatten → CSV; good base for Prompt 1 tables |
| `src/analysis/export_ablation_plots.py` | Ready-made contribution / LDF / reputation / sanction plots |
| `src/analysis/plot_results.py` | Single-file exploratory plotting |
| `src/analysis/plot_wordcloud.py` | Reasoning text tokenisation / wordclouds (Prompt 6) |

Limitations of existing analysis scripts relative to Prompt 1 needs:

- May not fully export proposal/vote panels, per-target punishment justifications, or belief-state expansions.
- Do not currently write into `docs/raw documentation/20260731/tables/`.
- Gossip bulletin extraction cannot come from this JSON (field absent).

---

## Reusable dashboard code

| Path | Notes |
|------|-------|
| `dashboard/index.html` | UI shell / chart containers |
| `dashboard/app.js` | Client-side loaders, KPIs, charts, democracy cards, wordclouds, sanction network |
| `dashboard/styles.css` | Presentation only |

Useful for Prompt 0 documentation of what is already visualised. **Not authoritative** for scientific formulas:

- Pass-through metrics: cooperation rate, Gini, LDF pool fields.
- Heuristics: trust-label classification, default reputation `5`.
- Missing: gossip views.
- LDF detection heuristic may false-negative if all `ldf_contributions_total == 0`.

---

## Missing or malformed files

| Item | Status |
|------|--------|
| Sidecar config for `20260731_013853` | Missing |
| Dedicated run log for this timestamp | Missing |
| Spill JSONL for this run | Missing under `results/_spill/` |
| Gossip bulletin in results JSON | Missing field (code module exists) |
| Agent ID type | Present but string keys (`"0"`…`"25"`), not integers — parsers must coerce carefully |
| Round-0 `tom_scores` for sampled agent `"0"` | Empty object in spot check — may be timing/ordering; not labelled malformed without fuller scan |
| Duplicate result copy | Present but not malformed |

No corruption detected in the selected JSON (loads cleanly; 30 rounds; 26 agents each).

---

## Data-access limitations

1. **Single-seed lock:** only seed 1 for this timestamp; no within-date replication.
2. **Config reconstruction incomplete:** must infer historical settings from filename + in-file fields; current `parameters.py` defaults differ.
3. **Gossip not exported:** social-pressure analysis depending on bulletin contents cannot be reconstructed from this file alone.
4. **Large nested JSON:** ~4.8 MB; extraction should stream/flatten deterministically rather than manual browsing.
5. **Dashboard is not a data API:** analysis scripts should read the JSON directly, not scrape the dashboard.
6. **Do not modify originals:** all derived tables/plots/evidence must live under `docs/raw documentation/20260731/`.

---

## Analysis workspace created this stage

```text
docs/raw documentation/20260731/
├── 00_project_memory.md
├── 01_repository_inventory.md
├── scripts/
├── tables/
├── plots/
├── evidence/
├── architecture/
├── quantitative_analysis/
├── qualitative_analysis/
├── theory/
└── synthesis/
```

---

## Prompt 0 stop boundary

This inventory ends Prompt 0. No extraction pipeline, architecture write-up, or results interpretation has been started.

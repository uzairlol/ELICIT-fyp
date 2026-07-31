# 00 — Project Memory (20260731)

Persistent memory file for all later analysis stages of the `20260731` run.
Prompt 0 only: repository audit, dataset lock, and analysis setup. No behavioural interpretation.

---

## Confirmed analysis run

| Field | Value |
|-------|-------|
| Exact results file (canonical) | `results/To_Use/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` |
| Duplicate copy (identical SHA256) | `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` |
| Exact run name | `simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853` |
| Run date / timestamp | `20260731_013853` (embedded in filename) |
| Configuration path | No sidecar config for this timestamp. Run identity encoded in filename; live defaults live in `src/core/parameters.py`; batch/CLI composition in `src/run_experiments.py` |
| Model (filename + params) | `llama3.1:8b` |
| Number of agents | 26 (verified in JSON and filename) |
| Number of rounds | 30 (verified in JSON and filename) |
| Seed | 1 (from filename `seed1`) |
| Scenario / flags | `scnldf` (LDF scenario), `sh1` (shocks on), `ldf1` (LDF on), condition `Full` |
| Agent categories | `agent_group`: `developed` (12), `developing` (14) at round 0 |
| Institution at round 0 | `SI` (12), `SFI` (14) — matches developed→SI / developing→SFI routing described in README for climate/LDF mode |
| Output format | JSON array of 30 round objects; agent keys are string IDs (`"0"` … `"25"`) |
| SHA256 | `14FDCECAFBFAAAC6367FA2BE1E9441C439D911C1D5AAE5AA3A47C3C9507D9757` |
| File size | 4,753,997 bytes |

Shock rounds observed in this file: round 5 (severity 0.1), round 10 (severity 0.2).

Democracy / `constitutional_change` present on rounds: 5, 10, 15, 20, 25, 30.

---

## Repository map

| Path | Purpose |
|------|---------|
| `src/` | Simulation engine, LLM clients, prompts, parsers, modules, analysis scripts |
| `src/core/` | Environment, agents, institutions, LDF, subsidy, parameters, scenario config |
| `src/modules/` | ToM, gossip, democracy, oracle |
| `src/prompts/` | Prompt construction |
| `src/parsing/` | LLM response parsers |
| `src/llm/` | Ollama client and retry helpers |
| `src/analysis/` | Reusable parse / aggregate / plot utilities |
| `src/main.py` | Single-run entry |
| `src/run_experiments.py` | Batch sweeps |
| `results/` | Simulation JSON outputs |
| `results/To_Use/` | Curated result copies selected for analysis |
| `results/Baseline/` | Earlier baseline runs (not this dataset) |
| `results/_spill/` | Optional spill-to-disk round dumps (none matching `20260731`) |
| `dashboard/` | Static HTML/JS visualizer (`index.html`, `app.js`, `styles.css`) |
| `docs/` | Project docs and PDFs |
| `docs/raw documentation/` | Existing raw documentation directory (this analysis lives here) |
| `analysis_outputs/` | Generated metrics/plots (local / often gitignored) |
| `README.md` | Project overview and folder structure |
| `requirements.txt` | Python dependencies |

---

## Existing analysis utilities

Located under `src/analysis/`:

| Script | Role |
|--------|------|
| `export_ablation_metrics.py` | Parse result filenames; flatten JSON → round/agent DataFrames; write CSVs under `analysis_outputs/metrics/` |
| `export_ablation_plots.py` | Same flatten path; export PNGs (institutions, contributions, payoffs, reputation, punishments, LDF flows, damage coverage) |
| `plot_results.py` | Interactive CLI: load one JSON; plot core series + LDF extras when present |
| `plot_wordcloud.py` | GUI file picker; parse reasoning/facts/belief text; per-round wordclouds |
| `__init__.py` | Package marker |

Reusable pattern: load list-of-rounds JSON → flatten with `source_file` / run metadata → CSV or PNG. Prefer reuse in Prompt 1 rather than rewriting parsers unless incomplete for reasoning/gossip/proposals.

---

## Existing dashboard utilities

Located under `dashboard/` (`app.js` is the calculation surface).

### Data loading

| Function | What it does |
|----------|----------------|
| `loadFile` | `FileReader` → `JSON.parse` into `State.rounds` |
| `processData` | Builds `State.meta` / `State.agents`; flags LDF/shocks/democracy from field presence |

No server fetch; user drops a local simulation JSON.

### Plots / panels (do not treat as ground-truth formulas)

| UI / chart | Appears to show | Underlying transform (dashboard) |
|------------|-----------------|----------------------------------|
| Cooperation / Gini | `cooperation_rate×100` vs `gini_wealth` | Pass-through from JSON |
| Membership | SI vs SFI member counts | Lengths of `si_members` / `sfi_members` |
| Contributions | SI vs SFI totals | `si_total_contribution` / `sfi_total_contribution` |
| Wealth | Per-agent + group averages | Mean wealth by `agent_group` |
| Reputation | Per-agent reputation | `reputation \|\| 5` default |
| LDF pool | Pool, contribs, payouts, gross damage | Pass-through LDF fields |
| LDF payouts / contribs | By developing / developed | Filter on `agent_group` |
| Sanctions timeline / top | Punish/reward aggregates | Sums of `assigned_*` / `received_*` |
| Beliefs / perception | Trust-label buckets | Keyword `trustClass` heuristic |
| Wealth gap | Developed − developing mean wealth | `max(0, mean_dev − mean_dvg)` |
| Damage vs payout | Cumulative damage vs LDF payout | Developing agents only |
| Democracy cards | Proposals / votes / winning rule | `constitutional_change` |
| Wordclouds | Token frequency from reasoning | Client tokenisation + stopwords |
| Sanction network | vis-network edges | Punish/reward edges; node size ∝ contribution |

### Explicit dashboard gaps / caveats

- **No gossip visualisation** and no `gossip` field usage in `app.js`.
- Gini, cooperation rate, reputation update rule, and shock damage physics are **not recomputed** in the dashboard; values are read from JSON.
- LDF mode detection: `any(ldf_contributions_total > 0)` — can miss LDF-enabled zero-contribution edge cases.
- Default reputation fill `5` if missing.

---

## Confirmed terminology

Definitions below are taken from code or configuration only. No name-based guessing beyond quoted text.

### SI

From `src/core/institution.py`:

> “This module defines the Institution classes for the Sanctioning Institution (SI) and the Sanction-Free Institution (SFI).”
> “The Sanctioning Institution allows agents to assign punishments and rewards after contributions.”

Class: `SanctioningInstitution`. Choice string: `"SI"`.

LDF scenario display names (`src/core/scenario_config.py`):

- `"si_name": "Group B (Binding Climate Treaty)"`
- `"si_desc": "Strict enforcement protocol allowing trade tariffs (sanctions) or economic aid (rewards) towards other nations"`

### SFI

From `src/core/institution.py`:

> “The Sanction-Free Institution does not have mechanisms for punishment or reward.”

Class: `SanctionFreeInstitution`. Choice string: `"SFI"`.

LDF scenario display names:

- `"sfi_name": "Group A (Non-Binding Climate Agreement)"`
- `"sfi_desc": "No possibility to impose trade tariffs (sanctions) or economic aid (rewards) on other nations"`

### LDF

From `src/core/loss_damage_fund.py`:

> “Persistent Loss & Damage Fund for climate-shock compensation.”

State variable: `pool_balance`. Results fields: `ldf_pool_start`, `ldf_pool_end`, `ldf_contributions_total`, `ldf_payouts_total`, plus per-agent `ldf_contribution_round`, `ldf_payout_round`. Filename flag `ldf1` = LDF on.

### ToM

From `src/modules/tom_module.py`:

> “Theory of Mind (ToM) Module… each agent silently ‘audits’ every other agent for behavioural consistency (hypocrisy detection)… The LLM scores each agent pair on a trustworthiness scale of 1-10. These scores are stored on each Agent as `tom_scores` and averaged into a `reputation` value…”

### Gossip

From `src/modules/gossip_module.py`:

> “Handles the aggregation and distribution of 'Social Gossip' derived from the Theory of Mind (ToM) audits. Converts private trust-scores into public social pressure.”

Parameter: `GOSSIP_TRIGGER_SCORE = 7.0` — “Only share gossip for trust scores <= this value” (`parameters.py`).

**Data note:** the selected results JSON has **no top-level or per-agent `gossip` key**. Gossip may be prompt-injected at runtime but is not persisted in this export. Treat as an open question for extraction stages.

### Reputation

From `src/core/environment.py` / agent init:

- Default: `self.reputation = 5.0` (peer-average trust / neutral default in agent code comments).
- Update: “Update each agent's reputation as the average of all incoming scores” (`environment.py`).

### Democracy / proposals / votes / rules

From `src/modules/democracy_module.py` and parameters:

- `DEMOCRACY_ENABLED`, `DEMOCRACY_INTERVAL = 5`.
- Results field `constitutional_change` with keys: `proposals`, `votes`, `tally`, `winning_proposal`, `applied`.

### Climatic / climate shocks

Code and parameters use **“climate shock”** (not “climatic”). Environment applies shocks via `_apply_climate_shock_and_ldf()`; results fields: `shock_occurred`, `shock_severity`, `gross_damage_total`, `net_damage_total`, per-agent `climate_damage_taken_round`, `climate_damage_taken_cumulative`. Filename `sh1` = shocks on.

### Contribution

Stage-1 public-goods contribution stored as agent `contribution`; institution aggregates `si_total_contribution` / `sfi_total_contribution`. Separate LDF deposit amounts appear as `ldf_contribution_round` / `ldf_contributions_total`.

### Institutional choice

Agent field `institution_choice` ∈ {`"SI"`, `"SFI"`}. Membership lists: `si_members`, `sfi_members`.

### Fund balance

Not named “fund balance” in code. LDF uses `pool_balance`, exported as `ldf_pool_start` / `ldf_pool_end`.

### Redistribution

Subsidy module / parameters: subsidy redistributes a fraction of the punishment pool to top contributors (`SUBSIDY_ENABLED`, democracy-editable `SUBSIDY_FRACTION`). Agent field: `subsidy`. Separate from LDF payout redistribution (`ldf_payout_round`).

---

## Confirmed model details

| Detail | Status | Source |
|--------|--------|--------|
| Model name | `llama3.1:8b` | Filename + `parameters.LLM_MODEL` |
| Model size | 8B (tag) | Model tag only; no separate size config |
| Instruct / base | Not verified beyond Ollama tag `llama3.1:8b` | Open question |
| Quantisation | Not verified in repo for this run | Open question |
| Execution | Local Ollama via `LLM_BASE_URL = "http://localhost:11434/v1"` | `parameters.py` (current tree) |
| Timeout | `OLLAMA_REQUEST_TIMEOUT_SECONDS = 300.0` | Current `parameters.py` (may differ from historical run) |
| Context | `OLLAMA_NUM_CTX = 4096` | Current `parameters.py` |
| Parallelism | `OLLAMA_NUM_PARALLEL = 4`, `LLM_MAX_CONCURRENCY = 2`, `TOM_MAX_CONCURRENCY = 4` | Current `parameters.py` |

**Caution:** current `parameters.py` defaults (`NUM_AGENTS = 7`, `SCENARIO = "abstract"`, `SEED = 42`, `LDF_ENABLED = False`, `CLIMATE_SHOCK_ENABLED = False`) do **not** match this run’s filename. The run was almost certainly launched via experiment CLI overrides. Do not treat current defaults as the historical run config without further evidence.

---

## Data fields

### Round-level (always present in this file)

`round_number`, `si_members`, `sfi_members`, `si_total_contribution`, `sfi_total_contribution`, `si_avg_contribution`, `sfi_avg_contribution`, `shock_occurred`, `shock_severity`, `gross_damage_total`, `net_damage_total`, `ldf_pool_start`, `ldf_contributions_total`, `ldf_payouts_total`, `ldf_pool_end`, `agents`, `cooperation_rate`, `gini_wealth`

### Round-level (conditional)

`constitutional_change` on democracy rounds, with:

- `proposals[]`: `rule`, `new_value`, `reason`, `proposer`
- `votes`: voter → proposal index / choice
- `tally`
- `winning_proposal`
- `applied` (bool)

### Agent-level (this file)

`agent_group`, `institution_choice`, `contribution`, `contribution_capacity`, `wealth`, `reputation`, `payoff`, `stage1_payoff`, `stage2_payoff`, `cumulative_payoff`, `rank`, `strategy`, `subsidy`, `assigned_punishments`, `assigned_rewards`, `received_punishments`, `received_rewards`, `rule_of_law_blocks`, `tom_scores`, `belief_state` (`trust_levels`, `institutional_strategy`, `observations`), `historical_emissions`, `vulnerability`, `climate_damage_taken_round`, `climate_damage_taken_cumulative`, `ldf_contribution_round`, `ldf_payout_round`, `net_climate_transfer_round`, reasoning/facts/parser meta fields (`institution_*`, `contribution_*`, `punishment_*`, `deanonymized_punishment_reasoning`, `punishment_justifications`), `parsing_failures`, `round_number`

### Not present in this export (verified absence)

- Top-level or agent-level `gossip` / gossip bulletin
- Separate utility field distinct from `payoff` / stage payoffs
- Sidecar run log or checkpoint for `20260731`
- Matching files under `results/_spill/` for this timestamp

---

## Evidence convention

All later Markdown reports must cite sources in this form:

```text
[Evidence: <source-file> | run=<run> | round=<round> | agent=<agent-id> | record=<record-id>]
```

Examples:

```text
[Evidence: results/To_Use/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json | run=20260731_013853 | round=5 | agent=4 | record=constitutional_change.proposals[0]]
```

```text
[Evidence: src/core/institution.py | run=n/a | round=n/a | agent=n/a | record=module_docstring]
```

Rules:

- Every substantive empirical claim needs at least one Evidence tag.
- `record` should identify the JSON path or code symbol when possible.
- If a field is missing, say so explicitly; do not invent values.

---

## Confirmed facts

1. Exactly two repository files contain `20260731` in the name; they are byte-identical (same SHA256).
2. Canonical analysis path is the curated copy under `results/To_Use/`.
3. The run is a 26-agent, 30-round LDF Full simulation with shocks and LDF enabled, seed 1, model tag `llama3.1:8b`.
4. Agent groups in-file: 12 developed, 14 developing; institutions at round 0: 12 SI, 14 SFI.
5. Climate shocks occur at rounds 5 and 10 in this file.
6. Democracy / constitutional change appears every 5 rounds (5…30) in this file.
7. Existing raw documentation directory is `docs/raw documentation` (space in name).
8. SI and SFI meanings above are supported by `institution.py` and `scenario_config.py`.
9. Gossip module exists in code, but gossip bulletin is not stored in this results JSON.
10. Dashboard does not visualise gossip and does not recompute core economic formulas from first principles.
11. Stage-1 LDF contribution cap = `max(MIN_CONTRIBUTION, int(wealth))` with `MIN_CONTRIBUTION = 0` (`agent.get_stage1_contribution_cap`).
12. `contribution_capacity` is a static group index (1.0 / 0.10), not the stage-1 currency budget.
13. Agents see own LDF contribution/payout/damage in prompts; they do **not** see numeric `ldf_pool_start/end`.
14. Extraction yields 780 agent-round rows, 3854 reasoning blocks, 14 proposals, 156 votes, 6 adopted rules; developed↔SI / developing↔SFI holds all rounds.
15. Round 1 has empty `tom_scores` for all 26 agents; later rounds are populated in the export.

---

## Confirmed formulas (Prompt 1)

- **Stage-1 cap (LDF):** \(\max(0, \lfloor wealth \rfloor)\) at decision time.
- **Analyst proportional columns:** `prop_of_wealth`, `prop_of_capacity`, `prop_of_stage1_cap` (see `02_data_schema.md`); none are stored in the raw JSON.
- **Reputation:** mean of incoming ToM scores when present; default init 5.0.
- **LDF pool (results):** `LossDamageFund.pool_balance` → `ldf_pool_start` / `ldf_pool_end`.

---

## Confirmed data visibility (Prompt 1)

| Information | Visible to agents? | Source |
|-------------|--------------------|--------|
| Own wealth, group, vulnerability, emissions | Yes | `_build_common_snapshot` |
| Own LDF contribution / payout / climate damage (round) | Yes | `_build_common_snapshot` |
| Numeric LDF pool balance | **No** | Not in prompts; only in results |
| That contributions deposit into LDF pool | Yes (qualitative reminder) | `_append_climate_role_guidance` |
| Gossip bulletin | Code can inject; **not in this JSON** | export gap |

---

## Exact agent-type definitions used in tables

- `agent_group`: `developed` | `developing`
- `institution_choice`: `SI` | `SFI`
- This run: developed always SI; developing always SFI (0 routing mismatches)

---

## Open questions

1. Exact Ollama quantisation / instruct-vs-base details for the model binary used on 2026-07-31.
2. Exact historical `parameters.py` / CLI argument set for this run (current repo defaults disagree with filename).
3. Whether gossip bulletins were shown to agents during the run but omitted from JSON export.
4. Decision-time wealth reconstruction for exact proportional contribution (end-of-round wealth causes ~35 approximate over-cap INFO flags).
5. Exact definitions of stored `cooperation_rate` and `gini_wealth` (deferred to architecture stage if needed).
6. No dedicated run log / metadata sidecar found for `20260731`.

**Resolved in Prompt 1:**

- Proportional contribution has no single stored denominator; simulation uses wealth-based stage-1 cap; extractor emits multiple labelled ratios.
- Agents do not observe numeric fund balance.
- Empty `tom_scores` concentrated in round 1 (26/26).

---

## Unresolved schema issues

- Gossip bulletin not reconstructible from this export
- Stage-1 cap validation using end-of-round wealth is approximate
- No sidecar parameter dump for the historical run

---

## Confirmed architectural and mathematical facts (Prompt 2)

1. Round order: institution → contribute → PG → SI sanctions → subsidy → shock/LDF → payoffs → record/beliefs → ToM/gossip → (interval) democracy.
2. LDF/climate institution membership is **forced** by `agent_group` (developed→SI, developing→SFI), not LLM-chosen.
3. Stage-1 climate payoff: \(\pi_1 = (m C)/n - c_i\); MCPR \(= m/n\) is prompt-only.
4. Stage-2: received effect = tokens × EFFECT; sender pays tokens × COST; climate \(\pi_2\) has no free endowment.
5. Subsidy: floor of SI punishment-token costs × `SUBSIDY_FRACTION`, split among top `SUBSIDY_TOP_N` SI contributors.
6. Shock damage: `CLIMATE_DAMAGE_BASE * severity * vulnerability` (deterministic schedule path).
7. LDF deposit amount equals Stage-1 `contribution` (no separate levy); payouts to developing only, coverage-capped.
8. Wealth: add \(\pi_1\), then add \(\pi_2 + \mathrm{subsidy} + \mathrm{payout} - d\), floor at 0.
9. Reputation = mean incoming ToM scores; gossip = lowest scores ≤ trigger, top-k; target sees `"YOU"`.
10. Democracy: **all** agents propose/vote in code (docstring SI-only is wrong); plurality + live `parameters` write.
11. Agents never see numeric LDF pool; see own LDF flows/damage only.
12. One \(c_i\) dual-feeds public good and LDF pool when collection is open.

### Prompt 3 quantitative facts (associational, single run)

13. Mean `prop_of_wealth` ≈ 0.291 (SI, n=360) vs 0.296 (SFI, n=420); Hedges’ g ≈ −0.008; CIs overlap.
14. SFI median prop (0.034) ≪ mean — right-skew; SI zeros 6.4% vs SFI 16.2% of agent-rounds.
15. Absolute mean contribution SI ≈ 1.20e7 vs SFI ≈ 8.14e4 (wealth scale), not proportional effort.
16. Shocks only at rounds 5 (sev 0.1) and 10 (sev 0.2); both also democracy rounds.
17. After R5: SI mean prop falls (R6 zeros 41.7%); SFI mean rise is outlier-fragile (median Δ≈0).
18. Around R10: both elevate during; SI more often increases post vs pre (8/12) than SFI.
19. Analysis metric decision: primary = `prop_of_wealth`; institution contrasts confounded with developed/developing.

### Prompt 4 facts (associational)

20. Gossip bulletin absent from JSON; reconstructed from `tom_scores` with trigger ≤7, top-5 (tie-order approximate).
21. Bad-rep definition used: \(\rho < 4\) (below default 5); also \(\Delta\rho \le -1\).
22. After bad_rep / gossip_target / rep_drop, mean immediate Δ prop is **negative** (SI and SFI); frac Δ>0 ≈ 0.31–0.39.
23. Diff-in-diff vs co-round controls also negative for affected agents.
24. Post-event contribution reasoning rarely mentions reputation/gossip; opportunistic tokens more common (29 vs 3).
25. 54 cases of cooperative language with zero contribution; 0 empty-reasoning positive contributions.

### Prompt 5 facts

26. 14 proposals / 6 democracy rounds / 6 adopted; only 2–3 proposals reach each ballot.
27. Adopted path: subsidy fraction ↑ (0.3→0.4→0.6), LDF equity ↑ (0.5→0.7), LDF damage weight 1.5; punishment-weakening (EFFECT→1) proposed twice, never adopted.
28. Proposers: 8 SI + 6 SFI; mean proposer prop 0.36 vs population 0.29.
29. Membership still forced — democracy changes parameters, not SI↔SFI assignment.
30. Stage-2 enforcement is costly; ToM/gossip/voting are not. Mean corr(prop, enforcement spend)≈0.14; top-quartile prop agents pay ~35% of SI enforcement tokens.
31. Vote same-group-as-proposer rate ≈0.51 (near base rate).

---

## Analysis decisions

| Decision | Rationale |
|----------|-----------|
| Select `results/To_Use/...20260731_013853.json` as canonical | Curated folder + identical hash to root copy |
| Exclude root duplicate as working copy | Same bytes; avoid double-counting |
| Do not invent SI/SFI meanings beyond code quotes | Prompt 0 non-negotiable rule |
| Do not interpret LDF effectiveness yet | Prompt 0–1 scope |
| Prefer existing `src/analysis` flatteners in later stages | Avoid duplicate parsers unless incomplete |
| Treat dashboard metrics as display helpers, not authoritative formulas | Dashboard mostly pass-through |
| Emit three proportional columns, not one | Denominator ambiguity; label as analyst-derived |
| Gossip CSV header-only | Field absent from results JSON |
| Dedicated extractor under `docs/.../scripts/` | Ablation exporter incomplete for reasoning/proposals/evidence IDs |
| Prompt 3 primary metric = `prop_of_wealth` | Comparable across wealth scales; absolute used only with confound warning |
| No causal SI vs SFI claims | Forced routing ⇒ perfect collinearity with agent_group |
| Reconstruct gossip from tom_scores | Only feasible bulletin proxy; document tie-order limit |
| Bad-rep threshold = 4.0 | Anchored below code default neutral 5.0; disclosed analyst choice |
| Code PUNISHMENT_EFFECT proposals as weakening | In-run values move 3→1 vs parameter default |

---

## Completed outputs

Prompt 0:

- `docs/raw documentation/20260731/` folder tree (`scripts`, `tables`, `plots`, `evidence`, `architecture`, `quantitative_analysis`, `qualitative_analysis`, `theory`, `synthesis`)
- `docs/raw documentation/20260731/00_project_memory.md` (this file)
- `docs/raw documentation/20260731/01_repository_inventory.md`

Prompt 1:

- `docs/raw documentation/20260731/scripts/extract_20260731_results.py`
- `docs/raw documentation/20260731/02_data_schema.md`
- `docs/raw documentation/20260731/03_extraction_pipeline.md`
- `docs/raw documentation/20260731/tables/*.csv` (including `data_quality_summary.csv`)
- `docs/raw documentation/20260731/evidence/reasoning_block_index.md`
- `docs/raw documentation/20260731/evidence/malformed_or_missing_records.md`
- `docs/raw documentation/20260731/tables/reasoning_blocks.csv`

Prompt 2:

- `docs/raw documentation/20260731/architecture/04_system_architecture.md`
- `docs/raw documentation/20260731/architecture/05_mathematical_model.md`
- `docs/raw documentation/20260731/architecture/06_agent_information_boundaries.md`
- `docs/raw documentation/20260731/architecture/07_module_interaction_map.md`

Prompt 3:

- `docs/raw documentation/20260731/scripts/analyze_20260731_contributions.py`
- `docs/raw documentation/20260731/quantitative_analysis/08_contribution_trajectories.md`
- `docs/raw documentation/20260731/quantitative_analysis/09_si_sfi_comparison.md`
- `docs/raw documentation/20260731/quantitative_analysis/10_climatic_shock_event_study.md`
- Tables: `contribution_round_summary.csv`, `contribution_agent_persistence.csv`, `si_sfi_*.csv/json`, `shock_event_study.csv`, `shock_agent_deltas.csv`, `prompt3_numeric_summary.json`
- Plots: `plots/contrib_*.png`, `plots/shock_delta_boxplot.png`

Prompt 4:

- `docs/raw documentation/20260731/scripts/analyze_20260731_reputation_gossip.py`
- `docs/raw documentation/20260731/qualitative_analysis/11_reputation_and_gossip_events.md`
- `docs/raw documentation/20260731/qualitative_analysis/12_agent_strategy_profiles.md`
- `docs/raw documentation/20260731/qualitative_analysis/13_reasoning_action_consistency.md`
- `docs/raw documentation/20260731/evidence/reputation_gossip_reasoning_excerpts.md`
- Tables: `gossip_bulletins_reconstructed.csv`, `reputation_gossip_*.csv`, `agent_strategy_profiles.csv`, `reasoning_action_flags.csv`, `prompt4_numeric_summary.json`
- Plots: `reputation_mean_trajectories.png`, `gossip_target_frequency.png`, `reputation_event_deltas.png`

Prompt 5:

- `docs/raw documentation/20260731/scripts/analyze_20260731_democracy.py`
- `docs/raw documentation/20260731/qualitative_analysis/14_proposal_trends.md`
- `docs/raw documentation/20260731/qualitative_analysis/15_proposer_profiles_and_reasoning.md`
- `docs/raw documentation/20260731/qualitative_analysis/16_institutional_choice_si_vs_sfi.md`
- `docs/raw documentation/20260731/qualitative_analysis/17_enforcement_as_public_good.md`
- `docs/raw documentation/20260731/qualitative_analysis/18_political_economy_of_governance.md`
- Tables: `proposals_coded.csv`, `votes_parsed.csv`, `enforcement_burden_*.csv`, `post_adoption_prop_changes.csv`, `prompt5_numeric_summary.json`
- Plots: `proposal_categories_timeline.png`, `adopted_rules_timeline.png`, `proposers_by_institution.png`, `enforcement_burden.png`

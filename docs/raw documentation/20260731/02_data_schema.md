# 02 — Data Schema (20260731)

Schema for the locked run and derived analysis tables. No behavioural interpretation.

**Source:** `results/To_Use/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json`  
**Run:** `20260731_013853`

---

## 1. Raw results JSON

### Shape

- Top level: JSON **array** of 30 round objects
- Round numbers: **1 … 30**
- Agent map keys: **strings** (`"0"` … `"25"`)
- Units: LDF scenario currency (wealth / contributions / damage / LDF flows are numeric floats in the same unit as simulation wealth)

### Round-level fields

| Field | Type | Meaning | Notes |
|-------|------|---------|-------|
| `round_number` | int | Round index | 1-based in this file |
| `si_members` | list[int] | Agents in SI | Sanctioning Institution |
| `sfi_members` | list[int] | Agents in SFI | Sanction-Free Institution |
| `si_total_contribution` | float | Sum of SI contributions | Pass-through aggregate |
| `sfi_total_contribution` | float | Sum of SFI contributions | |
| `si_avg_contribution` | float | Mean SI contribution | |
| `sfi_avg_contribution` | float | Mean SFI contribution | |
| `shock_occurred` | bool | Climate shock this round | |
| `shock_severity` | float | Shock severity | 0 when no shock |
| `gross_damage_total` | float | Gross climate damage | |
| `net_damage_total` | float | Net damage after mechanisms | |
| `ldf_pool_start` | float | LDF `pool_balance` before round ops | Results only; not shown in agent prompts as a numeric balance |
| `ldf_contributions_total` | float | Total LDF deposits this round | |
| `ldf_payouts_total` | float | Total LDF payouts this round | |
| `ldf_pool_end` | float | LDF balance after round ops | |
| `agents` | object | Agent-id → agent record | |
| `cooperation_rate` | float | Simulation-computed cooperation metric | Formula not re-derived here |
| `gini_wealth` | float | Wealth Gini | Formula not re-derived here |
| `constitutional_change` | object\|absent | Democracy session | Present rounds 5,10,15,20,25,30 |

### `constitutional_change` fields

| Field | Type | Meaning |
|-------|------|---------|
| `proposals` | list | `{rule, new_value, reason, proposer}` |
| `votes` | object | voter_id → vote choice / proposal index |
| `tally` | object | vote tallies |
| `winning_proposal` | object | Winning `{rule, new_value, reason, proposer}` |
| `applied` | bool | Whether winning rule was applied |

### Agent-level fields (selected)

| Field | Type | Meaning |
|-------|------|---------|
| `agent_group` | str | `developed` or `developing` |
| `institution_choice` | str | `SI` or `SFI` |
| `contribution` | float | Stage-1 contribution amount |
| `contribution_capacity` | float | Static capacity index (1.0 developed / 0.10 developing); **not** the stage-1 decision budget |
| `wealth` | float | End-of-round wealth |
| `reputation` | float | Peer-average ToM score |
| `tom_scores` | object | Incoming ToM scores (may be empty early) |
| `belief_state` | object | `trust_levels`, `institutional_strategy`, `observations` |
| `payoff`, `stage1_payoff`, `stage2_payoff`, `cumulative_payoff` | float | Payoffs |
| `assigned_punishments` / `assigned_rewards` | object | Target → amount maps |
| `received_punishments` / `received_rewards` | float | Totals received |
| `subsidy` | float | SI subsidy redistribution |
| `ldf_contribution_round` / `ldf_payout_round` / `net_climate_transfer_round` | float | Per-agent LDF flows |
| `climate_damage_taken_round` / `_cumulative` | float | Damage |
| `*_reasoning`, `*_facts_used`, `punishment_justifications` | text/object | LLM traces |
| `parsing_failures` | any | Parser failure marker |

### Absent from this export

- `gossip` / `gossip_bulletin`
- Precomputed proportional contribution
- Numeric LDF pool balance inside agent-visible prompt snapshots (see §4)

---

## 2. Confirmed formulas (simulation)

### Stage-1 contribution cap (LDF / climate budget)

From `src/core/agent.py` `get_stage1_contribution_cap` and `src/prompts/prompt_generator.py` `_contribution_budget`:

\[
\text{stage1\_cap} = \max(\texttt{MIN\_CONTRIBUTION}, \lfloor \text{wealth} \rfloor)
\]

with `MIN_CONTRIBUTION = 0` in `parameters.py`.

Contribution is clamped to \([0, \text{stage1\_cap}]\) at decision time.

### `contribution_capacity` (distinct)

From `parameters.py` / `main.py`:

- Developed: `DEVELOPED_CONTRIBUTION_CAPACITY = 1.00`
- Developing: `DEVELOPING_CONTRIBUTION_CAPACITY = 0.10`

This is a **group attribute / index**, not the numeric token budget used in the contribution JSON contract.

### Analyst-derived proportional columns

The simulation does **not** store proportional contribution. Extractor emits:

| Column | Formula | Caveat |
|--------|---------|--------|
| `prop_of_wealth` | `contribution / wealth_end_of_round` | Wealth is **end-of-round** |
| `prop_of_capacity` | `contribution / contribution_capacity` | Capacity is 1.0 or 0.1 index |
| `prop_of_stage1_cap` | `contribution / max(0, int(wealth_end_of_round))` | Reconstructs cap from **end-of-round** wealth; decision-time wealth may differ |

Prefer `prop_of_wealth` or a future pre-contribution reconstruction for behavioural work; treat `prop_of_capacity` carefully because capacity is not a currency endowment.

### Reputation

`reputation = mean(incoming ToM scores)` when scores exist (`environment.py`). Default init 5.0.

### LDF pool (results-side)

`pool_balance` updated in `LossDamageFund`; exported as `ldf_pool_start` / `ldf_pool_end`.

---

## 3. Derived CSV tables

All under `docs/raw documentation/20260731/tables/`. Every row includes `run`, `source_file` where applicable.

| File | Grain | Row count (this run) |
|------|-------|----------------------|
| `agent_metadata.csv` | agent | 26 |
| `round_agent_state.csv` | agent × round | 780 |
| `contributions.csv` | agent × round | 780 |
| `fund_state.csv` | round | 30 |
| `reputation_events.csv` | agent × round | 780 |
| `proposals.csv` | proposal | 14 |
| `votes.csv` | vote | 156 |
| `adopted_rules.csv` | democracy round | 6 |
| `climatic_shocks.csv` | round | 30 |
| `agent_actions.csv` | agent × round | 780 |
| `payoffs.csv` | agent × round | 780 |
| `redistribution.csv` | agent × round | 780 |
| `institutional_state.csv` | round | 30 |
| `reasoning_blocks.csv` | reasoning block | 3854 |
| `gossip_bulletins.csv` | (empty) | 0 |
| `data_quality_summary.csv` | check | (validation) |

---

## 4. Agent visibility of the fund balance

**Verdict: agents do not observe the numeric LDF pool balance.**

Verified:

1. `_build_common_snapshot` shows own wealth, own LDF contribution/payout this round, and own climate damage — **not** `ldf_pool_start/end`  
   [Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_build_common_snapshot]
2. LDF reminder states that contributions are deposited into the pool, without stating current pool size  
   [Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_append_climate_role_guidance]
3. Round feedback / anonymous peer data in `environment.py` include peer contributions and payoffs, not pool balance  
   [Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=anonymous_entry]
4. `ldf_pool_*` exists in **results JSON for analysts**, not as an agent prompt field

Agents **can** see their own round LDF contribution and payout amounts in the decision snapshot.

---

## 5. Agent-type definitions used in tables

| Field | Values | Definition source |
|-------|--------|-------------------|
| `agent_group` | `developed`, `developing` | Results + LDF setup in `main.py` |
| `institution_choice` | `SI`, `SFI` | `institution.py` / agent choice |
| Routing in this run | developed → SI; developing → SFI every round | Verified 0 mismatches in extraction |

---

## 6. Known limitations

1. End-of-round wealth ≠ decision-time wealth → ~35 approximate over-cap flags (INFO, may false-positive).
2. Gossip not exportable from this JSON.
3. Round-1 `tom_scores` empty for all 26 agents (timing of first audit vs save).
4. `cooperation_rate` / `gini_wealth` meanings taken as stored; formulas deferred if needed later.
5. Historical exact CLI parameter file for this run remains unavailable (Prompt 0 open question).

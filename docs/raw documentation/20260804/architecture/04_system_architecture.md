# 04 â€” System Architecture (20260804)

Evidence-backed description of how the ELICIT simulation is implemented.
Focus: modules, information flow, and state updates. No results interpretation.

**Canonical run context:** LDF Full, shocks on, LDF on, 26 agents, 30 rounds  
[Evidence: `docs/raw documentation/20260804/00_project_memory.md` | run=20260804_024555 | round=n/a | agent=n/a | record=Confirmed_analysis_run]

---

## Distinction legend

| Label | Meaning |
|-------|---------|
| **Implemented** | Hard-coded state transition or formula in Python |
| **Prompted** | Soft guidance or LLM decision; not a closed-form rule |
| **Emergent / analyst** | Behavioural pattern in outputs; not claimed here |

---

## High-level system

ELICIT is a repeated multi-agent public-goods game with optional climate shocks and a Loss & Damage Fund. Agents are LLM-driven (`llama3.1:8b` via local Ollama in this project configuration).

Core packages:

| Package | Role |
|---------|------|
| `src/core/` | Environment loop, agents, institutions, LDF, subsidy, parameters |
| `src/modules/` | ToM, gossip, democracy, oracle |
| `src/prompts/` | Decision / belief prompt construction |
| `src/parsing/` | Strict JSON parsers with retries |
| `src/llm/` | Ollama client + shared retry helper |

---

## Round lifecycle (implemented)

Source: `Environment.run_simulation` / `run_round`  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=run_simulation]

Per round \(r = 1 \ldots N\):

1. **Reset institutions** (SI / SFI membership cleared)
2. **Institution assignment**
   - Climate/LDF mode (**this run**): **forced** â€” developed â†’ SI, developing â†’ SFI  
     [Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=setup_agent_climate_mode]
   - Abstract mode: LLM institution choice (**prompted**)
3. **Stage 1 â€” Contributions** (`collect_contributions`) â€” LLM amounts (**prompted**), clamped to stage-1 cap (**implemented**)
4. **Public-goods distribution** (`distribute_public_goods`) â€” share formula (**implemented**)
5. **Stage 2 â€” SI only** punish/reward assign + apply (**prompted** allocations; **implemented** effects)
6. **Subsidy** (if enabled) â€” top SI contributors (**implemented**)
7. **Climate shock + LDF** collect/payout (**implemented**)
8. **Payoffs / wealth update** (`calculate_payoffs`) (**implemented**)
9. **Record history + belief updates** (**implemented** logging; belief text **prompted**)
10. **ToM audit + reputation + gossip** (if enabled) â€” scores **prompted**; mean reputation / bulletin filter **implemented**
11. **Democracy** every `DEMOCRACY_INTERVAL` rounds â€” proposals/votes **prompted**; tally/apply **implemented**
12. Optional Ollama soft-reset

---

## Module catalogue

### Voluntary contributions

| Step | Detail |
|------|--------|
| Input | Wealth (budget), institution, MCPR/group size, beliefs, gossip, T-1 peer averages |
| Visible info | Own wealth; not pool balance (see `06_agent_information_boundaries.md`) |
| Decision | LLM JSON `contribution` (**prompted**) |
| Action | `agent.contribution` clamped to `[MIN, stage1_cap]` |
| State update | Feeds PG share, LDF deposit (same amount), Stage-1 payoff |
| Code | `Agent.make_contribution`, `Institution.collect_contributions` |
| Config | `MIN_CONTRIBUTION`, climate wealth cap |
| Results | `contribution`, `contribution_reasoning`, LDF fields |

### Institutions (SI / SFI)

| | SI | SFI |
|--|----|-----|
| Code class | `SanctioningInstitution` | `SanctionFreeInstitution` |
| Stage 2 | Yes | No |
| LDF labels | Binding Climate Treaty | Non-Binding Climate Agreement |

[Evidence: `src/core/institution.py` | run=n/a | round=n/a | agent=n/a | record=module_docstring]

### Theory of Mind

| Step | Detail |
|------|--------|
| Input | Targetâ€™s stated contribution reasoning vs actual contribution |
| Decision | Pairwise LLM trust score 1â€“10 (**prompted**; score-only contract in current ToM) |
| State update | `tom_scores`; `reputation = mean(incoming)` |
| Downstream | Gossip filter; Stage 0/2 prompts show own reputation / own scores of peers |
| Code | `TomModule.audit_round`, `Environment.run_tom_audit` |

### Gossip

| Step | Detail |
|------|--------|
| Input | All ToM audits this round |
| Selection | Scores â‰¤ `GOSSIP_TRIGGER_SCORE`; top `MAX_GOSSIP_ITEMS` worst |
| Visibility | Personalized; target sees `"YOU"`; source does not see own outbound item |
| Timing | After round decisions; consumed in **next** round prompts |
| Code | `GossipModule.compile_gossip`, `get_gossip_for_agent` |
| Results gap | Bulletin **not** written into the 20260804 JSON export |

### Reputation

Implemented as peer-average ToM score. Default init `5.0`.  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=run_tom_audit]

### Democracy / proposals / voting / rule adoption

| Step | Detail |
|------|--------|
| Who proposes | **All agents** in code (module docstring saying SI-only is **wrong**) |
| Who votes | **All agents** |
| Win rule | Plurality (`max` votes); ties broken randomly â€” not strict majority |
| Apply | `setattr(parameters, rule, new_value)` with clamp to ~\[0.1Ã—, 10Ã—\] current |
| Oracle | Optional annotations appended to proposal text before vote |
| Code | `DemocracyModule` |
| Results | `constitutional_change` on democracy rounds |

### Climatic shocks

Deterministic schedule when `CLIMATE_SHOCK_DETERMINISTIC=True`:  
`CLIMATE_SHOCK_SCHEDULE = [(5, 0.10), (10, 0.20)]` for this project config.  
Damage: `CLIMATE_DAMAGE_BASE * severity * vulnerability`.  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=_apply_climate_shock_and_ldf]

### Fund accumulation & redistribution (LDF)

| Step | Detail |
|------|--------|
| Deposit | Stage-1 `contribution` amount added to `pool_balance` when collection gate open |
| Payout | Developing agents only; damage-weighted; capped by `LDF_MAX_COVERAGE` |
| Visibility | Agents see own flows; **not** pool balance |
| Code | `LossDamageFund` |

### Payoffs / utility

Round payoff (climate/LDF): Stage-1 net + Stage-2 net + subsidy + LDF payout âˆ’ climate damage.  
Wealth floored at 0. See `05_mathematical_model.md`.

### Agent memory & observations

| Store | Cap / role |
|-------|------------|
| `belief_state` | LLM scratchpad: trust_levels, strategy, observations |
| `anonymous_data_history` | Last `DISPLAY_PAST_ACTIONS` (default 1) peer snapshots |
| `history` | Last 1 feedback dict (often unused by live prompts) |
| `history_institutions` / `history_contributions` | â‰¤10; last 3 shown on cards |
| `recent_gossip` | Overwritten each ToM round |

### Reasoning capture

Institution / contribution / punishment reasoning, facts_used, justifications, belief fields, democracy proposal reasons persisted into results JSON (and extracted in Prompt 1).

---

## Configuration note for this run

Filename flags (`scnldf`, `sh1`, `ldf1`) imply LDF scenario + shocks + LDF enabled via experiment CLI. Current `parameters.py` defaults still show `LDF_ENABLED=False` / `CLIMATE_SHOCK_ENABLED=False` â€” those defaults are **not** the historical run switches. Prefer filename + in-file shock/LDF fields as evidence of what ran.

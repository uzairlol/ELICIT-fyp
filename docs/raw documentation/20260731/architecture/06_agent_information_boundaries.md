# 06 — Agent Information Boundaries (20260731)

What agents can and cannot observe when deciding. Verified from prompts and feedback construction — **not** inferred from results fields alone.

---

## Verdict on fund balance (critical)

**Agents do not observe the numeric LDF pool balance** (`ldf_pool_start` / `ldf_pool_end` / totals).

| What | Visible? | Evidence |
|------|----------|----------|
| Own LDF contribution this round | Yes | `_build_common_snapshot` |
| Own LDF payout this round | Yes | same |
| Own climate damage this round | Yes | same |
| Qualitative “contributions deposit into LDF pool” | Yes (prompt reminder) | `_append_climate_role_guidance` |
| Numeric pool balance / pool totals | **No** | Absent from all decision prompts; present only in results JSON |

[Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_build_common_snapshot]  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=ldf_pool_fields_in_round_data]

**Interpretive implication (method note, not a results claim):** contribution choices cannot be read as optimisation against the true fund stock.

---

## Decision-stage visibility matrix

Legend: **I** implemented in prompt · **P** soft guidance · **N** not shown

### Stage 0 — Institution

| Channel | Status |
|---------|--------|
| Own wealth, group, vulnerability, emissions | I |
| Own reputation | I |
| SI/SFI rule descriptions | I |
| Belief scratchpad + gossip (prev) | I |
| Free LLM institution choice | **N in LDF/climate** — forced by `agent_group` |

[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=climate_mode_forced_institution]

### Stage 1 — Contribution

| Channel | Status |
|---------|--------|
| Own budget min/max (`int(wealth)`) | I |
| Group size, MCPR | I |
| Previous same-institution average contribution | I |
| Current-round peer contributions | N (not yet known) |
| LDF pool balance | N |
| Belief + gossip | I |
| Climate role soft guidance | P |

### Stage 2 — Punishment (SI only)

| Channel | Status |
|---------|--------|
| SI peers only (real IDs in LDF) | I |
| Peer contribution, deviation, Stage-1 payoff, stated intent | I |
| Own ToM score for each SI peer | I (if ToM on) |
| Peer aggregate reputations | N |
| Gossip filtered to SI peers | I |
| SFI agents as punish targets | N (forbidden) |

---

## Peer anonymity

| Mode | Anonymity |
|------|-----------|
| LDF / climate | **Off** — real agent IDs |
| Abstract | Depends on `ANONYMITY` parameter |

[Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_use_anonymity]

T-1 peer block includes institution, wealth, contribution, received punish/reward, payoffs — **not** peers’ assigned punish/reward maps.

---

## Reputation & ToM visibility

| Signal | Agent sees? |
|--------|-------------|
| Own aggregate reputation | Yes (Stage 0; also ToM line) |
| Own scores of peers | Yes at Stage 2 |
| Other agents’ aggregate reputations | No |
| Full ToM audit log | No (internal / cleared) |

---

## Gossip boundaries

| Rule | Implemented |
|------|-------------|
| Timing | Compiled after round \(t\) decisions; shown in round \(t+1\) prompts |
| Source | Does not receive own outbound gossip item |
| Target | Sees item labelled `"YOU"` |
| Content | Score (+ reasoning if present); real agent IDs in code |
| Export | **Not** in 20260731 results JSON |

[Evidence: `src/modules/gossip_module.py` | run=n/a | round=n/a | agent=n/a | record=get_gossip_for_agent]

---

## Democracy visibility

| Aspect | Implemented |
|--------|-------------|
| Who proposes / votes | All agents (code); docstring “SI-only” is inaccurate |
| Proposal text to voters | Full list + optional oracle annotation |
| Injection into Stage 0–2 cards | No — separate constitutional session |
| Persistence | `constitutional_change` in results |

[Evidence: `src/modules/democracy_module.py` | run=n/a | round=n/a | agent=n/a | record=_collect_proposals]

---

## Belief / memory boundaries

| Store | Fed into decisions? | Cap |
|-------|---------------------|-----|
| `belief_state` | Yes (all stages; SI-filtered at Stage 2) | LLM-compressed |
| `anonymous_data_history` | Latest round in belief append / Stage-1 avg | `DISPLAY_PAST_ACTIONS` (1) |
| `history` (full feedback) | Effectively unused by live constructors | 1 round |
| Institution/contrib history lists | Last 3 on cards | ≤10 stored |

Belief update itself uses a compact peer sample (top deviant contributors), not the full 25-peer dump — Prompt 1/prior engineering fix.  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=update_beliefs]

---

## Results-only fields (analysts, not agents)

- `ldf_pool_start`, `ldf_pool_end`, `ldf_contributions_total`, `ldf_payouts_total`
- `shock_occurred`, `shock_severity`, gross/net damage totals
- `cooperation_rate`, `gini_wealth`
- Peer aggregate reputations; full punishment assignment maps of others
- Parser meta / deepseek think dumps (if present)

---

## Classification summary

| Behaviour | Type |
|-----------|------|
| Forced developed→SI / developing→SFI | Implemented |
| Hidden pool balance | Implemented information boundary |
| “Contribute to LDF via emissions contribution” reminder | Prompted |
| Contribution amount | Prompted (+ implemented clamp) |
| Optimising against true fund stock | **Not supported** by information design |

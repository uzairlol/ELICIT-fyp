# 13 — Reasoning–Action Consistency (20260731)

Checks alignment between contribution reasoning text and observed contribution / social-event context.

Script flags: `tables/reasoning_action_flags.csv`  
Motif table: `tables/reputation_motif_counts.csv`  
Excerpts: `evidence/reputation_gossip_reasoning_excerpts.md`

---

## Automated consistency flags

| Flag | Count | Meaning |
|------|------:|---------|
| `cooperative_language_zero_contrib` | 54 | Text mentions cooperate/contribute/support while contribution = 0 |
| `free_ride_language_positive_contrib` | 16 | Free-ride / zero language while contribution > 0 |
| `mentions_reputation_after_gossip` | 2–3 | Reputation/trust words in contribution text after gossip_prev |
| `action_without_reasoning` | 0 | Empty contribution reasoning with positive contribution (none in this export) |

[Evidence: `tables/reasoning_action_flags.csv` | run=20260731_013853 | round=varies | agent=varies | record=flags]

**Finding:** The most common misalignment is **cooperative wording with zero contribution** (54 cases). Explicit reputation talk right after gossip is rare (2–3).

These are string heuristics — not full semantic intent parsing.

---

## Post-event language vs behaviour

Among contribution reasonings after bad_rep/gossip exposure:

- Opportunistic / free-ride / self-interest tokens: **29**
- Reputation-management tokens: **3**
- Explicit “gossip” token: **0**

Combined with Prompt 4 event study (mean Δ prop negative after events):

| Claim | Support |
|-------|---------|
| Agents systematically narrate image repair then raise contributions | **Weak / contrary** — rare repair language; average prop falls |
| Agents sometimes use cooperative language without contributing | **Supported** (54 flags) |
| Gossip bulletin is explicitly cited in contribution reasoning | **Not observed** in keyword scan |

---

## Illustrative paired examples

Full excerpts with context live in `evidence/reputation_gossip_reasoning_excerpts.md`.  
When quoting in later synthesis, keep agent, round, contribution, institution, and event flags attached.

Pattern classes observed in excerpts (**descriptive**):

1. **High contribution + generic cooperation talk** — language matches direction of action.
2. **Zero contribution + cooperation talk** — flagged inconsistency.
3. **Post-gossip round without mentioning reputation** — common; cannot infer disregard vs unstated use (**open**).

---

## Method limits

1. Regex motifs miss paraphrase.
2. LLM boilerplate can inflate “cooperative” tokens.
3. Belief-state text not fully scored here for consistency with next-round contribution.
4. Punishment reasoning consistency deferred (Stage-2 SI only).

---

## Bottom line for later stages

Reasoning and action are **imperfectly aligned**. Social events in this run are followed more often by contribution **decreases** than by narrated repair. Treat “reputation mechanism works as intended social pressure” as an open empirical claim, not a confirmed result.

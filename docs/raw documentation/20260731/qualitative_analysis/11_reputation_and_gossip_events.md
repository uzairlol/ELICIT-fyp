# 11 — Reputation and Gossip Events (20260731)

Event study of contribution changes after negative reputation / gossip exposure.

---

## Event definitions (from code, not intuition)

### Reputation

- **Implemented:** after each ToM round, \(\rho_i = \mathrm{mean}(\text{incoming ToM scores})\); default init `5.0`.  
  [Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=run_tom_audit]
- **Analyst bad-reputation event (this stage):** end-of-round \(\rho_i < 4.0\) (strictly below neutral default).  
  Alternative: **reputation drop** \(\Delta\rho_i \le -1.0\) vs prior round.
- Timing: reputation is updated **after** round-\(t\) decisions; it enters prompts in round \(t+1\).

### Gossip

| Question | Answer from code |
|----------|------------------|
| What appears in gossip? | ToM audits with `score <= GOSSIP_TRIGGER_SCORE` (7.0), lowest scores first, top `MAX_GOSSIP_ITEMS` (5) |
| Bulletin visible to all? | Personalized string to each agent |
| When received? | After round \(t\) ToM; labelled previous-round in round \(t+1\) prompts |
| Does target see self? | Yes — labelled `"YOU"` |
| Factual vs generated? | Score is LLM ToM judgment; reasoning often empty in current ToM contract |

[Evidence: `src/modules/gossip_module.py` | run=n/a | round=n/a | agent=n/a | record=compile_gossip]

### Export limitation → reconstruction

The 20260731 JSON has **no** stored gossip bulletin. This stage **reconstructs** candidate bulletins from saved outgoing `tom_scores` using the same threshold/top-k rule.

**Limitation:** live ToM completion order can change tie-breaking among equal scores; reconstruction sorts by `(score, source, target)` deterministically. Treat as approximate gossip exposure.

Table: `tables/gossip_bulletins_reconstructed.csv`  
[Evidence: `tables/gossip_bulletins_reconstructed.csv` | run=20260731_013853 | round=varies | agent=n/a | record=reconstruction]

---

## Quantitative event study

Script: `scripts/analyze_20260731_reputation_gossip.py`  
Primary outcome: \(\Delta\) `prop_of_wealth` from event round \(t\) to post window (\(t+1\), or mean of \(t+1..t+k\)).

### Counts

| Event | Agent-rounds flagged |
|-------|----------------------|
| bad_rep (\(\rho<4\)) | 107 |
| gossip_target (reconstructed) | 90 |
| rep_drop (\(\Delta\rho\le-1\)) | (see event table; 155 imm rows across SI+SFI) |

### Immediate horizon (\(t+1 - t\)) — mean Δ prop

| Event | SI mean Δ (n) | SFI mean Δ (n) | Frac Δ>0 (SI / SFI) |
|-------|---------------|----------------|---------------------|
| bad_rep | −0.036 (36) | −0.103 (68) | 0.39 / 0.38 |
| rep_drop | −0.091 (74) | −0.119 (81) | 0.32 / 0.31 |
| gossip_target | −0.048 (35) | −0.201 (52) | 0.31 / 0.31 |

[Evidence: `tables/reputation_gossip_event_summary.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=horizon=imm]

**Finding:** On average, proportional contribution **falls** after negative social events; fewer than 40% of events are followed by an increase. This is **not** consistent with a dominant “image repair → higher contribution” pattern in this run.

### Selection note (important)

Gossip-target events have **high** mean prop at event time (≈0.52) falling to ≈0.38 after — compatible with regression-to-mean / ToM hypocrisy targeting of high contributors, not only free-rider shaming.

### Vs unaffected agents (same rounds)

Mean across rounds of (affected Δ − control Δ):

| Event | Affected mean Δ | Control mean Δ | Diff-in-diff |
|-------|-----------------|----------------|--------------|
| bad_rep | −0.291 | −0.003 | **−0.288** |
| gossip_target | −0.197 | +0.011 | **−0.208** |
| rep_drop | −0.124 | +0.019 | **−0.143** |

[Evidence: `tables/reputation_gossip_controls.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=diff_in_diff]

Affected agents reduce prop more than co-round controls. Still **associational** (events are endogenous to behaviour/ToM).

### First-time vs repeat

| Event | Mean first Δ | Mean repeat Δ |
|-------|--------------|---------------|
| bad_rep | −0.166 | −0.066 |
| gossip_target | −0.206 | −0.097 |
| rep_drop | −0.255 | −0.080 |

First hits show larger negative Δ than later repeats (attenuation / habituation **or** composition). Not causal.

Plot: `plots/reputation_event_deltas.png`, `plots/reputation_mean_trajectories.png`, `plots/gossip_target_frequency.png`

---

## Reasoning around events

Motif scan on contribution reasoning in rounds with `bad_rep_prev` or `gossip_prev` (`tables/reputation_motif_counts.csv`):

| Motif | Count (post-event contribution texts) |
|-------|---------------------------------------|
| opportunistic / free-ride / self-interest language | 29 |
| conformity | 5 |
| reputation_management | 3 |
| named_agents | 3 |
| future_rounds | 1 |
| gossip_reference | 0 |

Excerpts: `evidence/reputation_gossip_reasoning_excerpts.md`

**Finding:** Explicit reputation-repair or gossip-response language is **rare**. Opportunistic / free-ride wording appears more often. Absence of the word “gossip” does not prove agents ignored the bulletin (prompt may not encourage that token).

Label as **inference** where motives are not explicit.

---

## Limitations

1. Gossip reconstructed, not logged.
2. Bad-rep threshold `<4` is analyst-chosen relative to default 5 (disclosed).
3. Endogenous events; no exogenous reputation shock.
4. `prop_of_wealth` end-of-round denominator.
5. Single run / seed.
6. ToM scores often discrete/extreme (many 1s/5s) — gossip may be noisy.

# 22 — Cooperation Stability Assessment (20260731)

Separate from norm internalisation: is **positive contribution behaviour** reasonably stable over the run?

---

## Metrics (disclosed thresholds)

| Metric | Value | Read |
|--------|------:|------|
| Overall mean prop_of_wealth | 0.293 | Positive on average |
| Overall median prop | 0.092 | Typical agent-round far below mean |
| Group-mean lag-1 autocorr | 0.031 | Aggregate path not sticky |
| Agent-mean lag-1 autocorr | 0.215 | Mild individual persistence |
| Early vs late mean std | 0.688 → 0.657 | Little variance compression |
| Early vs late mean IQR | 0.238 → 0.178 | Mild narrowing |
| Early vs late zero-share | 0.192 → 0.119 | Fewer zeros later |
| Rounds with mean prop ≥0.1 / 0.2 / 0.3 | 30 / 26 / 17 | Level often “moderate,” rarely stably high |
| Near-zero agents (mean&lt;0.05) | 5 / 26 | Persistent free-rider-like specialists |
| High agents (mean≥0.25) | 13 / 26 | Parallel high-effort cluster |
| Shock regain pre-mean | R5: 1 round; R10: 2 rounds | Fast mean recovery, uneven composition |

[Evidence: `tables/prompt7_numeric_summary.json` | run=20260731_013853 | round=1-30 | agent=all | record=all]

SI vs SFI mean prop nearly identical (~0.29); SFI much more zero-heavy and right-skewed (Prompt 3).

---

## Stress tests

| Test | Outcome |
|------|---------|
| Climatic shocks | Temporary disturbance; no permanent mean collapse; R5 SI pullback |
| Reputation/gossip events | Associated with **declines**, not stabilising repair |
| Democracy / rule changes | Mild post-adoption mean prop ↑ (confounded); rules drift toward rewards/equity |
| Leave-one-agent-out (SI−SFI) | Mean prop gap stays near zero (Prompt 3) |
| Subgroup consistency | Both groups contribute on mean; distributions differ sharply |

---

## Verdict — cooperation stability

**Moderately positive average cooperation with limited path stability.**

There is sustained positive mean proportional contribution and no terminal collapse, but the series is skewed, polarised, weakly autocorrelated at the aggregate level, and sensitive to shocks/social events without clear equilibration on a shared contribution rate.

This **differs** from the norm-emergence verdict: cooperation-as-positive-transfers can persist without a strong shared norm.

**Confidence:** moderate (single seed; end-of-round wealth denominator).

---

## Path narratives behind the averages

Stability is “moderately positive on average” because many agent-rounds still transfer positive amounts, yet the path is jagged:

- **R1→R2:** mean prop 0.231→0.445 as SFI leaves cold-start zeros (doc 31/32).  
- **R6:** SI zero share 41.7% with payoff-max templates — a cooperation dip without terminal collapse.  
- **Gossip/bad-rep:** mean Δ prop negative (doc 11) — social events do not stabilise upward.  
- **Polarisation:** agent 19 mean prop ≈0.001 coexists with agent 20 mean ≈0.60.

Example of a non-stable high agent after social pressure (agent 3, SI, R6):

> Given a high budget and low marginal return, I choose to contribute nothing to maximize my payoff.

Example of persistent caution (agent 19, SFI, R1):

> Contributing nothing allows me to conserve resources and observe the behavior of other agents…

Together these show why mean levels can stay positive while path stability and shared norms fail.


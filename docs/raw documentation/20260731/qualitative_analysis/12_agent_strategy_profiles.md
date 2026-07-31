# 12 — Agent Strategy Profiles (20260731)

Concise per-agent profiles from contributions, reputation/gossip exposure, shock deltas, and motif tags.  
Institution = forced group membership in this run (developed→SI, developing→SFI).

Data: `tables/agent_strategy_profiles.csv`  
[Evidence: `tables/agent_strategy_profiles.csv` | run=20260731_013853 | round=1-30 | agent=all | record=profiles]

---

## How to read a profile

| Field | Meaning |
|-------|---------|
| mean/median/std prop | `prop_of_wealth` over 30 rounds |
| zero_share | Fraction of rounds with contribution = 0 |
| baseline vs late | Mean prop rounds 1–4 vs 20–30; `adaptation_flag` if \|Δ\|>0.15 |
| gossip / bad_rep counts | Reconstructed bulletin appearances; \(\rho<4\) rounds |
| mean Δ after gossip/bad_rep | Immediate post-event prop change (NaN if never flagged) |
| shock_deltas | From Prompt 3 within-agent post−pre prop |
| top_motifs | Regex tags from reasoning near social events |

Motives not stated in text are labelled **inference**.

---

## SI agents (developed)

| ID | mean prop | zeros | gossip hits | Δ after gossip | adaptation | Sketch |
|----|-----------|-------|-------------|----------------|------------|--------|
| 2 | 0.163 | 0.03 | 3 | +0.012 | no | Low-moderate steady contributor |
| 3 | 0.490 | 0.13 | 7 | −0.214 | no | High mean prop; frequent gossip target; cuts after hits |
| 5 | 0.197 | 0.10 | 3 | +0.151 | yes | Moderate; some post-gossip increases; adapts late |
| 6 | 0.334 | 0.07 | 3 | −0.059 | yes | Mid-high; mild post-gossip decline |
| 10 | 0.203 | 0.10 | 3 | +0.011 | no | Stable moderate |
| 13 | 0.130 | 0.00 | 0 | — | yes | Never zero; never gossip-target in reconstruction; late shift |
| 14 | 0.221 | 0.13 | 8 | −0.027 | yes | Often gossip-targeted; small average decline after |
| 16 | 0.125 | 0.00 | 2 | −0.026 | yes | Consistent positive contrib; low prop level |
| 21 | 0.425 | 0.00 | 1 | −0.129 | yes | High prop; rare gossip; drops after the hit |
| 22 | 0.317 | 0.03 | 1 | +0.052 | no | Mid-high stable |
| 23 | 0.469 | 0.07 | 2 | +0.015 | yes | High contributor |
| 25 | 0.412 | 0.10 | 2 | −0.102 | yes | High; declines after gossip |

**SI pattern (descriptive):** Several high-prop agents are frequent reconstructed gossip targets and often **reduce** prop afterward — inconsistent with simple shame-driven upshifts; more consistent with noisy ToM / mean reversion (**inference**).

---

## SFI agents (developing)

| ID | mean prop | zeros | gossip hits | Δ after gossip | adaptation | Sketch |
|----|-----------|-------|-------------|----------------|------------|--------|
| 0 | 0.236 | 0.43 | 8 | ≈0 | no | High zeroing; often targeted |
| 1 | 0.002 | 0.03 | 2 | ≈0 | no | Near-zero prop strategy (tiny positive amounts) |
| 4 | 0.423 | 0.23 | 7 | +0.058 | yes | Volatile high mean; mixed post-gossip |
| 7 | 0.440 | 0.30 | 8 | +0.125 | yes | High zeros + high mean (bursty) |
| 8 | 0.249 | 0.17 | 5 | +0.408 | yes | Post-gossip mean Δ positive (outlier-sensitive) |
| 9 | 0.529 | 0.10 | 3 | −2.55 | yes | Extreme post-gossip drop (single large prop episodes) |
| 11 | 0.023 | 0.03 | 1 | ≈0 | no | Persistently low prop |
| 12 | 0.462 | 0.17 | 4 | +0.120 | yes | High bursty |
| 15 | 0.579 | 0.20 | 6 | −0.867 | yes | High mean; large post-gossip declines |
| 17 | 0.024 | 0.03 | 0 | — | no | Low prop, untargeted |
| 18 | 0.538 | 0.23 | 6 | −0.357 | yes | High; declines after gossip |
| 19 | 0.001 | 0.03 | 0 | — | no | Near-zero strategy |
| 20 | 0.603 | 0.07 | 0 | — | yes | High prop without reconstructed gossip hits |
| 24 | 0.032 | 0.23 | 5 | −0.018 | no | Low prop; repeated targets |

**SFI pattern (descriptive):** Polarised — near-zero specialists (1, 11, 17, 19, 24) vs high-burst contributors (9, 15, 18, 20). Gossip hits cluster among high-mean agents.

---

## Cross-cutting strategy types (taxonomy, descriptive)

1. **Near-zero specialists** — mean prop ≲ 0.03 (e.g. 1, 11, 17, 19).
2. **Steady low-moderate** — low zeros, modest prop (e.g. 13, 16, 2).
3. **High burst / high variance** — high mean + non-trivial zeros (e.g. 7, 4, 15).
4. **High & gossip-exposed** — high prop + many bulletin hits, often negative post Δ (e.g. 3, 14, 15, 18).

Shock responses remain agent-specific (`shock_deltas` column); see Prompt 3 for group event study.

---

## Limitations

Profiles compress 30 rounds; extreme single-round props dominate some means/Δs (agents 9, 15).  
Gossip is reconstructed.  
No claim that strategy labels are intentional mental models unless reasoning says so.

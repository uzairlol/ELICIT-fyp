# 37 — Additional Research Questions: Answers Index (20260731)

Maps [`additional_research_questions.md`](../../../../additional_research_questions.md) (repo root) to what this deepening pass can say for run `20260731_013853`. Statuses: **Answered** | **Partial** | **Deferred**.

---

## Theory of Mind

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 1 Hypocrisy vs visibility | Partial | Gossip targets have high mean prop at event (~0.52); mid-pack ranks (~14/26). Full regression of ToM on abs vs prop vs deviation not fit this pass. | docs 11; `gossip_target_prop_ranks.csv` |
| 2 ToM distribution shape | **Answered** | Dominated by **5.0** (12,647) and **1.0** (2,370) of 18,850 scores; 8.0 common (3,000); 10 rare (10). Effectively coarse/binned, not smooth continuous reputation. | `prompt_dashboard_rq_summary.json` tom_gossip |
| 3 Cross-group ToM bias | **Answered** | Means: SI→SI 5.09, SFI→SFI 4.80, SI→SFI 4.88, SFI→SI 5.01. Mild same-group elevation for SI; not dramatic in-group favouritism after averaging. | same |
| 4 First-impression lock-in | Deferred | Needs partial correlation R2 incoming vs late reputation net of prop trajectory. | — |

## Gossip

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 5 Info content / ≤7 fraction | **Answered** | **84%** of ToM scores ≤7 → threshold nearly ambient; top-5 is a lower-tail sample, not rare indictment. | tom_gossip.frac_score_le_7 |
| 6 Redundant vs Stage-2 | Partial | Semantic doc: SI already sees peer contrib — gossip partly redundant for SI; more unique for SFI. No systematic SI-peer language scan completed beyond spot checks. | arch 33 |
| 7 Disciplining vs amplifier | **Answered** | Targets often mid/high prop; mean Δ prop after gossip **negative** — consistent with piling onto visible agents, not free-rider repair. | docs 11, 31 |

## Contributions / BE

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 8 Contrib Gini vs wealth Gini | **Answered** | Abs-contrib Gini high; prop Gini volatile; wealth Gini U-shaped; wealth **gap widens**. | doc 34 |
| 9 SFI burst timing | **Answered** | 14 bursts; 1/14 after payout; 5/14 democracy rounds — not clean payout reciprocity. | `sfi_burst_rounds.csv`; doc 31 |
| 10 Payout → next prop | **Answered** | n=28; mean Δ +0.06 vs baseline, **median ~0** — weak/heterogeneous reciprocity. | doc 35 |
| 11 Liquidity / wealth floor | **Answered** | 0/91 zeros look liquidity-forced under end-wealth cap≈0 approx; SI R6 zeros have huge wealth. | doc 31 |
| 12 R2 spike | **Answered** | Mean prop 0.231→0.445; SFI 0.022→0.602; cold-start + peer-history texts. | docs 31–32 |
| 27 Warm glow | Partial | 54 language–action flags; most are MCPR/free-ride talk, not classic warm-glow. | docs 13, 32 |

## Democracy

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 13 Dissenters post-loss | Deferred | Needs vote×prop join beyond current tables. | — |
| 14 Missing 142 proposals | Deferred | Needs parse-failure / empty proposal audit from debug logs. | — |
| 15 Ratchet | **Partial** | Adopted path only ↑ subsidy/equity/damage; punish-weaken fails; no stronger EFFECT proposed. | docs 14, 18 |

## Shocks / info / vulnerability

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 16 Shock absorber 2×2 | **Answered** | down_down 9, down_up 8, up_down 6, up_up 3 — few consistent absorbers. | `shock_absorber_2x2.csv` |
| 17 Fund language without pool | **Answered** | ~1.8% contribution texts match fund lexicon; pool hidden. | doc 35; arch 33 |
| 18 Vulnerability vs prop | Deferred | Correlation not computed this pass (easy follow-up). | — |

## Math / economics

| Q | Status | Answer summary | Where |
|---|--------|----------------|-------|
| 19 MCPR internalized? | **Answered** | **31.8%** of contribution blocks mention MCPR/marginal return/etc. Zeros especially MCPR-heavy (62%). Agents *do* verbalise MCPR — often to justify zero/low. | prompt_dashboard_rq_summary; doc 31 |
| 20 Subsidy rank-gaming | Deferred | Needs rank-2/3 bunching study. | — |
| 21 Conditional coop vs norm vs reputation | **Partial** | Peer-prev mean corr SI≈0.05, SFI≈−0.09 — weak CC on full path; R2 spike still CC-compatible; norms limited (doc 21); reputation repair fails (doc 11). | summary.conditional_coop |
| 22 Endogenous enforcement efficiency | Partial | Burden corr 0.14; hubs in doc 36; punished→next prop efficiency not fully computed. | docs 17, 36 |
| 23 Unraveling | Partial | R6 SI zero spike then recovery — dip not sustained ≥3-round SI collapse in mean; polarisation persists. | docs 22, 31 |
| 24 SI effective tax | Deferred | Needs wealth_start reconstruction. | — |
| 25 LDF coverage | **Answered** | 76.8% at R5 and R10; pool ≫ payouts. | doc 35 |
| 26 Net receivers / PG counterfactual | Deferred | Lifetime net LDF table exists (`ldf_lifetime_net_transfers.csv`) — interpret in follow-up. | tables |
| 28–32 (misc paper threads) | Mixed | Wealth gap answered (34); leave-one-out multi-seed deferred; strategy scatter partial via profiles. | — |

---

## Deferred class (needs new runs / code)

Endogenous SI/SFI choice; visible LDF pool treatment; desynchronised democracy vs shocks; native gossip logging; cross-model / multi-seed replication; separate LDF pledge instrument.

---

## Pack note

Answers here are for **one** Full LDF seed-1 `llama3.1:8b` run. Treat as mechanism evidence, not external FRLD evaluation.

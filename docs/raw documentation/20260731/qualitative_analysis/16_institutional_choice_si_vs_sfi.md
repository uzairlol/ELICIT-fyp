# 16 — Institutional Choice: SI vs SFI (20260731)

How agents relate to institutions under LDF rules.

---

## Critical mechanism fact

In climate/LDF mode, membership is **forced**:

- developed → **SI**
- developing → **SFI**

[Evidence: `architecture/04_system_architecture.md` | run=n/a | round=n/a | agent=n/a | record=forced_institution]

Agents **cannot** strategically switch institutions. “Institutional choice” in this run means:

1. Living under assigned SI/SFI rules, and  
2. Using **democracy** to change **numeric parameters** (not SI↔SFI assignment).

---

## Do agents recognise that rules can change?

**Yes (prompted + observed):** democracy prompts ask for whitelist parameter changes; 14 proposals and 156 votes recorded.  
Reasoning repeatedly frames changes as improving “cooperation,” “trust,” “sustainability.”

[Evidence: `tables/proposals.csv` | run=20260731_013853 | round=5 | agent=4 | record=CC-R05-P0]

---

## SI vs SFI use of democracy

| | SI | SFI |
|--|----|-----|
| Proposals | 8 | 6 |
| Can Stage-2 punish/reward | Yes | No |
| Propose subsidy (SI mechanism) | Yes | Yes (incl. winning R5 proposer 4; R15 winner 24; R30 winner 15) |
| Propose LDF equity/coverage | Yes | Yes |
| Propose weaker punishment | Yes (10, 21) | No in this set |

**Finding:** SFI agents actively reshape **SI subsidy** and **LDF** parameters even though they never pay Stage-2 enforcement costs. That is institutional politics across group lines, not exit/entry choice.

Same-group voting rate ≈ **0.51** (`votes_parsed.csv`) — near population base rate; little evidence of bloc voting by institution in aggregate.

---

## Evidence checklist (Prompt 5 questions)

| Behaviour | Evidence |
|-----------|----------|
| Recognise rules can change | Strong (participation + reasons) |
| Propose to alter incentives | Strong (subsidy↑, LDF weights, punishment↓ attempts) |
| Vote strategically | Weak — templated reasons; plurality outcomes |
| Adapt contributions after adoption | Mild positive mean Δ prop after most adoptions (`post_adoption_prop_changes.csv`); confounded |
| Rely on institutions over reciprocity | Mixed — still large contribution heterogeneity |
| Oppose constraining rules | Punishment-weakening proposals exist but lose |
| Support enforcement while avoiding cost | See doc 17 — SI-only costs; SFI vote on SI rules without paying Stage 2 |
| Use democracy to shift burdens | **Inference:** SFI-led subsidy wins shift SI reward pool; LDF equity shifts payout formula toward developing |

---

## What “institutional adaptation” is *not* here

- Not endogenous formation of SI vs SFI clubs.
- Not exit from binding treaty.
- Parameter drift inside a fixed membership partition.

---

## Limitations

Forced routing is a design choice of the LDF scenario — limits external validity for “institutional choice” theories that require free entry/exit (e.g. classic Gürerk et al. SI/SFI experiments).

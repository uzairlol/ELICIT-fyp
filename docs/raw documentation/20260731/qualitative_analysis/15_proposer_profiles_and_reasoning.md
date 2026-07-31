# 15 — Proposer Profiles and Reasoning (20260731)

**Opening claim.** Proposers are not a random draw from the agent pool: mean proposer prop (0.364) exceeds overall mean prop (0.293). Their written reasons, however, are short, repetitive cooperation slogans that barely differentiate a subsidy hike from a punishment cut. Profile heterogeneity shows up in *who proposes what*, not in distinctive prose styles.

---

## Quantitative backbone

| Metric | Value |
|--------|------:|
| Mean proposer prop | 0.364 |
| Mean all-agent prop | 0.293 |
| Distinct proposers | ~12 across 14 proposals |
| Mean proposal reason length | ~150 chars / ~13 tokens (Prompt 6) |

[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=mean_proposer_prop]

Notable proposers: SFI agent 4 (early subsidy, high gossip exposure); SI agent 22 (LDF equity twice); SI agents 10 and 21 (failed punishment weakening); SFI agent 15 (late subsidy 0.6); near-zero agent 1 proposed coverage expansion and failed.

---

## Raw discourse — proposers in their own words

Full reasons are listed in doc 14. Highlight contrasts:

**High-prop SFI agent 20** proposing coverage / top-N (failed):

> Increasing the maximum fraction of climate damage covered by LDF payouts will incentivize cooperation and reduce free-riding…

**Near-zero SFI agent 1** (mean prop ≈0.002) using the *same* cooperation/free-riding frame for coverage — showing that low contributors can still author redistributive LDF proposals without contributing much themselves.

**SI agent 10** (failed weaken punishment):

> Reducing the punishment effect will encourage cooperation and reduce retaliation…

**SI agent 14** (adopted damage weight):

> Increasing the weight of direct damage on LDF payouts will incentivize agents to prioritize cooperation and reduce free-riding…

Punishment weakeners and LDF tighteners invoke identical virtue words. Differentiation is in the **parameter**, not the essay.

[Evidence: `tables/proposals_coded.csv` | run=20260731_013853 | round=10,20 | agent=1,10,14,20 | record=reason]

---

## Counterexamples

Agent 20 also has high mean prop (0.60) and proposes expansionist LDF coverage — not only free-riders seek coverage. SI high contributors sometimes propose equity for developing nations (22) — whether altruistic or cheap talk is unresolved.

---

## Limits

n=14. No private motives beyond text. Confidence medium on selection of proposers, high that reasons are boilerplate.

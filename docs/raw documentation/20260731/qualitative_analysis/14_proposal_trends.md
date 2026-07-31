# 14 — Proposal Trends (20260731)

**Opening claim.** Democracy in this run produces a thin but directional agenda: **raise subsidies and LDF equity/damage weights**; never adopt stronger punishment; twice attempt (and fail) to weaken `PUNISHMENT_EFFECT`. Proposal reasons reuse a cooperation/trust boilerplate that does not reveal contested incidence of benefits.

---

## Quantitative backbone

| Stat | Value |
|------|------:|
| Democracy rounds | 6 (every 5) |
| Proposals | 14 |
| Adopted | 6 |
| By category | reward_subsidy 6, ldf_equity 3, ldf_redistribution 2, punishment_weakening 2, ldf_damage_weight 1 |
| SI vs SFI proposers | 8 vs 6 |

Adopted path: subsidy↑, LDF equity↑, damage weight↑.  
[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=proposals]

---

## Raw discourse — every proposal reason (verbatim)

**R5, agent 4 SFI, SUBSIDY_FRACTION→0.3, adopted** (`CC-R05-P0`):

> Increasing the subsidy fraction will incentivize cooperation by rewarding top contributors and potentially reducing punishment costs, thereby fostering a more collaborative community.

**R5, agent 23 SI, SUBSIDY_FRACTION→0.5, failed** — nearly identical boilerplate (“collaborative environment”).

**R10, agent 1 SFI, LDF_MAX_COVERAGE→0.95, failed** (`CC-R10-P0`):

> Increasing the maximum fraction of climate damage covered by LDF payouts will incentivize cooperation and reduce free-riding, leading to increased trust and sustainability.

**R10, agent 22 SI, LDF_EQUITY_WEIGHT→0.5, adopted** (`CC-R10-P1`):

> Increasing the weight of equity in LDF payouts will incentivize cooperation and fairness by prioritizing poorer developing nations, promoting trust within the community.

**R15, agent 24 SFI, SUBSIDY_FRACTION→0.4, adopted** (`CC-R15-P1`):

> Increasing the subsidy fraction will incentivize cooperation by providing a stronger reward for contributing to the public good

**R20, agent 14 SI, LDF_PAYOUT_DAMAGE_WEIGHT→1.5, adopted** (`CC-R20-P1`):

> Increasing the weight of direct damage on LDF payouts will incentivize agents to prioritize cooperation and reduce free-riding, leading to improved collective welfare.

**R20, agent 10 SI, PUNISHMENT_EFFECT→1, failed** (`CC-R20-P2`):

> Reducing the punishment effect will encourage cooperation and reduce retaliation, promoting a more sustainable community.

**R25, agent 21 SI, PUNISHMENT_EFFECT→1, failed** (`CC-R25-P2`):

> Reducing the punishment effect to 1 will discourage excessive retaliation and promote cooperation by making punishment less costly.

**R30, agent 15 SFI, SUBSIDY_FRACTION→0.6, adopted** (`CC-R30-P0`):

> Increasing the subsidy fraction will incentivize cooperation and trust by providing a stronger reward for contributing to the common good

[Evidence: `tables/proposals_coded.csv` | run=20260731_013853 | round=5-30 | agent=varies | record=reason]

---

## Interpretation with reasoning

Every successful proposal wraps a *distributional* parameter change in cooperation rhetoric. SI agents successfully move LDF equity/damage rules that mainly affect developing payouts; SFI agents successfully raise SI subsidy fractions. The text does not say “this helps my group’s pocketbook”; the **coding of rule targets** supplies that political-economy reading (doc 18). Failed punishment-weakening uses the *same* cooperation frame to argue for softer sanctions — showing the rhetoric is cheap and portable.

**Ratchet (RQ 15, partial):** adopted changes move subsidy/equity/damage weights up; no adopted proposal tightens punishment. Failed proposals include weakening punishment and expanding coverage — nothing proposes *stronger* EFFECT.

---

## Counterexamples / limits

Only 14/156 possible proposal slots fill — agenda scarcity (RQ 14 deferred on parse failures). Plurality with 2–3 options per session. Confidence high on category counts and verbatim reasons; medium on strategic intent behind cross-group rule shopping.

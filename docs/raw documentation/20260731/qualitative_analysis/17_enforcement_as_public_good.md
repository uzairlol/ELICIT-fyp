# 17 — Enforcement as a Public Good (20260731)

**Opening claim.** Costly Stage-2 punishment/reward is available only inside SI and is unevenly provided. Agents *talk* as if punishing free-riders sustains cooperation, yet democracy twice fails to weaken punishment while never strengthening it, and contribution–enforcement correlation is only ~0.14. Enforcement is a second-order public good with cheap democratic substitutes.

---

## Quantitative backbone

| Mechanism | Costly? | Who |
|-----------|---------|-----|
| Stage-2 punish/reward | Yes | SI only |
| Gossip / ToM | No tokens | All |
| Democracy | No tokens | All |

Mean corr(prop, enforcement tokens) ≈ 0.14; top-quartile prop agents pay ~35% of tokens. Top punish givers (lifetime): agents 25, 2, 14, 3, 22. Top receivers: 14, 10, 6, 16, 22.

[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=enforcement_corr_mean]  
[Evidence: `tables/prompt_dashboard_rq_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=top5_punish_givers]

---

## Raw discourse — how SI agents justify Stage-2

**Agent 2, SI, R1** (`RB-01-A2-punishment`):

> Punishing free-riders and rewarding cooperative agents to encourage cooperation and discourage opportunistic behavior.

**Agent 3, SI, R1** (`RB-01-A3-punishment`):

> Punished free-riders and rewarded cooperative agents to balance self-interest and institutional credibility.

**Agent 5, SI, R2** (`RB-02-A5-punishment`):

> Punishing free-riders and those who did not match their stated intentions to maintain cooperation and fairness within the group.

**Agent 10, SI, R1** (`RB-01-A10-punishment`):

> Punished free-riders below the group average, while rewarding those who contributed significantly above the average or demonstrated a strong commitment to emissions reduction.

These texts assert a **monitoring-and-sanction** logic. They do not discuss second-order free-riding (“I hope someone else pays to punish”).

### Democracy about enforcement intensity

**Agent 10, R20 (failed):** “Reducing the punishment effect will encourage cooperation and reduce retaliation…”  
**Agent 21, R25 (failed):** “Reducing the punishment effect to 1 will discourage excessive retaliation and promote cooperation by making punishment less costly.”

Voters kept EFFECT high on paper while individual Stage-2 effort stayed uneven — the second-order tension.

[Evidence: `tables/proposals_coded.csv` | run=20260731_013853 | round=20,25 | agent=10,21 | record=reason]

---

## Counterexamples

Some SI agents spend little on Stage-2 (enforcement-light) while still using punish rhetoric when they do act. Gossip provides costless social pressure that can substitute — though empirically it does not raise contributions (doc 11).

---

## Limits

No survey separating support vs spend. Wealth-scaled token budgets. Confidence medium on second-order interpretation; high on SI-only cost structure.

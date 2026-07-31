# 17 — Enforcement as a Public Good (20260731)

Is punishment/monitoring a second collective-action problem in this simulation?

---

## What the code implements

| Mechanism | Costly to sender? | Who can use it? |
|-----------|-------------------|-----------------|
| Stage-2 punishment/reward tokens | **Yes** — `PUNISHMENT_COST` / `REWARD_COST` (default 1) | **SI only** |
| Subsidy | Transfer from punishment-token pool to top SI contributors | SI members receive |
| ToM / gossip | LLM compute only — **no token cost** to agents | All agents |
| Democracy proposals/votes | **No** token cost | All agents (in code) |

[Evidence: `architecture/05_mathematical_model.md` | run=n/a | round=n/a | agent=n/a | record=stage2]  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=get_stage2_payoff]

**Important:** Gossip and voting are **not** modelled as costly enforcement. Only Stage-2 spending is a material second-order public good inside SI.

---

## Who bears enforcement cost?

From `tables/enforcement_burden_by_round.csv` / `enforcement_burden_by_agent.csv`:

- Mean correlation (within round) between SI `prop_of_wealth` and enforcement tokens spent ≈ **0.14** (weak positive).
- Mean share of enforcement tokens paid by top-quartile prop agents ≈ **0.35** — some concentration, not total capture by high contributors.
- Plot: `plots/enforcement_burden.png`

**Finding:** High contributors are somewhat more likely to spend on sanctions/rewards, but enforcement is not exclusively their burden.

---

## Who benefits?

- Targets of rewards gain Stage-2 payoff; punished agents lose.
- Subsidy recycles a fraction of punishment **costs** to top contributors — partial rebate to high \(c_i\), not to enforcers per se.
- SFI agents never pay Stage-2 costs but may benefit from LDF rules shaped in democracy and from climate/LDF transfers.

---

## Second-order free-riding?

| Question | Answer in this run |
|----------|--------------------|
| Support punishment but avoid paying? | **Mixed.** Two proposals aim to **weaken** `PUNISHMENT_EFFECT` (to 1); both fail. Vote reasons often praise cooperation without volunteering more sanctions. |
| Are high contributors also institutional maintainers? | Weakly yes on Stage-2 spend correlation; democracy proposers are mixed. |
| Do proposals distribute enforcement costs? | Subsidy proposals redistribute punishment **pool**, not Stage-2 budgets. No proposal directly raises `PUNISHMENT_COST` or forces equal enforcement. |
| Rewards vs punishments | Rewards cheaper in effect (EFFECT 1 vs 3); subsidy is reward-side politics. |

**Inference (labelled):** Failed punishment-weakening votes suggest the polity prefers keeping strong EFFECT on paper, while individual Stage-2 effort remains uneven — classic second-order tension, but not proven as conscious free-riding.

---

## Democracy as costless “meta-enforcement”

Changing rules is free in tokens. Agents can try to reshape incentives without paying Stage-2 costs. That makes democracy a **cheap substitute** for costly peer punishment — especially attractive to SFI agents.

---

## Limitations

- No explicit “support punishment in survey but not spend” item — inferred from proposals/votes/spending.
- Enforcement token totals are wealth-scaled in LDF; absolute costs differ hugely across agents.
- ToM/gossip pressure has no budget constraint.

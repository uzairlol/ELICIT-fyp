# 35 — LDF Coverage and Transfers (20260731)

Dashboard LDF view: coverage ratio, pool dynamics, incidence. Tables: `ldf_coverage_by_round.csv`, `ldf_coverage_by_agent_round.csv`, `ldf_lifetime_net_transfers.csv`, `ldf_payout_next_prop.csv`. Plot: `ldf_pool_dynamics.png`.

---

## Opening claim

At both shock rounds, LDF payouts cover **~76.8%** of gross damage (`LDF_MAX_COVERAGE` default 0.90 binds with equity formula). Cumulative payouts (8.5e5) are tiny versus the terminal pool (~4.34e9). **Collection does not imply aggressive disbursement.** Agents almost never discuss fund adequacy in contribution text (~1.8%), consistent with the hidden-pool information boundary.

---

## Shock coverage

| Round | Gross damage | Payouts | Coverage |
|------:|-------------:|--------:|---------:|
| 5 | 369,000 | 283,500 | 0.768 |
| 10 | 738,000 | 567,000 | 0.768 |

[Evidence: `tables/prompt_dashboard_rq_summary.json` | run=20260731_013853 | round=5,10 | agent=n/a | record=fund.shock_coverage_ratios]

Net damage remains positive (under-coverage relative to full loss), so developing agents experience residual climate loss even when the pool is large.

---

## Pool dynamics

Pool end grows every non-payout round because Stage-1 contributions dual-deposit. Payout spikes are visually negligible on a linear scale; log plot shows them as small notches. Externally, the fund is over-capitalised relative to realised damage in this 30-round window.

---

## Payout → next contribution (RQ 10)

28 developing-agent events with `ldf_payout_round > 0` and a next round: mean Δ prop vs prior-3 baseline **+0.060**, but **median ≈ 0**. Reciprocity is weak/heterogeneous — not a clean dose-response for the group.

[Evidence: `tables/prompt_dashboard_rq_summary.json` | run=20260731_013853 | round=n/a | agent=developing | record=payout_next_prop]

---

## Fund language (RQ 17)

Only 14/780 contribution blocks match fund/pool/damage adequacy lexicon; many hits are generic “funds/budget” not LDF stock reasoning. Example that *does* mention funds without pool maths (agent 9, R1):

> Contributing nothing allows me to conserve resources and observe the behavior of other agents without committing my institution's funds.

[Evidence: `tables/prompt_dashboard_rq_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=fund_mcpr_language]

---

## Limits

Payout formula exogenous; dual-use deposit; agents cannot see pool. Do not claim real FRLD effectiveness. Confidence high on coverage arithmetic; low on behavioural reciprocity.

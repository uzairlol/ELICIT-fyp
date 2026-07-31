# 31 — Zero-Contribution Episodes (Quantitative) (20260731)

Inventory and event structure of `contribution == 0` agent-rounds. Qualitative quotes live in [`32_zero_contribution_reasoning.md`](../qualitative_analysis/32_zero_contribution_reasoning.md).

**Run:** `20260731_013853`  
**Tables:** `zero_contribution_inventory.csv`, `zero_contribution_by_round.csv`, `zero_contribution_episodes.csv`, `zero_si_r4_r7_window.csv`, `r1_r2_spike_by_agent.csv`, `prompt_zero_numeric_summary.json`

---

## Why zeros matter

In this public-goods stage game, MCPR = \(m/n\) is about 0.13 (SI) / 0.11 (SFI). A purely selfish one-shot best response is **zero contribution**. Every positive contribution therefore needs an explanation; every zero needs one too — especially when zeros cluster after shocks or at cold-start.

---

## Inventory

| Institution | Agent-rounds | Zeros | Zero share | Agents ever zero |
|-------------|-------------:|------:|-----------:|-----------------:|
| SI | 360 | 23 | 6.4% | 9 |
| SFI | 420 | 68 | 16.2% | 14 |
| ALL | 780 | 91 | 11.7% | 23 |

[Evidence: `tables/prompt_zero_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=inventory]

**Liquidity vs voluntary.** Using the analyst approximation `stage1_cap_from_end_wealth == 0`, **zero** of the 91 zeros look liquidity-forced. All 91 are coded `voluntary_zero_approx`. Limitation: decision-time wealth can differ from end-of-round wealth, so a few edge cases could be misclassified — but SI agents who zeroed at R6 still had large end-of-round wealth (millions), so those zeros are clearly not budget clips.

---

## Round structure

SFI zeros are front-loaded: **R1 zero share = 71.4%** (10 of 14 SFI agents). SI zeros spike after the first shock: **R6 zero share = 41.7%** (agents 2, 3, 5, 6, 14). Later rounds return toward lower SI zero rates; SFI remains more zero-prone and bursty.

[Evidence: `tables/zero_contribution_by_round.csv` | run=20260731_013853 | round=1,6 | agent=n/a | record=zero_share]

---

## SI focus — the R6 zero episode

Five of twelve SI agents contributed nothing in round 6, the round after shock severity 0.1 at round 5 (also a democracy round).

| Agent | R5 contrib | R5 reason (abbrev) | R6 reason |
|------:|-----------:|--------------------|-----------|
| 2 | 3,799,420 | maximize near max allowed, MCPR + Stage 2 | “high budget and low marginal return… contribute nothing” |
| 3 | 300,000 | balance self-interest and cooperation | same high-budget / low-MR template |
| 5 | 0 | already zero citing MCPR 0.1333 | “low MCPR… optimal to contribute nothing” |
| 6 | 1,350,000 | higher contribution to maximize payoff | “low MCPR… contributing nothing maximizes my payoff” |
| 14 | 880,000 | significant amount given past contrib + MR | “no marginal return… optimal… contribute nothing” |

[Evidence: `tables/zero_si_r4_r7_window.csv` | run=20260731_013853 | round=5-6 | agent=2,3,5,6,14 | record=contribution_reasoning]

**Mechanism reading (interpretive, anchored in text):** the dominant stated reason is **MCPR / marginal-return payoff maximisation**, not “I cannot afford to give” and not “I was gossiped.” Several agents who gave substantial amounts at R5 flip to the zero template at R6. That pattern is consistent with (a) shock+democracy context disrupting prior contribution plans and (b) the model falling back to the individually rational zero benchmark once MCPR is salient in the prompt. It is **not** consistent with liquidity exhaustion for these SI agents.

**Counterevidence:** other SI agents (10, 13, 16, 21, 22, 23, 25) did **not** zero at R6, so the episode is a factional collapse, not an institution-wide shutdown.

---

## SFI focus — cold start, specialists, bursts

### R1 mass zeros

Ten SFI agents opened at zero. Mean SFI prop R1 = **0.022**; R2 jumps to **0.602**. Overall mean prop R1→R2: 0.231 → 0.445.

[Evidence: `tables/prompt_zero_numeric_summary.json` | run=20260731_013853 | round=1-2 | agent=n/a | record=sfi_r1_mean_prop]

R1 reasoning for zeros emphasises exploration, conservation, and lack of history — classic cold-start / wait-and-see (see doc 32).

### Persistent near-zero specialists

From strategy profiles, agents with very low mean prop and high zero shares (notably 1, 11, 17, 19 in earlier profiles; inventory shows SFI zeros spread across 14 agents) repeatedly choose zero with MCPR and free-ride language. They are not liquidity-clipped in the approximate sense above.

### Bursty agents

Fourteen burst rounds (contribution > own mean + 1.5 SD) appear among high-variance SFI agents. Only **1/14** bursts immediately follow a positive LDF payout; **5/14** fall on democracy rounds; **2/14** on shock rounds. Burst timing is therefore **not** cleanly explained by payout reciprocity; democracy-round visibility is a partial correlate.

[Evidence: `tables/sfi_burst_rounds.csv` | run=20260731_013853 | round=varies | agent=0,4,7,8,12,15,18 | record=after_payout]

---

## R2 spike (RQ 12)

The largest single-round jump in mean prop is R1→R2, driven especially by SFI (0.022 → 0.602). Drivers include agents who leave zero and agents who escalate already-positive contributions once R1 peer history exists. Full per-agent table: `r1_r2_spike_by_agent.csv`.

**Competing explanations:**

1. **Conditional cooperation:** agents update toward observed R1 peer contributions once history appears in prompts.
2. **Cold-start artefact:** without peer history, the instruct model defaults to caution/zero; R2 unlocks richer context.

Both are compatible with the data; R2 reasoning frequently references peer patterns and institutional strategy (doc 32). The near-zero SI–SFI peer-mean correlation later in the run (Phase 5: SI corr≈0.05, SFI≈−0.09) warns against treating conditional cooperation as a stable law of the whole path.

---

## Theme rates among zero rounds

Among 91 zero episodes with contribution reasoning:

| Theme regex | Share of zero rounds |
|-------------|---------------------:|
| MCPR / marginal return / payoff max | 61.5% |
| Free-ride / contribute nothing | 44.0% |
| Conserve / budget / wealth | 30.8% |
| Cooperation lexicon | 6.6% |

[Evidence: `tables/zero_contribution_episodes.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=theme_flags]

Zeros are overwhelmingly framed as **individually rational free-riding under low MCPR**, not as “I want to cooperate but cannot.”

---

## Warm-glow note (RQ 27)

`reasoning_action_flags.csv` marks **54** `cooperative_language_zero_contrib` cases (39 SFI, 15 SI). Inspection shows many of those excerpts are MCPR/free-ride rationales that the earlier flagger treated as “cooperative language” broadly. True warm-glow (cooperative *intent* language + zero action) is rarer in a strict cooperation-lexicon filter. Treat the 54 as **language–action inconsistency candidates**, not proven warm-glow utility.

---

## Confidence

High on counts and R6/R1 zero shares. Medium on mechanism (MCPR salience vs shock). Low on liquidity classification precision (end-of-round wealth proxy).

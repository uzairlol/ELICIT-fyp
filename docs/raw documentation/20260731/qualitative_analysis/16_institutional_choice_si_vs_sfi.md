# 16 — Institutional Choice SI vs SFI (20260731)

**Opening claim.** There is **no endogenous institutional choice** in this climate/LDF run. Developed agents are forced into SI; developing agents into SFI every round. Apparent “SI vs SFI behaviour” is therefore collinear with group, wealth, Stage-2 rights, and prompt role text. Treating mean prop gaps as causal institution effects is unsupported.

---

## Quantitative backbone

12 SI / 14 SFI every round; 0 mismatches in extraction QC. Mean prop nearly identical (0.291 vs 0.296); distributions differ (SFI median 0.034, more zeros).

[Evidence: `tables/prompt3_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=si_sfi]  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=climate_mode_forced_institution]

---

## Raw discourse — forced routing in agents’ own institution text

**Developing / SFI agents, R1** (repeated across agents 0,1,4,…):

> Climate/LDF mode defaults developing countries to the non-binding agreement.

**Developed / SI agents** analogously cite binding-treaty routing. These strings are **scenario facts injected into reasoning**, not deliberative choice.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1 | agent=0,1,4 | record=examples.SFI_damage_or_ldf]  
[Evidence: `tables/reasoning_blocks.csv` | run=20260731_013853 | round=1 | agent=varies | record=kind=institution]

Contribution-stage language still *uses* the institution label:

**SI agent 2, R2:** “…considering previous round's group average and my internal beliefs about SI strategy.”  
**SFI agent 1, R1:** “…balance immediate resilience needs with long-run cooperation incentives.”

So agents *talk about* their assigned institution’s strategy, but they did not select it.

---

## Counterexamples / what would change the claim

An abstract (non-LDF) scenario with free Stage-0 choice would be required to study institutional preference. This pack’s Full LDF run cannot.

---

## Limits

High confidence on forced routing. Null causal SI effect is a design fact, not a behavioural discovery.

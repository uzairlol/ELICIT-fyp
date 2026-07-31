# 32 — Zero-Contribution Reasoning (Qualitative) (20260731)

Raw contribution-reasoning for zero and near-zero episodes. Numbers and episode lists: [`31_zero_contribution_episodes.md`](../quantitative_analysis/31_zero_contribution_episodes.md).

**Claim in prose:** When agents contribute zero in this run, they usually *say* they are maximising payoff under low MCPR or conserving wealth while they learn — not that the engine forced them to. SI’s post-shock R6 zeros use almost identical payoff-max templates. SFI’s R1 zeros sound like exploration. Later SFI zeros often name free-riding explicitly.

---

## SI — round 6 zero bloc (after shock R5)

Five SI agents went to zero together. Their own words:

**Agent 2, R6 (SI), evidence `RB-06-A2-contribution`:**

> Given a high budget and low marginal return, I choose to contribute nothing to maximize my payoff.

One round earlier the same agent wrote (R5):

> Maximizing cumulative payoff by choosing a contribution that is near the maximum allowed, taking into account MCPR and Stage 2 budget.

[Evidence: `tables/zero_si_r4_r7_window.csv` | run=20260731_013853 | round=5-6 | agent=2 | record=contribution_reasoning]

**Agent 3, R6:** same “high budget and low marginal return… contribute nothing” template. At R5 they still framed a moderate contribution as balancing self-interest and cooperation.

**Agent 5, R5 and R6:** already zero at the shock round, citing MCPR 0.1333; R6 repeats optimality of nothing. This agent did not “collapse after giving” — they stayed on a zero strategy through the shock window.

**Agent 6, R6:**

> Given a low MCPR and no free endowment, contributing nothing maximizes my payoff in this scenario.

**Agent 14, R6:**

> Given no marginal return to me per unit contributed, it is optimal for my payoff to contribute nothing.

**Reading:** The shared semantic content is *individual payoff + MCPR*, not climate damage, not gossip, not democracy. The shock calendar may still have triggered the re-evaluation (timing), but the *stated* reason is stage-game selfishness. Confidence: medium on timing link, high on stated content.

**Counterexample SI who did not zero at R6** (agent 21, R6 contribution reasoning from blocks — positive contributors continued “strategy / cooperation balance” talk). The institution did not speak with one voice.

---

## SFI — round 1 cold-start zeros

**Agent 0, R1 (`RB-01-A0-contribution`):**

> Contributing nothing allows me to conserve wealth and assess future opportunities.

**Agent 9, R1 (`RB-01-A9-contribution`):**

> Contributing nothing allows me to conserve resources and observe the behavior of other agents without committing my institution's funds.

**Agent 24, R1 (`RB-01-A24-contribution`):**

> Choosing a contribution of 0 million USD, as I have no prior experience with this institution and need to explore options without committing significant funds.

[Evidence: `tables/reasoning_blocks.csv` | run=20260731_013853 | round=1 | agent=0,9,24 | record=contribution]

These are **wait-and-see / exploration** frames. They do not claim inability to pay; they claim informational caution. That supports the cold-start artefact reading of the R1→R2 spike.

---

## SFI — explicit free-ride language (later zeros)

**Agent 0, R5 (`RB-05-A0-contribution`):**

> Given high contributions from SI members, I choose to free ride and contribute nothing.

**Agent 0, R3:**

> Given high peer contributions and no significant marginal return to me per unit contributed, I choose not to contribute.

Here the agent both *observes* high peer (SI) contributions and *chooses* to free-ride — the opposite of image repair. This is also an example of the language–action flag class: the text discusses contribution/peers while the action is zero.

[Evidence: `tables/reasoning_action_flags.csv` | run=20260731_013853 | round=3,5 | agent=0 | record=cooperative_language_zero_contrib]

**Agent 1, R2:**

> Given our institution's history of minimal contribution and no cooperation incentives, it is rational to choose a zero-contribution strategy.

That is **conditional defection** (match a low-contribution peer history), not warm glow.

---

## R2 spike — what agents say when they leave zero

SFI mean prop jumps from 0.022 to 0.602. Example movers (from `r1_r2_spike_by_agent.csv`):

Many R2 texts shift from conservation to “balance immediate resilience needs with long-run cooperation incentives” (a Prompt-6 SFI template). Example from Prompt 6 lock:

**Agent 1, R1 (SFI):**

> Choosing a moderate contribution to balance immediate resilience needs with long-run cooperation incentives.

**Agent 19, R1 (SFI) — stayed cautious:**

> Contributing nothing allows me to conserve resources and observe the behavior of other agents, without immediately committing to a cooperative action.

So R2 is not universal conversion; specialists remain. The spike is a **compositional** jump: enough SFI agents escalate that the mean explodes while a zero-prone minority remains.

[Evidence: `tables/r1_r2_spike_by_agent.csv` | run=20260731_013853 | round=1-2 | agent=all | record=delta_prop]  
[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1 | agent=1,19 | record=examples.SFI_cooperate]

---

## Burst after zero — agent 8

Agent 8 burst at R6 with contribution 430,812 after a prior LDF payout of 20,250 (one of the rare `after_payout=1` bursts). Without claiming gratitude as proven motive, the sequence is: receive payout → large proportional contribution. Most other bursts do **not** follow payouts (doc 31).

[Evidence: `tables/sfi_burst_rounds.csv` | run=20260731_013853 | round=6 | agent=8 | record=after_payout]

---

## Warm-glow versus free-ride rhetoric

Of 54 rows flagged `cooperative_language_zero_contrib`, the modal content is still MCPR/free-ride (see samples above). A stricter reading: agents often **narrate the contribution decision problem** while selecting zero — expressive engagement with the game without paying. That is related to warm-glow but not identical to “I feel good about helping.” Prefer the label **decoupled cooperative talk** unless the sentence affirms cooperative intent.

---

## Limits

- Reasoning is short, templated, and model-specific (`llama3.1:8b`).
- Shock and democracy coincide at R5 — cannot separate those triggers from text alone.
- Gossip reconstruction does not appear in the R6 SI zero templates.

**Confidence:** high that stated reasons are MCPR/payoff/conserve; medium that R6 clustering is shock-triggered; low on latent motives beyond the text.

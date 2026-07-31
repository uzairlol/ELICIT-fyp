# 24 — Behavioural Economics Interpretation (20260731)

Organising question: **How can repeated interaction move a group from voluntary contribution, through social enforcement, toward institutional adaptation when collective resources, enforcement responsibilities, and redistribution mechanisms are imperfectly observed or controlled?**

This document maps only concepts that earn their keep against Prompts 3–7 evidence. Concepts without traction are listed as unused (not forced).

**Run:** `20260731_013853` · Model: `llama3.1:8b`

---

## Summary map

| Concept | Fit | One-line finding |
|---------|-----|------------------|
| Conditional cooperation / peer matching talk | Moderate | Agents cite peer averages / “contributors follow” language; prop distributions remain polarised |
| Reputation / signalling | Weak–moderate (negative on repair) | Bad-rep and gossip targets show mean Δ prop **negative**, not image repair |
| Punishment / negative reciprocity | Moderate (SI only) | Costly Stage-2 exists; language cites free-riders; punishment-weakening proposals fail |
| Reward / positive reciprocity | Moderate | Subsidy↑ proposals dominate democracy; rewards cheaper than punish EFFECT |
| Enforcement as public good / second-order free-riding | Moderate | Weak corr(~0.14) between prop and enforcement spend; democracy is costless substitute |
| Bounded rationality / prompt-shaped beliefs | Strong (method) | Short, repetitive reasoning; strategy/self-interest vs incentives templates |
| Institutional choice / path dependence | Strong (architecture) / Mixed (behaviour) | Forced SI/SFI by group; parameter drift toward subsidy/LDF equity |
| Inequity aversion / fairness norms | Weak | Fairness language rare outside SI punish blocks; concept rates ≈0 for fairness/reciprocity in shared corpus |
| Conformity | Weak–moderate | Mild IQR compression; 5 near-zero vs 13 high specialists persist |
| Crowding out of intrinsic motivation | Speculative | Not identifiable; no intrinsic baseline |

---

## Concept-by-concept

### 1. Conditional cooperation

**Definition:** Contribute more when expecting peers to contribute (Fischbacher et al.–style conditional cooperators).

**Evidence for:** Contribution prompts expose previous same-institution average; SI keyness highlights “contributors follow”, “contribution peers”, “follow strategy”. SFI: “peers contribute”, “low contributors”.

[Evidence: `architecture/06_agent_information_boundaries.md` | run=n/a | round=n/a | agent=n/a | record=Stage1_prev_avg]  
[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=top_SI_bigrams]

**Excerpt:** “Medium contribution to balance self-interest with cooperation, considering previous round's group average…” (agent 2, round 2, SI).

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=2 | agent=2 | record=examples.SI_cooperate]

**Counterevidence:** Mean prop SI≈0.291 vs SFI≈0.296 (negligible); SFI median≈0.034 with polarisation — not a single conditional schedule.

**Strength:** Moderate (language + information design); weak as identified behavioural type.

---

### 2. Reputation and signalling

**Definition:** Agents manage social image / expected future treatment via reputation-relevant actions.

**Evidence for:** Reputation and ToM exist; gossip reconstructed from low ToM scores; agents see own reputation.

**Evidence against repair:** After bad-rep / gossip-target events, mean Δ `prop_of_wealth` is typically **negative** (e.g. SFI gossip imm mean Δ≈−0.20; SI/SFI bad-rep imm mean Δ negative).

[Evidence: `tables/prompt4_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=event_summary_head]  
[Evidence: `qualitative_analysis/11_reputation_and_gossip_events.md` | run=20260731_013853 | round=n/a | agent=n/a | record=negative_delta]

**Counterevidence:** No clean “punished → contribute more” pattern; gossip not in raw JSON (reconstruction limits).

**Strength:** Moderate that reputation events matter; **weak/contrary** for classic image-repair signalling.

---

### 3. Negative reciprocity / punishment

**Definition:** Costly sanction of free-riders or norm violators.

**Evidence for:** SI Stage-2 costly punish; excerpts: “Punishing free-riders and rewarding cooperative agents…”. Two proposals to set `PUNISHMENT_EFFECT=1` fail adoption.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1 | agent=2 | record=examples.SI_punishment]  
[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=20,25 | agent=10,21 | record=punishment_proposals]

**Counterevidence:** SFI cannot punish; enforcement spend only weakly tracks contribution; sparse democracy ballots.

**Strength:** Moderate inside SI; not a whole-economy mechanism.

---

### 4. Positive reciprocity / rewards

**Definition:** Costly or institutional rewards for cooperators.

**Evidence for:** Reward tokens in SI; adopted rules cluster on `SUBSIDY_FRACTION` increases (3 of 6 adopted); subsidy recycles punishment-pool resources toward top contributors.

[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=adopted_by_category]

**Counterevidence:** Post-adoption Δ prop is small/confounded; rewards do not erase polarisation.

**Strength:** Moderate for institutional preference toward reward-side adaptation.

---

### 5. Enforcement as a public good / second-order free-riding

**Definition:** Maintaining sanctions is itself a costly collective good; agents may free-ride on others’ enforcement.

**Evidence for:** Stage-2 costs fall on SI only; mean within-round corr(prop, enforcement tokens)≈0.14; top-quartile prop agents pay ~35% of tokens — concentration without monopoly. Democracy is **token-costless** meta-governance (cheap substitute).

[Evidence: `qualitative_analysis/17_enforcement_as_public_good.md` | run=20260731_013853 | round=n/a | agent=n/a | record=burden]  
[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=enforcement_corr_mean]

**Counterevidence:** No survey item separating “support punish” from “spend”; failed weakening votes show preference for strong EFFECT on paper.

**Strength:** Moderate (structural + spending pattern); motives remain interpretive.

---

### 6. Bounded rationality and belief formation

**Definition:** Limited computation, heuristic belief updates, prompt-sensitive strategies.

**Evidence for:** Mean contribution reasoning ~10 tokens; repetitive SI “self-interest/strategy” vs SFI “immediate/long-run incentives” templates; ToM empty at round 1 then filled; agents lack numeric LDF pool.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=corpus_stats]  
[Evidence: `architecture/06_agent_information_boundaries.md` | run=20260731_013853 | round=n/a | agent=n/a | record=ldf_pool_hidden]

**Counterevidence:** Some multi-factor excerpts exist; not pure noise.

**Strength:** Strong as modelling premise; moderate as explanation of specific quantities.

---

### 7. Strategic uncertainty

**Definition:** Uncertainty about others’ strategies and rule paths.

**Evidence for:** No current-round peer contributions at decision time; hidden LDF stock; sparse proposals (14 across 6 sessions).

[Evidence: `architecture/06_agent_information_boundaries.md` | run=n/a | round=n/a | agent=n/a | record=Stage1]  
[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=n_proposals]

**Strength:** Moderate (design-supported).

---

### 8. Institutional choice and path dependence

**Definition:** Agents select or inherit rules; early choices constrain later equilibria.

**Evidence for:** Climate mode **forces** developed→SI, developing→SFI every round; democracy drifts subsidy↑ and LDF equity↑; punishment-weakening path blocked.

[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=climate_mode_forced_institution]  
[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=adopted_by_category]

**Counterevidence:** Institution membership itself is not endogenous here — path dependence is in **parameters**, not SI↔SFI switching.

**Strength:** Strong for forced routing; moderate for parameter path dependence (single seed).

---

### 9. Inequity aversion / fairness / social preferences

**Definition:** Utility reduced by unfair payoff/contribution gaps (Fehr–Schmidt style) or fairness motives.

**Evidence for:** Occasional SI punish fairness talk; LDF equity-weight proposals adopted twice.

**Counterevidence:** Shared-corpus fairness/reciprocity concept rates ≈ absent; SFI_fair examples empty in Prompt 6 sample; absolute SI≫SFI wealth transfers persist by design.

[Evidence: `qualitative_analysis/19_si_sfi_language_comparison.md` | run=20260731_013853 | round=n/a | agent=n/a | record=concept_rates]  
[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=examples.SFI_fair]

**Strength:** Weak as primary driver; moderate only for equity **rule** politics.

---

### 10. Conformity

**Definition:** Match modal group behaviour.

**Evidence for:** Late IQR prop 0.178 vs early 0.238; zero-share 0.19→0.12.

**Counterevidence:** Late std still ~0.66; 5 near-zero vs 13 high-mean agents; group-mean autocorr≈0.03.

[Evidence: `tables/prompt7_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=dispersion]

**Strength:** Weak–moderate.

---

### Concepts intentionally unused or speculative only

| Concept | Why unused / speculative |
|---------|--------------------------|
| Crowding out of intrinsic motivation | No intrinsic vs extrinsic treatment contrast |
| Pure altruism | Not separable from prompt boilerplate “cooperation” |
| Guilt aversion | No second-order belief elicitation of expectations about expectations |

---

## Answer to the organising question (bounded)

In this run, repeated interaction sustains **positive average voluntary contributions** without clear norm internalisation. Social enforcement (reputation/gossip) does **not** produce contribution repair. Institutional adaptation occurs through **costless democracy**, favouring subsidies and LDF equity weights, while costly Stage-2 enforcement remains uneven and SI-gated. Imperfect observation of the LDF pool and forced SI/SFI assignment limit claims that agents optimise redistribution or choose institutions endogenously.

**Confidence:** moderate on descriptive mapping; low on deep preference identification (single seed, LLM artefacts).

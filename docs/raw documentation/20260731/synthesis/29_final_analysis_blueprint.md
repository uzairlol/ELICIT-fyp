# 29 — Final Analysis Blueprint (20260731)

Analysis blueprint only — not a polished paper manuscript. Synthesises Prompts 0–8 for run:

`simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853`

**Primary metric:** analyst `prop_of_wealth = contribution / wealth_end_of_round` (disclosed approximation).  
**Model:** `llama3.1:8b` (local Ollama).

Every major conclusion below includes quantitative evidence, reasoning evidence, counterevidence, limitation, and confidence.

---

## 1. Research motivation

Climate-finance governance embeds repeated contribution, contested enforcement, and evolving rules under incomplete observation of collective resources. ELICIT provides a logged multi-agent laboratory for those mechanisms.

| Element | Content |
|---------|---------|
| Quantitative | 26 agents × 30 rounds; 780 agent-rounds; 6 democracy sessions |
| Reasoning | 3854 reasoning blocks with evidence IDs |
| Counterevidence | Single Full condition — not a multi-scenario proof of motivation |
| Limitation | Not calibrated to real Parties |
| Confidence | High that the *design* targets the motivation; low as policy relevance proof |

---

## 2. Core economics question

**How can repeated interaction move a group from voluntary contribution, through social enforcement, toward institutional adaptation when collective resources, enforcement responsibilities, and redistribution mechanisms are imperfectly observed or controlled?**

| Element | Content |
|---------|---------|
| Quantitative | Mean prop≈0.293 persists; democracy adopts 6 rules; Stage-2 SI-only |
| Reasoning | Contribution talk mixes self-interest/cooperation; proposal talk cites cooperation/trust |
| Counterevidence | Reputation/gossip → mean Δ prop negative (enforcement channel fails repair) |
| Limitation | Forced SI/SFI removes endogenous institutional choice |
| Confidence | High as organising question; mixed as answered by this run |

---

## 3. Why the Loss and Damage Fund is suitable for multi-agent modelling

Real FRLD: established COP27 (2/CP.27); operationalised COP28 (1/CP.28 Governing Instrument + Board; World Bank interim FIF invitation). Contribution, access, and delivery remain contested institutional problems.

| Element | Content |
|---------|---------|
| Quantitative | Sim: dual-use Stage-1→LDF deposits; developing-only payouts; shocks R5/R10 |
| Reasoning | Climate-role prompt text; SFI damage/LDF boilerplate |
| Counterevidence | Real fund ≠ stylised pool; pledges/disbursement not modelled |
| Limitation | Hidden pool + exogenous payout family |
| Confidence | High for *suitability of the problem class*; low for external validity of results |

[External: `theory/28_external_sources.md`]

---

## 4. Why repeated interaction matters

| Element | Content |
|---------|---------|
| Quantitative | Agent lag-1 autocorr≈0.215; group-mean autocorr≈0.031; shock regain 1–2 rounds |
| Reasoning | Agents reference previous group averages |
| Counterevidence | Aggregate path not sticky — repetition alone does not lock a rate |
| Limitation | Finite 30-round horizon |
| Confidence | High that dynamics require repetition to observe; medium on stabilisation |

---

## 5. Why a small instruct model was used

Methodological: controllable local inference, volume of agent-rounds, inspectable traces, ablation feasibility, bounded decision surface. Not “cost sympathy.”

| Element | Content |
|---------|---------|
| Quantitative | Mean contribution block ~10 tokens; template keyness SI vs SFI |
| Reasoning | Repetitive strategy/self-interest vs incentives/immediate/long-run |
| Counterevidence | Limited strategic depth may understate human institutional bargaining |
| Limitation | Model-specific artefacts; no cross-model replication here |
| Confidence | High on which model; medium on defence |

---

## 6. Simulation architecture

Round pipeline: (forced) institution → Stage-1 contribution / PG → SI Stage-2 punish/reward → subsidy → optional shock → LDF collect/payout → reputation/ToM/gossip → periodic democracy.

| Element | Content |
|---------|---------|
| Quantitative | Modules present in JSON: LDF fields, `constitutional_change`, `tom_scores` |
| Reasoning | Debug/reasoning kinds: contribution, punishment, institution, proposal |
| Counterevidence | README “batched ToM” wording may lag code (pairwise in later engineering) |
| Limitation | Architecture docs describe code; behaviour is LLM-stochastic |
| Confidence | High on architecture map |

---

## 7. Mathematical model

Implemented equations in `architecture/05_mathematical_model.md`: Stage-1 cap `max(0,int(wealth))`; PG multiplier; Stage-2 costs; LDF pool updates; damage = base×severity×vulnerability; analyst prop columns.

| Element | Content |
|---------|---------|
| Quantitative | Formulas verified against `loss_damage_fund.py`, `agent.py`, `environment.py` |
| Reasoning | N/A (code) |
| Counterevidence | `contribution_capacity` is index 1.0/0.10 — not budget |
| Limitation | End-of-round wealth denominator for prop |
| Confidence | High |

---

## 8. Agent information boundaries

Agents see own LDF flows/damage, peer history (delayed), own reputation; **do not** see numeric LDF pool or same-round peer contributions. Climate mode forces SI/SFI by group.

| Element | Content |
|---------|---------|
| Quantitative | Prompt construction audit in doc 06 |
| Reasoning | Institution strings echo forced-routing facts |
| Counterevidence | Real IDs (low anonymity) in LDF mode |
| Limitation | Cannot claim fund-stock optimisation |
| Confidence | High |

---

## 9. SI and SFI contribution behaviour

| Element | Content |
|---------|---------|
| Quantitative | Mean prop SI 0.291 vs SFI 0.296 (g≈0); medians 0.194 vs 0.034; abs SI≫SFI; SFI zeros 16% vs SI 6% |
| Reasoning | SI: strategy/self-interest; SFI: incentives/immediate/long-run |
| Counterevidence | Means similar — distributional story dominates averages |
| Limitation | Perfect collinearity institution↔group |
| Confidence | High descriptive; null causal institution effect |

---

## 10. Contribution responses to climatic shocks

| Element | Content |
|---------|---------|
| Quantitative | R5: SI mean Δ≈−0.18, SFI +0.19 (skewed); R10 mixed; regain pre-mean 1–2 rounds |
| Reasoning | Post-shock blocks still short/template |
| Counterevidence | Shock rounds coincide with democracy (5,10) — confound |
| Limitation | Only two shock events |
| Confidence | Medium |

---

## 11. Reputation and gossip effects

| Element | Content |
|---------|---------|
| Quantitative | 145 reconstructed gossip rows; bad-rep/gossip mean Δ prop typically negative (e.g. SFI gossip imm −0.20) |
| Reasoning | Rare repair motifs vs more opportunistic tags |
| Counterevidence | Some agents show +Δ after events (e.g. SI agent 5) |
| Limitation | Gossip reconstructed (trigger≤7, top-5); not in raw JSON |
| Confidence | Medium–high on average decline; medium on mechanism |

---

## 12. Individual agent strategies

| Element | Content |
|---------|---------|
| Quantitative | 5 near-zero (mean prop&lt;0.05) vs 13 high (≥0.25); heterogeneous gossip exposure |
| Reasoning | Motif tags per profile CSV |
| Counterevidence | Not all high contributors cut after gossip |
| Limitation | Regex motifs; inference labelled |
| Confidence | Medium |

---

## 13. Proposal trends

| Element | Content |
|---------|---------|
| Quantitative | 14 proposals: reward_subsidy 6, ldf_equity 3, ldf_redistribution 2, punishment_weakening 2, ldf_damage_weight 1; 6 adopted |
| Reasoning | Cooperation/trust boilerplate in proposal reasons |
| Counterevidence | Thin agenda (2–3 proposals/session) |
| Limitation | Parameter whitelist bounds agenda |
| Confidence | High on category counts |

---

## 14. Reasoning behind proposals

| Element | Content |
|---------|---------|
| Quantitative | Mean proposer prop 0.364 vs overall 0.293 |
| Reasoning | Short texts (~13 tokens); fairness language more in SI punish than SFI proposals |
| Counterevidence | Rhetoric ≠ incidence of benefits (cross-group rule shopping) |
| Limitation | Sparse sample (14) |
| Confidence | Medium |

---

## 15. Institutional choice

| Element | Content |
|---------|---------|
| Quantitative | 12 SI / 14 SFI every round |
| Reasoning | Forced-routing institution reasoning strings |
| Counterevidence | Free choice **not** tested in this scenario |
| Limitation | Cannot identify preference for SI vs SFI |
| Confidence | High (null endogenous choice) |

---

## 16. Enforcement as a public good

| Element | Content |
|---------|---------|
| Quantitative | Corr(prop, Stage-2 spend)≈0.14; top-quartile prop pay ~35% of tokens; punishment-weakening fails twice |
| Reasoning | SI punish excerpts cite free-riders |
| Counterevidence | Democracy is costless — substitutes for costly enforcement |
| Limitation | No survey of “support vs spend” |
| Confidence | Medium |

---

## 17. Political economy of governance

| Element | Content |
|---------|---------|
| Quantitative | Adopted path: subsidy↑, LDF equity↑, damage weight↑; SFI proposers win SI subsidy; SI proposers win LDF params |
| Reasoning | Cooperative frames in votes |
| Counterevidence | Same-group vote rate only ~0.51 — weak bloc voting |
| Limitation | Single seed; plurality with sparse ballots |
| Confidence | Medium–high descriptive |

---

## 18. Behavioural economics interpretation

Strongest fits: bounded/prompt-shaped reasoning; parameter path dependence; conditional-cooperation *talk*; weak/contrary image repair; moderate second-order enforcement tension. Weak: inequity aversion as primary driver; crowding-out unidentified.

| Confidence | Medium on mapping; low on deep preference ID |

---

## 19. Ostrom and governing the commons

Partial analogues (repetition, monitoring fragments, sanctions, collective choice). Missing: graduated sanction ladder, nested enterprises, voluntary membership, polycentric local rules. **Do not claim design-principle implementation.**

| Confidence | High on non-claim; medium on partial mapping |

---

## 20. Norm emergence verdict

**Limited or mixed evidence of norm emergence.** Positive mean contributions and some rule formalisation coexist with polarisation, weak obligation language, and non-repair after social sanctions.

| Confidence | Moderate |

---

## 21. Cooperation stability verdict

**Moderately positive average cooperation with limited path stability.** Separate from norms: transfers persist on average without a shared internalised contribution rate.

| Confidence | Moderate |

---

## 22. Limitations

1. Single seed, single model, single Full condition.  
2. Forced SI=developed / SFI=developing confound.  
3. Gossip not in results JSON (reconstructed).  
4. `prop_of_wealth` uses end-of-round wealth.  
5. Shock–democracy calendar overlap.  
6. Dual-use Stage-1/LDF deposit.  
7. Hidden LDF pool.  
8. Redistribution algorithm largely exogenous.  
9. Small-instruct template artefacts.  
10. No real-world calibration/validation.

---

## 23. Future work

Directions that arise from **observed** results (not generic wishlist):

| Finding that motivates it | Future direction |
|---------------------------|------------------|
| Stable but different strategies (near-zero vs high clusters) | Longer runs; strategy-type classification; seed sweeps |
| SI/SFI language diverge while mean prop similar | Ablate prompts; cross-model replication |
| Reputation/gossip → contribution decline | Test repair incentives; store native gossip; vary ToM |
| Punishment-weakening fails; Stage-2 burden uneven | Costly voting; enforcement-cost treatments |
| Proposal cascades on democracy+shock rounds | Stagger democracy vs shocks experimentally |
| Parameter path toward subsidy/equity | Lock-in vs reset treatments; agenda variation |
| Contribution without strong norm language | Separately measure norms vs behaviour |
| Hidden pool / dual-use deposit | Make fund visibility and separate LDF pledges experimental factors |
| Forced membership | Endogenous SI/SFI choice condition |
| Exogenous payout family | Endogenous redistribution / access rules |
| llama3.1:8b artefacts | Larger/different LMs; prompt ablations |
| Absolute SI≫SFI wealth | Calibrated country-like actors (careful external claims) |

Do **not** claim empirical prediction of real FRLD performance without calibration and validation.

---

## Quality gate (Prompt 9)

Numbers above checked against `prompt3`–`prompt7` JSON summaries; SI/SFI labels = forced group; run name and model as locked in `00_project_memory.md`; COP27 vs COP28 distinction as in `28_external_sources.md`. Unsupported causal SI-vs-SFI and fund-effectiveness claims avoided.

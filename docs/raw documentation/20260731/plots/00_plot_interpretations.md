# 00 — Plot Interpretations (20260731)

Interpretation of every PNG in this folder for run `20260731_013853`. Each entry: what is plotted, what is visible, how it ties to a documented claim, caveats, evidence pointer.

---

## Contributions

### `contrib_mean_prop_trajectories.png`
- **Plot:** Mean `prop_of_wealth` by round for SI, SFI, ALL.  
- **Visible:** R2 spike; SI dip around R6; series stay positive but volatile; SI≈SFI means.  
- **Claim:** Moderately positive average cooperation without path stability (docs 08, 22, 31).  
- **Caveats:** End-of-round wealth denominator; forced SI/SFI.  
- **Evidence:** `tables/contribution_round_summary.csv`

### `contrib_smoothed_prop.png`
- **Plot:** Smoothed mean prop trajectories.  
- **Visible:** Same structure with less noise — R2 jump and mid-run wiggles remain.  
- **Claim:** Smoothing does not create a flat equilibrium.  
- **Caveats:** Bandwidth choice.  
- **Evidence:** Prompt 3 script

### `contrib_median_prop_iqr.png`
- **Plot:** Median prop with IQR bands by institution.  
- **Visible:** SFI median near floor much of the run; SI median higher; IQR wide.  
- **Claim:** Means mislead — SFI skew/polarisation (doc 09).  
- **Caveats:** —  
- **Evidence:** `si_sfi_prop_by_round.csv`

### `contrib_dispersion_prop.png`
- **Plot:** Within-round dispersion of prop (std/IQR).  
- **Visible:** High residual dispersion; mild late compression only.  
- **Claim:** Weak convergence → limited norm emergence (doc 21).  
- **Evidence:** `norm_stability_round_series.csv`

### `contrib_zero_frequency.png`
- **Plot:** Zero-contribution share by round/institution.  
- **Visible:** SFI R1 ~71% zeros; SI R6 ~42% zeros; later SI zeros rarer.  
- **Claim:** Cold-start and post-shock voluntary zeros (docs 31–32).  
- **Caveats:** Not liquidity-forced (approx).  
- **Evidence:** `zero_contribution_by_round.csv`

### `contrib_mean_absolute_log.png`
- **Plot:** Mean absolute contributions (log scale), SI vs SFI.  
- **Visible:** SI orders of magnitude above SFI.  
- **Claim:** Absolute SI≫SFI while prop means similar — wealth confound.  
- **Caveats:** Log compresses; dual-use LDF deposit.  
- **Evidence:** prompt3 absolute means

### `contrib_individual_prop_SI.png` / `contrib_individual_prop_SFI.png`
- **Plot:** Per-agent prop paths.  
- **Visible:** SI more banded mid-range; SFI shows near-zero lines and spike lines.  
- **Claim:** Strategy heterogeneity (doc 12).  
- **Caveats:** Overplotting.  
- **Evidence:** `contributions.csv`

### `shock_delta_boxplot.png`
- **Plot:** Within-agent Δ prop around R5/R10 by institution.  
- **Visible:** Wide spreads; SI negative tendency post-R5; mixed R10.  
- **Claim:** Shocks disturb composition; means recover (doc 10).  
- **Caveats:** Democracy same rounds.  
- **Evidence:** `shock_agent_deltas.csv`

---

## Reputation / gossip

### `reputation_mean_trajectories.png`
- **Plot:** Mean reputation by group/institution over rounds.  
- **Visible:** Movement after R1 empty ToM; not a smooth climb to high trust.  
- **Claim:** Reputation is live but not a stabilising high-trust attractor.  
- **Caveats:** Default 5.0 init; discrete ToM.  
- **Evidence:** `reputation_gossip_panel.csv`

### `reputation_event_deltas.png`
- **Plot:** Distribution of Δ prop after bad-rep / gossip / rep-drop.  
- **Visible:** Mass on negative side; minority positive.  
- **Claim:** No dominant image-repair response (doc 11).  
- **Caveats:** Endogenous events.  
- **Evidence:** `reputation_gossip_event_summary.csv`

### `gossip_target_frequency.png`
- **Plot:** How often agents appear as reconstructed gossip targets.  
- **Visible:** Uneven — some agents repeatedly named; some never.  
- **Claim:** Concentrated social pressure; often mid/high prop agents (RQ 7).  
- **Caveats:** Reconstruction / ties.  
- **Evidence:** `gossip_bulletins_reconstructed.csv`

---

## Democracy / enforcement

### `proposal_categories_timeline.png`
- **Plot:** Proposal categories by democracy round.  
- **Visible:** Sparse points; subsidy and LDF categories recur; punishment weakening at R20/R25.  
- **Claim:** Thin agenda, reward/equity bias (doc 14).  
- **Evidence:** `proposals_coded.csv`

### `adopted_rules_timeline.png`
- **Plot:** Adopted parameter changes over rounds.  
- **Visible:** Upward subsidy/equity/damage path; no EFFECT increase.  
- **Claim:** Ratchet toward carrots/redistribution (doc 18).  
- **Evidence:** `adopted_rules.csv`

### `proposers_by_institution.png`
- **Plot:** Counts of proposers SI vs SFI.  
- **Visible:** Both sides propose; SI slightly more.  
- **Claim:** Cross-group rule shopping possible (doc 15).  
- **Evidence:** `proposals_coded.csv`

### `enforcement_burden.png`
- **Plot:** Enforcement spending vs contribution burden.  
- **Visible:** Weak positive association; not exclusive high-contributor police.  
- **Claim:** Second-order public good (doc 17).  
- **Evidence:** `enforcement_burden_by_agent.csv`

### `sanction_punish_reward_timeline.png` *(dashboard expansion)*
- **Plot:** Total punish vs reward tokens per round.  
- **Visible:** Both channels used across rounds; not a pure punishment regime.  
- **Claim:** SI uses carrots and sticks; democracy still expands subsidies.  
- **Caveats:** Wealth-scaled budgets.  
- **Evidence:** `sanction_timeline.csv`

---

## Language

### `wordcloud_SI_shared.png` / `wordcloud_SFI_shared.png`
- **Plot:** Token clouds on shared kinds.  
- **Visible:** SI: strategy/self-interest; SFI: incentives/immediate/institution.  
- **Claim:** Dialect split (docs 19–20).  
- **Caveats:** Not causal preferences.  
- **Evidence:** prompt6 corpora

### `wordcloud_SI_contribution.png` / `wordcloud_SFI_contribution.png`
- **Plot:** Contribution-only clouds.  
- **Visible:** Same split, decision-stage focus.  
- **Claim:** Contribution talk drives keyness.  
- **Evidence:** prompt6

### `keyness_shared_unigrams.png`
- **Plot:** Signed log-odds z for SI vs SFI.  
- **Visible:** Large |z| on strategy vs incentives terms.  
- **Claim:** Robust lexical contrast (LOO Jaccard high).  
- **Evidence:** `language_logodds_shared_unigrams.csv`

### `concept_rates_shared.png`
- **Plot:** Concept rates (self-interest, fairness, etc.).  
- **Visible:** SI self-interest elevated; fairness/reciprocity near zero.  
- **Claim:** Weak obligation language (doc 21).  
- **Evidence:** `language_concept_rates.csv`

---

## Macro / LDF / inequality (dashboard expansion)

### `gini_wealth_cooperation_rate.png`
- **Plot:** Stored `gini_wealth` and `cooperation_rate` over rounds; shock lines.  
- **Visible:** Coop rate spikes at R2 and fluctuates; wealth Gini falls early then rises again toward ~0.65.  
- **Claim:** Dashboard cooperation_rate ≠ analyst prop story one-to-one; inequality does not steadily vanish.  
- **Caveats:** `cooperation_rate` is simulation-stored, not re-derived here.  
- **Evidence:** `dashboard_macro_series.csv`

### `gini_contribution_vs_wealth.png`
- **Plot:** Gini of absolute contributions, Gini of prop, Gini of wealth.  
- **Visible:** Contribution absolute Gini stays high; prop Gini volatile; wealth Gini U-shaped.  
- **Claim:** Effort inequality and wealth inequality are distinct (RQ 8).  
- **Evidence:** `dashboard_macro_series.csv`

### `wealth_gap_developed_developing.png`
- **Plot:** Mean developed wealth − mean developing wealth.  
- **Visible:** Gap **widens** from ~4.6e6 (R1) to ~2.15e8 (R30).  
- **Claim:** LDF payouts do not close the developed–developing wealth gap in this run (RQ 29 / doc 34).  
- **Caveats:** Initial endowment gulf; PG returns to large absolute SI contributions.  
- **Evidence:** `dashboard_macro_series.csv`

### `ldf_pool_dynamics.png`
- **Plot:** Pool end, contributions total, payouts (log).  
- **Visible:** Pool grows hugely; payouts tiny spikes at R5/R10.  
- **Claim:** Collection ≫ disbursement; agents cannot see pool (docs 06, 35).  
- **Evidence:** `ldf_coverage_by_round.csv`

---

## Reading rule

If a plot’s visual pattern is used in a claim, this file or the parent analysis doc must state the claim in prose with an Evidence tag — plots alone are not arguments.

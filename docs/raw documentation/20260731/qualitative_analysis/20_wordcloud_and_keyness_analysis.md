# 20 — Wordcloud and Keyness Analysis (20260731)

**Opening claim.** Wordclouds and log-odds keyness visualise the same SI/SFI dialect split documented in doc 19: SI clouds denser in strategy/self-interest/follow; SFI denser in incentives/immediate/institution. Clouds alone are descriptive; keyness z-scores and leave-one-out Jaccard justify that the split is not one-agent noise.

Plots: `wordcloud_SI_shared.png`, `wordcloud_SFI_shared.png`, `wordcloud_SI_contribution.png`, `wordcloud_SFI_contribution.png`, `keyness_shared_unigrams.png`, `concept_rates_shared.png`.

---

## Quantitative backbone

Top SI keyness (z): strategy 12.5, following 6.5, self-interest 5.7, payoff 5.4, maximize 5.1.  
Top SFI keyness (z): sfi −10.7, incentives −7.2, highly −5.5, immediate −5.4, long-run −5.2.  
LOO Jaccard: SI mean 0.87 (min 0.76); SFI mean 1.0.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=top_SI_key_terms]

---

## Raw discourse behind the clouds

Wordclouds compress tokens; these sentences are what the tokens come from.

**SI bigram territory (“follow strategy”, “self-interest cooperate”):**

> Medium contribution to balance self-interest with cooperation, considering previous round's group average and my internal beliefs about SI strategy.  
> — agent 2, R2, SI (`RB-02-A2-contribution`)

**SFI bigram territory (“balance immediate”, “cooperate incentives”):**

> Maximizing my cumulative payoff requires a balance between immediate resilience needs and long-run cooperation incentives…  
> — agent 18, R1, SFI (`RB-01-A18-contribution`)

**Concept-rate spike SI self-interest post-shock** (Prompt 6: SI post-shock self_interest rate high) pairs with R6 zero templates:

> Given a high budget and low marginal return, I choose to contribute nothing to maximize my payoff.  
> — agent 2, R6, SI

**Absence in clouds:** fairness/reciprocity tokens barely register — matching empty SFI_fair examples and ≈0 concept rates.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1-6 | agent=2,18 | record=examples]  
[Evidence: `plots/keyness_shared_unigrams.png` | run=20260731_013853 | round=n/a | agent=n/a | record=figure]

---

## How to read the plots (preview of `plots/00_plot_interpretations.md`)

- Shared wordclouds exclude SI-only punishment blocks so SI “fairness” punish talk does not falsely dominate contribution comparisons.  
- Contribution-only clouds emphasise decision-stage lexicon.  
- Keyness bar chart is signed log-odds z, not raw frequency.

---

## Limits

Stopwording and tokenizer choices. Clouds invite over-reading. Confidence high that SI/SFI lexical contrast is robust to leave-one-out; low that tokens equal preferences.

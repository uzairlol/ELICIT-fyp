# 19 — SI / SFI Language Comparison (20260731)

Comparable reasoning corpora and concept-coded differences. Wordclouds alone are insufficient; this report emphasises rates, keyness, and leave-one-agent-out stability.

**Script:** `scripts/analyze_20260731_language.py`  
**Primary contrast:** `SI_shared_kinds` vs `SFI_shared_kinds` (contribution + belief + institution; **excludes** SI-only punishment blocks).  
**Also reported:** contribution-only and post-shock / post-gossip / post-badrep slices.

[Evidence: `tables/language_corpus_stats.csv` | run=20260731_013853 | round=1-30 | agent=all | record=corpus_stats]

---

## Corpus construction

| Corpus | Blocks | Agents | Rounds | Tokens | Mean tokens/block |
|--------|-------:|-------:|-------:|-------:|------------------:|
| SI_all | 2168 | 12 | 30 | 16309 | 7.5 |
| SFI_all | 1686 | 14 | 30 | 11162 | 6.6 |
| SI_shared_kinds | 1440 | 12 | 30 | 9567 | 6.6 |
| SFI_shared_kinds | 1680 | 14 | 30 | 11079 | 6.6 |
| SI_contribution | 360 | 12 | 30 | 3702 | 10.3 |
| SFI_contribution | 420 | 14 | 30 | 4196 | 10.0 |
| SI_proposal_reason | 8 | 7 | 5 | 104 | 13.0 |
| SFI_proposal_reason | 6 | 5 | 5 | 83 | 13.8 |
| SI_post_shock (contrib) | 48 | 12 | 4 | 495 | 10.3 |
| SFI_post_shock (contrib) | 56 | 14 | 4 | 568 | 10.1 |
| SI_post_gossip | 35 | 11 | 18 | 367 | 10.5 |
| SFI_post_gossip | 52 | 11 | 25 | 534 | 10.3 |
| SI_post_badrep | 36 | 12 | 18 | 382 | 10.6 |
| SFI_post_badrep | 68 | 14 | 24 | 707 | 10.4 |

Missing empty texts: **0** in these corpora.

**Comparability notes:**
- SI_all is inflated by 360 punishment blocks — do not use for head-to-head without exclusion.
- Shared-kinds means are nearly identical (~6.6 tokens) — good balance.
- Proposal corpora are tiny (n=8/6) — descriptive only.
- Vote reasoning lives in `votes_parsed.csv`, not `reasoning_blocks.csv` (not merged into main TF corpora here).

Processing: lowercasing; strip `Agent N` strings; drop stopwords/digits/len≤2; light lemma map; **retain** fairness/contribute/punish/cooperate/reputation/rule/loss/trust/future.

---

## Concept-category rates (shared kinds)

Share of blocks with ≥1 regex hit (`tables/language_concept_rates.csv`):

| Concept | SI rate | SFI rate |
|---------|--------:|---------:|
| institutional_choice (SI/SFI/institution…) | 0.768 | 0.792 |
| strategic_adaptation | **0.363** | 0.145 |
| redistribution / LDF | 0.251 | 0.251 |
| self_interest | **0.081** | 0.013 |
| conformity | 0.026 | **0.039** |
| reward | 0.044 | 0.024 |
| reputation | 0.005 | 0.002 |
| punishment | 0.003 | 0.002 |
| group_welfare | 0.006 | 0.002 |
| fairness | ≈0 | 0 |
| reciprocity | 0 | 0 |
| shocks (explicit) | ≈0 | 0 |

**Contribution-only self_interest:** SI **0.303** vs SFI **0.050**.  
**Post-shock contribution self_interest:** SI **0.479** vs SFI **0.054**.

[Evidence: `tables/language_concept_rates.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=self_interest_rate]

Plot: `plots/concept_rates_shared.png`

---

## Keyness (log-odds z, shared kinds)

SI-associated unigrams (highest z): `strategy`, `following`, `self-interest`, `follow`, `significant`, …  
SFI-associated: `sfi`, `incentives`, `highly`, `immediate`, `long-run`, …

Contribution-only SI keys: `self-interest`, `significant`, `payoff`, `strategy`, `maximize`, `cumulative`  
Contribution-only SFI keys: `immediate`, `long-run`, `incentives`, `sfi`, `recent`, `balance`

Distinctive bigrams (shared):  
- SI: `contributors follow`, `follow strategy`, `high contribution`  
- SFI: `peers contribute`, `cooperate incentives`, `contribute highly`

Tables: `language_logodds_shared_*.csv`, `language_logodds_contribution_unigrams.csv`  
Plot: `plots/keyness_shared_unigrams.png`

---

## Stability across agents

Leave-one-agent-out Jaccard on top-15 keyness terms:

- SI side mean Jaccard ≈ **0.87** (min still high)
- SFI side mean Jaccard ≈ **1.0**

[Evidence: `tables/language_keyness_leave_one_out.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=jaccard]

**Finding:** SI/SFI lexical contrasts are **not** an artefact of a single verbose agent.

---

## Interpretation (bounded)

1. **SI language** more often frames **strategy / self-interest / payoff maximisation**, especially in contribution and post-shock slices.  
2. **SFI language** more often names **SFI**, **incentives**, and **immediate vs long-run** tradeoffs (climate-role prompt residue possible).  
3. Classic behavioural tokens (**fairness, reciprocity**) are almost **absent** in coded hits — do not claim strong fairness discourse from this run.  
4. High `institutional_choice` rates partly reflect literal `SI`/`SFI` tokens in belief text (prompted structure), not deep constitutional theory.

Example excerpts (from `prompt6_numeric_summary.json`): see accompanying doc 20 and evidence IDs there.

---

## Limitations

- Bag-of-words / regex concepts miss paraphrase.
- Prompt templates push “cooperation/incentives” language.
- Forced SI=developed / SFI=developing confound remains.
- Punishment corpus asymmetry handled via shared-kinds filter.
- Vote reasons not in primary TF pipeline.

# 20 — Wordcloud and Keyness Analysis (20260731)

Visual term clouds plus defensible frequency / TF-IDF / log-odds comparisons.

**Script:** `scripts/analyze_20260731_language.py`

---

## Wordclouds (illustrative only)

| Plot | Corpus |
|------|--------|
| `plots/wordcloud_SI_shared.png` | SI shared kinds |
| `plots/wordcloud_SFI_shared.png` | SFI shared kinds |
| `plots/wordcloud_SI_contribution.png` | SI contribution reasoning |
| `plots/wordcloud_SFI_contribution.png` | SFI contribution reasoning |

Wordclouds use top-40 term frequencies with size∝freq. They are **not** inferential; use keyness tables for claims.

---

## Term frequency

Top terms (normalised frequency) in shared-kinds corpora: `tables/language_term_freq_shared.csv`.

Both sides heavily use contribution / cooperate / institution vocabulary (prompt gravity). Differences are clearer in keyness than in raw top-10 lists.

---

## TF-IDF (two-document SI vs SFI)

`tables/language_tfidf_shared.csv` — each institution collapsed to one mega-document. Useful as a second view; still sensitive to corpus size. Prefer log-odds z for directed contrast.

---

## Log-odds keyness (primary)

Method: Monroe-style informative Dirichlet log-odds with small prior; report **z**.

### Shared-kinds unigrams

**SI-leaning (z≫0):** strategy, following, self-interest, follow, significant  
**SFI-leaning (z≪0):** sfi, incentives, highly, immediate, long-run  

[Evidence: `tables/language_logodds_shared_unigrams.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=top_z]

Plot: `plots/keyness_shared_unigrams.png`

### Bigrams / trigrams

Files: `language_logodds_shared_bigrams.csv`, `language_logodds_shared_trigrams.csv`.

Notable bigrams:

| Side | Examples |
|------|----------|
| SI | contributors follow; follow strategy; significant amount; high contribution |
| SFI | peers contribute; cooperate incentives; contribute highly; mostly institution |

### Contribution-only keyness

Confirms SI tilt toward **self-interest / maximize / payoff / cumulative** vs SFI **immediate / long-run / incentives / balance**.

[Evidence: `tables/language_logodds_contribution_unigrams.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=contribution_keyness]

---

## Example reasoning blocks (traceable)

### SI + self-interest / strategy vocabulary

See `tables/prompt6_numeric_summary.json` → `examples.SI_cooperate` / contribution keyness contexts.  
When citing in papers, pull full `evidence_id` from `reasoning_blocks.csv` and attach:

`[Evidence: results/To_Use/...20260731_013853.json | run=20260731_013853 | round=<r> | agent=<id> | record=<source_path>]`

### SFI + incentives / long-run

SFI key terms `immediate` / `long-run` align with climate-role prompt guidance for developing agents (`_append_climate_role_guidance`) — **prompted register**, not necessarily emergent theory talk.

[Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_append_climate_role_guidance]

---

## Verbosity / single-agent check

Leave-one-out Jaccard on top-15 keyness terms remains high (SI≈0.87, SFI≈1.0). Differences survive removing any one agent.

[Evidence: `tables/language_keyness_leave_one_out.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=loo]

Mean block length is similar in shared kinds (~74 chars; ~6.6 tokens) — SI is not simply “more verbose” in the comparable corpus (SI_all looks longer mainly due to punishment blocks).

---

## Bottom line

1. Wordclouds show shared cooperation vocabulary.  
2. Keyness + concept rates show a robust SI tilt to **strategic/self-interest framing** and an SFI tilt to **incentives / temporal tradeoff / SFI-label** language.  
3. Fairness/reciprocity discourse is weak in coded rates.  
4. Some SFI distinctive language likely inherits **prompted climate-role** wording.

Stop: no norm-emergence verdict here (Prompt 7).

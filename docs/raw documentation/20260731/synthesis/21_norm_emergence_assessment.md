# 21 — Norm Emergence Assessment (20260731)

Qualified verdict on whether a contribution **norm** emerged. Defined criteria precede interpretation.

**Run:** `20260731_013853`  
**Support metrics:** `tables/prompt7_numeric_summary.json`, Prompts 3–6 outputs.

---

## Distinctions (held fixed)

| Term | Not equivalent to |
|------|-------------------|
| Positive average contribution | Norm |
| Cooperation (positive transfers) | Stable cooperation |
| Conformity / similar language | Internalised obligation |
| Democracy parameter drift | Social norm |
| Prompt-encouraged “cooperate” talk | Emergent norm |

---

## Pre-registered style criteria (disclosed)

### Evidence that would support norm emergence

1. Convergence toward a shared contribution level (falling dispersion)
2. Persistence across rounds (agent autocorr; sustained thresholds)
3. Recovery after shocks without permanent collapse
4. Behavioural response to norm violations (reputation/gossip → repair)
5. Reputation/gossip reinforcing expected conduct
6. Rule proposals formalising shared expectations
7. Language of obligation / fairness / reciprocity
8. Compliance when private incentives differ (not only self-interest talk)
9. Cross-agent recognition of a common expectation

### Evidence against

1. Unstable oscillation / high residual variance
2. Shock- or democracy-driven spikes without consolidation
3. Compliance mainly under sanction threat (weak here: punishment often unused in language)
4. No shared obligation language
5. Persistent polarisation (near-zero vs high contributors)
6. Image management without behavioural repair
7. Prompt wording explaining the talk
8. Institutions changing too often for expectations to settle

Thresholds used in metrics (disclosed): group mean prop levels 0.1/0.2/0.3; near-zero agent mean prop &lt;0.05; high agent ≥0.25.

---

## Criterion-by-criterion results

| Criterion | Result | Key evidence |
|-----------|--------|--------------|
| Convergence / lower dispersion | **Partial** | Late mean IQR prop 0.178 vs early 0.238; late std still high (~0.66). Median≪mean (0.09 vs 0.29) → skew remains |
| Persistence | **Mixed** | Agent lag-1 autocorr ≈0.21; **group-mean** autocorr ≈0.03 (unstable aggregate path) |
| Shock recovery | **Partial** | Group mean regains pre-R5 in 1 round, pre-R10 in 2; but R5 SI zeros spike; patterns differ by group |
| Violation → repair | **Contrary** | After bad-rep/gossip, mean Δ prop **negative** (Prompt 4) |
| Gossip/reputation reinforce norms | **Weak** | Rare repair language; opportunistic tokens more common |
| Proposals formalise expectations | **Partial** | Subsidy/LDF equity drift; no contribution-threshold norm rule; punishment-weakening fails |
| Obligation language | **Weak** | Fairness/reciprocity ≈0 in concept rates; SI self-interest high |
| Cross-agent shared expectation | **Weak** | 5 near-zero specialists vs 13 high-mean agents; SFI median prop 0.034 |
| Prompt-induced talk | **Present** | Climate-role / cooperation boilerplate; democracy vote templates |

[Evidence: `tables/prompt7_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=stability_metrics]  
[Evidence: `quantitative_analysis/09_si_sfi_comparison.md` | run=20260731_013853 | round=n/a | agent=n/a | record=median_gap]  
[Evidence: `qualitative_analysis/11_reputation_and_gossip_events.md` | run=20260731_013853 | round=n/a | agent=n/a | record=negative_delta]

---

## Verdict — norm emergence

**Limited or mixed evidence of norm emergence.**

Positive average proportional contributions and some institutional formalisation (subsidy/LDF parameters) coexist with polarisation, weak obligation language, non-repair after social sanctions, and prompt-shaped rhetoric. A shared, internalised contribution norm is **not** persuasively established for this single run.

**Confidence:** moderate in the negative-on-strong-norm conclusion; low on fine-grained motive claims.

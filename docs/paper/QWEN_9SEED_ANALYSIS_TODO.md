# Qwen2.5-14B Nine-Seed Analysis Checklist

**Scope:** `results/simulation_qwen2.5-14b_Full_scnldf_sh1_ldf1_seed{1..9}_26agents_30rounds_*.json` only.<br>
**Environment:** Conda environment `ml` (Python 3.11).<br>
**Primary deliverable:** `docs/paper/qwen2_5_14b_9seed_results_report.md` (written).
**Code:** `src/analysis/qwen_9seed/`. **Artifacts:** `analysis_outputs/qwen2_5_14b_9seed/`.

## Progress

- [x] Define model, run, and treatment scope.
- [x] Locate all candidate Qwen2.5-14B result files.
- [x] Verify the `ml` environment and core scientific Python stack.
- [x] Complete an independent raw-data integrity and provenance audit. (Structural and accounting checks pass: 270 rounds, 7,020 agent-round records, all identities reconcile; parser intervention is reported separately from the zero-valued `parsing_failures` field.)
- [x] Reconstruct the implemented simulation and its causal estimands from source code. (Round order, deterministic shock schedule, LDF cap, institution routing, public-good payoff.)
- [x] Build a documented raw-to-tidy extraction pipeline with validation checks. (`extract.py` plus 14 tidy tables.)
- [x] Produce run-, round-, agent-, and event-level analysis tables.
- [x] Analyze contributions and cooperation dynamics over time. (Participation rises 0.643 to 0.940; intensity falls 0.166 to 0.105.)
- [x] Quantify inequality, free-riding, burden sharing, and distribution. (Gini 0.665 to 0.373; group ratio 10.70 to 2.78, range 0.67 to 8.18.)
- [x] Analyze LDF funding, coverage, transfers, and the response to shocks. (Coverage 0.90 is the `LDF_MAX_COVERAGE` cap, not a behavioural estimate; total payouts are roughly 0.3% of deposits.)
- [x] Analyze democratic institution choice, enforcement, and sanctions. (54 sessions, all applied, mean plurality 0.952; stage-2 requested-vs-applied ratios reported.)
- [x] Analyze reputation, gossip, ToM, and language/reasoning mechanisms. (Event associations, belief vocabulary, plus new `reasoning_profile.csv` showing 8.45-word templated rationales.)
- [x] Estimate uncertainty using seed-level inference and appropriate multilevel methods. (Run-level bootstrap, 20,000 resamples, exact sign-flip tests, run-clustered aggregation.)
- [x] Test robustness to alternative specifications, windows, and outlier rules. (Four windows, leave-one-seed-out, denominator, parser-clean, and event-threshold checks.)
- [x] Audit missingness, parser failures, malformed records, and attrition. (No missing required keys, no negative values, and no attrition; zero-cap records are flagged as structurally ineligible, while parser auto-fit/fallback metadata is reported.)
- [x] Generate publication-oriented tables and figures with source-data provenance. (Eight figures, all from derived tables.)
- [x] Cross-check every reported number against the generated analysis artifacts. (Headline tokens, image links, and artifact paths pass `validate_report.py`; the machine-readable claim ledger is the numeric source.)
- [x] Write the detailed paper-oriented Markdown report in explanatory prose.
- [x] Perform a final reproducibility, citation-path, and claim-strength review.

## Required quality gates

- [x] No model other than Qwen2.5-14B is included in inferential statistics.
- [x] No run is silently duplicated or excluded; every exclusion is justified. (All nine runs retained; the cold-start round is excluded only from explicitly labelled windows.)
- [x] The simulation run is treated as the top-level sampling unit; agents/rounds are not misrepresented as independent replications.
- [x] Descriptive findings, exploratory findings, and causal claims are clearly distinguished. (No causal claims; report uses descriptive and associational language throughout.)
- [x] Seed-level effect estimates include uncertainty and sample-size disclosures.
- [x] Key game-theory statements are tied to measured outcomes rather than intuition alone. (Public-goods framing is tied to the measured marginal return of 1.6/group size and the logged payoff outcomes.)
- [x] Every major report table/figure points to a reproducible script and derived dataset.
- [x] Reproduction commands run successfully with the `ml` environment. (`run_all` completes end-to-end; the refreshed pipeline summary and report validation are saved.)
- [x] The final report emphasizes balanced, readable paragraphs rather than bullet-heavy prose.

## Open items for follow-up work

- [ ] Run the same protocol on additional model families to enable cross-model claims (out of scope here by design).
- [ ] Recover a control condition (shock-off or LDF-off) before making any causal claim.
- [ ] If deliberation traces are ever serialised, re-run the language section; the current rationales cannot support mechanism claims.

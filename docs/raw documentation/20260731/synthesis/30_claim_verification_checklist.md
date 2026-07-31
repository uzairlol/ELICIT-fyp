# 30 — Claim Verification Checklist (20260731)

Status key:

| Status | Meaning |
|--------|---------|
| **verified** | Directly supported by tables/code/official sources cited |
| **partially supported** | Directionally supported; material caveats remain |
| **interpretive** | Reasonable reading; not uniquely identified |
| **unsupported** | Contradicted or lacking evidence — must not be asserted |
| **unresolved** | Needs more data/runs/design changes |

Run lock: `20260731_013853` · Model: `llama3.1:8b` · Metric: `prop_of_wealth`.

---

## A. Dataset and architecture

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| A1 | Canonical file is To_Use `...20260731_013853.json`; SHA256 `14FDCECA…9757` | verified | `00_project_memory.md` |
| A2 | 26 agents, 30 rounds, seed 1, Full, scnldf, sh1, ldf1, llama3.1:8b | verified | filename + JSON |
| A3 | Developed→SI, developing→SFI forced every round | verified | `environment.py`; extraction |
| A4 | Shocks at rounds 5 (0.1) and 10 (0.2) | verified | results JSON |
| A5 | Democracy rounds 5,10,15,20,25,30 | verified | `constitutional_change` |
| A6 | Stage-1 LDF cap = max(0, int(wealth)) | verified | `agent.get_stage1_contribution_cap` |
| A7 | `contribution_capacity` is 1.0/0.10 index, not budget | verified | parameters + schema |
| A8 | Agents do not see numeric LDF pool | verified | doc 06 / prompts |
| A9 | LDF deposit amount = Stage-1 contribution | verified | `loss_damage_fund._contribution_amount` |
| A10 | Gossip bulletin stored in results JSON | unsupported | field absent; reconstructed only |
| A11 | Dashboard recomputes core formulas from first principles | unsupported | pass-through `app.js` |

---

## B. Contribution and shocks

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| B1 | Mean prop SI≈0.291, SFI≈0.296 | verified | `prompt3_numeric_summary.json` |
| B2 | SI vs SFI mean prop difference is a causal institution effect | unsupported | perfect collinearity with group |
| B3 | SFI more zero-heavy / lower median prop | verified | zeros 16% vs 6%; med 0.034 vs 0.194 |
| B4 | Absolute SI contributions ≫ SFI | verified | mean abs ~1.2e7 vs ~8.1e4 |
| B5 | Shocks cause permanent cooperation collapse | unsupported | regain pre-mean in 1–2 rounds |
| B6 | Shock effects are cleanly identified vs democracy | unresolved | calendar overlap R5/R10 |
| B7 | Overall mean prop≈0.293, median≈0.092 | verified | `prompt7_numeric_summary.json` |

---

## C. Reputation, gossip, strategies

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| C1 | After bad-rep/gossip, mean Δ prop is negative on average | verified | `prompt4_numeric_summary.json` |
| C2 | Agents systematically repair reputation by raising contributions | unsupported | contrary average deltas |
| C3 | Gossip reconstruction equals exact in-run bulletin order | partially supported | trigger/top-5 OK; ties approximate |
| C4 | Near-zero vs high contributor clusters exist | verified | 5 vs 13 agents at disclosed thresholds |
| C5 | Individual motives are identified (altruism, spite, etc.) | interpretive / unresolved | motifs + actions only |

---

## D. Democracy and enforcement

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| D1 | 14 proposals, 6 adopted across 6 sessions | verified | `prompt5_numeric_summary.json` |
| D2 | Adopted path emphasises subsidy and LDF equity/damage weights | verified | adopted_by_category |
| D3 | Punishment-weakening proposals failed | verified | rounds 20, 25; adopted=0 |
| D4 | Only SI agents may propose/vote | unsupported | code allows all; docstring historically wrong |
| D5 | Enforcement is a costly second-order public good (Stage-2) | verified | costs in SI; doc 17 |
| D6 | High contributors solely fund enforcement | unsupported | top-quartile share ~0.35; corr~0.14 |
| D7 | Post-adoption prop increases are caused by the adopted rule | interpretive | confounded; small deltas |

---

## E. Language and norms

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| E1 | SI language enriched for strategy/self-interest vs SFI incentives/immediate/long-run | verified | Prompt 6 keyness |
| E2 | Fairness/reciprocity dominate shared-kind reasoning | unsupported | concept rates ≈0 |
| E3 | Strong contribution norm emerged | unsupported | Prompt 7 limited/mixed verdict |
| E4 | Limited/mixed norm emergence | verified | doc 21 + matrix |
| E5 | Moderately positive average cooperation with limited path stability | verified | doc 22; autocorr 0.03 |
| E6 | Positive mean cooperation implies internalised norm | unsupported | explicitly distinguished in Prompt 7 |
| E7 | Keyness is a one-agent artefact | unsupported | LOO Jaccard high |

---

## F. Theory and external LDF

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| F1 | FRLD funding arrangements/fund established at COP27 (2/CP.27) | verified | `28_external_sources.md` E1–E3 |
| F2 | Fund operationalised at COP28 with Governing Instrument + Board (1/CP.28) | verified | E3–E5 |
| F3 | World Bank invited as interim FIF host (~4 years, conditional) | verified | E4–E7 |
| F4 | Establishment = operationalisation = pledges = disbursement | unsupported | must keep stages distinct |
| F5 | Simulation proves real FRLD effectiveness | unsupported | stylised; no calibration |
| F6 | Simulation implements Ostrom’s full design principles | unsupported | doc 25 non-claim |
| F7 | Partial Ostrom analogues exist (repetition, sanctions, rule change) | partially supported | mapping table |
| F8 | llama3.1:8b choice is methodologically defensible for volume + traces | interpretive | doc 27 |
| F9 | Smaller models are automatically more realistic humans | unsupported | rejected in doc 27 |

---

## G. Unresolved questions (explicit)

1. Would endogenous SI/SFI choice change contribution and enforcement patterns?  
2. Would visible LDF pool balances induce fund-stock strategies?  
3. Do shock effects survive if democracy is desynchronised?  
4. Does native (non-reconstructed) gossip change event studies?  
5. Are findings robust across seeds and model families?  
6. Can separate LDF pledge actions (vs Stage-1 dual-use) alter politics?  
7. What voting rule / proposal density would produce stronger institutional lock-in?

---

## H. Final pack gate

| Check | Result |
|-------|--------|
| Numbers vs generated tables | Pass (spot-checked prompt3–7 JSON) |
| Quotations vs logs | Pass for cited Prompt 6 examples |
| SI/SFI labels | Pass (forced routing) |
| Exact run name / model | Pass |
| Proportional formula disclosure | Pass |
| Shock rounds | Pass |
| Proposal counts | Pass |
| Reputation/gossip definitions disclosed | Pass |
| COP27 vs later LDF timeline | Pass |
| Unsupported causal language removed | Pass (flagged unsupported above) |
| Hallucinated citations | Pass (external list only verified sources) |

**Pack status:** Prompts 0–9 complete; deepening pass added docs 31–37, semantic architecture 33, plot interpretations, dashboard dimensions, and RQ answer index.

---

## I. Deepening-pass claims

| # | Claim | Status | Anchor |
|---|-------|--------|--------|
| I1 | 91 voluntary-approx zeros; 0 liquidity-forced under end-wealth proxy | verified | prompt_zero_numeric_summary |
| I2 | SI R6 zero share 41.7% with MCPR payoff-max reasoning | verified | zero_si_r4_r7_window + quotes |
| I3 | SFI R1 zero share 71.4%; R2 prop spike 0.022→0.602 | verified | prompt_zero |
| I4 | ToM scores dominated by 5.0 and 1.0; 84% ≤7 | verified | prompt_dashboard_rq_summary |
| I5 | LDF shock coverage ≈0.768; final pool ≫ cumulative payouts | verified | ldf_coverage_by_round |
| I6 | Developed–developing wealth gap widens R1→R30 | verified | dashboard_macro_series |
| I7 | Conditional-coop corr weak on full path (SI~0.05, SFI~−0.09) | verified | conditional_coop in summary |
| I8 | Gossip threshold is informative rare filter | unsupported | 84% scores ≤7 |
| I9 | LDF closes wealth gap in this run | unsupported | gap widens |
| I10 | Semantic presence of LDF pool in decisions | unsupported | hidden + rare fund language |

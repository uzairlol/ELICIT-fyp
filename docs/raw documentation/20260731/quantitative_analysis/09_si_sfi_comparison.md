# 09 — SI versus SFI Contribution Comparison (20260731)

Compare proportional and absolute contributions between SI and SFI in the locked run.

**Critical design fact:** In LDF/climate mode, institution membership is **forced** by `agent_group` (developed→SI, developing→SFI). SI vs SFI is therefore **perfectly collinear** with developed vs developing. Differences cannot be identified as causal effects of the sanctioning institution alone.

[Evidence: `architecture/04_system_architecture.md` | run=n/a | round=n/a | agent=n/a | record=forced_institution]  
[Evidence: `tables/data_quality_summary.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=agent_type_institution_mismatches=0]

**Metric:** `prop_of_wealth` (primary); absolute contribution secondary.  
**Script:** `scripts/analyze_20260731_contributions.py`  
**Summary JSON:** `tables/si_sfi_comparison_summary.json`

---

## Sample sizes

| Group | Agents | Agent-rounds |
|-------|--------|--------------|
| SI (developed) | 12 | 360 |
| SFI (developing) | 14 | 420 |

---

## Multiple averages (proportional)

### Agent-round weighted mean of `prop_of_wealth`

| Group | Mean | Median | Std | 95% bootstrap CI | Zero-share |
|-------|------|--------|-----|------------------|------------|
| SI | **0.291** | 0.194 | 0.446 | [0.246, 0.339] | 0.064 |
| SFI | **0.296** | 0.034 | 0.800 | [0.224, 0.378] | 0.162 |

Difference (SI − SFI) ≈ **−0.005** (essentially null on the mean).  
Hedges’ *g* (SI − SFI, agent-round) ≈ **−0.008** (negligible).

Bootstrap: 2000 resamples, seed 20260731.

[Evidence: `tables/si_sfi_comparison_summary.json` | run=20260731_013853 | round=all | agent=all | record=SI_agent_round_mean_prop]

### Mean of individual-agent means

| Group | Mean of agent means | 95% CI | n agents |
|-------|---------------------|--------|----------|
| SI | 0.291 | [0.220, 0.366] | 12 |
| SFI | 0.296 | [0.180, 0.410] | 14 |

Hedges’ *g* on agent means ≈ **−0.026** (still negligible).

Because each agent has the same number of rounds (30), agent-round mean equals mean of agent means here.

---

## Absolute contributions (wealth-dominated)

| Group | Mean abs | Median abs |
|-------|----------|------------|
| SI | 1.20×10⁷ | 1.06×10⁷ |
| SFI | 8.14×10⁴ | 3.08×10⁴ |

**Finding:** Absolute SI contributions dwarf SFI amounts; proportional means do **not**. Any narrative that “SI contributes more” must specify the metric.

---

## What drives the apparent pattern?

| Candidate driver | Assessment in this run |
|------------------|------------------------|
| Extreme agents | Leave-one-out SI−SFI mean-prop diff ranges **[−0.028, +0.018]** vs full-sample **−0.005** — no single agent flips the qualitative near-zero mean gap (`tables/si_sfi_leave_one_out.csv`) |
| Starting positions | SFI R1 mean prop 0.022 vs SI 0.476 — large early gap that later compresses on the **mean** |
| Skew / outliers | SFI median (0.034) ≪ mean (0.296); SI median (0.194) closer to mean — SFI mean is outlier-sensitive |
| Climatic shocks | See `10_climatic_shock_event_study.md` — group responses differ by shock |
| Institutional sanctions | Confounded with developed status; **cannot** isolate |
| Fund stock | Not observed by agents |

**Do not claim:** “SI causes higher cooperation.”  
**Can claim:** On proportional wealth share, agent-round means are statistically similar; SFI distribution is more zero-heavy and right-skewed; absolute levels differ by wealth.

---

## Democracy-round proximity (descriptive)

Democracy sessions occur rounds 5,10,15,20,25,30 (also shock rounds 5 and 10).  
Table: `tables/si_sfi_prop_democracy_rounds.csv`.

Because democracy coincides with shocks at R5/R10, democracy-only effects are **not identified** here.

---

## Limitations

1. Single seed / single run — no cross-run inference.
2. End-of-round wealth denominator.
3. Perfect SI↔developed confounding.
4. Overlapping CIs and near-zero effect size on mean prop.
5. No causal contrast for institution rules.

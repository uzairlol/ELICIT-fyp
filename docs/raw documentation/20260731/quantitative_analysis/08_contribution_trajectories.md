# 08 — Contribution Trajectories (20260731)

Quantitative description of contribution levels over rounds. Primary proportional metric: analyst-derived `prop_of_wealth = contribution / wealth_end_of_round` (see `02_data_schema.md`). Absolute amounts are reported with wealth-confound caveats.

**Run:** `20260731_013853`  
**Sample:** 26 agents × 30 rounds = 780 agent-rounds  
**Method:** descriptive time series from `tables/contributions.csv`  
**Script:** `scripts/analyze_20260731_contributions.py`

[Evidence: `docs/raw documentation/20260731/tables/contribution_round_summary.csv` | run=20260731_013853 | round=1-30 | agent=all | record=round_summary]

---

## Definitions used here

| Term | Definition in this run |
|------|------------------------|
| SI | Sanctioning Institution; here = all `developed` agents (forced routing) |
| SFI | Sanction-Free Institution; here = all `developing` agents |
| Proportional contribution | `prop_of_wealth` (not stored by sim; end-of-round wealth denominator) |

Fund-information constraint: agents do **not** see numeric LDF pool balance; trajectories must not be read as optimisation against fund stock.  
[Evidence: `architecture/06_agent_information_boundaries.md` | run=n/a | round=n/a | agent=n/a | record=fund_visibility]

---

## All-agent trajectories

| Round window | Mean prop | Zero-share | Notes |
|--------------|-----------|------------|-------|
| R1 | 0.231 | 0.538 | High initial zeroing |
| R2 | 0.445 | 0.154 | Spike then settle |
| R3–4 | ~0.21–0.27 | 0.12–0.31 | Pre-shock 1 |
| R5 (shock 0.1) | 0.338 | 0.231 | During first shock |
| R6 | 0.277 | 0.308 | Immediate post |
| R10 (shock 0.2) | 0.396 | 0.038 | During second shock |
| R11–13 | ~0.31–0.34 | ~0 | Post second shock |

**Finding (level):** Group mean proportional contribution typically sits in a rough ~0.25–0.40 band after early rounds, with large cross-sectional dispersion (std often 0.4–0.9).  
**n:** 26 agents per round.  
**Limitation:** End-of-round wealth denominator can inflate/deflate prop when wealth jumps from payoffs/damage in the same round.  
**Evidence:** `tables/contribution_round_summary.csv` (`institution_choice=ALL`).

Plots:

- `plots/contrib_mean_prop_trajectories.png`
- `plots/contrib_smoothed_prop.png`
- `plots/contrib_dispersion_prop.png`
- `plots/contrib_zero_frequency.png`

---

## SI trajectories

- Mean prop starts high (R1 ≈ 0.476) then oscillates roughly 0.13–0.41.
- Zero-share usually low (overall SI zero-share 6.4% of agent-rounds) but spikes at R6 to **41.7%** after shock 5.
- Mean lag-1 autocorr of prop across SI agents ≈ **0.21** (moderate persistence, not lock-in).
- Mean change in |deviation from peer mean prop| ≈ **−0.020** → mild average movement **toward** SI peer mean.

[Evidence: `tables/contribution_agent_persistence.csv` | run=20260731_013853 | round=1-30 | agent=SI | record=autocorr_prop_lag1]

Plot: `plots/contrib_individual_prop_SI.png`

---

## SFI trajectories

- R1 mean prop very low (0.022) with zero-share **71.4%**; R2 jumps (mean prop 0.60) then volatile.
- Overall zero-share **16.2%** of agent-rounds (higher than SI).
- Median prop is much lower than mean (overall median ≈ 0.034 vs mean ≈ 0.296) → **right-skew / outlier-driven means**.
- Mean lag-1 autocorr ≈ **0.22** (similar to SI).
- Mean change in |peer deviation| ≈ **+0.022** → mild average movement **away** from SFI peer mean (polarisation signal, weak).

[Evidence: `tables/contribution_round_summary.csv` | run=20260731_013853 | round=1-30 | agent=SFI | record=median_vs_mean]

Plot: `plots/contrib_individual_prop_SFI.png`

---

## Absolute vs proportional

| Group | Mean absolute contribution | Median absolute | Mean prop_of_wealth |
|-------|----------------------------|-----------------|---------------------|
| SI | ≈ 1.20×10⁷ | ≈ 1.06×10⁷ | 0.291 |
| SFI | ≈ 8.14×10⁴ | ≈ 3.08×10⁴ | 0.296 |

Absolute SI contributions are ~**147×** larger on average — expected from wealth endowments, **not** evidence of higher proportional effort.  
Plot: `plots/contrib_mean_absolute_log.png`

---

## Persistence and convergence summary

| Metric | SI | SFI | Method |
|--------|----|-----|--------|
| Mean lag-1 autocorr (prop) | 0.212 | 0.217 | Per-agent corr; then mean |
| Mean Δ\|dev from peer prop\| | −0.020 | +0.022 | Negative ⇒ convergence |
| Overall zero-share | 0.064 | 0.162 | Agent-rounds |

**Limitation:** Autocorr undefined/unstable for near-constant series (numpy warnings); treat as descriptive.

---

## Fund-visibility interpretation note

Because agents lack the numeric pool stock, rising or falling contributions around shocks should be attributed to observed damages/payouts, peer behaviour, reputation/gossip (next-round), and prompts — **not** to tracking `ldf_pool_end`.

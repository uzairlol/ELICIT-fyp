# Cross-Seed Comparison — seed1 (20260731) vs seed2 (20260804)

**Scope.** Both runs: Llama 3.1 8B, Full / scnldf / sh1 / ldf1, 26 agents, 30 rounds. Differ only by random seed (1 vs 2) and any parser/runtime drift between execution dates.

**Primary metric.** `prop_of_wealth`.

## Executive findings

1. **Levels:** Seed2 mean prop (0.365) exceeds seed1 (0.293). Round-path correlation across seeds is weak (Pearson r=0.194, p=0.305).
2. **SI≈SFI means** in both seeds; agent-mean Mann–Whitney SI vs SFI is non-significant in both. Agent-round tests can reject due to huge N / skew — interpret carefully.
3. **Reputation backfires is seed-sensitive for SI:** SFI gossip/bad-rep immediate Δprop stays negative in both seeds; SI gossip Δprop flips from negative (seed1) to positive (seed2).
4. **Democracy path diverges:** both expand subsidies / LDF equity themes; seed2 **adopts punishment weakening** (PUNISHMENT_EFFECT=2); seed1 rejected punishment weakening.
5. **Macro stocks:** Seed2 ends with larger wealth gap and larger LDF pool.
6. **Agent-id personas are not stable across seeds** (only 12/26 keep the same group label). Do not treat agent_id correlations as fixed-character consistency.

[Evidence: `tables/cross_seed_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=notes]

## Macro trajectories

| Statistic | Seed1 | Seed2 |
|-----------|------:|------:|
| Mean round prop (ALL) | 0.2933 | 0.3650 |
| Pearson r (round means) | 0.1937 (p=0.305) | — |
| Spearman r | 0.2169 (p=0.250) | — |
| RMSE (round means) | 0.1236 | — |

Plots: `plots/cross_seed/mean_prop_trajectories_by_institution.png`.

[Evidence: `tables/cross_seed_round_prop_correlation.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=ALL]

### Trend tests

Mann–Kendall on round-mean prop: neither seed shows a significant monotonic trend at p<0.05 (seed1 tau≈−0.03 p≈0.83; seed2 tau≈−0.21 p≈0.11). ADF skipped (statsmodels unavailable).

## Wealth & LDF

| Quantity | Seed1 | Seed2 |
|----------|------:|------:|
| Final developed−developing wealth gap | ~2.15e8 | ~5.83e8 |
| Final LDF pool end | ~4.34e9 | ~1.30e10 |

Plots: `plots/cross_seed/wealth_gap_developed_minus_developing.png`, `ldf_pool_end_by_round.png`.

## Micro: agent consistency

Pearson/Spearman correlations of per-`agent_id` mean prop across seeds are near zero (r≈0.08, p≈0.68). Because group labels reshuffle for 14/26 IDs, this is **not** a clean persona test.

[Evidence: `tables/cross_seed_agent_prop_correlation.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=agent_id]

## SI vs SFI tests

| Seed | Mean SI | Mean SFI | MW p (agent means) |
|------|--------:|--------:|-------------------:|
| 1 | 0.291 | 0.296 | 0.817 |
| 2 | 0.364 | 0.366 | 0.777 |

Institution means stay matched within seed; level shift is a **seed-level** cooperation increase, not SI−SFI divergence.

[Evidence: `tables/cross_seed_mannwhitney_si_sfi.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=tests]

## Shock event study

Within-agent post−pre Δprop Wilcoxon p-values are non-significant for R5/R10 in both seeds (see `cross_seed_shock_wilcoxon.csv`). Seed2 R5 mean delta is more negative (−0.08) than seed1 (+0.02), matching slower R5 recovery.

Plot: `plots/cross_seed/shock_delta_boxplot_cross_seed.png`.

## Reputation / gossip sensitivity

| Event | Seed1 SI Δ | Seed1 SFI Δ | Seed2 SI Δ | Seed2 SFI Δ |
|-------|-----------:|------------:|-----------:|------------:|
| bad_rep imm | −0.036 | −0.103 | +0.055 | −0.069 |
| gossip imm | −0.048 | −0.201 | +0.187 | −0.084 |
| rep_drop imm | −0.091 | −0.119 | +0.058 | −0.017 |

**Synthesis:** The developing/SFI “social pressure → lower prop” association replicates in sign. The developed/SI association does **not** replicate in sign. Papers claiming universal reputation backfire must qualify by institution/role or pool seeds carefully.

Plot: `plots/cross_seed/reputation_imm_delta_prop_by_family.png`.

[Evidence: `tables/cross_seed_reputation_imm_delta_prop.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=imm]

## Governance path dependence

| Seed | Adopted (n) | Notable |
|------|------------:|---------|
| 1 | 6 | Subsidy ↑, LDF equity ↑; punishment weakening **failed** |
| 2 | 6 | Subsidy ↑, LDF equity ↑; punishment effect **weakened to 2** |

Shared round-rule pairs across seeds: 1 (low literal overlap). Political economy is path-dependent under seed noise.

[Evidence: `tables/cross_seed_adopted_rules.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=adopted]

## Qualitative / cognitive

Both seeds show SI strategy/self-interest keyness vs SFI incentives/immediacy keyness. That dialect split is a **universal** pattern in this design; event-study signs for SI are the main stochastic divergence.

## Claim checklist

| Claim | Status |
|-------|--------|
| Seed2 higher mean cooperation than seed1 | Supported |
| SI≈SFI means in both seeds | Supported |
| SFI gossip/bad-rep → negative mean Δprop in both | Supported |
| SI gossip → negative mean Δprop in both | **Unsupported** (sign flip) |
| Identical democracy path | Unsupported |
| Agent_id personas stable across seeds | Unsupported |
| Causal SI vs SFI | Unsupported |

## ROI for the paper

- Keep **SFI/developing social-pressure association** as the robust core.
- Treat SI positive gossip response in seed2 as a boundary condition / heterogeneity result.
- Use seed2’s adopted punishment weakening as Paper-2 democracy material.

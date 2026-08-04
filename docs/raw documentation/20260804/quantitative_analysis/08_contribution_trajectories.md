# 08 — Contribution Trajectories (seed2 / 20260804)

**Opening claim.** Seed2 shows moderately higher average contribution intensity than seed1, with SI≈SFI means under forced routing and limited path autocorrelation.

## Design reminder

Developed→SI and developing→SFI are forced. Institution comparisons are descriptive of the joint assignment.

Agents do not observe the numeric LDF pool balance.

## Levels

| Statistic | Value |
|-----------|------:|
| Mean prop (all) | 0.3650 |
| Median prop | 0.2000 |
| SI mean prop | 0.3641 |
| SFI mean prop | 0.3658 |
| Hedges g (SI−SFI, agent-round) | -0.0030 |
| Zero share ALL | 0.1718 |

[Evidence: `tables/prompt3_numeric_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=si_sfi]

## Persistence

| Statistic | Value |
|-----------|------:|
| Group-mean lag-1 autocorr | 0.0943 |
| Agent-mean lag-1 autocorr | 0.0144 |
| Rounds with mean prop ≥0.2 | 30 / 30 |
| Rounds with mean prop ≥0.3 | 23 / 30 |

[Evidence: `tables/prompt7_numeric_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=autocorr]

## Shock recovery

| Shock | Pre-mean prop | Rounds to regain |
|-------|--------------:|-----------------:|
| R5 | 0.4709 | 6 |
| R10 | 0.3949 | 1 |

R5 recovery is slower than seed1’s typical 1-round regain; R10 recovers in 1 round.

[Evidence: `tables/prompt7_numeric_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=shock_recoveries]

## Plots

See `plots/contrib_mean_prop_trajectories.png`, `contrib_median_prop_iqr.png`, `contrib_zero_frequency.png`.

## Claim-safe verdict

Positive average transfers with weak autocorrelation. Not a settled contribution norm.

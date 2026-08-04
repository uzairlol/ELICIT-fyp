# 11 — Reputation and Gossip Events (seed2)

**Opening claim.** Negative social marks remain associated with declines for **SFI** agents; SI responses are mixed and include positive mean gossip deltas — a seed-sensitive contrast with seed1.

## Immediate horizon

| Event | Inst | n | Mean Δprop | Frac Δ>0 |
|-------|------|--:|----------:|---------:|
| bad_rep | SFI | 98 | -0.0689 | 0.388 |
| bad_rep | SI | 48 | 0.0549 | 0.354 |
| rep_drop | SFI | 100 | -0.0166 | 0.400 |
| rep_drop | SI | 59 | 0.0578 | 0.407 |
| gossip_target | SFI | 85 | -0.0841 | 0.353 |
| gossip_target | SI | 29 | 0.1870 | 0.483 |

[Evidence: `tables/prompt4_numeric_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=event_summary_head]

## Cross-seed note

In seed1, SI gossip imm mean Δprop was negative (~−0.05). In seed2, SI gossip imm mean Δprop is **positive** (~+0.19), while SFI remains negative (~−0.08). The “reputation backfires” pattern is **not seed-invariant for SI**; it is more stable for SFI / developing agents under forced routing.

## Motifs

See `tables/reputation_motif_counts.csv` and strategy profiles.

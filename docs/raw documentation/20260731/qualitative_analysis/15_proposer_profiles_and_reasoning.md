# 15 — Proposer Profiles and Reasoning (20260731)

Who proposes, with what history, and what their stated reasons say.

**Tables:** `proposals_coded.csv`, `votes_parsed.csv`  
[Evidence: `tables/proposals_coded.csv` | run=20260731_013853 | round=varies | agent=proposers | record=coded]

---

## Proposer roster

| Round | Proposer | Inst | mean prop | prop prev3 | mean rep | gossip hits | Rule → value | Adopted? |
|-------|----------|------|-----------|------------|----------|-------------|--------------|----------|
| 5 | 4 | SFI | 0.423 | (see table) | 4.70 | 7 | SUBSIDY_FRACTION 0.3 | yes |
| 5 | 23 | SI | 0.469 | | 5.00 | 2 | SUBSIDY_FRACTION 0.5 | no |
| 10 | 1 | SFI | 0.002 | | 4.77 | 2 | LDF_MAX_COVERAGE 0.95 | no |
| 10 | 22 | SI | 0.317 | | 5.08 | 1 | LDF_EQUITY_WEIGHT 0.5 | yes |
| 15 | 20 | SFI | 0.603 | | 5.46 | 0 | SUBSIDY_TOP_N 5 | no |
| 15 | 24 | SFI | 0.032 | | 4.29 | 5 | SUBSIDY_FRACTION 0.4 | yes |
| 20 | 25 | SI | 0.412 | | 4.91 | 2 | LDF_EQUITY_WEIGHT 0.7 | no |
| 20 | 14 | SI | 0.221 | | 4.36 | 8 | LDF_PAYOUT_DAMAGE_WEIGHT 1.5 | yes |
| 20 | 10 | SI | 0.203 | | 4.94 | 3 | PUNISHMENT_EFFECT 1 | no |
| 25 | 20 | SFI | 0.603 | | 5.46 | 0 | LDF_MAX_COVERAGE 0.95 | no |
| 25 | 22 | SI | 0.317 | | 5.08 | 1 | LDF_EQUITY_WEIGHT 0.7 | yes |
| 25 | 21 | SI | 0.425 | | 5.41 | 1 | PUNISHMENT_EFFECT 1 | no |
| 30 | 15 | SFI | 0.579 | | 4.55 | 6 | SUBSIDY_FRACTION 0.6 | yes |
| 30 | 3 | SI | 0.490 | | 4.67 | 7 | SUBSIDY_FRACTION 0.5 | no |

Mean proposer prop ≈ **0.364** vs all-agent mean ≈ **0.293** — proposers skew slightly higher-prop, but roster includes near-zero agent 1 and low-prop agent 24.

---

## Who tends to propose? (checklist)

| Hypothesis | Support in this run |
|------------|---------------------|
| High contributors | Mixed — several high-prop (15,20,23,3) but also low (1,24) |
| Low contributors | Present (1, 24) especially on LDF coverage / subsidy |
| Recently criticised (gossip) | Partial — 4,14,15,24 have many gossip hits |
| Weak reputation | Partial — several proposers have mean rep ≤5 |
| Facing losses / shocks | R5/R10 proposers coincide with shocks; not separable |
| SI agents | 8/14 proposals |
| SFI agents | 6/14 — **active despite no Stage-2** |
| Declining preferred outcomes | Not cleanly measured; LDF equity proposers include SI agents advocating for developing payouts |

**Do not reduce to “only high contributors propose.”**

---

## Stated proposal reasons (themes)

Recurring boilerplate (prompted community-welfare frame):

- “incentivize cooperation”
- “reduce free-riding”
- “promote trust / sustainability”
- Subsidy: “rewarding top contributors” / “reducing punishment costs”
- LDF equity: “prioritizing poorer developing nations”
- Punishment=1: “discourage excessive retaliation” / “punishment less costly” (**note:** lowering EFFECT reduces target impact, not necessarily sender cost)

[Evidence: `tables/proposals.csv` | run=20260731_013853 | round=20 | agent=10 | record=CC-R20-P2]

Many vote reasons are near-duplicates (“conservative adjustment…”) — likely template convergence of `llama3.1:8b`, not independent deliberation.

---

## Repeat proposers

- Agent **22** (SI): wins LDF equity at R10 and R25.
- Agent **20** (SFI): proposes twice (subsidy top-N; LDF coverage); neither wins.
- Subsidy contests often SI vs SFI alternative values in the same round.

---

## Limitations

- Only successful/parsed proposals observed.
- Prior 3-round prop in `proposals_coded.csv` for finer timing.
- Vote reasons highly non-unique → weak evidence of strategic voting sophistication.

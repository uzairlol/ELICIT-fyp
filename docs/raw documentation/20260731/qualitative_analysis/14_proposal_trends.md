# 14 — Proposal Trends (20260731)

Democracy proposal frequency, topics, and adoption over the locked run.

**Data:** 14 proposals across 6 constitutional rounds (5,10,15,20,25,30); 6 adopted.  
**Script:** `scripts/analyze_20260731_democracy.py`  
**Tables:** `proposals_coded.csv`, `adopted_rules.csv`, `prompt5_numeric_summary.json`

[Evidence: `tables/proposals.csv` | run=20260731_013853 | round=5-30 | agent=n/a | record=all_proposals]

---

## Coding scheme

| Category code | Rules included | Interpretation |
|---------------|----------------|----------------|
| `reward_subsidy` | `SUBSIDY_FRACTION`, `SUBSIDY_TOP_N` | Enlarge SI reward redistribution |
| `punishment_weakening` | `PUNISHMENT_EFFECT` with value &lt; default 3 | Soften sanctions |
| `ldf_redistribution` | `LDF_MAX_COVERAGE` | Broader LDF payout coverage |
| `ldf_equity` | `LDF_EQUITY_WEIGHT` | Tilt LDF toward poorer developing agents |
| `ldf_damage_weight` | `LDF_PAYOUT_DAMAGE_WEIGHT` | Weight payouts by damage |

Original proposal text retained in `reason` columns alongside codes.

---

## Frequency over time

| Round | N proposals | Shock? | Categories present |
|-------|------------:|--------|--------------------|
| 5 | 2 | yes | reward_subsidy ×2 |
| 10 | 2 | yes | ldf_redistribution, ldf_equity |
| 15 | 2 | no | reward_subsidy ×2 |
| 20 | 3 | no | ldf_equity, ldf_damage_weight, punishment_weakening |
| 25 | 3 | no | ldf_redistribution, ldf_equity, punishment_weakening |
| 30 | 2 | no | reward_subsidy ×2 |

Only **2–3 proposals per session** enter the vote (not one per agent). Many agents either fail validation or do not yield a recorded proposal — democracy is sparse relative to population (26).

Plot: `plots/proposal_categories_timeline.png`

---

## Topic trends

| Category | N proposals | N adopted |
|----------|------------:|----------:|
| reward_subsidy | 6 | 3 |
| ldf_equity | 3 | 2 |
| ldf_redistribution | 2 | 0 |
| punishment_weakening | 2 | 0 |
| ldf_damage_weight | 1 | 1 |

**Trend (descriptive):**
1. Early/late sessions favour **raising subsidy fraction** (0.3 → 0.4 → 0.6 adopted path).
2. Mid sessions emphasise **LDF equity / damage weighting**.
3. **Punishment-weakening** appears late (R20, R25) and is **never adopted**.
4. No proposals for transparency, reputation mechanism, contribution thresholds, or Stage-1 endowment in this run’s whitelist outcomes.

---

## Strictness / orientation

| Orientation | Evidence in this run |
|-------------|----------------------|
| Reward-oriented | Dominant (subsidy increases) |
| Punishment-oriented (stronger) | **Absent** — proposals move `PUNISHMENT_EFFECT` 3→1 (weaker) |
| Redistribution / equity | Strong LDF equity theme |
| Reaction after shocks | R5 subsidy; R10 LDF equity/coverage — plausible reaction, but also democracy schedule |

---

## Repeated / reformulated proposals

- `SUBSIDY_FRACTION` reappears R5, R15, R30 with rising proposed values (0.3/0.5 → 0.4 → 0.5/0.6).
- `LDF_EQUITY_WEIGHT` proposed R10 (0.5, **adopted**), R20 (0.7), R25 (0.7, **adopted**).
- `LDF_MAX_COVERAGE` 0.95 proposed R10 and R25 (neither adopted).
- `PUNISHMENT_EFFECT=1` proposed R20 and R25 (neither adopted).

---

## SI vs SFI proposal counts

| Institution | N proposals |
|-------------|------------:|
| SI | 8 |
| SFI | 6 |

Both groups propose; SFI agents successfully place LDF and subsidy proposals despite lacking Stage-2 tools themselves.

---

## Limitations

- Sparse proposal set (14) — topic shares are fragile.
- Whitelist constrains what can be proposed (not open-ended norms).
- Vote text is highly templated (see doc 15).
- Shock/democracy coincidence at R5/R10.

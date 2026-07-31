# 10 — Climatic Shock Event Study (20260731)

Event-study of contributions around verified shock rounds.

## Shock identification

From results + schedule config:

| Round | Severity | Gross damage (file) | Net damage (file) |
|-------|----------|---------------------|-------------------|
| 5 | 0.1 | 369000 | 85500 |
| 10 | 0.2 | 738000 | 171000 |

[Evidence: `tables/climatic_shocks.csv` | run=20260731_013853 | round=5,10 | agent=n/a | record=shock_occurred]  
[Evidence: `src/core/parameters.py` | run=n/a | round=n/a | agent=n/a | record=CLIMATE_SHOCK_SCHEDULE]

No other shocks in this 30-round file.

---

## Method

Windows (agent-rounds):

| Window | Relative rounds |
|--------|-----------------|
| `pre` | −3…−1 |
| `during` | 0 |
| `post_immediate` | +1 |
| `post_later` | +2…+3 |
| `post_wide` | +1…+4 |

Within-agent deltas: mean prop in {−2,−1} vs {+1,+2} (`tables/shock_agent_deltas.csv`).

Primary outcome: `prop_of_wealth`. Absolute contribution reported secondarily.

**Non-causal language:** shocks are scheduled; no control series without shocks in this run. Estimates are before/after associations.

Fund constraint: agents see own damage/payouts, not pool balance.

---

## Shock round 5 (severity 0.1)

### Window means — proportional (`tables/shock_event_study.csv`)

| Window | SI mean prop (n AR) | SFI mean prop (n AR) | ALL mean prop |
|--------|---------------------|----------------------|---------------|
| pre (2–4) | 0.335 (36) | 0.285 (42) | 0.308 |
| during (5) | 0.347 (12) | 0.331 (14) | 0.338 |
| post_immediate (6) | **0.127** (12) | 0.405 (14) | 0.277 |
| post_later (7–8) | 0.251 (24) | 0.310 (28) | 0.283 |
| post_wide (6–9) | 0.261 (48) | 0.312 (56) | 0.288 |

### Within-agent Δ (post − pre)

| Group | Mean Δ | Median Δ | Frac Δ>0 | n |
|-------|--------|----------|----------|---|
| SI | **−0.178** | −0.064 | 0.417 | 12 |
| SFI | **+0.195** | −0.008 | 0.286 | 14 |

### Notable behavioural signals (associational)

- **SI after R5:** sharp drop in mean prop at R6; zero-share jumps to **41.7%** (from `contribution_round_summary`). Suggests temporary pullback, not persistent increase.
- **SFI:** mean prop rises post-immediate, but median Δ is near zero and only 29% of agents increase — mean lift is **outlier-driven**, not broad.
- Dispersion (std prop) for SFI during/post remains very high (>1.0 in some windows).

**Finding (R5):** No clean evidence of persistent cooperative surge. SI shows temporary **decrease** post-shock; SFI mean increase is fragile to outliers.  
**Limitation:** R5 is also a democracy round — confound with constitutional session.

---

## Shock round 10 (severity 0.2)

### Window means — proportional

| Window | SI mean prop | SFI mean prop | ALL |
|--------|--------------|---------------|-----|
| pre (7–9) | 0.305 | 0.281 | 0.292 |
| during (10) | **0.385** | **0.406** | **0.396** |
| post_immediate (11) | 0.347 | 0.281 | 0.312 |
| post_later (12–13) | **0.385** | 0.270 | 0.323 |
| post_wide (11–14) | 0.359 | 0.281 | 0.317 |

### Within-agent Δ (post − pre)

| Group | Mean Δ | Median Δ | Frac Δ>0 | n |
|-------|--------|----------|----------|---|
| SI | **+0.049** | +0.117 | **0.667** | 12 |
| SFI | −0.022 | −0.001 | 0.429 | 14 |

### Notable behavioural signals

- Both groups elevate **during** R10 on mean prop; zero-share falls (ALL zeros only 3.8% during).
- **SI:** post means stay elevated vs pre; majority of SI agents (8/12) raise post vs pre prop — closest pattern to a temporary/partial increase with some persistence in this sample.
- **SFI:** during spike, then post mean returns near pre; median within-agent Δ ≈ 0.

**Finding (R10):** Stronger during-shock elevation than R5; SI shows more post-support than SFI. Still **not** identifiable as “shock causes cooperation” (democracy confound; single run; no counterfactual).

---

## Checklist against Prompt 3 questions

| Hypothesis | Support in this run |
|------------|---------------------|
| Temporary contribution increase | Partial — clearer at R10 during; R5 SI falls after |
| Persistent increase | Weak/mixed — SI post-R10 elevated; not for SFI; R5 opposite for SI |
| Contribution decrease | Yes for SI immediately after R5 |
| Greater variance | Yes around shocks (esp. SFI std) |
| Stronger conditional cooperation | Not tested directly here (needs peer-response design) |
| Free-riding | Higher SFI zero-share overall; R6 SI zero spike |
| Convergence | Mild SI toward peer mean overall; not shock-specific |
| Polarisation | Mild SFI away-from-peer overall; shock windows noisy |

---

## Plots

- `plots/shock_delta_boxplot.png` — within-agent post−pre by institution
- Vertical dashed lines on trajectory plots mark R5 and R10

---

## Limitations

1. Only two shock events; R5/R10 coincide with democracy.
2. No no-shock control path in this file.
3. `prop_of_wealth` uses end-of-round wealth (damage/payout same round).
4. Single seed.
5. Agents lack pool-balance information — do not narrate fund-stock targeting.

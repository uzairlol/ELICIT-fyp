# 00 — Project Memory (20260804)

Persistent memory for the seed2 Full LDF analysis pack. Companion to `docs/raw documentation/20260731/` (seed1).

## Confirmed analysis run

| Field | Value |
|-------|-------|
| Exact results file | `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json` |
| Exact run name | `simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555` |
| Run timestamp | `20260804_024555` |
| Model | `llama3.1:8b` (local Ollama) |
| Agents / rounds | 26 / 30 |
| Seed | **2** |
| Scenario / flags | Full / scnldf / sh1 / ldf1 |
| Groups at R1 | developed 12 → SI; developing 14 → SFI (forced) |
| SHA256 | `9CE44CE613698436DE86940E8042D0A9EF6BA4030B13E67C02544F9EA00C5A6E` |
| File size | 4,810,512 bytes |
| Shock rounds | R5 sev 0.1; R10 sev 0.2 |
| Democracy rounds | 5, 10, 15, 20, 25, 30 |

Baseline reference: seed1 pack under `docs/raw documentation/20260731/` (`SHA256` of seed1 JSON documented there).

## Locked claim rules

1. Do **not** treat SI vs SFI mean gaps as causal institution effects (forced routing ⇒ group collinearity).
2. Do **not** claim real-world FRLD effectiveness from this simulation.
3. Separate cooperation *levels* from *norm emergence*.
4. Gossip in exports is reconstructed from ToM scores when bulletins are absent.
5. Agent IDs are **not** persona-matched across seeds (only 12/26 keep the same developed/developing label); cross-seed agent_id correlations are descriptive only.
6. Every numeric claim cites a table/JSON evidence pointer.

## Primary metric

`prop_of_wealth = contribution / wealth_end_of_round` (analyst-derived).

## Headline seed2 numbers (locked)

| Quantity | Value | Source |
|----------|------:|--------|
| Mean prop (all) | 0.3650 | prompt7 |
| Median prop | 0.2000 | prompt7 |
| SI / SFI mean prop | 0.3641 / 0.3658 | prompt3 |
| Zero share ALL | 0.1718 | prompt_zero |
| SFI gossip imm mean Δprop | −0.084 | prompt4 |
| SI gossip imm mean Δprop | +0.187 | prompt4 |
| Adopted rules | 6 (incl. PUNISHMENT_EFFECT→2) | prompt5 |

## Structure lock

This folder mirrors `20260731/`: architecture, evidence, qualitative_analysis, quantitative_analysis, synthesis, tables, theory, paper_story, plots, scripts, plus `cross_seed_comparison.md`.

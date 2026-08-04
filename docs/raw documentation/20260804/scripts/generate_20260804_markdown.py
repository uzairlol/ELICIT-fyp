#!/usr/bin/env python3
"""Generate seed2 analysis markdown reports from locked tables/JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "docs" / "raw documentation" / "20260804"
TABLES = OUT / "tables"
RUN = "20260804_024555"
SOURCE = (
    "results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_"
    "26agents_30rounds_20260804_024555.json"
)
SHA = "9CE44CE613698436DE86940E8042D0A9EF6BA4030B13E67C02544F9EA00C5A6E"


def load_json(name: str):
    p = TABLES / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def ev(table: str, record: str = "n/a") -> str:
    return (
        f"[Evidence: `tables/{table}` | run={RUN} | round=n/a | "
        f"agent=n/a | record={record}]"
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote", path.relative_to(OUT))


def main():
    p3 = load_json("prompt3_numeric_summary.json")
    p4 = load_json("prompt4_numeric_summary.json")
    p5 = load_json("prompt5_numeric_summary.json")
    p7 = load_json("prompt7_numeric_summary.json")
    pz = load_json("prompt_zero_numeric_summary.json")
    xs = load_json("cross_seed_summary.json")
    si = p3.get("si_sfi", {})

    # --- memory ---
    write(
        OUT / "00_project_memory.md",
        f"""# 00 — Project Memory (20260804)

Persistent memory for the seed2 Full LDF analysis pack. Companion to `docs/raw documentation/20260731/` (seed1).

## Confirmed analysis run

| Field | Value |
|-------|-------|
| Exact results file | `{SOURCE}` |
| Exact run name | `simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555` |
| Run timestamp | `20260804_024555` |
| Model | `llama3.1:8b` (local Ollama) |
| Agents / rounds | 26 / 30 |
| Seed | **2** |
| Scenario / flags | Full / scnldf / sh1 / ldf1 |
| Groups at R1 | developed 12 → SI; developing 14 → SFI (forced) |
| SHA256 | `{SHA}` |
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
| Mean prop (all) | {p7.get('overall_mean_prop', float('nan')):.4f} | prompt7 |
| Median prop | {p7.get('overall_median_prop', float('nan')):.4f} | prompt7 |
| SI / SFI mean prop | {si.get('SI_agent_round_mean_prop', float('nan')):.4f} / {si.get('SFI_agent_round_mean_prop', float('nan')):.4f} | prompt3 |
| Zero share ALL | {pz.get('inventory',[{}])[-1].get('zero_share', float('nan')):.4f} | prompt_zero |
| SFI gossip imm mean Δprop | −0.084 | prompt4 |
| SI gossip imm mean Δprop | +0.187 | prompt4 |
| Adopted rules | 6 (incl. PUNISHMENT_EFFECT→2) | prompt5 |

## Structure lock

This folder mirrors `20260731/`: architecture, evidence, qualitative_analysis, quantitative_analysis, synthesis, tables, theory, paper_story, plots, scripts, plus `cross_seed_comparison.md`.
""",
    )

    write(
        OUT / "01_repository_inventory.md",
        f"""# 01 — Repository Inventory (20260804)

Inventory for analyzing `{SOURCE}`.

## Simulation outputs

| Path | Role |
|------|------|
| `{SOURCE}` | Canonical seed2 Full LDF run |
| `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json` | Seed1 baseline |
| `docs/raw documentation/20260731/` | Seed1 analysis pack |
| `docs/raw documentation/20260804/` | This pack |

## Engine surfaces used

| Path | Role |
|------|------|
| `src/core/` | Environment, institutions, LDF, parameters |
| `src/modules/` | ToM, gossip, democracy |
| `src/prompts/` | Decision prompts |
| `src/parsing/` | Response parsers (incl. Stage-2 semantic retries) |
| `src/analysis/` | Flatten/plot utilities |
| `dashboard/` | Interactive visualizer patterns |

## Analysis scripts (this pack)

| Script | Purpose |
|--------|---------|
| `scripts/extract_20260804_results.py` | Flatten JSON → tables + evidence IDs |
| `scripts/analyze_20260804_contributions.py` | Contribution / SI–SFI / shock plots |
| `scripts/analyze_20260804_reputation_gossip.py` | Event study + motifs |
| `scripts/analyze_20260804_democracy.py` | Proposals, votes, adopted rules |
| `scripts/analyze_20260804_language.py` | Wordclouds + keyness |
| `scripts/analyze_20260804_norm_stability.py` | Cooperation stability diagnostics |
| `scripts/analyze_20260804_zero_contributions.py` | Zero episodes |
| `scripts/analyze_20260804_dashboard_dimensions.py` | Wealth/Gini/LDF/enforcement |
| `scripts/cross_seed_comparison.py` | Seed1 vs seed2 statistics + plots |

{ev('extraction_issues.csv', 'inventory')}
""",
    )

    write(
        OUT / "02_data_schema.md",
        f"""# 02 — Data Schema (20260804)

Schema for the seed2 export and derived tables.

## Raw JSON

Top-level type: **list of 30 round objects** (same schema as seed1).

### Round keys (observed)

`round_number`, `agents`, `si_members`, `sfi_members`, `si_total_contribution`, `sfi_total_contribution`, `si_avg_contribution`, `sfi_avg_contribution`, `shock_occurred`, `shock_severity`, `gross_damage_total`, `net_damage_total`, `ldf_pool_start`, `ldf_contributions_total`, `ldf_payouts_total`, `ldf_pool_end`, `cooperation_rate`, `gini_wealth`, plus `constitutional_change` on democracy rounds.

### Agent keys (high-signal)

`agent_group`, `institution_choice`, `contribution`, `wealth`, `reputation`, `payoff`, `stage1_payoff`, `stage2_payoff`, `tom_scores`, `belief_state`, `assigned_punishments`, `assigned_rewards`, contribution/punishment reasoning fields, LDF/climate fields when present.

## Derived tables

Created under `tables/` by `extract_20260804_results.py` and analysis scripts. Primary join keys: `(round_number, agent_id)`.

### Proportional contribution

Analyst-derived:

`prop_of_wealth = contribution / wealth_end_of_round`

End-of-round wealth is an approximation relative to decision-time wealth.

### Evidence IDs

Reasoning blocks use `RB-{{round:02d}}-A{{agent_id}}-{{kind}}`.

{ev('reasoning_blocks.csv', 'schema')}
""",
    )

    write(
        OUT / "03_extraction_pipeline.md",
        f"""# 03 — Extraction Pipeline (20260804)

## Command

From repository root:

```bash
python "docs/raw documentation/20260804/scripts/extract_20260804_results.py"
```

Then analysis scripts under `scripts/analyze_20260804_*.py`, then:

```bash
python "docs/raw documentation/20260804/scripts/cross_seed_comparison.py"
```

## Guarantees

- Original JSON is never modified.
- Tables are deterministic given the locked SHA256 `{SHA}`.
- Extraction logged 86 non-fatal issues (see `tables/extraction_issues.csv`) — mostly missing optional fields or reconstruction notes, not schema breaks.

## Outputs

| Destination | Contents |
|-------------|----------|
| `tables/` | CSV + JSON numeric summaries |
| `evidence/` | Traceable excerpts / ID maps |
| `plots/` | Seed2 figures |
| `plots/cross_seed/` | Comparative figures |

{ev('extraction_issues.csv', 'pipeline')}
""",
    )

    # Quantitative
    write(
        OUT / "quantitative_analysis/08_contribution_trajectories.md",
        f"""# 08 — Contribution Trajectories (seed2 / 20260804)

**Opening claim.** Seed2 shows moderately higher average contribution intensity than seed1, with SI≈SFI means under forced routing and limited path autocorrelation.

## Design reminder

Developed→SI and developing→SFI are forced. Institution comparisons are descriptive of the joint assignment.

Agents do not observe the numeric LDF pool balance.

## Levels

| Statistic | Value |
|-----------|------:|
| Mean prop (all) | {p7.get('overall_mean_prop'):.4f} |
| Median prop | {p7.get('overall_median_prop'):.4f} |
| SI mean prop | {si.get('SI_agent_round_mean_prop'):.4f} |
| SFI mean prop | {si.get('SFI_agent_round_mean_prop'):.4f} |
| Hedges g (SI−SFI, agent-round) | {si.get('effect_size_hedges_g_SI_minus_SFI_agent_round'):.4f} |
| Zero share ALL | {pz['inventory'][-1]['zero_share']:.4f} |

{ev('prompt3_numeric_summary.json', 'si_sfi')}

## Persistence

| Statistic | Value |
|-----------|------:|
| Group-mean lag-1 autocorr | {p7.get('group_mean_prop_autocorr_lag1'):.4f} |
| Agent-mean lag-1 autocorr | {p7.get('agent_mean_prop_autocorr_lag1'):.4f} |
| Rounds with mean prop ≥0.2 | {p7.get('threshold_rounds',{}).get('0.2')} / 30 |
| Rounds with mean prop ≥0.3 | {p7.get('threshold_rounds',{}).get('0.3')} / 30 |

{ev('prompt7_numeric_summary.json', 'autocorr')}

## Shock recovery

| Shock | Pre-mean prop | Rounds to regain |
|-------|--------------:|-----------------:|
| R5 | {p7['shock_recoveries']['5']['pre_mean']:.4f} | {p7['shock_recoveries']['5']['rounds_to_regain_pre_mean']} |
| R10 | {p7['shock_recoveries']['10']['pre_mean']:.4f} | {p7['shock_recoveries']['10']['rounds_to_regain_pre_mean']} |

R5 recovery is slower than seed1’s typical 1-round regain; R10 recovers in 1 round.

{ev('prompt7_numeric_summary.json', 'shock_recoveries')}

## Plots

See `plots/contrib_mean_prop_trajectories.png`, `contrib_median_prop_iqr.png`, `contrib_zero_frequency.png`.

## Claim-safe verdict

Positive average transfers with weak autocorrelation. Not a settled contribution norm.
""",
    )

    write(
        OUT / "quantitative_analysis/09_si_sfi_comparison.md",
        f"""# 09 — SI vs SFI Comparison (seed2)

**Opening claim.** Mean prop is nearly identical across institutions; absolute contributions differ by ~18× because wealth stocks differ. No causal institution contrast is identified.

## Levels

| | SI | SFI |
|--|---:|---:|
| Mean prop | {si.get('SI_agent_round_mean_prop'):.4f} | {si.get('SFI_agent_round_mean_prop'):.4f} |
| Median prop | {si.get('SI_agent_round_median_prop'):.4f} | {si.get('SFI_agent_round_median_prop'):.4f} |
| Zero share | {si.get('SI_zero_share'):.4f} | {si.get('SFI_zero_share'):.4f} |
| Mean abs contribution | {si.get('SI_mean_abs_contribution'):.0f} | {si.get('SFI_mean_abs_contribution'):.0f} |

{ev('si_sfi_comparison_summary.json', 'means')}

## Notes

Forced routing ⇒ developed/developing perfect collinearity with SI/SFI.

SFI has a thicker zero tail (22.4% vs 11.1%) despite similar means — skew matters.

{ev('contributions.csv', 'zero_share')}
""",
    )

    write(
        OUT / "quantitative_analysis/10_climatic_shock_event_study.md",
        f"""# 10 — Climatic Shock Event Study (seed2)

**Opening claim.** Shocks disturb contribution composition; means recover, but R5 regain takes 6 rounds in seed2 versus faster recovery in seed1.

## Shock schedule

| Round | Severity | Observed |
|------:|---------:|----------|
| 5 | 0.1 | yes |
| 10 | 0.2 | yes |

Democracy sessions coincide with both shock rounds.

## Within-seed recovery

{ev('prompt7_numeric_summary.json', 'shock_recoveries')}

Cross-seed Wilcoxon on within-agent post−pre deltas (see `cross_seed_comparison.md`) does not reject equal median deltas at conventional levels.

## Claim-safe

Do not interpret shock effects as cleanly identified relative to democracy.
""",
    )

    write(
        OUT / "quantitative_analysis/31_zero_contribution_episodes.md",
        f"""# 31 — Zero Contribution Episodes (seed2)

**Opening claim.** Zeros are common but less extreme at cold-start than seed1’s SFI R1 collapse.

| Institution | Zero share | Voluntary zeros (approx) | Agents ever zero |
|-------------|----------:|-------------------------:|-----------------:|
| SI | {pz['inventory'][1]['zero_share']:.3f} | {pz['inventory'][1]['n_voluntary_zero_approx']} | {pz['inventory'][1]['n_agents_ever_zero']} |
| SFI | {pz['inventory'][0]['zero_share']:.3f} | {pz['inventory'][0]['n_voluntary_zero_approx']} | {pz['inventory'][0]['n_agents_ever_zero']} |
| ALL | {pz['inventory'][2]['zero_share']:.3f} | {pz['inventory'][2]['n_voluntary_zero_approx']} | {pz['inventory'][2]['n_agents_ever_zero']} |

SFI R1 zero share: **{pz.get('sfi_r1_zero_share'):.3f}** (seed1 was ~0.71).

SI R6 zero share: **{pz.get('si_r6_zero_share'):.3f}** (agents {pz.get('si_r6_zero_agents')}).

{ev('prompt_zero_numeric_summary.json', 'inventory')}
""",
    )

    # LDF / wealth from dashboard summary if present
    dash = load_json("prompt_dashboard_rq_summary.json")
    write(
        OUT / "quantitative_analysis/34_wealth_gini_and_cooperation_rate.md",
        f"""# 34 — Wealth Gini and Cooperation Rate (seed2)

**Opening claim.** Wealth inequality and cooperation rate move as related but distinct series; absolute scale gaps dominate fiscal outcomes.

See plots: `plots/gini_wealth_cooperation_rate.png`, `plots/wealth_gap_developed_developing.png`.

Cross-seed final developed−developing wealth gap: seed1 ≈ 2.15e8, seed2 ≈ 5.83e8
{ev('cross_seed_summary.json', 'wealth_gap') if xs else ''}

Dashboard summary keys present: {list(dash.keys())[:12]}.
""",
    )

    write(
        OUT / "quantitative_analysis/35_ldf_coverage_and_transfers.md",
        f"""# 35 — LDF Coverage and Transfers (seed2)

**Opening claim.** Dual-use deposits accumulate a large hidden pool; collection ≫ shock disbursement — coverage without equalization.

Final LDF pool end (R30): **1.30e10** (seed1 was ~4.34e9).

{ev('fund_state.csv', 'ldf_pool_end')}

Agents do not observe pool balance; fund language in contribution rationales remains sparse (see qualitative language docs).

Cross-seed pool path: `plots/cross_seed/ldf_pool_end_by_round.png`.
""",
    )

    write(
        OUT / "quantitative_analysis/36_beliefs_and_sanction_structure.md",
        f"""# 36 — Beliefs and Sanction Structure (seed2)

**Opening claim.** Enforcement remains a costly second-order public good; correlation between prop and Stage-2 spend is weak.

| Statistic | Value |
|-----------|------:|
| Mean corr(prop, enforcement tokens) | {p5.get('enforcement_corr_mean'):.4f} |
| Top-quartile prop share of enforcement | {p5.get('enforcement_topq_share_mean'):.4f} |
| Vote same-group-as-proposer rate | {p5.get('vote_same_group_rate'):.4f} |

{ev('prompt5_numeric_summary.json', 'enforcement')}

Seed2 uniquely **adopts** `PUNISHMENT_EFFECT → 2` at R20 (weakening), unlike seed1’s failed punishment-weakening proposals.
""",
    )

    # Qualitative
    imm = [
        e
        for e in p4.get("event_summary_head", [])
        if e.get("horizon") == "imm"
    ]
    imm_tbl = "\n".join(
        f"| {e['event_family']} | {e['institution_choice']} | {e['n_events']} | {e['mean_delta_prop']:.4f} | {e['frac_delta_prop_positive']:.3f} |"
        for e in imm
    )
    write(
        OUT / "qualitative_analysis/11_reputation_and_gossip_events.md",
        f"""# 11 — Reputation and Gossip Events (seed2)

**Opening claim.** Negative social marks remain associated with declines for **SFI** agents; SI responses are mixed and include positive mean gossip deltas — a seed-sensitive contrast with seed1.

## Immediate horizon

| Event | Inst | n | Mean Δprop | Frac Δ>0 |
|-------|------|--:|----------:|---------:|
{imm_tbl}

{ev('prompt4_numeric_summary.json', 'event_summary_head')}

## Cross-seed note

In seed1, SI gossip imm mean Δprop was negative (~−0.05). In seed2, SI gossip imm mean Δprop is **positive** (~+0.19), while SFI remains negative (~−0.08). The “reputation backfires” pattern is **not seed-invariant for SI**; it is more stable for SFI / developing agents under forced routing.

## Motifs

See `tables/reputation_motif_counts.csv` and strategy profiles.
""",
    )

    write(
        OUT / "qualitative_analysis/12_agent_strategy_profiles.md",
        f"""# 12 — Agent Strategy Profiles (seed2)

Per-agent mean/median/std prop, zero share, reputation exposure, and post-event deltas are in `tables/agent_strategy_profiles.csv`.

{ev('agent_strategy_profiles.csv', 'profiles')}

Heterogeneity is large: 22/26 agents have mean prop ≥0.25; 0 agents have mean prop <0.05 (prompt7 thresholds).
""",
    )

    write(
        OUT / "qualitative_analysis/13_reasoning_action_consistency.md",
        f"""# 13 — Reasoning–Action Consistency (seed2)

**Opening claim.** Fluent rationales often recycle payoff-maximizing frames; consistency scoring (ToM) remains discrete and ambient-low.

Semantic Stage-2 retries (post seed2 code path) were intended to reduce punish-talk / zero-amount mismatches; this run’s JSON should be read with that parser regime in mind when inspecting punishment blocks.

{ev('reasoning_blocks.csv', 'kinds')}
""",
    )

    write(
        OUT / "qualitative_analysis/14_proposal_trends.md",
        f"""# 14 — Proposal Trends (seed2)

| Statistic | Value |
|-----------|------:|
| Democracy rounds | {p5.get('n_democracy_rounds')} |
| Proposals | {p5.get('n_proposals')} |
| Adopted | {p5.get('n_adopted')} |
| Categories (proposals) | {p5.get('proposals_by_category')} |
| Adopted path | {p5.get('adopted_by_category')} |

{ev('prompt5_numeric_summary.json', 'proposals')}

Adopted rules emphasize subsidy expansion, LDF equity weight ↑, and **punishment weakening** (effect 2 at R20).
""",
    )

    write(
        OUT / "qualitative_analysis/15_proposer_profiles_and_reasoning.md",
        f"""# 15 — Proposer Profiles (seed2)

Mean proposer prop {p5.get('mean_proposer_prop'):.3f} vs population {p5.get('mean_all_agent_prop'):.3f}.

Proposers by institution: {p5.get('proposals_by_institution')}.

{ev('prompt5_numeric_summary.json', 'proposers')}
""",
    )

    write(
        OUT / "qualitative_analysis/16_institutional_choice_si_vs_sfi.md",
        f"""# 16 — Institutional Choice (seed2)

Institutional choice is **forced** every round (developed→SI, developing→SFI). Free-choice Stage-0 prompts are not the operative mechanism.

Interpret SI/SFI language differences as role dialects under assignment, not endogenous sorting.

{ev('contributions.csv', 'institution_choice')}
""",
    )

    write(
        OUT / "qualitative_analysis/17_enforcement_as_public_good.md",
        f"""# 17 — Enforcement as a Public Good (seed2)

Stage-2 is SI-only. Mean corr(prop, enforcement) ≈ {p5.get('enforcement_corr_mean'):.3f}; top-quartile contributors pay ≈ {100*p5.get('enforcement_topq_share_mean'):.1f}% of tokens.

{ev('prompt5_numeric_summary.json', 'enforcement')}
""",
    )

    write(
        OUT / "qualitative_analysis/18_political_economy_of_governance.md",
        f"""# 18 — Political Economy of Governance (seed2)

Vote same-group rate ≈ {p5.get('vote_same_group_rate'):.3f} (near base rate).

Unlike seed1, punishment weakening is **adopted**. Subsidy fraction ratchets upward (0.5→0.8→1.0 on the adopted path).

{ev('adopted_rules.csv', 'rules')}
""",
    )

    write(
        OUT / "qualitative_analysis/19_si_sfi_language_comparison.md",
        f"""# 19 — SI vs SFI Language Comparison (seed2)

Keyness (shared kinds) again separates dialects:

- SI-distinctive: strategy, follow, self-interest
- SFI-distinctive: sfi, long-run, incentives, immediate

Leave-one-out Jaccard remains high (~0.97), so the split is not one-agent noise.

{ev('prompt6_numeric_summary.json', 'keyness')}
""",
    )

    write(
        OUT / "qualitative_analysis/20_wordcloud_and_keyness_analysis.md",
        f"""# 20 — Wordclouds and Keyness (seed2)

Plots: `plots/wordcloud_SI_contribution.png`, `wordcloud_SFI_contribution.png`, `wordcloud_SI_shared.png`, `wordcloud_SFI_shared.png`, `keyness_shared_unigrams.png`, `concept_rates_shared.png`.

Contribution clouds reinforce opportunistic/incentive registers over fairness/repair vocabulary — consistent with motif imbalance after social events.

{ev('prompt6_numeric_summary.json', 'wordclouds')}
""",
    )

    write(
        OUT / "qualitative_analysis/32_zero_contribution_reasoning.md",
        f"""# 32 — Zero Contribution Reasoning (seed2)

Cold-start zeros are rarer than seed1 (SFI R1 zero share 0.0). Later zeros still cite payoff/MCPR and conservation frames.

{ev('prompt_zero_numeric_summary.json', 'reasoning')}
""",
    )

    # Cross-seed MD
    rcorr = xs.get("round_mean_prop_correlation_ALL", {})
    write(
        OUT / "cross_seed_comparison.md",
        f"""# Cross-Seed Comparison — seed1 (20260731) vs seed2 (20260804)

**Scope.** Both runs: Llama 3.1 8B, Full / scnldf / sh1 / ldf1, 26 agents, 30 rounds. Differ only by random seed (1 vs 2) and any parser/runtime drift between execution dates.

**Primary metric.** `prop_of_wealth`.

## Executive findings

1. **Levels:** Seed2 mean prop ({rcorr.get('mean_seed2'):.3f}) exceeds seed1 ({rcorr.get('mean_seed1'):.3f}). Round-path correlation across seeds is weak (Pearson r={rcorr.get('pearson_r'):.3f}, p={rcorr.get('pearson_p'):.3f}).
2. **SI≈SFI means** in both seeds; agent-mean Mann–Whitney SI vs SFI is non-significant in both. Agent-round tests can reject due to huge N / skew — interpret carefully.
3. **Reputation backfires is seed-sensitive for SI:** SFI gossip/bad-rep immediate Δprop stays negative in both seeds; SI gossip Δprop flips from negative (seed1) to positive (seed2).
4. **Democracy path diverges:** both expand subsidies / LDF equity themes; seed2 **adopts punishment weakening** (PUNISHMENT_EFFECT=2); seed1 rejected punishment weakening.
5. **Macro stocks:** Seed2 ends with larger wealth gap and larger LDF pool.
6. **Agent-id personas are not stable across seeds** (only 12/26 keep the same group label). Do not treat agent_id correlations as fixed-character consistency.

{ev('cross_seed_summary.json', 'notes')}

## Macro trajectories

| Statistic | Seed1 | Seed2 |
|-----------|------:|------:|
| Mean round prop (ALL) | {rcorr.get('mean_seed1'):.4f} | {rcorr.get('mean_seed2'):.4f} |
| Pearson r (round means) | {rcorr.get('pearson_r'):.4f} (p={rcorr.get('pearson_p'):.3f}) | — |
| Spearman r | {rcorr.get('spearman_r'):.4f} (p={rcorr.get('spearman_p'):.3f}) | — |
| RMSE (round means) | {rcorr.get('rmse'):.4f} | — |

Plots: `plots/cross_seed/mean_prop_trajectories_by_institution.png`.

{ev('cross_seed_round_prop_correlation.csv', 'ALL')}

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

{ev('cross_seed_agent_prop_correlation.csv', 'agent_id')}

## SI vs SFI tests

| Seed | Mean SI | Mean SFI | MW p (agent means) |
|------|--------:|--------:|-------------------:|
| 1 | 0.291 | 0.296 | 0.817 |
| 2 | 0.364 | 0.366 | 0.777 |

Institution means stay matched within seed; level shift is a **seed-level** cooperation increase, not SI−SFI divergence.

{ev('cross_seed_mannwhitney_si_sfi.csv', 'tests')}

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

{ev('cross_seed_reputation_imm_delta_prop.csv', 'imm')}

## Governance path dependence

| Seed | Adopted (n) | Notable |
|------|------------:|---------|
| 1 | 6 | Subsidy ↑, LDF equity ↑; punishment weakening **failed** |
| 2 | 6 | Subsidy ↑, LDF equity ↑; punishment effect **weakened to 2** |

Shared round-rule pairs across seeds: 1 (low literal overlap). Political economy is path-dependent under seed noise.

{ev('cross_seed_adopted_rules.csv', 'adopted')}

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
""",
    )

    # Synthesis + paper story
    write(
        OUT / "synthesis/21_executive_summary.md",
        f"""# 21 — Executive Summary (seed2)

Seed2 (Full LDF, llama3.1:8b, seed=2) reproduces the institutional skeleton of seed1 with higher average prop (~0.365), rare cold-start zeros, SFI-negative social-event deltas, SI-mixed/positive gossip deltas, subsidy/equity democracy with adopted punishment weakening, and a larger terminal LDF pool/wealth gap.

Norm emergence remains limited: weak autocorrelation, persistent dispersion.

Cross-seed comparison is mandatory before claiming seed-invariant mechanisms.
""",
    )

    write(
        OUT / "synthesis/22_norm_emergence_verdict.md",
        f"""# 22 — Norm Emergence Verdict (seed2)

| Criterion | Seed2 evidence | Verdict |
|-----------|----------------|---------|
| Positive mean transfers | mean prop {p7.get('overall_mean_prop'):.3f} | Levels OK |
| Path stability | group autocorr {p7.get('group_mean_prop_autocorr_lag1'):.3f} | Weak |
| Convergence | late IQR {p7.get('late_mean_iqr_prop'):.3f} | Limited |
| Repair after social stigma | SFI negative; SI mixed | Mixed |
| Overall | — | **Limited / mixed norm emergence** |

{ev('prompt7_numeric_summary.json', 'verdict')}
""",
    )

    write(
        OUT / "synthesis/23_evidence_matrix.md",
        f"""# 23 — Evidence Matrix (seed2)

| Claim node | Seed2 | Seed1 | Cross-seed |
|------------|-------|-------|------------|
| C1 bad-rep/gossip → negative Δprop (SFI) | Yes | Yes | Robust |
| C1 for SI | Mixed/positive | Negative | Fragile |
| Positive mean cooperation | Yes (higher) | Yes | Level shift |
| Norm emergence | Limited/mixed | Limited/mixed | Shared |
| Democracy subsidy ratchet | Yes | Yes | Shared theme |
| Punishment weakening adopted | Yes | No | Divergent |

Evidence roots: `tables/prompt*_numeric_summary.json`, `cross_seed_summary.json`.
""",
    )

    write(
        OUT / "paper_story/01_seed2_and_cross_seed_story.md",
        f"""# Paper Story — Seed2 Extension & Cross-Seed Bridge

## Organising question

Which reputation/gossip findings from the seed1 “reputation backfires” paper are seed-invariant under identical Full LDF protocol?

## Answer in one paragraph

Under forced SI/SFI routing, **SFI/developing agents again reduce contribution intensity after gossip/bad-rep on average**, while **SI/developed responses flip sign relative to seed1**. Mean cooperation rises in seed2 without producing strong path stability. Democracy again favors subsidies and LDF equity, but seed2 uniquely weakens punishment. LDF pools grow larger while wealth gaps widen — coverage without equalization remains the fiscal punchline.

## Recommended manuscript updates

1. Add a short **multi-seed robustness** subsection with the event-study table by seed×institution.
2. Soften universal wording to: social pressure associates with lower intensity **especially among developing/SFI agents**.
3. Keep seed2 democracy divergence for the follow-up governance paper.
4. Do not pool agent_ids across seeds as fixed personas without remapping groups.

## High-ROI next runs

- Seed3+ for SI gossip sign stability.
- Ablate gossip threshold / bulletin cap.
- Free institutional choice under shocks (breaks collinearity).
""",
    )

    write(
        OUT / "plots/00_plot_interpretations.md",
        f"""# Plot Interpretations (20260804)

Seed2 plots mirror the seed1 set under `plots/`. Cross-seed figures live in `plots/cross_seed/`.

Interpret with the same caveats as seed1 (forced routing, end-of-round wealth denominator, reconstructed gossip). Highlight differences via `cross_seed_comparison.md`.
""",
    )


if __name__ == "__main__":
    main()

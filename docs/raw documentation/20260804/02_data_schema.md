# 02 — Data Schema (20260804)

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

Reasoning blocks use `RB-{round:02d}-A{agent_id}-{kind}`.

[Evidence: `tables/reasoning_blocks.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=schema]

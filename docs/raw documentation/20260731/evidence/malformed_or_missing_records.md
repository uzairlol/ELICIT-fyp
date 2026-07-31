# Malformed or Missing Records

Run: `simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853`
Source: `results/To_Use/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed1_26agents_30rounds_20260731_013853.json`

## Summary checks

| check | value | status | detail |
|---|---|---|---|
| agent_round_rows | 780 | PASS | expected 780 |
| unique_agents | 26 | PASS | filename says 26 |
| n_rounds | 30 | PASS | filename says 30 |
| duplicate_round_agent | 0 | PASS |  |
| round_min | 1 | INFO |  |
| round_max | 30 | INFO |  |
| round_range_complete | 1 | PASS |  |
| missing_rate_contribution | 0.0 | PASS | 0/780 |
| missing_rate_wealth | 0.0 | PASS | 0/780 |
| missing_rate_reputation | 0.0 | PASS | 0/780 |
| missing_rate_institution_choice | 0.0 | PASS | 0/780 |
| missing_rate_agent_group | 0.0 | PASS | 0/780 |
| invalid_negative_contribution | 0 | PASS |  |
| approx_over_stage1_cap_flags | 35 | INFO | uses end-of-round wealth; may false-positive |
| impossible_reputation_flags | 0 | PASS |  |
| agent_type_institution_mismatches | 0 | PASS |  |
| shock_consistency_flags | 0 | PASS |  |
| proposal_vote_consistency_flags | 0 | PASS |  |
| empty_tom_scores_count | 26 | INFO | expected possibly early rounds |
| contrib_reasoning_action_gaps | 0 | INFO |  |
| gossip_rows | 0 | INFO | field absent from JSON |
| reasoning_blocks_extracted | 3854 | INFO |  |
| proposals_extracted | 14 | INFO |  |
| votes_extracted | 156 | INFO |  |
| adopted_rules_extracted | 6 | INFO |  |
| issue_log_lines | 62 | INFO |  |

## Issue log

### Empty `tom_scores`

- round 1: 26 agents

### Other issues

- GOSSIP_ABSENT: results JSON has no gossip / gossip_bulletin field; gossip_bulletins.csv emitted with header only
- round=1 agent=23: contribution 4000000.0 > reconstructed stage1_cap_from_end_wealth 1296995.0 (approx; end-of-round wealth)
- round=10 agent=15: contribution 400000.0 > reconstructed stage1_cap_from_end_wealth 143829.0 (approx; end-of-round wealth)
- round=12 agent=18: contribution 300000.0 > reconstructed stage1_cap_from_end_wealth 266020.0 (approx; end-of-round wealth)
- round=14 agent=0: contribution 200000.0 > reconstructed stage1_cap_from_end_wealth 172327.0 (approx; end-of-round wealth)
- round=15 agent=0: contribution 171000.0 > reconstructed stage1_cap_from_end_wealth 148998.0 (approx; end-of-round wealth)
- round=16 agent=18: contribution 200000.0 > reconstructed stage1_cap_from_end_wealth 193444.0 (approx; end-of-round wealth)
- round=16 agent=6: contribution 53333575.0 > reconstructed stage1_cap_from_end_wealth 28451060.0 (approx; end-of-round wealth)
- round=17 agent=12: contribution 1881923.0 > reconstructed stage1_cap_from_end_wealth 330739.0 (approx; end-of-round wealth)
- round=18 agent=3: contribution 59692200.0 > reconstructed stage1_cap_from_end_wealth 31155802.0 (approx; end-of-round wealth)
- round=2 agent=9: contribution 381648.0 > reconstructed stage1_cap_from_end_wealth 45919.0 (approx; end-of-round wealth)
- round=20 agent=15: contribution 549809.0 > reconstructed stage1_cap_from_end_wealth 197451.0 (approx; end-of-round wealth)
- round=22 agent=20: contribution 213382.0 > reconstructed stage1_cap_from_end_wealth 182578.0 (approx; end-of-round wealth)
- round=22 agent=22: contribution 109657850.0 > reconstructed stage1_cap_from_end_wealth 42071064.0 (approx; end-of-round wealth)
- round=23 agent=20: contribution 182578.0 > reconstructed stage1_cap_from_end_wealth 110723.0 (approx; end-of-round wealth)
- round=23 agent=25: contribution 104641839.0 > reconstructed stage1_cap_from_end_wealth 37100494.0 (approx; end-of-round wealth)
- round=23 agent=4: contribution 200000.0 > reconstructed stage1_cap_from_end_wealth 166255.0 (approx; end-of-round wealth)
- round=24 agent=12: contribution 213382.0 > reconstructed stage1_cap_from_end_wealth 115942.0 (approx; end-of-round wealth)
- round=25 agent=18: contribution 1000000.0 > reconstructed stage1_cap_from_end_wealth 173007.0 (approx; end-of-round wealth)
- round=26 agent=23: contribution 150000000.0 > reconstructed stage1_cap_from_end_wealth 41192413.0 (approx; end-of-round wealth)
- round=26 agent=7: contribution 878934.0 > reconstructed stage1_cap_from_end_wealth 212855.0 (approx; end-of-round wealth)
- round=27 agent=12: contribution 213382.0 > reconstructed stage1_cap_from_end_wealth 206168.0 (approx; end-of-round wealth)
- round=27 agent=18: contribution 385862.0 > reconstructed stage1_cap_from_end_wealth 134820.0 (approx; end-of-round wealth)
- round=27 agent=3: contribution 166000000.0 > reconstructed stage1_cap_from_end_wealth 50651687.0 (approx; end-of-round wealth)
- round=28 agent=15: contribution 822880.0 > reconstructed stage1_cap_from_end_wealth 199311.0 (approx; end-of-round wealth)
- round=29 agent=12: contribution 213382.0 > reconstructed stage1_cap_from_end_wealth 187225.0 (approx; end-of-round wealth)
- round=3 agent=3: contribution 5083896.0 > reconstructed stage1_cap_from_end_wealth 2600761.0 (approx; end-of-round wealth)
- round=30 agent=15: contribution 300000.0 > reconstructed stage1_cap_from_end_wealth 182510.0 (approx; end-of-round wealth)
- round=30 agent=4: contribution 654813.0 > reconstructed stage1_cap_from_end_wealth 181171.0 (approx; end-of-round wealth)
- round=4 agent=6: contribution 5000000.0 > reconstructed stage1_cap_from_end_wealth 2722447.0 (approx; end-of-round wealth)
- round=5 agent=20: contribution 1000000.0 > reconstructed stage1_cap_from_end_wealth 240209.0 (approx; end-of-round wealth)
- round=5 agent=21: contribution 6529794.0 > reconstructed stage1_cap_from_end_wealth 2872554.0 (approx; end-of-round wealth)
- round=6 agent=8: contribution 430812.0 > reconstructed stage1_cap_from_end_wealth 91782.0 (approx; end-of-round wealth)
- round=7 agent=8: contribution 91782.0 > reconstructed stage1_cap_from_end_wealth 68508.0 (approx; end-of-round wealth)
- round=8 agent=7: contribution 443081.0 > reconstructed stage1_cap_from_end_wealth 123815.0 (approx; end-of-round wealth)
- round=9 agent=3: contribution 11454338.0 > reconstructed stage1_cap_from_end_wealth 6255844.0 (approx; end-of-round wealth)

## Gossip

No `gossip` / `gossip_bulletin` field exists in the selected results JSON. `tables/gossip_bulletins.csv` is emitted with headers only.

# Malformed or Missing Records

Run: `simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555`
Source: `results/simulation_llama3.1_8b_Full_scnldf_sh1_ldf1_seed2_26agents_30rounds_20260804_024555.json`

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
| approx_over_stage1_cap_flags | 59 | INFO | uses end-of-round wealth; may false-positive |
| impossible_reputation_flags | 0 | PASS |  |
| agent_type_institution_mismatches | 0 | PASS |  |
| shock_consistency_flags | 0 | PASS |  |
| proposal_vote_consistency_flags | 0 | PASS |  |
| empty_tom_scores_count | 26 | INFO | expected possibly early rounds |
| contrib_reasoning_action_gaps | 0 | INFO |  |
| gossip_rows | 0 | INFO | field absent from JSON |
| reasoning_blocks_extracted | 3850 | INFO |  |
| proposals_extracted | 10 | INFO |  |
| votes_extracted | 156 | INFO |  |
| adopted_rules_extracted | 6 | INFO |  |
| issue_log_lines | 86 | INFO |  |

## Issue log

### Empty `tom_scores`

- round 1: 26 agents

### Other issues

- GOSSIP_ABSENT: results JSON has no gossip / gossip_bulletin field; gossip_bulletins.csv emitted with header only
- round=1 agent=13: contribution 2000000.0 > reconstructed stage1_cap_from_end_wealth 690641.0 (approx; end-of-round wealth)
- round=1 agent=4: contribution 20000000.0 > reconstructed stage1_cap_from_end_wealth 12858133.0 (approx; end-of-round wealth)
- round=1 agent=9: contribution 532700.0 > reconstructed stage1_cap_from_end_wealth 360641.0 (approx; end-of-round wealth)
- round=11 agent=0: contribution 48714218.0 > reconstructed stage1_cap_from_end_wealth 29525226.0 (approx; end-of-round wealth)
- round=11 agent=17: contribution 3418544.0 > reconstructed stage1_cap_from_end_wealth 1360695.0 (approx; end-of-round wealth)
- round=11 agent=9: contribution 4207801.0 > reconstructed stage1_cap_from_end_wealth 1360695.0 (approx; end-of-round wealth)
- round=12 agent=15: contribution 5338556.0 > reconstructed stage1_cap_from_end_wealth 1764503.0 (approx; end-of-round wealth)
- round=12 agent=16: contribution 3714830.0 > reconstructed stage1_cap_from_end_wealth 1764503.0 (approx; end-of-round wealth)
- round=13 agent=12: contribution 3187348.0 > reconstructed stage1_cap_from_end_wealth 2085225.0 (approx; end-of-round wealth)
- round=13 agent=23: contribution 5363263.0 > reconstructed stage1_cap_from_end_wealth 2085225.0 (approx; end-of-round wealth)
- round=14 agent=12: contribution 2085225.0 > reconstructed stage1_cap_from_end_wealth 1891052.0 (approx; end-of-round wealth)
- round=14 agent=16: contribution 2947838.0 > reconstructed stage1_cap_from_end_wealth 1891052.0 (approx; end-of-round wealth)
- round=15 agent=13: contribution 4011935.0 > reconstructed stage1_cap_from_end_wealth 1488513.0 (approx; end-of-round wealth)
- round=16 agent=0: contribution 91986136.0 > reconstructed stage1_cap_from_end_wealth 51930845.0 (approx; end-of-round wealth)
- round=16 agent=23: contribution 5000000.0 > reconstructed stage1_cap_from_end_wealth 1885859.0 (approx; end-of-round wealth)
- round=17 agent=1: contribution 5836180.0 > reconstructed stage1_cap_from_end_wealth 2155618.0 (approx; end-of-round wealth)
- round=17 agent=20: contribution 114225258.0 > reconstructed stage1_cap_from_end_wealth 74107594.0 (approx; end-of-round wealth)
- round=17 agent=3: contribution 3941841.0 > reconstructed stage1_cap_from_end_wealth 2155618.0 (approx; end-of-round wealth)
- round=17 agent=4: contribution 157731079.0 > reconstructed stage1_cap_from_end_wealth 74107469.0 (approx; end-of-round wealth)
- round=18 agent=3: contribution 1500000.0 > reconstructed stage1_cap_from_end_wealth 1410718.0 (approx; end-of-round wealth)
- round=19 agent=0: contribution 91760192.0 > reconstructed stage1_cap_from_end_wealth 49222990.0 (approx; end-of-round wealth)
- round=2 agent=12: contribution 500000.0 > reconstructed stage1_cap_from_end_wealth 480274.0 (approx; end-of-round wealth)
- round=2 agent=15: contribution 500000.0 > reconstructed stage1_cap_from_end_wealth 482634.0 (approx; end-of-round wealth)
- round=2 agent=18: contribution 4000000.0 > reconstructed stage1_cap_from_end_wealth 3971854.0 (approx; end-of-round wealth)
- round=2 agent=8: contribution 514341.0 > reconstructed stage1_cap_from_end_wealth 251933.0 (approx; end-of-round wealth)
- round=20 agent=2: contribution 17327707.0 > reconstructed stage1_cap_from_end_wealth 3725254.0 (approx; end-of-round wealth)
- round=21 agent=7: contribution 120000000.0 > reconstructed stage1_cap_from_end_wealth 57659156.0 (approx; end-of-round wealth)
- round=21 agent=9: contribution 10000000.0 > reconstructed stage1_cap_from_end_wealth 9945816.0 (approx; end-of-round wealth)
- round=22 agent=0: contribution 91760192.0 > reconstructed stage1_cap_from_end_wealth 42821027.0 (approx; end-of-round wealth)
- round=22 agent=7: contribution 57659156.0 > reconstructed stage1_cap_from_end_wealth 42206822.0 (approx; end-of-round wealth)
- round=23 agent=24: contribution 219423727.0 > reconstructed stage1_cap_from_end_wealth 101559300.0 (approx; end-of-round wealth)
- round=23 agent=25: contribution 294951895.0 > reconstructed stage1_cap_from_end_wealth 101559297.0 (approx; end-of-round wealth)
- round=23 agent=5: contribution 20000000.0 > reconstructed stage1_cap_from_end_wealth 8883891.0 (approx; end-of-round wealth)
- round=24 agent=1: contribution 11495243.0 > reconstructed stage1_cap_from_end_wealth 4269513.0 (approx; end-of-round wealth)
- round=25 agent=7: contribution 80000000.0 > reconstructed stage1_cap_from_end_wealth 68688081.0 (approx; end-of-round wealth)
- round=26 agent=4: contribution 275939867.0 > reconstructed stage1_cap_from_end_wealth 72228777.0 (approx; end-of-round wealth)
- round=27 agent=11: contribution 27098600.0 > reconstructed stage1_cap_from_end_wealth 9601805.0 (approx; end-of-round wealth)
- round=27 agent=13: contribution 20000000.0 > reconstructed stage1_cap_from_end_wealth 12037328.0 (approx; end-of-round wealth)
- round=27 agent=14: contribution 429454230.0 > reconstructed stage1_cap_from_end_wealth 165338582.0 (approx; end-of-round wealth)
- round=27 agent=6: contribution 496094528.0 > reconstructed stage1_cap_from_end_wealth 165338524.0 (approx; end-of-round wealth)
- round=29 agent=14: contribution 214659906.0 > reconstructed stage1_cap_from_end_wealth 184658290.0 (approx; end-of-round wealth)
- round=29 agent=18: contribution 638841702.0 > reconstructed stage1_cap_from_end_wealth 184660435.0 (approx; end-of-round wealth)
- round=3 agent=25: contribution 10608737.0 > reconstructed stage1_cap_from_end_wealth 5038884.0 (approx; end-of-round wealth)
- round=3 agent=2: contribution 1000364.0 > reconstructed stage1_cap_from_end_wealth 236562.0 (approx; end-of-round wealth)
- round=3 agent=4: contribution 12000000.0 > reconstructed stage1_cap_from_end_wealth 8741802.0 (approx; end-of-round wealth)
- round=30 agent=11: contribution 15000000.0 > reconstructed stage1_cap_from_end_wealth 12589566.0 (approx; end-of-round wealth)
- round=30 agent=17: contribution 30000000.0 > reconstructed stage1_cap_from_end_wealth 15575615.0 (approx; end-of-round wealth)
- round=30 agent=21: contribution 962023781.0 > reconstructed stage1_cap_from_end_wealth 283120606.0 (approx; end-of-round wealth)
- round=4 agent=10: contribution 1212136.0 > reconstructed stage1_cap_from_end_wealth 425190.0 (approx; end-of-round wealth)
- round=4 agent=12: contribution 716836.0 > reconstructed stage1_cap_from_end_wealth 425190.0 (approx; end-of-round wealth)
- round=4 agent=13: contribution 890000.0 > reconstructed stage1_cap_from_end_wealth 425433.0 (approx; end-of-round wealth)
- round=4 agent=19: contribution 10000000.0 > reconstructed stage1_cap_from_end_wealth 7318908.0 (approx; end-of-round wealth)
- round=5 agent=14: contribution 8000000.0 > reconstructed stage1_cap_from_end_wealth 7269189.0 (approx; end-of-round wealth)
- round=5 agent=3: contribution 1784326.0 > reconstructed stage1_cap_from_end_wealth 779340.0 (approx; end-of-round wealth)
- round=5 agent=5: contribution 1215506.0 > reconstructed stage1_cap_from_end_wealth 779340.0 (approx; end-of-round wealth)
- round=6 agent=16: contribution 1059966.0 > reconstructed stage1_cap_from_end_wealth 662427.0 (approx; end-of-round wealth)
- round=6 agent=22: contribution 10000000.0 > reconstructed stage1_cap_from_end_wealth 8686721.0 (approx; end-of-round wealth)
- round=7 agent=0: contribution 31966882.0 > reconstructed stage1_cap_from_end_wealth 12281276.0 (approx; end-of-round wealth)
- round=8 agent=6: contribution 30000000.0 > reconstructed stage1_cap_from_end_wealth 23251345.0 (approx; end-of-round wealth)

## Gossip

No `gossip` / `gossip_bulletin` field exists in the selected results JSON. `tables/gossip_bulletins.csv` is emitted with headers only.

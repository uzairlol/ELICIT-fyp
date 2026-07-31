# 36 — Beliefs and Sanction Structure (20260731)

Dashboard beliefs + sanctions network summaries. Tables: `belief_trust_buckets.csv`, `belief_agent_perception_counts.csv`, `sanction_timeline.csv`, `sanction_top_givers.csv`, `sanction_top_receivers.csv`. Plot: `sanction_punish_reward_timeline.png`.

---

## Opening claim

Belief `trust_levels` are mostly unclassified/default (79%), with **free-rider** labels (~13%) outnumbering **cooperative** labels (~8%). Sanctioning is active inside SI: 130 unique punish edges and 131 reward edges over the run, concentrated among a few wealthy givers/receivers — a hub structure, not equal peer monitoring.

---

## Belief buckets (dashboard `trustClass`)

| Bucket | Count | Share |
|--------|------:|------:|
| default | 5928 | 0.795 |
| free-rider | 955 | 0.128 |
| cooperative | 575 | 0.077 |
| unreliable | 1 | ~0 |

[Evidence: `tables/belief_trust_buckets.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=all]

**Reasoning:** Free-rider labelling is common enough to show negative social categorisation in beliefs, yet contribution norms remain weak and gossip does not raise prop — **naming** defection ≠ **correcting** it.

---

## Sanction hubs

Top punish givers (tokens): 25, 2, 14, 3, 22 (all SI).  
Top receivers: 14, 10, 6, 16, 22.  
Agent 14 appears as both heavy giver and top receiver — a conflictual hub.

Timeline plot shows punish and reward tokens co-evolving; the polity is not punishment-only.

[Evidence: `tables/sanction_top_givers.csv` | run=20260731_013853 | round=n/a | agent=n/a | record=lifetime]

---

## Link to enforcement-as-public-good

Hub concentration supports the second-order story: a subset of SI agents supply most costly monitoring while democracy expands subsidies that recycle punishment-pool resources toward top contributors (docs 17–18).

---

## Limits

`trustClass` is keyword heuristic (same as dashboard). Edge list not fully exported as graph ML features. Confidence high on bucket counts and top giver lists; medium on network interpretation without centrality suite.

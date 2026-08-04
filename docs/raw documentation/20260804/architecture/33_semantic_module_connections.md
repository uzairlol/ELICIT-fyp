# 33 â€” Semantic Module Connections (20260804)

[`07_module_interaction_map.md`](07_module_interaction_map.md) shows **control flow** (what runs after what). This document shows **semantic coupling**: what each module *means* to an agent, what information crosses the edge, the timing lag, and what the 20260804 run suggests about behavioural consequence.

Cross-links: [`06_agent_information_boundaries.md`](06_agent_information_boundaries.md), [`04_system_architecture.md`](04_system_architecture.md).

---

## Architectural vs semantic coupling

| Edge | Architecturally connected? | Semantically available to agent? | 20260804 consequence |
|------|----------------------------|----------------------------------|------------------------|
| Stage-1 contribution â†’ LDF pool deposit | Yes (dual-use) | Pool **balance** not shown; own deposit/payout/damage shown | Cannot optimise against fund stock; fund language in only ~1.8% of contribution texts |
| LDF pool â†’ payouts | Yes | Own payout only | Coverage ~77% at shocks; huge residual pool unused as decision signal |
| Contribution â†’ ToM scores | Yes | Scorer sees peer history; scored agent sees own reputation later | ToM highly discrete (many 5s/1s); 84% of scores â‰¤7 |
| ToM â†’ reputation mean | Yes | Own Ï visible next round | Bad-rep events â†’ mean Î” prop **negative** |
| ToM â†’ gossip bulletin | Yes | Personalized top-5 â‰¤7; `"YOU"` label | Gossip targets often mid/high prop; mean Î” prop negative; almost no â€œgossipâ€ token in reasoning |
| Gossip â†’ Stage-2 (SI) | Weak | SI already sees peer contrib/deviation | Gossip partly **redundant** for SI punish; more informative for SFI |
| Stage-2 â†’ subsidy pool | Yes | Indirect | Democracy raises subsidy fraction â€” carrot politics |
| Democracy â†’ parameters | Yes | Free to propose/vote | Costless meta-governance substitutes for costly enforcement |
| Forced institution â†’ prompts | Yes | Agents recite routing facts | No semantic â€œchoiceâ€ of SI/SFI |

---

## Semantic feedback graph

```mermaid
flowchart LR
  contrib[Stage1_contribution]
  tom[ToM_pairwise_scores]
  rep[Reputation_mean]
  gossip[Gossip_bulletin]
  stage2[Stage2_sanctions_SI]
  belief[Belief_trust_labels]
  demo[Democracy_parameters]
  ldfPool[LDF_pool_hidden]
  ldfOwn[Own_LDF_payout_damage]
  nextContrib[Next_contribution_prompt]

  contrib --> tom
  tom --> rep
  tom --> gossip
  rep --> nextContrib
  gossip --> nextContrib
  contrib --> stage2
  stage2 --> nextContrib
  contrib --> belief
  belief --> nextContrib
  contrib --> ldfPool
  ldfPool -.->|not observed| nextContrib
  ldfOwn --> nextContrib
  demo --> nextContrib
```

Dashed edge = architectural write without semantic read.

---

## Edge-by-edge meaning

### 1. Contribution â†’ ToM (â€œwas this agent trustworthy?â€)

**Meaning to scorer:** LLM judges peers, often collapsing to extreme bins (score 5: 12,647; score 1: 2,370 of 18,850).  
**Lag:** after round actions.  
**Behavioural note:** first impressions (R2 first non-empty ToM) can path-depend reputation (RQ 4 deferred for full partials; distribution shape answered in RQ index).

[Evidence: `tables/prompt_dashboard_rq_summary.json` | run=20260804_024555 | round=n/a | agent=n/a | record=tom_gossip]

### 2. ToM â†’ gossip (â€œwho is socially flagged?â€)

**Meaning:** lowest scores â‰¤7, top 5 â€” but **84%** of all scores are â‰¤7, so the threshold is nearly ambient rather than rare indictment.  
**Lag:** bulletin compiled after t; read at t+1.  
**Behavioural note:** targetsâ€™ mean prop at event â‰ˆ0.52; mean Î” afterward negative (doc 11). Semantic intent â€œdiscipline free-ridersâ€ â‰  observed selection.

### 3. Reputation â†’ next contribution

**Meaning:** scalar social image in prompt.  
**Observed talk:** rare explicit repair; more MCPR/payoff (docs 11, 32).  
**Consequence:** not a reliable upward stabiliser.

### 4. Stage-2 sanctions â†’ payoffs / beliefs

**Meaning:** costly moralistic aggression / reward inside SI.  
**Talk:** â€œpunish free-ridersâ€¦ fairnessâ€ (doc 17).  
**Consequence:** uneven provision; democracy prefers carrots.

### 5. Belief trust_levels â†’ perception

**Meaning:** categorical labels of peers. Dashboard buckets: default 79%, free-rider 13%, cooperative 8%.  
**Consequence:** free-rider labelling is common relative to cooperative labelling, yet contribution norms stay weak â€” labels do not equal repaired cooperation.

[Evidence: `tables/belief_trust_buckets.csv` | run=20260804_024555 | round=n/a | agent=n/a | record=buckets]

### 6. LDF pool (hidden) vs own flows (visible)

**Semantic hole:** agents can know they were under-covered relative to own damage, but cannot see whether the fund is rich or poor globally. Final pool ~4.34e9 with cumulative payouts only 8.5e5 â€” externally the fund is flush; internally agents almost never discuss pool adequacy.

### 7. Democracy as semantic override

Changing `SUBSIDY_FRACTION` or `LDF_EQUITY_WEIGHT` rewrites the payoff meaning of prior Stage-2 and LDF modules without requiring agents to re-negotiate informal norms. That is why formal rules can drift while obligation language stays thin (Prompt 7).

---

## Summary thesis

Modules are tightly wired in code, but **meaning is sparse and lagged**. The strongest semantic channels in agent text are MCPR/payoff and institution strategy templates; the weakest are fund adequacy, gossip acknowledgement, and fairness-as-contribution-obligation. Behavioural results (no repair after gossip; dual-use hidden pool; reward ratchet) follow from that semantic thinness as much as from the architectural diagram.

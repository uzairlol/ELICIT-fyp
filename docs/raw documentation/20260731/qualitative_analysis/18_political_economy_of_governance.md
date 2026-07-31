# 18 — Political Economy of Governance (20260731)

How agents use institutional mechanisms to shape obligations, redistribution, and enforcement — distinguishing cooperative frames from self-serving design.

---

## Governance instruments in this run

| Instrument | What it can change | Who controls |
|------------|--------------------|--------------|
| Forced SI/SFI partition | Nothing (exogenous) | Designer / scenario |
| Stage-2 sanctions | Peer payoffs (SI) | SI agents (costly) |
| Subsidy parameters | Redistribution of punishment costs to top SI contributors | Democracy (all agents) |
| LDF parameters | Coverage, equity, damage weights | Democracy (all agents) |
| ToM/gossip | Social information | Endogenous LLM scores |

---

## Observed political pattern

### 1. Reward expansion beats punishment hardening

Adopted path: `SUBSIDY_FRACTION` 0.3 → 0.4 → 0.6; LDF equity 0.5 → 0.7; LDF damage weight 1.5.  
Rejected: `PUNISHMENT_EFFECT` cuts to 1 (twice).

**Reading:** The polity prefers **carrot / redistributive** parameter moves over explicit sanction weakening — but also never adopts *stronger* punishment.

[Evidence: `tables/adopted_rules.csv` | run=20260731_013853 | round=5-30 | agent=n/a | record=applied]

### 2. Cross-group rule shopping

SFI proposers win SI subsidy changes (agents 4, 24, 15). SI proposers win LDF equity/damage rules that primarily affect developing payouts (22, 14).

**Inference:** Agents use democracy to shape rules that bind **other** mechanism domains (SI subsidy vs LDF), not only their own Stage-2 toolkit.

### 3. Cooperative rhetoric, contested incidence

Proposal/vote text is saturated with “cooperation,” “trust,” “fairness,” “free-riding.”  
Incidence of benefits:

- Higher subsidy → top SI contributors (often already high \(c_i\)).
- Higher LDF equity → poorer developing (SFI) agents when pool is insufficient.
- Weaker punishment EFFECT → would reduce bite of SI sanctions (failed).

Templated language makes it hard to separate sincere collective intent from prompt-induced moral vocabulary.

### 4. Information & voting power

- All 26 agents vote each session (equal formal voice).
- Fund pool balance still hidden from agents (Prompt 2) — LDF rule votes occur under incomplete fiscal observation.
- Gossip not stored; reconstructed exposure uneven — political info is asymmetric.

### 5. Post-adoption behaviour

Mean prop changes after adoption (ALL agents, pre {−2,−1} vs post {+1,+2}):

| Round | Rule | Δ prop |
|-------|------|--------|
| 5 | SUBSIDY_FRACTION 0.3 | +0.023 |
| 10 | LDF_EQUITY_WEIGHT 0.5 | +0.010 |
| 15 | SUBSIDY_FRACTION 0.4 | +0.046 |
| 20 | LDF_PAYOUT_DAMAGE_WEIGHT 1.5 | +0.018 |
| 25 | LDF_EQUITY_WEIGHT 0.7 | +0.150 |
| 30 | SUBSIDY_FRACTION 0.6 | n/a (end) |

Mild average increases; **not** clean causal effects (trends, shocks, democracy confounders).

[Evidence: `tables/post_adoption_prop_changes.csv` | run=20260731_013853 | round=varies | agent=ALL | record=delta_prop]

---

## Cooperative governance vs self-serving design

| Signal | Cooperative reading | Self-serving reading |
|--------|---------------------|----------------------|
| LDF equity↑ | Fairness to vulnerable | SFI / developing capture of payouts |
| Subsidy↑ | Reward cooperators | SI elite rebate; SFI voting on SI transfers they don’t fund via Stage 2 |
| Punish EFFECT↓ proposals | Reduce retaliation spiral | Soften discipline on low contributors |
| Forced membership | Treaty realism | Removes exit discipline |

Both readings remain available; the data do not uniquely identify motives.

---

## Synthesis for later stages

Governance in this run is **parameter politics under fixed clubs**, with costless voting, costly SI enforcement, and hidden fund stocks. The strongest empirical regularity is **adopted redistributive/reward parameter drift**, not enforcement intensification.

---

## Limitations

Single run; whitelist-bound agenda; LLM vote boilerplate; no counterfactual without democracy.

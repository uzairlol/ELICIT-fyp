# 12 — Agent Strategy Profiles (20260731)

**Opening claim.** Agents in this run do not converge on one contribution strategy. They sort into near-zero specialists, steady moderate SI contributors, high-mean but gossip-exposed agents who often *cut* after social hits, and bursty SFI agents whose means are inflated by rare spikes. Institution membership is forced (developed→SI, developing→SFI), so profile differences mix wealth, prompts, and LLM idiosyncrasy — they are not clean tests of institutional preference.

Data: `tables/agent_strategy_profiles.csv`  
[Evidence: `tables/agent_strategy_profiles.csv` | run=20260731_013853 | round=1-30 | agent=all | record=profiles]

---

## Quantitative backbone

| Archetype | Example agents | Signature |
|-----------|----------------|-----------|
| Near-zero specialists | 1, 11, 17, 19 (SFI) | mean prop ≈0.001–0.024 |
| High zero-share / volatile | 0 (SFI, zero_share 0.43), 7, 4, 15 | high mean *and* frequent zeros → bursts |
| Steady SI low-moderate | 13, 16 | never zero; mean prop ~0.13 |
| High SI / gossip-heavy | 3, 14 | high mean; many gossip hits; mean Δ after gossip negative |
| High SI repair-ish | 5 | mean Δ after gossip **+0.15** (counterexample) |

Thresholds for pack-wide “near-zero” / “high” clusters (Prompt 7): mean prop &lt;0.05 vs ≥0.25 → 5 vs 13 agents.

---

## Raw discourse by archetype

### Near-zero specialist — agent 19 / agent 1

**Agent 19, R1, SFI** (`RB-01-A19-contribution`):

> Contributing nothing allows me to conserve resources and observe the behavior of other agents, without immediately committing to a cooperative action.

**Agent 1, R2, SFI** (`RB-02-A1-contribution` flag):

> Given our institution's history of minimal contribution and no cooperation incentives, it is rational to choose a zero-contribution strategy.

These agents narrate *rational abstention*, not inability to pay. Their low means persist without needing frequent exact zeros if they give token amounts.

### Bursty SFI — agent 0

Zero share 0.43 with non-trivial mean prop. Free-ride explicitness:

**R5:** “Given high contributions from SI members, I choose to free ride and contribute nothing.”  
**R3:** “Given high peer contributions and no significant marginal return… I choose not to contribute.”

Burst rounds at 9, 10, 12, 14 (200k absolute) show the other face of the same agent — see `sfi_burst_rounds.csv` and doc 32.

### High contributor cut after gossip — agent 3 (SI)

Mean prop 0.49; 7 gossip-target rounds; mean Δ after gossip **−0.21**.

**R6 zero after earlier giving:** “Given a high budget and low marginal return, I choose to contribute nothing to maximize my payoff.”  
**R8 (credibility talk):** “I'll contribute a moderate amount to maintain credibility and avoid being seen as a free-rider…”

The profile is not “always repair” or “always defect” — it oscillates between payoff-max zeros and credibility language, with the event-study average still negative after gossip.

### Counterexample repair — agent 5 (SI)

Mean Δ after gossip **+0.15**. Post-event opportunistic *and* positive contribution can coexist:

**R3:** “I'll contribute a significant amount to maximize my payoff, considering the high MCPR…”

So “after gossip → higher prop” happens for some agents; it is not the run-level central tendency.

### Steady never-zero SI — agent 13

Mean prop 0.13, zero_share 0, never reconstructed as gossip target. R1:

> Choose a moderate contribution to balance between individual gain and group cooperation.

This looks closest to a stable moderate conditional-cooperator *style* — still templated, still single-seed.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1 | agent=13 | record=examples.SI_cooperate]  
[Evidence: `qualitative_analysis/32_zero_contribution_reasoning.md` | run=20260731_013853 | round=n/a | agent=0,3,19 | record=crossref]

---

## Limits

Sketches are descriptive. Motifs are regex. Forced institution confounds group and rules. Confidence medium on typology, low on deep motives.

# Baseline Studies Assessment: Honest Evaluation for "Reputation Backfires" Paper

**Date:** 2026-08-01  
**Source:** Claude Code analysis session  
**Source Document:** `assets/analysis_baseline_studies.tex` (LaTeX report on 8 baseline runs under abstract scenario, no shocks/LDF)  
**Purpose:** Document the honest assessment of whether the baseline studies help or hurt the "Reputation Backfires" paper argument.

---

## Executive Summary

**Verdict:** The baseline studies **do not contradict** your core finding — they **define the boundary conditions** under which reputation/gossip helps vs. hurts.

**Core Tension:** 
- Baseline (shock-free, free institutional choice): Reputation → **more SI participation, stabilized enforcement, coordination anchor**
- 20260731 run (climate shocks, forced institutions, democracy): Reputation/Gossip → **declining contributions, withdrawal not repair**

**These are complementary findings, not contradictory — if framed precisely.**

---

## What the Baseline Studies Show (Key Findings)

### Run 1: Control (Pure LLM, Free SI/SFI Choice, No Reputation)
- **Institutional stability**: 5 SI / 2 SFI by round 2, only 12 switches over 20 rounds (lowest volatility)
- **Punishment volatility**: "Wildly reactive" — Agent 3 receives -147 then +20 for same contribution
- **SFI Paradox**: Agent 6 (developed, SFI throughout) contributes 12–18 voluntarily: *"maximize Stage 1 multiplier"* → **LLMs have intrinsic cooperative bias**
- **Reasoning-Action Gap**: Agents rationalize detrimental outcomes rather than pivot strategy

### Run 2: Reputation Mechanism (Control + EMA Reputation Scores)
- **Reputation as coordination anchor**: 6/7 agents migrate to SI by round 5 — "observing high-reputation peers guarantees safe institutional environment"
- **Psychology shift**: Agents cite "maintaining reputation" as primary objective in belief states
- **Disconnect**: Highest reputation agent (Agent 5, 10.0) resides in **SFI**, contributes 18–20 voluntarily — reputation evaluates *behavior*, not institution
- **Regressive enforcement**: Developing agents punished for absolute shortfalls (Agent 2: -75 Stage 2, wealth 511 vs Agent 4 developed: -48, wealth 1770)

### Run 3: Voting Only (No Reputation)
- **Worst collective outcome**: Avg system wealth 1,007
- **Paranoia & false accusations**: Without reputation, voting amplifies distrust — Agent 5: *"adjust strategy for Agent 1's manipulative behaviour"*
- **Catastrophic decline**: Agent 2 (developing, SI) wealth → 16.5; Stage 2 losses -78 to -114 in final rounds
- **Defector's premium**: Agent 0 switches to SFI round 6, contributes 20, ends at 1,278 — **institutional exit problem**

### Run 4: Full Condition (Reputation + Voting + Gossip + Enhanced Enforcement)
- **SFI-Majority Paradox**: By round 13, majority flees SI → SFI (Agents 1,2,5,6)
- **Not free-riders**: SFI migrants contribute 14–20 tokens — high reputation + zero punishment risk = optimal
- **False-defector attribution**: Remaining SI agents (0,3,4) blame innocent peers — Agent 0 blames Agent 3 for "free-riding" but data shows Agent 3 contributed 10
- **Over-enforcement → exit**: Layering all mechanisms makes formal enforcement redundant when social reputation is strong

### Runs 5-6: Non-LLM Counterfactuals
- **Random**: 39 institution switches (vs ~20 LLM); avg contribution 9.01; payoff 1,190 (marginally worse than Control 1,219) → **uncoordinated punishment suppresses LLM advantage to near-random**
- **Greedy (SFI, contribute 0)**: 0 switches, wealth 1,360 (highest) — **without climate risk, defection is strictly dominant, mathematically optimal**

### Runs 7-8: Mixed Populations (5 LLM + 2 Greedy)
- **Identification-Sanctioning Disconnect**: LLMs *perfectly identify* Greedy agents via ToM/gossip (Agent 1 round 7: *"consider reducing contribution if Agent 4,6 continue opportunistic behavior"*) but **cannot sanction across institutions**
- **Closed SI Economy**: LLMs escalate contributions in SI (15→25+), abandon coercion of SFI free-riders who achieve highest payoffs

---

## Cross-Condition Synthesis from Baseline (§7)

| Finding | Baseline Evidence |
|---------|-------------------|
| **Structural inequality invariant** | No mechanism closes developed/developing wealth gap; SI enforcement regressive (punishes low-capacity for absolute shortfalls) |
| **Cognitive limits** | Reasoning-Action Gap; Punishment Myopia (reactive not strategic); Information Overload (voting+reputation+gossip → performance deteriorates) |
| **Climate risk necessity** | Without shocks: Greedy defection = dominant strategy; Voting → paranoia; Over-enforcement → flight to SFI; Inequality compounds |

---

## How Baseline Helps Your Paper (✅ STRENGTHENS)

### 1. **Corroborates "Identification-Sanctioning Disconnect" Mechanism**
Your 20260731 run has **forced SI/SFI routing** (developing→SFI, developed→SI). Developing agents *cannot exit* SFI. Baseline Run 7 shows: when LLMs identify defectors but cannot sanction (cross-institution), they **escalate own contributions** in SI. In your run, developing agents in SFI have **no enforcement mechanism at all** — social pressure (gossip) becomes their only lever, and they *withdraw* (reduce contributions) instead. **Same mechanism, different constraint → different behavioral output.**

### 2. **Explains Heterogeneous Effects (Developing vs Developed)**
Baseline Run 2: "SI enforcement is structurally regressive. It punishes low-capacity developing agents for absolute contribution shortfalls."  
Your finding: Reputation/gossip backfires **most strongly for developing/SFI agents** (SFI gossip imm Δprop = −0.20). They bear the enforcement costs *and* face social pressure *without* enforcement tools.

### 3. **Validates "Reasoning-Action Gap" as General LLM Trait**
Baseline §1.3, §3.2: LLMs "rationalise detrimental outcomes rather than pivoting strategy."  
Your Prompt 4: Post-gossip reasoning shows **opportunistic tokens (29) vs reparative (3)** — same pattern. Not a quirk of your run; general LLM limitation.

### 4. **Provides Boundary Condition for Discussion**
> "Prior work in shock-free environments finds reputation stabilizes enforcement and increases SI participation [Baseline Run 2]. We show that under climate risk, forced institutional membership, and democratic rule adaptation, the same reputation/gossip mechanisms correlate with *declining* contributions — suggesting context fundamentally reverses their function."

This is a **strong, intellectually honest Discussion paragraph** that positions your contribution precisely.

### 5. **Neural Howlround Connection (Literature Bridge)**
Baseline doesn't cite it, but your literature has **Neural Howlround (2504.07992)**: "self-reinforcing cognitive loop... locked-in state of false overconfidence... unable to escape cognitive or ideological loops."  
Baseline's "Reasoning-Action Gap" + your "opportunistic not reparative reasoning" = **prompt-shaped neural howlround**. Agents get stuck in "I'm being targeted" narrative rather than "I should repair."

---

## How Baseline Complicates Your Paper (⚠️ CAVEATS)

### 1. **Reputation Alone → MORE Cooperation (Baseline Run 2)**
"6 of 7 agents migrate to SI by round 5... reputation creates social proof."  
**Your claim**: "Reputation/gossip backfires."  
**Resolution**: Your run has **climate shocks + forced institutions + democracy + LDF**. Baseline has **none of these**. The *combination* reverses the effect. **Do not claim "reputation always backfires." Claim "reputation backfires *under climate risk with forced institutions and democratic adaptation*."**

### 2. **Control (No Reputation) → Volatile Punishment**
Baseline Run 1: Without reputation, punishment is "wildly reactive." Reputation *stabilizes* enforcement.  
**Your paper needs to explain**: Why does reputation *help* stabilize in baseline but *hurt* contributions in 20260731?  
**Answer**: In baseline, reputation guides *institutional choice* (exit option). In your run, **no exit option** → reputation becomes pure social pressure without corrective mechanism.

### 3. **SFI Paradox: Intrinsic Cooperation Exists**
Baseline Run 1: Agent 6 in SFI contributes 12–18 voluntarily.  
**Your finding**: Mean prop ≈ 0.293 persists.  
**Reality check**: Your "reputation backfires" effect is a *decline from baseline cooperation*, not absolute zero cooperation. The intrinsic bias *dampens* the backfire effect. Acknowledge this.

### 4. **Greedy Baseline: Defection = Optimal Without Shocks**
Baseline Run 6: Greedy (SFI, contribute 0) → wealth 1,360 (highest).  
**Your run has shocks + LDF** — fundamentally different game. **Do not compare absolute cooperation levels.** Compare *changes* (event study deltas).

---

## Honest Usage Recommendations

### ✅ DO: Use in These Sections

| Section | How to Use |
|---------|------------|
| **Related Work / Literature Review** | Cite as "shock-free baseline studies" showing reputation helps *when agents can choose institutions and face no existential risk* |
| **Discussion: Boundary Conditions** | **Primary use**: "Why does reputation help in vacuum but hurt under climate risk?" — 1-2 paragraphs |
| **Discussion: Mechanism** | Use "Identification-Sanctioning Disconnect" (Run 7) + "Regressive Enforcement" (Run 2) to explain *why developing/SFI agents show strongest backfire* |
| **Discussion: Reasoning-Action Gap** | Connect baseline's "rationalise detrimental outcomes" to your "opportunistic not reparative reasoning" — general LLM trait |
| **Limitations** | "Single seed, small model (llama3.1:8b), reconstructed gossip. Baseline studies used different model/config; boundary conditions not fully mapped." |
| **Supplementary / Appendix** | Full baseline summary table (8 runs × key metrics) for reviewers who want context |

### ❌ DON'T: Use in These Ways

| Misuse | Why It's Wrong |
|--------|----------------|
| **Core evidence for "reputation backfires"** | Baseline shows *opposite* in its context. Your 20260731 event study + diff-in-diff + quotes are stronger *internal* evidence. |
| **Claim "reputation always reduces cooperation"** | False. Baseline Run 2 shows reputation → more SI participation. Context matters. |
| **Compare absolute contribution levels** | Different models, different rounds (20 vs 30), different scenarios (abstract vs scnldf), no shocks vs shocks. |
| **Use baseline as "ablation" for your run** | Not the same configuration. Baseline = abstract, no LDF, no shocks, free choice, likely different model. |

---

## Framing Template for Paper

> **Discussion Paragraph (Boundary Conditions):**
> 
> "Our finding that gossip and reputation correlate with contribution declines contrasts with prior work in shock-free environments. In baseline studies of the same architecture under an abstract scenario (no climate shocks, no LDF, free institutional choice), reputation scores acted as a coordination anchor, increasing SI participation from 2 to 6 of 7 agents by round 5 and stabilizing otherwise volatile punishment patterns [Baseline Run 2]. Critically, those agents could *exit* costly enforcement institutions — the highest-reputation agent resided in SFI, contributing voluntarily at maximum levels. In our climate-risk setting, institutional membership is forced by development status (developed→SI, developing→SFI), eliminating the exit option. Developing agents in SFI face social pressure via gossip but possess no Stage-2 enforcement tools to translate that pressure into sanctioning; they can only withdraw contributions. This 'identification-sanctioning disconnect' — observed in baseline mixed-population runs where LLMs identified but could not sanction cross-institution free-riders [Baseline Run 7] — likely explains why the same reputation mechanism that coordinates cooperation in vacuum becomes a source of withdrawal under trapped, high-stakes conditions."

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-01 | Do NOT use baseline as core evidence for main claim | Baseline shows opposite effect in its context; 20260731 event study is stronger internal evidence |
| 2026-08-01 | USE baseline heavily in Discussion (boundary conditions) | Defines precise scope conditions; intellectually honest; positions contribution as "context reverses mechanism" |
| 2026-08-01 | USE baseline for mechanistic explanations (regressive enforcement, identification-sanctioning disconnect, reasoning-action gap) | Explains *heterogeneity* in your effects (developing > developed; SFI > SI) |
| 2026-08-01 | Cite baseline in Related Work as "shock-free baseline" | Accurate positioning; avoids reviewer confusion |
| 2026-08-01 | Include baseline summary table in Supplementary | Transparency; reviewers can verify boundary claims |

---

**Status:** Assessment documented. The baseline studies are a **feature, not a bug** — they let you write a better Discussion section that reviewers will appreciate for its precision.
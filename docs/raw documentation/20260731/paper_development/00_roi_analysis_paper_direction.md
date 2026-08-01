# ROI Analysis: Paper Direction Selection for 20260731 Run

**Date:** 2026-08-01  
**Source:** Claude Code analysis session  
**Purpose:** Document the ROI-based reasoning for selecting the primary paper direction from the 20260731 research package.

---

## Executive Summary

After analyzing the complete research package (150+ files in `docs/raw documentation/20260731/` + 60+ literature papers in `assets/literature/`), five viable paper directions were identified and evaluated against ROI criteria: **acceptance likelihood, citation potential, writing effort, novelty, venue fit**.

**Recommendation:** **Direction 1 — "When Reputation Backfires: Gossip and Social Pressure Undermine Cooperation in LLM Agent Societies"** — highest ROI.

**Secondary:** Direction 2 — "Democratic Institutional Adaptation..." for a follow-up paper.

---

## Five Candidate Directions Evaluated

### Direction 1: Reputation/Gossip Backfires ⭐⭐⭐⭐⭐ **SELECTED**

| Criterion | Assessment |
|-----------|------------|
| **Novelty** | First demonstration that gossip/reputation — the canonical cooperation mechanism in MAS literature — **systematically reduces** contributions in LLM agents (mean Δprop negative, 69% show decline post-event). Contradicts 20+ years of MAS literature (RepuNet, GOVSIM, Axelrod, Boyd & Richerson). |
| **Writing Effort** | **~60% done**: Event study (doc 11), reconstructed gossip (145 rows), reasoning excerpts (doc 11), strategy profiles (doc 12), consistency analysis (doc 13), quantitative tables, plots. Just needs framing + discussion. |
| **Venue Fit** | **ICML/NeurIPS/ICLR** (ML for multi-agent systems), **ACL/EMNLP** (LLM agent behavior), **AAMAS/JAAMAS** (MAS). Hot topic: "LLM agents fail at human-like social reasoning." |
| **Citation Magnet** | RepuNet (2505.05029), GOVSIM (2404.16698), Generative Agents (Park et al.) all *assume* reputation helps. You falsify this. Reviewers love "canonical mechanism fails" papers. |
| **Story Clarity** | One crisp finding: "Social pressure → less contribution, not more." One figure (event study Δprop), one table (regression), 3-4 quotes. |

**Core Evidence from 20260731:**
- Prompt 4: 145 reconstructed gossip rows; bad-rep/gossip mean Δprop typically negative (e.g., SFI gossip imm −0.20)
- Prompt 4: Rare repair motifs vs more opportunistic tags (29 vs 3)
- Prompt 6: SI language enriched for strategy/self-interest; SFI for incentives/immediate/long-run
- Prompt 7: Norm emergence = "limited or mixed"; cooperation stability = "moderately positive average with limited path stability"
- Claim Checklist C1: "After bad-rep/gossip, mean Δprop is negative on average" = **verified**
- Claim Checklist C2: "Agents systematically repair reputation by raising contributions" = **unsupported** (contrary average deltas)

---

### Direction 2: Democratic Institutional Adaptation ⭐⭐⭐⭐ **STRONG SECOND PAPER**

| Criterion | Assessment |
|-----------|------------|
| **Novelty** | First *endogenous* parameter evolution via democracy in LLM agents (not human-designed). 6 adopted rules, clear path: subsidy↑, LDF equity↑, damage weight↑. |
| **Writing Effort** | **~50% done**: Docs 14–18, proposals/votes tables, enforcement burden analysis, political economy framing. Needs more "so what?" |
| **Venue Fit** | **AAMAS/JAAMAS** (institutional dynamics), **PNAS Nexus** (collective intelligence), **Nature Human Behaviour** (if framed as "AI self-governance"). |
| **Citation Potential** | Connects to Ostrom (doc 25 mapping), algorithmic governance, AI alignment. |
| **Risk** | Harder to make *one* crisp claim; more descriptive. Reviewers may ask "but is it *good* adaptation?" |

**Core Evidence from 20260731:**
- Prompt 5: 14 proposals / 6 democracy rounds / 6 adopted; only 2–3 proposals reach each ballot
- Prompt 5: Adopted path: subsidy fraction ↑ (0.3→0.4→0.6), LDF equity ↑ (0.5→0.7), LDF damage weight 1.5; punishment-weakening proposed twice, never adopted
- Prompt 5: Proposers: 8 SI + 6 SFI; mean proposer prop 0.36 vs population 0.29
- Prompt 5: Stage-2 enforcement is costly; ToM/gossip/voting are not. Mean corr(prop, enforcement spend)≈0.14; top-quartile prop agents pay ~35% of SI enforcement tokens
- Prompt 5: Vote same-group-as-proposer rate ≈0.51 (near base rate)

---

### Direction 3: LDF/Climate Risk Sharing (Dual-Use Deposits) ⭐⭐⭐ **GOOD BUT HIGHER EFFORT**

| Criterion | Assessment |
|-----------|------------|
| **Novelty** | Dual-use deposit mechanism (Stage-1 → LDF) is unique; hidden pool + developing-only payouts. Timely (COP28/29). |
| **Writing Effort** | **~40% done**: Need to build climate finance narrative from scratch; docs 09, 10, 26, 35, 36 have pieces but not story. |
| **Venue Fit** | **Global Environmental Change**, **Climate Policy**, **Nature Climate Change** (if strong policy angle). *Different audience* — needs policy translation. |
| **Risk** | Reviewers will demand real-world calibration (you don't have). Checklist F5: "Simulation proves real FRLD effectiveness = unsupported." |

---

### Direction 4: Small LLMs as Valid Scientific Instruments ⭐⭐⭐ **METHODOLOGICAL PAPER**

| Criterion | Assessment |
|-----------|------------|
| **Novelty** | Methodological defense of small instruct models (llama3.1:8b) for volume + traces + ablation feasibility. |
| **Writing Effort** | Low — doc 27 has the argument. |
| **Venue Fit** | Methodology venues, maybe **JAIR** or **AI Magazine**. Lower citation ceiling. |

---

### Direction 5: Norms ≠ Cooperation Stability ⭐⭐⭐ **THEORETICAL CONTRIBUTION**

| Criterion | Assessment |
|-----------|------------|
| **Novelty** | Explicit distinction: "moderately positive average cooperation with limited path stability" ≠ "norm emergence." |
| **Writing Effort** | Medium — docs 21–23 have the verdicts and evidence matrix. |
| **Venue Fit** | Theory venues (**Games and Economic Behavior**, **Journal of Economic Theory**). Niche audience. |

---

## Critical Exclusion: SI vs SFI Causal Comparison

**Checklist B2**: "SI vs SFI mean prop difference is a causal institution effect" = **unsupported** (perfect collinearity with group).  
**No endogenous choice** (forced routing: developed→SI, developing→SFI).  
**Would be rejected** or require major caveats. **Do not pursue.**

---

## Strategic Recommendation: Two Papers from One Dataset

| Paper | Core Claim | Overlap | Timeline |
|-------|------------|---------|----------|
| **Paper 1: Reputation Backfires** | Social pressure → less cooperation under climate risk + forced institutions + democracy | Uses gossip/reputation data | Submit ICML 2027 (~Jan 2027) or AAMAS 2027 (~Nov 2026) |
| **Paper 2: Democratic Adaptation** | Agents evolve rules toward equity/subsidy under pressure | Uses democracy/proposals data | Submit 3–6 months after Paper 1 |

**Different dependent variables, different literatures, minimal reviewer overlap.** Highest lifetime ROI.

---

## Next Steps for Paper 1 (Reputation Backfires)

### Week 1: Structure & Core Evidence
- Write intro + methods (adapt docs 04–06, 11)
- Create **main figure**: event-study Δprop by institution × event type (bad-rep/gossip/rep-drop)
- Draft abstract (150 words)

### Week 2: Results & Discussion
- Results: quantitative (event study + diff-in-diff), qualitative (reasoning quotes: "opportunistic" vs "reparative"), strategy profiles
- Discussion: link to neural howlround (2504.07992 in lit), prompt-shaped reasoning, RepuNet/GOVSIM contrast
- Limitations (use checklist: single seed, reconstructed gossip, small model)

### Week 3: Polish & Submit
- Polish figures (consistent styling, labels, captions)
- Final limitations statement
- Submit to target venue

---

## Key References from Literature (Already in assets/literature/)

| Paper | Relevance to Paper 1 |
|-------|---------------------|
| **RepuNet (2505.05029)** | Canonical reputation system for LLM MAS — assumes reputation *helps* cooperation. Your finding contradicts. |
| **GOVSIM (2404.16698)** | Shows communication critical for cooperation; universalization reasoning helps. Your finding: gossip (a form of communication) *hurts*. |
| **Neural Howlround (2504.07992)** | Inference failure mode: self-reinforcing salience loops. Explains *why* LLM agents don't repair — "locked in" reasoning patterns. |
| **Warnakulasuriya et al. (2504.19487)** | Boyd & Richerson punishment strategies in LLM agents. Shows explicit punishment drives norms. Your setting: gossip replaces punishment. |
| **Ren et al. (2311.03220 / 2504.19487)** | Social norms in generative agents. Your "limited/mixed norm emergence" verdict extends this. |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-01 | Select Direction 1 (Reputation Backfires) as Paper 1 | Highest novelty, lowest writing effort, strongest venue fit, highest citation potential, cleanest story |
| 2026-08-01 | Reserve Direction 2 (Democratic Adaptation) for Paper 2 | Strong but needs more "punch"; better as follow-up |
| 2026-08-01 | Exclude SI vs SFI causal comparison | Checklist B2 = unsupported; perfect collinearity with group |
| 2026-08-01 | Use baseline studies as boundary condition contrast (not core evidence) | Baseline shows reputation *helps* in shock-free + free-choice settings; your run shows opposite under climate risk + forced institutions |

---

**Status:** Decision documented. Ready to proceed with Paper 1 outline and connections graph.
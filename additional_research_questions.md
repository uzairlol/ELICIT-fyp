# Additional Research Questions & Investigative Threads (v2)

> All questions go beyond your existing task list.
> Gossip surface-questions removed and replaced with sharper mechanistic ones.
> Economics section expanded generously.
> Data hooks noted for Cursor.

---

## 🧠 Theory of Mind — Deep Cuts

### 1. Is the ToM module detecting hypocrisy, or is it punishing visibility?

The mechanism is framed as "hypocrisy detection" — it compares stated intent against observed contribution. But there's a confound: agents who contribute large *absolute* amounts are also the most visible, and a small LLM asked to score "trustworthiness" may conflate wealth-signaling with reliability. The result could be that *high contributors are disproportionately targeted* not because they are hypocritical but because the model's attention is drawn to them.

**What to actually measure:**  
- Within each round, regress the outgoing ToM score agent *i* gives to agent *j* on three separate predictors: (a) *j*'s `prop_of_wealth`, (b) *j*'s absolute contribution, and (c) *j*'s deviation from the SI/SFI group mean contribution. Which predictor has the largest coefficient?  
- Cross-tabulate: do agents who are in the **top quartile of absolute contribution** in a given round receive lower mean incoming ToM scores than agents in the top quartile of *proportional* contribution? If the absolute-top and proportional-top disagree in direction, that tells you what the model is actually reacting to.  
- Check whether the deviation of *j*'s contribution from the prior round's average (which agents are shown in their prompt) predicts ToM score more strongly than deviation from the same-round average (which agents can't see until after decisions). This would reveal whether the model is scoring against what the judge had information about or against some internal prior.

**Data:** `reputation_gossip_panel.csv` + `contributions.csv` joined on `(agent_id, round_number)`.

---

### 2. ToM score distribution — what shape is it, and what does that reveal about the model?

The project memory notes "ToM scores often discrete/extreme (many 1s/5s)" — this is a significant statement about how a small instruction-tuned model operationalizes a continuous evaluation scale. If scores cluster at 1 and 5 (out of 10) rather than being smoothly distributed, the ToM mechanism is effectively a binary classifier with two output bins, not a continuous reputation signal.

**What to actually measure:**  
- Plot the full empirical frequency distribution of outgoing ToM scores across all rounds and all agent pairs. Is it bimodal with peaks at 1 and 5? Is 10 ever used? Is there a different pattern for SI→SFI vs SFI→SI vs within-group judgments?  
- Compute the entropy of the score distribution per round. Does entropy increase over time (more nuanced judgments as context builds) or decrease (model locks into heuristics)?  
- For the same (scorer, scored) pair across consecutive rounds, what is the score autocorrelation? If it's near 1.0, the model has locked in a first impression and is not updating on new contribution data — which means reputation is path-dependent on early behavior, not a live signal.  
- Does the distribution shape differ by institution? Does an SI agent scoring an SFI agent use a different range than an SFI agent scoring another SFI agent?

**Why this matters for the paper:** if ToM scores are effectively binary, the "continuous reputation" framing is overstated, and the gossip mechanism (which filters on score ≤7) may be nearly always triggered, making it ambient noise rather than targeted social pressure.

---

### 3. ToM score asymmetry between groups — is there systematic cross-group bias?

In the real world, in-group favoritism is one of the most robust findings in social psychology. The question is whether a small LLM exhibits this when embodying agents with different group identities.

**What to actually measure:**  
- Compute four mean ToM score buckets: (SI→SI), (SI→SFI), (SFI→SI), (SFI→SFI). Present as a 2×2 table. Is the diagonal higher than the off-diagonal?  
- More specifically: conditional on the *scored agent*'s proportional contribution being the same, do same-group scores differ from cross-group scores? This is the cleanest test for in-group bias net of contribution differences.  
- Does this pattern persist after controlling for wealth differences? SI agents are much wealthier — if the model conflates wealth with trustworthiness, that alone could produce asymmetry.

**Data:** Reconstruct the 26×26 score matrix per round from `tom_scores` field in the round data. Aggregate across rounds.

---

### 4. First-impression lock-in — do early ToM scores predict late reputation, independent of later behavior?

Round 1 has empty `tom_scores` for all agents. The first non-trivial ToM run is Round 2. Whatever scores emerge in Round 2 are formed without any feedback loop — they're pure reactions to Round 1 contribution. If those Round 2 scores strongly predict each agent's *average* reputation across all 30 rounds (controlling for cumulative contribution trajectory), then reputation is dominated by first impressions, not ongoing behavior.

**What to actually measure:**  
- For each agent, take their mean incoming ToM score in R2 (first non-empty round) and correlate it with their mean reputation across R10–R30. Partial out their mean `prop_of_wealth` R2–R30 to isolate the pure "first impression" residual.  
- Look at specific agents: agent 1 (SFI, near-zero contributor) — do they maintain a consistently low reputation despite almost no change in behavior, suggesting a locked-in judgment?  
- Conversely, are there agents who contributed low in R1 but recover reputation by R15–R20? If reputation *can* recover, what does their R2–R6 contribution trajectory look like? This gives you evidence for whether the reputation mechanism is forgiving or sticky.

---

## 🗣️ Gossip — Sharper Questions

### 5. What is the effective information content of the reconstructed gossip bulletin?

The bulletin shows the top-5 lowest ToM scores ≤7.0. If most scores fall below 7.0 (which given the distribution in Q2 above is plausible), the bulletin is essentially a **random sample from the lower tail** rather than a focused indictment of the worst free-riders.

**What to actually measure:**  
- Per round, what fraction of all 26×25 = 650 possible pairwise ToM scores fall at or below 7.0? If >50%, the threshold is nearly uninformative.  
- Given that each agent sees a personalized bulletin of up to 5 entries, and some entries are about the agent themselves (`"YOU"`), what is the *expected number of unique agents* mentioned in a typical bulletin? If it's 5 different agents each round, the social pressure is maximally diffuse. If the same 2–3 agents appear repeatedly, pressure concentrates.  
- Cross-check: are the agents who appear most often in reconstructed bulletins (`gossip_bulletins_reconstructed.csv`) also the agents whose contribution *reasoning* never mentions reputation? If the most gossip-exposed agents are also the ones most detached from social accountability language, the mechanism is failing at precisely the agents it's meant to discipline.

---

### 6. Does the gossip bulletin create a social information market, or is it redundant with direct observation?

In Stage 2, SI agents already see each SI peer's contribution, deviation, and stage-1 payoff. They also get their own ToM score for that peer. So for SI agents punishing other SI agents, the gossip bulletin's information is largely *redundant* — they can already see who didn't contribute.

**What to actually measure:**  
- For SI agents at Stage 2, compare the ToM score they gave a peer (which is in the gossip bulletin) against that peer's observed contribution deviation. How often does a low ToM score (≤7.0, hence gossip-included) correspond to a *positive* contribution deviation (the scored agent actually contributed above average)? If these cases exist, the gossip bulletin is spreading *socially inaccurate* information — flagging cooperators as untrustworthy.  
- For SFI agents at Stage 1 (who have no Stage-2 visibility into SI peers), the gossip bulletin is their *only* social information about SI peers. Scan the contribution reasoning of SFI agents in rounds following a round where SI agents appeared in their gossip bulletin. Is there any language referencing the behavior of SI peers, suggesting cross-institutional learning?

---

### 7. Is the gossip bulletin a disciplining device or a punishment amplifier for already-targeted agents?

The existing analysis shows that gossip-targeted agents have *high* mean prop at the time of targeting (≈0.52), which falls afterward. This could mean gossip is not disciplining free-riders but piling on visible cooperators. Probe this more sharply.

**What to actually measure:**  
- Rank all agents in each round by their `prop_of_wealth`. For those who appear in the gossip bulletin in that round, what is their mean rank? If gossip targets are concentrated in the *top half* of the contribution distribution, the mechanism is inverting its intended function — naming cooperators as untrustworthy.  
- Separate the gossip cases into (a) genuinely low contributors targeted (prop below median), (b) high contributors targeted. What fraction of all gossip events falls into each category? Does this fraction change across rounds (does the model "learn" to target low contributors more accurately as context builds)?  
- For the agents who are never in gossip bulletins (agents 13, 17, 19, 20 from the strategy profiles) — are these agents flying under the radar by contributing modestly-but-consistently, or are they simply never scored low? Pull their incoming ToM score distributions and compare to gossip-heavy agents.

---

## 💸 Contributions — Deeper Behavioral Economics

### 8. Gini coefficient of contributions over time — is contribution inequality converging or diverging?

The simulation stores `gini_wealth` at the round level, but there is no Gini computed over contributions directly. This is a gap: wealth Gini measures asset inequality, but contribution Gini measures *effort* inequality — they can move in opposite directions. As wealth diverges (rich get richer from public good returns), effort could converge (everyone gives 25–30% of wealth). Or both could diverge if the bursty SFI agents drive variance up.

**What to actually measure:**  
- Compute within-round Gini of `contribution` (absolute) and separately of `prop_of_wealth` for every round. Plot both series over 30 rounds with vertical lines at shock rounds and democracy rounds.  
- **Fehr–Schmidt test:** In the behavioral economics literature, agents with inequity aversion disutility reduce contribution when contribution inequality is high (they don't want to be the sucker). Test this: do rounds with high contribution Gini (measured in round *t*) predict a lower mean prop in round *t+1* for the agents who were above the mean in round *t* (i.e., the potential "suckers")? Look for this specifically in reasoning blocks — do agents in high-inequality rounds use language about fairness or others not pulling their weight?  
- Compare the evolution of contribution Gini to wealth Gini. If wealth Gini is increasing while contribution Gini is stable or decreasing, that's evidence that the proportional metric is doing its equalization job. If both are increasing, the system is stratifying on both dimensions.

**Data:** `contributions.csv` + `round_agent_state.csv` for wealth.

---

### 9. The "free ride then burst" pattern — is SFI bursty contribution strategically timed?

The strategy profiles show a clear archetype: agents 7, 4, 12, 15 have non-trivial zero-share (17–30%) combined with high mean prop. Their average is inflated by a small number of very large contributions. The question is whether those bursts are random noise or strategically timed.

**What to actually measure:**  
- For each "bursty" SFI agent, list every round where their contribution is more than 1.5 standard deviations above their own 30-round mean. What events occur in that round or the round immediately preceding? Specifically: (a) did they receive an LDF payout in the prior round? (b) did they appear in a gossip bulletin in the prior round? (c) is it a democracy round? (d) did they receive a positive reputation score uplift?  
- If (a) correlates most strongly — i.e., they burst-contribute shortly after receiving payouts — that is consistent with **conditional reciprocity**: contributing back to a system that just paid out to them. Pull the reasoning blocks from those specific agent-rounds and look for language about gratitude, fairness, or returning value.  
- If (c) correlates most strongly — they burst specifically in or around democracy rounds — that is consistent with **strategic visibility**: contributing when their behavior is being evaluated and voted on. This is a form of audience-sensitive cooperation.

---

### 10. LDF payout as a contribution inducer — does receiving a payout increase next-round contribution?

This is a test of reciprocity, one of the most fundamental mechanisms in behavioral economics. The question is whether developing agents treat the LDF as a mutual-aid pool they feel obligation to replenish after benefiting from it, or whether they treat it purely as an entitlement.

**What to actually measure:**  
- For each developing (SFI) agent in each round *t* where `ldf_payout_round > 0`, compute their `prop_of_wealth` in round *t+1* minus their mean `prop_of_wealth` over the 3 rounds preceding *t*. This is a within-agent "payout effect."  
- Separate these cases by payout amount — does a larger payout produce a larger next-round contribution uplift? If there's a dose-response relationship, that's evidence of proportional reciprocity.  
- Now do the converse: in rounds where a developing agent received *zero* payout despite having taken climate damage (i.e., the fund was insufficient or they were covered by another agent's payout), do they *reduce* contribution in the next round? If zero payout with damage causes defection, that's evidence of frustrated reciprocity or abandonment of the commons.  
- Pull reasoning blocks from the round *after* a large payout and scan for language about "received," "contributed back," "fair," "my turn." This lets you connect the behavioral pattern to stated motivation.

**Data:** `redistribution.csv` joined with `contributions.csv` on `(agent_id, round_number+1)`.

---

### 11. Wealth floor approach and contribution fatigue — liquidity constraints in action

The wealth floor is 0. With climate damage, SI punishment reception, and Stage-1 contributions all drawing from the same wealth stock, some agents may be pushed toward zero. At that point, their contribution cap (`max(0, floor(wealth))`) hits zero — they are *forced* to contribute nothing regardless of willingness.

**What to actually measure:**  
- Identify all agent-rounds where end-of-round `wealth` is below a threshold (say, ≤ 5% of that agent's initial endowment, or an absolute threshold like ≤ 1000). Call these "liquidity-constrained" rounds.  
- For the 5 rounds leading up to the first liquidity-constrained round for each agent, trace their `prop_of_wealth` — is there a gradual decline (strategic drawdown), a sudden fall (shock-triggered), or was it already volatile?  
- For rounds *after* recovery (wealth returns above the threshold), do agents return to their pre-constraint contribution level, or do they permanently shift lower? This maps to **path dependence in cooperative behavior** — a shock-induced participation gap can permanently change strategy.  
- Cross-check: in the liquidity-constrained rounds, what is the reasoning text? Do agents *acknowledge* that they cannot contribute (budget-excuse framing) or do they give a separate narrative that doesn't reference wealth limits? The latter would be interesting — the model generating cooperative language while the underlying engine clips their contribution to zero.

---

### 12. The R2 spike — the largest single-round jump in the entire dataset, completely unexplained

Mean prop goes from 0.231 in R1 to 0.445 in R2 for all agents combined. For SFI agents specifically, the R1 mean prop is 0.022 with 71.4% zeros — then in R2 it jumps dramatically. This is the single most striking discontinuity in the data.

**What to actually measure:**  
- Pull the reasoning blocks for *all 26 agents* in R2. What is the dominant theme? Is it ToM-related (first reputation scores just arrived), gossip-related (first bulletin just dropped), response to R1 peer behavior (they can see what others contributed in R1), or something else entirely?  
- Identify which agents drove the spike: for each agent, compare R1 vs R2 prop. Which agents more than doubled? Which agents were already high? Which were still at zero?  
- Check the prompt structure for R1 vs R2: in R1, agents have no peer history. In R2, they see R1 contributions from their institutional peers. Is the R2 spike consistent with **conditional cooperation** — agents updating toward what they observed in R1? If the SFI agents who had high R1 contributions are the same ones driving the R2 burst for others, that's strong evidence for conditional cooperation.  
- The alternative explanation is **prompt cold-start artifact**: R1 agents have minimal context and may contribute zero simply because the model without prior context defaults to caution. R2 unlocks richer context. This would be a model-behavioral finding, not a cooperation finding.

---

## 🏛️ Democracy — Unexplored Dimensions

### 13. Who votes *against* proposals that win — and do they change behavior after losing?

The existing analysis covers who *proposes*, and notes that same-group voting rate is ~0.51 (near base rate). But it doesn't look at the losing minority and their post-vote behavior.

**What to actually measure:**  
- For each adopted proposal, identify the dissenting voters. What is their mean `prop_of_wealth` in the 3 rounds after adoption, compared to the 3 rounds before? Is the losing coalition's behavior different from the winning coalition's?  
- Specifically for the punishment-weakening proposals that failed (R20, R25): who voted *for* them (wanted weaker punishment)? Are those the same agents who subsequently have low Stage-2 enforcement spending? This would reveal whether "vote for weaker rules, spend less on enforcement" is a coherent behavioral strategy.  
- For the LDF equity proposals that won (R10, R25): SI agents voted on rules that primarily benefit SFI/developing agents. Did SI agents who voted against the LDF equity increases subsequently *reduce* their LDF contribution (which is the same as their Stage-1 contribution, so it's visible) in the next rounds? Would suggest genuine opposition versus formal compliance.

**Data:** `votes_parsed.csv` joined with `contributions.csv` and `enforcement_burden_by_agent.csv`.

---

### 14. The missing 23 proposals — what happened to the agents who didn't propose?

26 agents participate in 6 democracy rounds = 156 possible proposal opportunities. Only 14 proposals surface. What happened to the other 142?

**What to actually measure:**  
- For each democracy round, check `parsing_failures` in the agent actions for each agent. How many failures are democracy-round-specific? Break down by: (a) parser could not extract a valid proposal format, (b) proposal was outside the whitelist, (c) agent produced no proposal (empty).  
- In the reasoning blocks from democracy rounds, are there agents who *discuss* what they might propose but produce no recorded proposal? This would be the LLM "thinking out loud" about reform but failing to format it — a different failure mode from genuine indifference.  
- Is there a selection effect: do the agents whose proposals surface have systematically *shorter* or *simpler* proposal text? If so, the agenda is being set by the agents who write the most parseable responses, not the ones with the most substantive positions.  
- Frame this for the paper: **the democratic agenda in this simulation is shaped partly by LLM capability variation**, not purely by strategic choice. This is a finding about the method, not just a limitation.

---

### 15. The ratchet hypothesis — does institutional change only move in one direction?

Adopted rules show subsidy fraction rising (0.2→0.3→0.4→0.6), LDF equity rising, punishment effect never strengthened. Is this a one-way ratchet?

**What to actually measure:**  
- Systematically code each adopted rule change as: (a) increases enforcement intensity, (b) decreases enforcement intensity, (c) increases redistribution to contributors, (d) increases redistribution to damage-exposed agents, (e) changes coverage/access. The current adopted path is all (c) and (d) — zero (a). Is this robust?  
- Now look at the *failed* proposals the same way. Failed proposals include punishment weakening (category b) and LDF coverage expansion (category d). Nothing proposed *stronger* punishment or lower subsidy. This suggests the *proposal generation* is itself ratcheted — the model doesn't generate proposals for tighter enforcement even when invited to.  
- **Status quo bias test:** Once a parameter is changed (e.g., SUBSIDY_FRACTION = 0.4 at R15), does any subsequent proposal attempt to *reduce* it? Code the proposal targets against the parameter values at the time of proposal. If all proposals are ≥ current value, that's strong evidence of a one-directional ratchet.  
- **Implication:** In a real governance system, this would raise a question about agenda agenda formation. Who benefits from never proposing stricter rules? The near-zero contributors (agents 1, 11, 17, 19) are the ones who would be most punished by stricter enforcement — yet they also rarely propose anything. The high contributors (3, 15, 20) who *do* propose seem to propose reward increases rather than contribution mandates. Frame this as a finding about who benefits from the governance equilibrium.

---

## 🌦️ Climate Shocks — Unexplored Dimensions

### 16. Individual shock absorption heterogeneity — who consistently absorbs and who defects?

The event study shows aggregate patterns, but those averages hide what could be a clean division between "shock absorbers" (agents who reliably increase contribution under stress) and "shock defectors."

**What to actually measure:**  
- For each agent, compute their within-agent Δ prop for R5 (post−pre) and for R10 (post−pre) separately. Create a 2×2 classification: R5-up/R5-down × R10-up/R10-down. How many agents are consistently up on both? Consistently down on both? This gives you the empirical base for claiming whether "shock response" is a stable agent trait or situational.  
- For consistently-up agents: pull their reasoning blocks from R5 and R10 and look for language about collective obligation, emergency response, or vulnerability of others. For consistently-down agents: look for language about self-preservation, capacity constraints, or skepticism about fund adequacy.  
- Cross this with institution: given that SI showed net decline post-R5 but net increase post-R10, are the same SI individuals who declined after R5 also the ones who increased after R10? Or is R5 vs R10 a different population of movers? This would tell you whether shock response is agent-stable or event-specific.  
- R5 is severity 0.1, R10 is severity 0.2. If the same agents respond oppositely to different severities, that could suggest a **severity threshold** below which agents use the shock as justification to free-ride (small shock, fund can handle it) and above which they treat it as a genuine emergency. Pull the reasoning blocks and look for "small/minor" language at R5 vs "serious/severe" at R10.

---

### 17. The information asymmetry puzzle — how do agents calibrate LDF contributions without seeing the fund balance?

Agents know their own damage and their own payout but not the pool balance or what others are contributing in real time. This creates a genuine **decision under uncertainty** that maps directly to real-world climate finance negotiations, where donor countries don't have perfect visibility into total fund commitments.

**What to actually measure:**  
- Scan all agent reasoning blocks from Stage-1 contribution decisions for language about the fund: "pool," "fund," "sufficient," "covered," "enough," "remaining." Count occurrences. Do agents reason about fund adequacy at all, or do they make decisions purely on local information (own damage/payout/wealth)?  
- Specifically: after R5 (a shock round with moderate damage), do agents' R6 contribution reasons reference anything about whether the fund was adequate? They received `ldf_payout_round` in R5 — if the payout was less than their damage, they experienced *undercoverage* which is implicit evidence that the fund was strained. Do they update their contribution strategy based on this implicit signal?  
- Compare agents with high `ldf_payout_round / climate_damage_taken_round` ratios (well-covered) vs those with low ratios (undercovered) in their next-round contribution reasoning. Does undercoverage experience produce any observable language about increasing contributions to make the fund more robust?

---

### 18. Vulnerability heterogeneity among developing agents — does higher vulnerability create more insurance-seeking behavior?

`vulnerability` varies across developing (SFI) agents, and the damage formula is `CLIMATE_DAMAGE_BASE * severity * vulnerability`. More vulnerable agents take larger hits from shocks, so they have more to gain from a well-funded LDF. The question is whether they internalize this and contribute more.

**What to actually measure:**  
- Rank developing agents by vulnerability. Do the top-3 most vulnerable developing agents have higher mean `prop_of_wealth` than the bottom-3? This tests whether vulnerability creates insurance-demand that translates into contribution effort.  
- More specifically: compute the *correlation* between an agent's `vulnerability` and their `prop_of_wealth` across all developing agents (n=14). If it's positive, higher-vulnerability agents behave as insurance purchasers. If it's zero or negative, vulnerability doesn't drive contribution (perhaps because agents don't believe the fund will actually pay out, or because low-vulnerability agents have more to contribute proportionally).  
- After a shock round, do the *most damaged* developing agents contribute more in the following round (reciprocity) or less (liquidity constraint)? These are competing hypotheses. Both are plausible. The reasoning blocks from the round after a large personal damage event will reveal which framing agents use.

---

## 📐 Mathematical Model — Economic Analysis

### 19. Does MCPR actually get internalized in agent reasoning?

MCPR = m/n = 1.6 / group_size. For SI (12 agents), MCPR ≈ 0.133 — meaning each unit contributed returns 0.133 to self and costs 1. It is a net loss for a purely selfish agent. For SFI (14 agents), MCPR ≈ 0.114. This means rational self-interest predicts *zero* contribution in this setup, which makes any positive contribution a cooperative act requiring explanation beyond payoff maximization.

**What to actually measure:**  
- Scan contribution reasoning blocks for any reference to the multiplier, the group return, "efficiency," "ratio," or anything that suggests an agent is computing whether contribution is individually profitable. If no agent ever references MCPR, they are not doing payoff calculation — they are responding to something else (norms, reputation, identity, or prompt induction).  
- Check whether agents who contribute proportionally more are the ones who state rationales that sound more economically sophisticated vs those who frame decisions in purely social/moral terms. Is there a correlation between reasoning quality (measured by length or mention of economic concepts) and contribution level?  
- This matters for the paper because the theoretical benchmark is zero contribution (Nash equilibrium in this stage game), and any departure needs explanation. If agents aren't reasoning about MCPR, their cooperation must be explained by the social mechanisms, not individual payoff calculation.

---

### 20. The subsidy creates a non-linear, rank-order payoff surface — do any agents appear to optimize against it?

The subsidy goes to the top `SUBSIDY_TOP_N` (default 2) SI contributors by absolute contribution. This means there's a discrete jump in payoff at the contribution rank boundary: being rank 2 vs rank 3 is worth the entire subsidy amount. For wealth-rich SI agents, this could be meaningful.

**What to actually measure:**  
- For each SI democracy round, reconstruct the rank ordering of SI contributions and identify who sits at rank 2 vs rank 3. Is there bunching of contributions near the cutoff? Specifically: do agents who are rank 3 or 4 in round *t* increase contribution in round *t+1* by exactly enough to break into the top 2? This would be direct evidence of rank-gaming.  
- More broadly: do SI agents who *received* the subsidy in round *t* maintain or increase contribution in round *t+1* (subsidy reinforces high contribution), or does receiving the subsidy allow them to *reduce* contribution in *t+1* (harvest the reward then coast)? The latter would be a "subsidy creates moral licensing" finding.  
- Pull reasoning from agents who are in the top-2 rank in a given round. Do any of them mention the subsidy, reward for top contribution, or any rank-based awareness?  
- After `SUBSIDY_FRACTION` increases via democracy (from 0.3 to 0.4 to 0.6), does the absolute amount of SI punishment spending *increase* (more punishment tokens → larger pool → larger subsidy)? This would mean the subsidy parameter change actually creates a feedback loop that incentivizes more enforcement spending. Check `enforcement_burden_by_round.csv` against the timeline of subsidy fraction changes.

---

## 📊 Economics — Substantive Questions

### 21. Is the public goods game solved by conditional cooperation, norm internalization, or neither?

This is the central theoretical question. Three mechanisms can sustain contribution above zero in a public goods game:

1. **Conditional cooperation** (Fischbacher et al. 2001): agents contribute what they expect others to contribute. Testable: do SI agents' contributions correlate with the prior round's *mean SI contribution*? Run a panel regression: agent_i's `prop_of_wealth` in round *t* as a function of the *group mean prop* in round *t-1* (their own excluded). A positive coefficient is evidence for conditional cooperation.

2. **Norm internalization**: agents contribute because they believe it is right, independent of what others do. Testable: are there agents who contribute above the group mean consistently even as others defect? Look at agents 13, 16 (SI) — never zero, consistent prop — and pull their reasoning. Do they justify high contribution by reference to collective duty, or by reference to what others are doing?

3. **Strategic reputation building**: agents contribute to maintain ToM scores and avoid gossip. Testable: is there a positive correlation between round *t* contribution and round *t+1* incoming ToM score, net of group-level trends? If yes, contributing "buys" reputation, which then justifies continued strategic contribution.

**Data:** `si_sfi_prop_by_round.csv` + `reputation_gossip_panel.csv`. Run fixed-effects panel model.

---

### 22. Does repeated interaction generate endogenous enforcement — and is it efficient?

Ostrom's framework predicts that communities with repeated interaction develop monitoring and sanctioning norms endogenously. In this simulation, enforcement (Stage-2 punishment) is costly and available to SI agents. The question is whether enforcement spending patterns resemble anything like an endogenous enforcement equilibrium.

**What to actually measure:**  
- Compute the per-round enforcement efficiency: total punishment tokens spent by SI agents divided by the mean proportional contribution increase (if any) in round *t+1*. Is enforcement "working" — do punished agents contribute more the next round — and if so, what is the return per enforcement token spent? If punishment costs 1 token and produces a Δ contribution of 0.05 proportional, is that a good investment relative to just contributing directly?  
- Identify cases where an SI agent punishes a *consistently contributing* peer (a false positive). This is wasteful enforcement and harms system efficiency. How frequent are false-positive punishments? Does the rate decline over rounds (learning) or stay constant?  
- Check whether there are "enforcement-heavy" agents who consistently spend Stage-2 tokens and "enforcement-light" agents who never spend. Is there a volunteer's dilemma — does the existence of enforcement-heavy agents allow the enforcement-light ones to free-ride on enforcement? (The second collective action problem you mentioned in your original list.)  
- Specifically: among SI agents with similar `prop_of_wealth`, do some spend heavily on enforcement while others spend nothing? If the high-enforcement agents don't get compensated (net of subsidy), they are subsidizing enforcement for the group — the textbook second-order free-rider problem.

**Data:** `enforcement_burden_by_agent.csv` + `contributions.csv` + `payoffs.csv`.

---

### 23. Is there evidence of conditional cooperation breakdown — and can you identify the trigger?

In repeated public goods experiments, conditional cooperators who observe low contributions by others eventually defect (called "unraveling"). The question is whether any period in the 30-round run shows signs of cooperation unraveling: falling mean prop, rising zero-share, and reasoning that references disillusionment with peers.

**What to actually measure:**  
- Compute a simple "cooperation collapse index" per round: (fraction of agents with contribution below their own prior-round contribution) × (fraction with contribution = 0). This captures both the direction and extent of a collapse. Plot across all 30 rounds.  
- Look specifically at the post-R6 period (after SI zeroing at 41.7%) and the late rounds (R20–R30). Does SI contribution ever show a sustained decline lasting ≥3 consecutive rounds? If yes, pull reasoning blocks from those rounds and look for language about "others not contributing," "pointless," or "no one cooperates."  
- For SFI, the polarization signal is already there (mean deviation from peer mean increases over time). Does this polarization intensify after specific events (shocks, democracy rounds, gossip bulletins)? Identify the round where SFI polarization is maximum and pull reasoning from that round.

---

### 24. What is the real effective tax rate that SI agents face, and does it approach a tipping point?

SI agents simultaneously face: (a) Stage-1 contribution (reduces wealth), (b) Stage-2 punishment spending, (c) received punishment (further reduces), (d) climate damage. The total extraction as a fraction of wealth in a given round is the effective tax rate. If this rate gets high enough, SI agents would rationally expect to be better off in SFI — but they can't switch.

**What to actually measure:**  
- For each SI agent in each round, compute: `effective_tax = (contribution + punishment_spent + received_punishment + climate_damage_taken_round) / wealth_start_of_round`. Average this across agents and across rounds to get the SI effective rate.  
- Track this over time: does the effective rate increase as punishment parameters drift (punishment-weakening proposals failing = PUNISHMENT_EFFECT stays at 3) and subsidy fraction rises (returns some costs)? Is the trend favorable or unfavorable to SI agents from a pure self-interest standpoint?  
- Compare to SFI effective rate: `(contribution + climate_damage) / wealth`. If SFI's effective rate is systematically lower and they get LDF payouts on top, the forced-membership design is imposing asymmetric net costs on SI. Does this asymmetry appear in SI reasoning? Do SI agents ever express that the arrangement is unfair or that they are bearing disproportionate costs?

**Note:** this directly maps to the real-world debate about whether developed countries (who bear enforcement costs and contribute more absolutely) are being asked to shoulder an asymmetric burden in climate finance.

---

### 25. What is the LDF coverage ratio and does redistribution work as intended?

Your project note says "climate finance is often discussed as if collection automatically implies effective redistribution." Test this directly.

**What to actually measure:**  
- For each developing agent in each shock round, compute `coverage_ratio = ldf_payout_round / climate_damage_taken_round`. If coverage = 1.0, the agent is fully compensated. If <1.0, they bear residual loss. If 0.0, the fund failed them entirely.  
- Plot these individual coverage ratios across agents in R5 and R10 separately. Is coverage uniform (everyone gets similar fraction of damage covered), or is there high heterogeneity (some agents fully covered, others getting nothing)?  
- Now connect to the equity weight parameter. `LDF_EQUITY_WEIGHT` was set to 0.5 (R10 adoption) and then 0.7 (R25 adoption). Did coverage become *more* equal (more uniform distribution) after these equity weight increases? Compute within-round Gini of coverage ratios for R5, R10, R15, R25+. This is a direct empirical test of whether the democracy-adopted equity rules actually improved equity.  
- The punchline finding: even with a functioning fund, democratic rule-setting, and explicit equity parameters, does coverage remain heterogeneous? If yes, you have evidence that the "collection implies redistribution" assumption fails *even in a simulation with idealized mechanics*, let alone in messy real-world institutions.

**Data:** `redistribution.csv` + `climatic_shocks.csv`.

---

### 26. Net transfer accounting — who are the net payers and net receivers across the full 30 rounds?

Beyond round-by-round analysis, compute the full 30-round net transfer for each agent: all money received from the system (LDF payouts, public good share, rewards, subsidies) minus all money extracted (contributions, punishment tokens spent, punishment received, climate damage). This is the agent's net gain or loss from participation versus a counterfactual of no interaction.

**What to actually measure:**  
- Rank all 26 agents by cumulative net transfer. Who are the top net receivers and top net payers? Does the net payer list consist entirely of SI (developed) agents, or are there surprising developing agents who also end up as net payers?  
- For each near-zero contributor (agents 1, 11, 17, 19) — are they net receivers despite contributing almost nothing? What does this say about the redistributive design of the system? If near-zero contributors receive public good shares and LDF payouts while contributing minimally, the system is providing a high-return free-ride option, which is exactly the collective action problem the design is meant to solve.  
- Now compute the *counterfactual transfer*: if all agents had contributed 0, what would total public good payoffs be? (Zero, since the public good is funded by contributions.) How much did each agent's participation add to their total wealth versus this zero-contribution baseline? This is the individual return to cooperation — and if it's negative for high contributors (they gave more than they got back from the public good), cooperation is being sustained by something other than payoff.

---

### 27. Is there a "warm glow" signal hiding in zero-contribution rounds with cooperative language?

54 instances of cooperative language paired with zero contribution have been flagged. Behavioral economics identifies "warm glow" as the utility from *intending* to give, independent of actual giving. If agents express cooperative intent while contributing zero, they may be extracting the warm glow without paying the cost.

**What to actually measure:**  
- For the 54 flagged cases, what is the *length* of the cooperative reasoning text? If agents who contribute zero write longer, more elaborate cooperative justifications than agents who actually contribute, that's a warm-glow signal — the verbal expression substitutes for the act.  
- Cluster the cooperative-language/zero-contribution cases by agent. Are the same agents responsible for most of these cases? The near-zero specialists (1, 11, 17, 19) are the prime candidates. If agent 1 (prop ≈ 0.002, nearly always near-zero) produces frequent cooperative language, the language is completely decoupled from behavior — this is expressive cooperation without instrumental cooperation.  
- Track whether this decoupling intensifies over rounds. If agents who cooperate verbally but not behaviorally are never sanctioned (because gossip targets high contributors, not low ones, as per Q7 above), then the system has no mechanism to discipline expressive-but-not-behavioral cooperation. That's a fundamental design flaw worth naming explicitly.

---

### 28. Do sanctions create chilling effects on contribution beyond the sanctioned agent?

When an SI agent is publicly punished (punishment is visible to peers in Stage-2 feedback), does this create a *deterrence externality* — do the *unsanctioned* SI peers reduce their contribution in the next round as if anticipating punishment themselves? Or does witnessing sanctions on others produce a *warm glow of justice* — increasing peer contributions because the commons are being enforced?

**What to actually measure:**  
- Identify rounds where agent *i* in SI receives a non-zero punishment. For every *other* SI agent *j* in the same round, compute their Δ prop in round *t+1*. Compare this distribution to Δ prop in rounds where no SI peer was punished. Is the mean Δ higher (punishment reassures cooperators) or lower (punishment scares contributors)?  
- Look specifically at whether the agents who *administered* the punishment in round *t* adjust their own contribution in round *t+1*. If they contribute more (I punished the free-rider, now I can cooperate freely) that's consistent with a "cleaning up the commons" effect. If they contribute less (punishment is exhausting), that's consistent with enforcement fatigue.  
- Pull reasoning from SI agents in rounds immediately following a visible punishment of a peer. Are there references to the punishment, the sanctioned agent's behavior, or any reflection on what the punishment means for the group's cooperation? Or does the punishment leave no trace in the subsequent round's reasoning?

---

### 29. Can you find evidence of social preferences (beyond narrow self-interest) in the payoff data?

Social preference models (Charness-Rabin, Fehr-Schmidt) predict that agents may sacrifice own payoff to increase others' payoff (positive social preferences) or to reduce inequity. The payoff data allows a direct test.

**What to actually measure:**  
- For each SI agent in each round, compare `stage1_payoff` with the maximum possible payoff they could have achieved by contributing zero (which would be `mC_{-i}/n` where *C_-i* is others' total — agents don't know this but we do as analysts). The gap between actual payoff and maximum-if-defected payoff is the *cost of cooperation*. Agents who consistently pay this cost despite receiving below-average total payoffs are exhibiting positive social preferences.  
- Identify agents with negative cumulative payoff over the full run. If any agents end the simulation with a cumulative payoff worse than their starting wealth — meaning they are net losers from participation — and they continued to contribute throughout, that's strong evidence of social preferences overriding self-interest. Check `payoffs.csv` cumulative columns.  
- Now compare the reasoning of these "net-loss cooperators" against the near-zero specialists who are almost certainly net gainers. Do the net-loss cooperators use more norm-based or identity-based language ("I believe in this," "it's the right thing"), while net-gainers use more self-referential language? This would map cleanly to the distinction between normative and strategic cooperation in the literature.

---

### 30. Redistribution from collection vs redistribution from punishment — which mechanism dominates?

There are *two* redistribution streams in this simulation: (a) the LDF, which collects contributions from all agents and pays out to developing agents after shocks, and (b) the subsidy, which collects punishment tokens from SI enforcers and redistributes to top SI contributors. These are distinct in who they help and why.

**What to actually measure:**  
- For each round, compute the total amount redistributed via LDF payouts vs the total amount redistributed via subsidy. Which is larger in magnitude across the run? Does the answer differ before vs after the democracy sessions that raised `SUBSIDY_FRACTION` (from 0.2 initially to 0.6 by R30)?  
- Compute who benefits from each stream: LDF redistribution goes to developing (SFI) agents by design. Subsidy goes to top SI contributors (developed agents). If the subsidy is growing via democracy and the LDF is being shaped by equity parameters also via democracy, the two redistributive systems are being pulled in opposite directions by different political coalitions (SFI agents shape LDF; high-prop SI agents benefit from subsidy). Quantify the total flow in each direction and compare.  
- Does the **net wealth gap** between developed and developing agents narrow or widen over 30 rounds? Compute `(mean SI wealth - mean SFI wealth)` per round and plot. Given that SI agents have massive initial wealth advantages, even proportional equal contributions leave SI ahead. Does the LDF payout mechanism actually shrink this gap, or does it merely slow the widening?  
- Frame: the real-world debate is whether the LDF can close the climate finance gap. Your simulation gives you a direct (if stylized) empirical answer on this mechanism in action.

---

### 31. Is cooperation stability a convergence phenomenon or a survival-of-the-persistent phenomenon?

Two radically different things could produce "stable cooperation" in the data:

1. **Convergence**: free-riders are disciplined by enforcement/reputation until they raise contributions, and cooperation becomes normal for most agents.  
2. **Survivor persistence**: low contributors are never effectively disciplined (because enforcement is imperfect and gossip targets the wrong agents), so cooperation is sustained entirely by a core of persistently cooperative agents who never quit, while free-riders continue to free-ride indefinitely.

**What to actually measure:**  
- Classify each agent as: (a) persistently cooperative (mean prop >0.25, zero-share <10%), (b) recovered defectors (started low/zero, raised over time), (c) persistent defectors (mean prop <0.10, zero-share >30%), (d) volatile (high variance, frequent switching). Then check: in rounds 20–30, are persistent defectors (like agents 1, 11, 17, 19) still defecting at the same rate? If yes, the system has not converted them — it has simply coexisted with them.  
- Compute what the cooperation rate would be if you removed the persistent defectors from the sample. Is "cooperation" primarily a statement about the persistently cooperative majority, not about system-wide norm convergence?  
- This matters enormously for the Ostrom framing: Ostrom's "governing the commons" describes communities that successfully *convert* or *exclude* defectors. In a simulation with forced membership (no exclusion) and imperfect enforcement (no conversion), the comparison to Ostrom may be partial at best.

---

### 32. What is the marginal value of the LDF relative to the public goods game — do developing agents benefit more from the LDF or from the PG?

Developing (SFI) agents contribute to the public good and receive a share of the multiplied pool. They also contribute (same amount) to the LDF and receive payouts after shocks. These are two benefits from one cost (Stage-1 contribution is dual-use).

**What to actually measure:**  
- For each developing agent, compute across all shock rounds: `ldf_payout_round` (LDF benefit) and `stage1_payoff` (PG benefit, which is the share minus contribution — but since contribution counts for both, it's the PG share received minus what they gave, net of LDF). Which is larger on average?  
- More precisely: for developing agents, `pi_1 = (m * SFI_total / n_SFI) - c_i`. Meanwhile the LDF provides `payout_i`. If `payout_i > stage1_payoff`, the LDF is more valuable to them than the public good itself. Under those conditions, their motivation for participating in the public goods game may be *primarily* driven by LDF access, not PG returns — especially since MCPR <1 means PG returns are individually negative.  
- This reframes the incentive problem entirely: if developing agents are net losers on the PG stage (MCPR means they give more than they get back individually) but net gainers from LDF, then the LDF is what sustains their participation, not the PG. This is a finding about the architecture of incentives in climate finance mechanisms.

---

## 🔬 Methodological / Model Validity

### 33. Prompt echo vs emergent language — what is the model actually generating?

The model receives a prompt with specific vocabulary: "cooperation," "free-riding," "LDF," "trust," "fairness." If the reasoning blocks primarily repeat this vocabulary without adding novel framing, the reasoning is an echo of the prompt, not emergent cognition.

**What to actually measure:**  
- Extract the unique vocabulary in the prompt template (from `prompt_utils.py` and `prompt_generator.py`). Compare to the vocabulary in reasoning blocks using term frequency. Calculate what fraction of the top-50 most frequent reasoning tokens were seeded by the prompt. A high fraction (>70%) suggests echo; a low fraction suggests genuine language generation.  
- Look for concepts that appear in reasoning that are *not* in the prompt. Examples might be: explicit game-theoretic reasoning ("if I contribute less, others will too"), historical analogies (real-world references), or novel moral frameworks. Every such instance is evidence of the model doing something beyond prompt recall.  
- Compare vocabulary between SI and SFI reasoning blocks. If they are statistically indistinguishable (same top tokens, same framing), the forced institution assignment produced no differentiation in how agents think about their situation — which would mean the institutional design has no cognitive effect, only a mechanical effect on payoffs.

---

### 34. Within-agent strategy drift — is agent behavior a stable "type" or is it noise around a mean?

The existing profiles summarize agent behavior over 30 rounds. But the question is whether those summaries describe a stable strategy or a mean of a random walk.

**What to actually measure:**  
- Compute the **within-agent standard deviation** of `prop_of_wealth` over 30 rounds for each agent. Agents with high mean AND high std are "bursty" (7, 4, 15). Agents with low std (relative to mean) are genuinely stable. Plot a 2D scatter of (mean prop, std prop) with agent labels — this reveals who is reliably cooperative vs who is nominally cooperative but actually volatile.  
- For each agent, compute the Hurst exponent of their `prop_of_wealth` time series (a measure of persistence: >0.5 = trending, =0.5 = random walk, <0.5 = mean-reverting). If most agents have Hurst ≈ 0.5, contributions are essentially a random walk and there is no stable strategy. If Hurst > 0.5, agents have momentum in their contributions (once they start high, they stay high).  
- This matters for the norm emergence claim: a system of random walks around group means looks like "stable cooperation" in aggregate even though no individual agent has a stable cooperative strategy. You need to distinguish these cases.

---

### 35. Seed robustness — which specific results are most fragile?

The run is seed 1. There is no way to definitively know which results would replicate under different seeds without running more experiments — but you can *reason* about which findings are most seed-sensitive.

**What to actually measure:**  
- Rank findings by their dependence on specific agents' behavior. Any finding driven by a single extreme agent (agents 9, 15 in SFI with extreme post-gossip drops) is maximally fragile. Any finding that appears in 20+ of the 26 agents is robust to seed. Create an explicit table of findings sorted by how many agents they depend on.  
- Specifically: the R2 spike (Q12 above), the post-R5 SI zeroing, and the "gossip targets high contributors" result all depend on the specific behavior of specific agents. Quantify how much each result would change if you removed the single most influential agent.  
- Frame this constructively for the paper: single-seed simulations with LLM agents are fundamentally different from single-seed simulations with deterministic agents — LLM stochasticity means even same-seed runs may not be bit-for-bit reproducible (temperature-based sampling). Acknowledge this explicitly and argue for what statistical reliability single runs can and cannot provide.

---

*Prepared based on full audit of existing docs in `docs/raw documentation/20260731/` as of 2026-07-31.*
*v2: Gossip surface questions replaced with mechanistic ones (§Gossip). All sections deepened. Economics section expanded (§21–32).*

# 13 — Reasoning–Action Consistency (20260731)

**Opening claim.** Agents often talk about cooperation, peers, or credibility while choosing actions that do not match a plain reading of that talk — especially **cooperative/peer language paired with zero contribution**, and **free-ride language paired with positive contribution**. The mismatch is a finding about the LLM decision surface, not proof of human-style hypocrisy.

Flags: `tables/reasoning_action_flags.csv` (73 flagged rows in Prompt 4 summary).

---

## Quantitative backbone

| Pattern | How flagged | Role in pack |
|---------|-------------|--------------|
| `cooperative_language_zero_contrib` | 54 rows (39 SFI, 15 SI) | Language–action decoupling / warm-glow *candidate* |
| `free_ride_language_positive_contrib` | present in flags | Talk of free-riding while still paying |
| Reputation-after-gossip | rare | Explicit image management |

Theme rates on *all* zeros (doc 31): MCPR language 62%, free-ride 44%, coop lexicon only 7% — so many “cooperative_language_zero” flags are broad contribution-decision talk, not warm praise of cooperation.

---

## Raw discourse — mismatches

### Zero action + peer/contribution narration

**Agent 0, SFI, R3** (`RB-03-A0-contribution`):

> Given high peer contributions and no significant marginal return to me per unit contributed, I choose not to contribute.

The sentence acknowledges high peer contributions *and* selects free-riding — consistent with conditional *defection*, inconsistent with “match the cooperators.”

**Agent 0, SFI, R5:**

> Given high contributions from SI members, I choose to free ride and contribute nothing.

### Zero action + MCPR optimality (SI R6 bloc)

**Agent 2, SI, R6:** “I choose to contribute nothing to maximize my payoff.”  
**Agent 14, SI, R6:** “it is optimal for my payoff to contribute nothing.”

Here language and action **match** (selfish zero). Consistency is high; cooperation is absent.

### Positive action + free-ride vocabulary

**Agent 2, SI, R20** (`RB-20-A2-contribution`):

> I'll contribute a moderate amount to avoid free-riding and maintain credibility, based on my institution's typical strategy and high MCPR.

**Agent 5, SI, R20:**

> I'll contribute a moderate amount to avoid free-riding and maintain credibility…

Action is positive; the word “free-riding” is something to *avoid*, so this is consistent anti-free-ride framing — still template-heavy.

### Reputation minimum giving

**Agent 4, SFI, R26:**

> Maximize personal payoff by contributing at the minimum level to avoid free-rider reputation while being consistent with previous actions.

Language admits payoff max subject to a reputation floor — a coherent (if thin) strategic story.

[Evidence: `tables/reasoning_action_flags.csv` | run=20260731_013853 | round=3,5,6,20,26 | agent=0,2,4,5,14 | record=excerpt]

---

## Counterexamples

Many SI punishment blocks are **consistent**: “Punishing free-riders and rewarding cooperative agents…” paired with Stage-2 assignments (doc 17). Contribution-stage inconsistency is the sharper problem for norm claims.

---

## Limits

Flag regexes over-include. Short texts limit nuance. Confidence medium that decoupling is real; low that it equals warm-glow utility.

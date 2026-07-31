# 19 — SI vs SFI Language Comparison (20260731)

**Opening claim.** On shared decision kinds (excluding SI-only punishment blocks), SI and SFI agents write different lexical worlds: SI leans on **strategy / self-interest / follow / payoff**; SFI leans on **incentives / immediate / long-run / sfi**. Fairness and reciprocity are nearly absent. These are prompt-conditioned dialects more than proof of distinct social preferences — but they are real textual facts of the run.

Primary contrast: `SI_shared_kinds` vs `SFI_shared_kinds`.

---

## Quantitative backbone

| Signal | SI | SFI |
|--------|----|-----|
| Top keyness unigrams | strategy, following, self-interest, payoff, maximize | sfi, incentives, highly, immediate, long-run |
| Self-interest concept rate (shared) | 0.081 | 0.013 |
| Fairness / reciprocity (shared) | ≈0 | ≈0 |
| LOO Jaccard keyness | ~0.87 | 1.0 |

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=top_SI_key_terms]

---

## Raw discourse — pasted examples (not paraphrases)

### SI contribution / strategy–self-interest

**Agent 2, SI, R2** (`RB-02-A2-contribution`):

> Medium contribution to balance self-interest with cooperation, considering previous round's group average and my internal beliefs about SI strategy.

**Agent 3, SI, R2** (`RB-02-A3-contribution`):

> I'm choosing a moderate contribution to balance self-interest and cooperation, while also considering the historical emissions index of 1.50.

**Agent 13, SI, R1** (`RB-01-A13-contribution`):

> Choose a moderate contribution to balance between individual gain and group cooperation.

### SFI contribution / incentives–horizon

**Agent 1, SFI, R1** (`RB-01-A1-contribution`):

> Choosing a moderate contribution to balance immediate resilience needs with long-run cooperation incentives.

**Agent 18, SFI, R1** (`RB-01-A18-contribution`):

> Maximizing my cumulative payoff requires a balance between immediate resilience needs and long-run cooperation incentives, so I choose a contribution that is substantial but not excessive.

**Agent 19, SFI, R1** (`RB-01-A19-contribution`):

> Contributing nothing allows me to conserve resources and observe the behavior of other agents, without immediately committing to a cooperative action.

### SI fairness language lives mainly in punishment blocks

**Agent 5, SI, R2** (`RB-02-A5-punishment`):

> Punishing free-riders and those who did not match their stated intentions to maintain cooperation and fairness within the group.

**Agent 3, SI, R4** (`RB-04-A3-punishment`):

> Punished free-riders and rewarded generous contributors to promote fairness and cooperation within the institution.

Prompt 6’s `SFI_fair` example list is **empty** — fairness talk is SI-sanction dialect, not a shared contribution norm language.

[Evidence: `tables/prompt6_numeric_summary.json` | run=20260731_013853 | round=1-4 | agent=1,2,3,5,13,18,19 | record=examples]

---

## Counterexamples

Some SI texts omit “self-interest”; some SFI texts sound payoff-max without “immediate/long-run.” Keyness is distributional. Forced group confounds.

---

## Limits

Boilerplate risk. Shared-kinds design avoids punishment asymmetry but cannot remove group confound. Confidence high on keyness direction; medium on preference interpretation.

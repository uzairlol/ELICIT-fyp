# 25 — Ostrom / Governing the Commons Mapping (20260731)

Cautious mapping of ELICIT mechanisms to themes in Elinor Ostrom’s institutional analysis of common-pool resources. **This simulation does not claim to implement Ostrom’s design principles as a complete package.**

Primary references for concepts (theory, not empirical validation of this run): Ostrom, *Governing the Commons* (1990); CPR design-principle literature. Empirical claims below cite repository evidence only.

---

## Mapping table

| Ostrom-related concept | Implemented analogue in ELICIT | Missing / diverging component | Evidence from 20260731 | Interpretive limitation |
|------------------------|--------------------------------|-------------------------------|------------------------|-------------------------|
| Repeated interaction | 30 rounds; same 26 agents | Finite horizon; no indefinite shadow of future | Run params; `prompt7` persistence metrics | End-game / horizon effects untested |
| Monitoring | Peer history in prompts; ToM scores; reputation aggregate | No dedicated monitors; gossip not stored in JSON | `06_agent_information_boundaries.md`; gossip reconstructed | Monitoring quality analyst-dependent |
| Reputation | Mean incoming ToM; gossip of low scores | Incomplete common knowledge of others’ reputations | Prompt 4 events; agents see **own** rep only | Not a transparent public ledger |
| Graduated sanctions | SI Stage-2 punish tokens + `PUNISHMENT_EFFECT` | No coded escalation ladder (warn→fine→expulsion) | `17_enforcement_as_public_good.md` | Continuous token spend ≠ graduated schedule |
| Collective-choice arrangements | Democracy every 5 rounds; proposals + plurality votes | Sparse ballots (14 proposals / 6 sessions); not nested enterprises | `prompt5_numeric_summary.json` | Plurality with thin participation ≠ robust CPR assembly |
| Conflict resolution | Informal: punish/reward + votes on parameters | No arbitration body or appeals | Democracy + Stage-2 only | Conflicts mostly numerical (contribution/rules) |
| Rule adaptation | Adopted: subsidy↑, LDF equity↑, damage weight | Cannot rewrite Stage-1 game form; membership forced | `prompt5` adopted_by_category | Adaptation within fixed architecture |
| Information boundaries | Hidden LDF pool; delayed gossip; no same-round peers | Real IDs in LDF (low anonymity) | `06_agent_information_boundaries.md` | Boundaries designed, not emergent |
| Legitimacy | Vote adoption; retained high PUNISHMENT_EFFECT | No legitimacy survey; forced SI/SFI may undermine “consent” | Failed punishment-weakening; forced routing in `environment.py` | Legitimacy inferred, not measured |
| Local institutional design | Parameter tweaks by agents | Global rules apply to all; not polycentric local rules | One parameter vector for world | Not polycentric CPR governance |
| Responsibility for maintaining governance | SI pays Stage-2 costs; all may propose/vote | SFI free of Stage-2; democracy costless | Prompt 5 enforcement_corr; SI-only Stage-2 | Second-order problem only partly modelled |
| Congruence rules↔conditions | Soft climate role guidance; LDF payouts to developing | Endowments / capacities exogenous; country labels stylised | `parameters.LDF_*`; `loss_damage_fund.py` | Not calibrated to real jurisdictions |
| Clearly defined boundaries | Fixed agent set; SI/SFI membership lists | Membership not voluntary in climate mode | Forced institution assignment | Boundary clarity without entry/exit rights |

---

## Design principles — explicit non-claims

Do **not** assert that ELICIT satisfies Ostrom’s eight design principles. Closest partial analogues:

1. **Boundaries** — agent IDs fixed; resource is abstract wealth / LDF pool (not a physical CPR).
2. **Congruence** — weak; rules are numerical knobs, not local ecological rules.
3. **Collective choice** — present but thin (few proposals).
4. **Monitoring** — partial, asymmetric, LLM-mediated.
5. **Graduated sanctions** — **not** implemented as a ladder.
6. **Conflict resolution** — minimal.
7. **Recognized rights to organize** — agents can propose parameters; cannot exit forced SI/SFI.
8. **Nested enterprises** — **absent**.

[Evidence: `src/modules/democracy_module.py` | run=n/a | round=n/a | agent=n/a | record=proposal_vote_adopt]  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=climate_mode_forced_institution]

---

## What the 20260731 run illustrates (cautious)

1. **Formal rules can drift without strong informal norms.** Subsidy/LDF equity parameters change while obligation language stays weak (Prompts 5–7).
2. **Social sanctions without repair.** Reputation/gossip events associate with contribution declines (Prompt 4) — unlike textbook stories where monitoring stabilises cooperation.
3. **Enforcement responsibility is asymmetric.** SI bears Stage-2 costs; SFI influences redistribution politics via votes — a political-economy wedge, not a classic CPR user group.

[Evidence: `synthesis/21_norm_emergence_assessment.md` | run=20260731_013853 | round=n/a | agent=n/a | record=verdict]  
[Evidence: `tables/prompt4_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=mean_delta_prop]

---

## Bottom line

ELICIT is best read as a **multi-stage public-goods + climate-transfer + meta-governance** lab, inspired by institutional themes Ostrom emphasised (repetition, monitoring, sanctions, rule change), not as an operationalisation of CPR design principles. Claims that “the simulation shows Ostromian self-governance” would overreach this codebase and this single run.

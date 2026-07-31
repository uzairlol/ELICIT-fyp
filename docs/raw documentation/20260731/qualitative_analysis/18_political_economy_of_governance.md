# 18 — Political Economy of Governance (20260731)

**Opening claim.** Governance in this run is a **reward-and-redistribution ratchet** wrapped in cooperation talk. Agents use costless democracy to reshape parameters that bind *other* mechanisms (SFI proposers hiking SI subsidies; SI proposers hiking LDF equity), while costly Stage-2 enforcement remains an SI private burden. Cooperative rhetoric does not disclose incidence.

---

## Quantitative backbone

Adopted: SUBSIDY_FRACTION path upward; LDF_EQUITY_WEIGHT 0.5→0.7; LDF_PAYOUT_DAMAGE_WEIGHT 1.5. Failed: PUNISHMENT_EFFECT→1 twice. Same-group vote rate ≈0.51 (near base rate). Post-adoption mean prop deltas small/confounded.

[Evidence: `tables/prompt5_numeric_summary.json` | run=20260731_013853 | round=n/a | agent=n/a | record=adopted_by_category]

---

## Raw discourse — politics in proposal text

**SFI agent 4 hiking SI subsidy (adopted R5):**

> Increasing the subsidy fraction will incentivize cooperation by rewarding top contributors and potentially reducing punishment costs…

**SI agent 22 hiking LDF equity (adopted R10):**

> …prioritizing poorer developing nations, promoting trust within the community.

**SI agent 14 hiking damage weight (adopted R20):**

> …incentivize agents to prioritize cooperation and reduce free-riding…

**SFI agent 15 late subsidy 0.6 (adopted R30):**

> …stronger reward for contributing to the common good

None of these sentences say “this transfers resources toward my group.” The political reading comes from matching **proposer institution** to **rule domain** (doc 14 table).

---

## Dual readings (labelled)

1. **Cooperative institutional design:** agents sincerely build carrots and equity.  
2. **Self-serving rule shopping:** agents move parameters that benefit their side’s pocketbook while outsourcing costs.

Both are compatible with the text; (2) is supported by cross-domain proposal patterns, not by confessions.

---

## Counterexamples

Same-group voting is weak (~0.51), so blocs are not tight. Some SI agents vote for developing-favouring LDF equity. Near-zero agent 1’s failed coverage proposal shows low contributors *attempt* redistribution expansions.

---

## Limits

Single seed; whitelist agenda; plurality. Confidence medium–high on descriptive politics; low on private intent.

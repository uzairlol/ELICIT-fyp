# 05 â€” Mathematical Model (20260804)

Equations as **implemented in code**. Variables defined. Each equation cites file + function.

Not an idealised model. Prompted LLM behaviour is called out separately.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| \(i\) | Agent |
| \(c_i\) | Stage-1 contribution |
| \(n\) | Institution group size |
| \(C = \sum_{j \in G} c_j\) | Total contribution in institution \(G\) |
| \(m\) | `PUBLIC_GOOD_MULTIPLIER` (default 1.6) |
| \(w_i\) | Wealth |
| \(v_i\) | Vulnerability |
| \(s\) | Shock severity |
| \(d_i\) | Gross climate damage |
| \(p_{ij}\) | Punishment tokens \(i\) assigns to \(j\) |
| \(r_{ij}\) | Reward tokens \(i\) assigns to \(j\) |
| \(B\) | LDF `pool_balance` |

---

## 1. Endowment / contribution capacity

### Initial wealth (LDF setup)

Implemented in `main.py` `apply_group_profile` using `LDF_DEVELOPED_INITIAL_ENDOWMENTS` / `LDF_DEVELOPING_INITIAL_ENDOWMENTS` (and related vulnerability/emissions/capacity).

Static capacity indices (not currency budgets):

\[
\kappa_i =
\begin{cases}
1.00 & \text{developed (}\texttt{DEVELOPED\_CONTRIBUTION\_CAPACITY}\text{)} \\
0.10 & \text{developing (}\texttt{DEVELOPING\_CONTRIBUTION\_CAPACITY}\text{)}
\end{cases}
\]

[Evidence: `src/core/parameters.py` | run=n/a | round=n/a | agent=n/a | record=DEVELOPED_CONTRIBUTION_CAPACITY]

### Stage-1 contribution cap (climate/LDF)

\[
\bar{c}_i = \max(\texttt{MIN\_CONTRIBUTION},\, \lfloor w_i \rfloor)
\]

with `MIN_CONTRIBUTION = 0`.  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=get_stage1_contribution_cap]

Abstract (non-climate) mode uses fixed `ENDOWMENT_STAGE_1` instead.

### Contribution amount (implemented clamp; value prompted)

\[
c_i \leftarrow \mathrm{clip}(c_i^{\mathrm{LLM}},\, \texttt{MIN\_CONTRIBUTION},\, \bar{c}_i)
\]

[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=make_contribution]

### Proportional contribution

**Not computed by the simulation.** Analyst-derived ratios documented in Prompt 1 (`02_data_schema.md`).

---

## 2. Public goods / Stage-1 payoff

### Share

\[
\mathrm{share}_i = \frac{m \cdot C}{n}
\]

[Evidence: `src/core/institution.py` | run=n/a | round=n/a | agent=n/a | record=distribute_public_goods]  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=get_stage1_payoff]

### MCPR (prompted metric only)

\[
\mathrm{MCPR} = \frac{m}{n}
\]

Shown in prompts; not a separate payoff branch.  
[Evidence: `src/prompts/prompt_generator.py` | run=n/a | round=n/a | agent=n/a | record=_format_mcpr_line]

### Stage-1 payoff

Climate/LDF:

\[
\pi_{1,i} = \mathrm{share}_i - c_i
\]

Abstract:

\[
\pi_{1,i} = (\bar{c}_i - c_i) + \mathrm{share}_i
\]

(with \(\bar{c}_i = \texttt{ENDOWMENT\_STAGE\_1}\) in abstract mode).

---

## 3. Stage-2 sanctions

### Effects on target (implemented)

\[
\mathrm{recvPunish}_i = \Big(\sum_k p_{ki}\Big) \cdot \texttt{PUNISHMENT\_EFFECT}
\]

\[
\mathrm{recvReward}_i = \Big(\sum_k r_{ki}\Big) \cdot \texttt{REWARD\_EFFECT}
\]

Defaults: `PUNISHMENT_EFFECT=3`, `REWARD_EFFECT=1`.  
[Evidence: `src/core/institution.py` | run=n/a | round=n/a | agent=n/a | record=apply_punishments_and_rewards]

### Cost to sender

\[
\mathrm{spent}_i = \Big(\sum_j p_{ij}\Big)\cdot\texttt{PUNISHMENT\_COST}
+ \Big(\sum_j r_{ij}\Big)\cdot\texttt{REWARD\_COST}
\]

Defaults: both costs = 1.

### Stage-2 payoff

Climate/LDF:

\[
\pi_{2,i} = -\mathrm{spent}_i + \mathrm{recvReward}_i - \mathrm{recvPunish}_i
\]

Abstract adds leftover `ENDOWMENT_STAGE_2`.  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=get_stage2_payoff]

### Stage-2 budget (climate/LDF)

\[
b_i^{(2)} = \max\big(\texttt{ENDOWMENT\_STAGE\_2},\, \lfloor w_i \cdot \texttt{STAGE\_2\_WEALTH\_FRACTION} \rfloor\big)
\]

with `STAGE_2_WEALTH_FRACTION = 0.05`.  
[Evidence: `src/core/agent.py` | run=n/a | round=n/a | agent=n/a | record=get_stage2_budget]

SFI members: \(\pi_{2,i}=0\) (no Stage 2).

---

## 4. Subsidy redistribution

Let \(P_{\mathrm{SI}} = \sum_{i\in\mathrm{SI}} \sum_j p_{ij}\).

\[
\mathrm{pool}_{\mathrm{sub}} = \left\lfloor P_{\mathrm{SI}} \cdot \texttt{PUNISHMENT\_COST} \cdot \texttt{SUBSIDY\_FRACTION} \right\rfloor
\]

Top `SUBSIDY_TOP_N` SI contributors (by \(c_i\)) each receive:

\[
\mathrm{subsidy}_i = \left\lfloor \frac{\mathrm{pool}_{\mathrm{sub}}}{N_{\mathrm{top}}} \right\rfloor
\]

Defaults: fraction `0.2`, top_n `2`. Remainder discarded by integer division.  
[Evidence: `src/core/subsidy.py` | run=n/a | round=n/a | agent=n/a | record=compute_subsidies]

---

## 5. Climate shock damage

If deterministic schedule matches round \(t\):

\[
s_t = s^{\mathrm{sched}}_t,\quad d_i = \texttt{CLIMATE\_DAMAGE\_BASE} \cdot s_t \cdot \max(0, v_i)
\]

Default base `150000`; schedule includes \((5,0.10)\), \((10,0.20)\).  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=_apply_climate_shock_and_ldf]

Stochastic branch (if enabled): Bernoulli(`CLIMATE_SHOCK_BASE_PROB`) then Uniform severity â€” **not** the path for deterministic schedule runs.

---

## 6. LDF fund balance update

### Collection gate

If `LDF_COLLECT_EVERY_ROUND`: collect every round; else when \(t \bmod \texttt{INTERVAL} = 1\).  
[Evidence: `src/core/loss_damage_fund.py` | run=n/a | round=n/a | agent=n/a | record=should_collect_contributions]

### Deposit

\[
a_i = \max(0, c_i),\qquad B \leftarrow B + \sum_i a_i
\]

**Important:** LDF deposit **reuses** Stage-1 public-goods contribution; there is no separate LDF levy decision.  
[Evidence: `src/core/loss_damage_fund.py` | run=n/a | round=n/a | agent=n/a | record=_contribution_amount]

### Payouts (developing only)

\[
\max_i = d_i \cdot \texttt{LDF\_MAX\_COVERAGE}
\]

If \(B \ge \sum \max_i\), equity multiplier \(e_i = 1\); else

\[
e_i = \max\!\Big(0,\; 1 + \big(\tfrac{\bar{w}}{w_i} - 1\big)\cdot\texttt{LDF\_EQUITY\_WEIGHT}\Big)
\]

with \(\bar{w}\) = mean developing wealth (floored wealth â‰¥ 1 in ratio).

\[
n_i = \texttt{LDF\_PAYOUT\_DAMAGE\_WEIGHT} \cdot d_i \cdot e_i
\]

\[
\mathrm{payout}_i = \min\Big(B\cdot\frac{n_i}{\sum n},\; \max_i,\; \text{remaining}\Big)
\]

\[
B \leftarrow B - \sum \mathrm{payout}_i
\]

Defaults: coverage `0.90`, damage weight `1.0`, equity weight `0.0`.  
[Evidence: `src/core/loss_damage_fund.py` | run=n/a | round=n/a | agent=n/a | record=distribute_payouts]

---

## 7. Round payoff and wealth evolution

[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=calculate_payoffs]

Order:

1. \(w_i \leftarrow w_i + \pi_{1,i}\)
2. Round payoff:

\[
\Pi_i = \pi_{1,i} + \pi_{2,i} + \mathrm{subsidy}_i + \mathrm{payout}_i - d_i
\]

3. \(w_i \leftarrow w_i + \pi_{2,i} + \mathrm{subsidy}_i + \mathrm{payout}_i - d_i\)
4. \(w_i \leftarrow \max(0, w_i)\)
5. Cumulative payoff accumulates \(\Pi_i\)

---

## 8. Reputation

After ToM, for agents with at least one incoming score:

\[
\rho_i = \frac{1}{|E_i|}\sum_{e\in E_i} \mathrm{score}_{e\to i}
\]

Scores \(\in [1,10]\) are LLM outputs (**prompted**). If no scores, prior \(\rho_i\) kept. Init \(\rho_i=5\).  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=run_tom_audit]

---

## 9. Gossip selection / publication

Keep audits with \(\mathrm{score} \le \texttt{GOSSIP\_TRIGGER\_SCORE}\) (default 7).  
Sort ascending; take top `MAX_GOSSIP_ITEMS` (default 5).  
[Evidence: `src/modules/gossip_module.py` | run=n/a | round=n/a | agent=n/a | record=compile_gossip]

---

## 10. Democracy / voting / rule activation

- Proposal eligibility: **all agents** (implemented loop; docstring outdated)
- Vote: each agent picks a proposal index (**prompted**)
- Outcome: plurality; ties â†’ `random.choice`
- Activation: write to live `parameters` with clamp \(\approx[0.1\times, 10\times]\) current value
- Editable whitelist includes sanction/subsidy params and, in LDF, `LDF_PAYOUT_DAMAGE_WEIGHT`, `LDF_MAX_COVERAGE`, `LDF_EQUITY_WEIGHT`

[Evidence: `src/modules/democracy_module.py` | run=n/a | round=n/a | agent=n/a | record=_collect_proposals]

---

## 11. Institutional transition (this run)

Climate/LDF mode:

\[
\mathrm{inst}_i =
\begin{cases}
\mathrm{SI} & \text{if } \mathrm{group}_i=\texttt{developed} \\
\mathrm{SFI} & \text{otherwise}
\end{cases}
\]

**Implemented** assignment; not an LLM choice in this mode.  
[Evidence: `src/core/environment.py` | run=n/a | round=n/a | agent=n/a | record=setup_agent_climate_mode]

---

## 12. Stochastic elements

| Element | Stochastic? | This-run path |
|---------|-------------|----------------|
| Climate shock timing/severity | Optional | Deterministic schedule |
| Democracy ties | Yes | `random.choice` |
| LLM sampling | Yes | temperature/top_p per stage |
| ToM / contribution / etc. | Yes | LLM |

---

## Prompted vs implemented (summary)

| Mechanism | Implemented closed form | Prompted |
|-----------|-------------------------|----------|
| PG share, payoffs, wealth | Yes | â€” |
| Contribution **value** | Clamp only | LLM chooses amount |
| Punish/reward **targets/amounts** | Effects/costs | LLM allocates |
| ToM score | Mean â†’ reputation | LLM score |
| Gossip set | Threshold + top-k | Score content |
| Democracy outcome | Plurality + apply | Proposal text / votes |
| Institution (LDF) | Forced by group | Soft labels in prompts |
| LDF deposit amount | \(= c_i\) | Via contribution choice |
| LDF pool visibility | Hidden from agents | Qualitative reminder only |

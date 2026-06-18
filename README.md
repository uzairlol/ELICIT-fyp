# LLM Multi-Agent Public Goods and Climate Risk-Sharing Simulator

This project is a multi-agent simulation framework for studying cooperation, sanctions, governance, and climate risk-sharing under repeated public goods interactions.

Agents are LLM-driven and make decisions each round about:

- Institutional membership (Sanctioning Institution or Sanction-Free Institution)
- Contribution levels
- Punishment and reward allocations (for Sanctioning Institution members)
- Policy changes through constitutional voting

The framework also supports climate shocks and a persistent Loss and Damage Fund (LDF), with heterogeneous developed/developing profiles.

## Scope of this repository upload

This README documents only the folders included in your GitHub upload:

- src
- results
- figures

## Core simulation model

Each round follows this high-level sequence:

1. Agents select institutions (or are routed by climate-mode rules)
2. Agents contribute in stage 1
3. Public goods returns are distributed
4. SI members assign punishments/rewards in stage 2
5. Optional subsidy redistribution is applied
6. Optional climate shock is sampled
7. Optional LDF contributions/payouts are computed
8. Round payoffs, wealth, reputation, and logs are updated
9. Optional Theory of Mind audits and gossip are applied
10. Optional democracy session runs every configured interval

## Institutions

- SFI: No stage-2 punish/reward actions
- SI: Stage-2 punish/reward is enabled

In climate/LDF mode, institution assignment is deterministic by group:

- Developed agents are routed to SI
- Developing agents are routed to SFI

## Climate and LDF behavior

Climate mode can be activated by scenario or flags:

- Scenario name climate is internally treated as ldf
- Climate shocks and LDF can be enabled independently by CLI flags

LDF flow logic in practice:

- Contributions are collected every replenishment interval (default every 5 rounds, at rounds where round % interval == 1)
- Payouts occur only in shock rounds
- Payouts are bounded by damage and max coverage policy
- Remaining funds stay in the pool for future rounds

Important modeled effects:

- Developed and developing groups can have very different wealth/endowment baselines
- Constitutional voting can modify LDF policy parameters during the run (for example LDF_BASE_RATE)
- This can produce late-run pool growth while payouts stay low if shock frequency or damage is limited

## Folder structure

```text
.
|- src/
|  |- main.py
|  |- environment.py
|  |- agent.py
|  |- institution.py
|  |- loss_damage_fund.py
|  |- democracy_module.py
|  |- tom_module.py
|  |- gossip_module.py
|  |- subsidy.py
|  |- oracle.py
|  |- prompt_generator.py
|  |- response_parser.py
|  |- scenario_config.py
|  |- parameters.py
|  |- ollama_client.py
|  |- run_experiments.py
|  |- plot_results.py
|  |- analyze_results_detailed.py
|  |- utils.py
|  |- debug_logs/
|- results/
|- figures/
```

## What each folder contains

### src

All executable simulation logic and analysis utilities.

Key files:

- main.py: Single-run entry point
- run_experiments.py: Batch runner across seeds/conditions/mixed populations
- environment.py: Round orchestration and state transitions
- loss_damage_fund.py: LDF contribution and payout mechanics
- plot_results.py: Generates per-run visual diagnostics
- analyze_results_detailed.py: Computes cross-run summary metrics
- parameters.py: Central configuration constants

### results

JSON outputs from simulation runs.

Each file contains a list of round-level snapshots with:

- Round aggregates (contributions, institution membership)
- Climate/LDF metrics (pool start/end, contributions, payouts, damages)
- Agent-level fields (contribution, payoffs, wealth, sanctions, reputation, ToM scores)
- Constitutional session payloads when voting is triggered

### figures

Plot outputs generated from result files.

The plotter creates one subfolder per selected simulation file and stores numbered charts such as:

- Average SI contribution trajectory
- Institutional population dynamics
- Cumulative payoff by agent
- Punishment assigned/received patterns
- Reputation trajectories
- LLM safety counters
- LDF pool/contribution/payout/damage dashboards for climate/LDF-tagged runs

### Featured figures (from 26-agent climate/LDF run)

Mean contribution per round:

![Mean contribution per round](fig_mean_contribution.png)

LDF pool dynamics (includes pool balance trajectory):

![LDF pool dynamics](fig_ldf_pool.png)

## Requirements

Install dependencies:

```bash
pip install openai backoff
```

The framework expects a local Ollama endpoint compatible with OpenAI-style requests.

Example model pull:

```bash
ollama pull llama3.1:8b
```

## Running a single simulation

Basic run:

```bash
python src/main.py
```

Common options:

```bash
# Change model
python src/main.py --model-name mistral:7b

# Scenario framing (abstract, ldf, climate, tax)
python src/main.py --scenario climate

# Enable climate shocks and LDF
python src/main.py --scenario climate --enable-climate-shocks --enable-ldf

# Persona mode for all agents
python src/main.py --agent-type Random
python src/main.py --agent-type Greedy

# Override size
python src/main.py --num-agents 7 --num-rounds 15
```

Notes:

- In climate/ldf scenario, number of agents may be auto-adjusted to match configured developed/developing counts
- Output files are timestamped and written to results

## Running experiment sweeps

Batch runner:

```bash
python src/run_experiments.py
```

Useful sweep configurations:

```bash
# Climate/LDF sweep
python src/run_experiments.py --scenario climate --enable-climate-shocks --enable-ldf

# Quick compare (single seed): Full + two mixed conditions
python src/run_experiments.py --quick-compare --seeds 1

# Only Full ablation condition
python src/run_experiments.py --full-only

# Skip mixed-population runs
python src/run_experiments.py --skip-mixed

# Quiet logs
python src/run_experiments.py --quiet
```

Important setup note for run_experiments.py:

- The script currently initializes repo_root and src_dir from a hardcoded local path near the top of the file
- Before sharing/running on another machine, update those path values to your local repository path

## Generating figures

Interactive plotting:

```bash
python src/plot_results.py
```

Workflow:

1. Script lists all JSON files in results
2. You select one run by index
3. Script writes charts into figures/<selected_simulation_filename>/

For climate/LDF-tagged files, additional LDF-specific dashboards are generated automatically.

## Result JSON schema (practical overview)

Each run file is a JSON list where each element is one round object.

Top-level per-round fields include:

- round_number
- si_members, sfi_members
- si_total_contribution, sfi_total_contribution
- cooperation_rate
- gini_wealth
- shock_occurred, shock_severity
- gross_damage_total, net_damage_total
- ldf_pool_start, ldf_contributions_total, ldf_payouts_total, ldf_pool_end
- agents (mapping from agent id to detailed per-agent state)
- constitutional_change (present on voting rounds)

Per-agent fields include:

- institution_choice and reasoning traces
- contribution and contribution reasoning
- stage1_payoff, stage2_payoff, payoff, cumulative_payoff
- wealth and climate profile attributes
- assigned_punishments, assigned_rewards
- received_punishments, received_rewards
- reputation, tom_scores
- climate_damage_taken_round/cumulative
- ldf_contribution_round, ldf_payout_round, net_climate_transfer_round
- parsing_failures, rule_of_law_blocks

## Configuration reference

Main tuning is in src/parameters.py.

Most important groups:

- Simulation controls: NUM_AGENTS, NUM_ROUNDS, SEED, SCENARIO
- LLM controls: LLM_MODEL, LLM_BASE_URL, LLM_MAX_CONCURRENCY
- Public goods game: ENDOWMENT_STAGE_1, PUBLIC_GOOD_MULTIPLIER, punishment/reward effects and costs
- Governance and cognition: TOM_ENABLED, GOSSIP_ENABLED, DEMOCRACY_ENABLED, DEMOCRACY_INTERVAL
- Subsidy: SUBSIDY_ENABLED, SUBSIDY_FRACTION, SUBSIDY_TOP_N
- Climate shocks: CLIMATE_SHOCK_ENABLED and CLIMATE_SHOCK_* parameters
- LDF policy: LDF_BASE_RATE, LDF_PROGRESSIVITY, LDF_EMISSIONS_WEIGHT, LDF_REPLENISHMENT_INTERVAL, LDF_MAX_COVERAGE
- Group composition/endowments: AGENT_GROUP_COUNTS and LDF_AGENT_GROUP_COUNTS (+ LDF_DEVELOPED_INITIAL_ENDOWMENTS)

## Reproducibility notes

- Random seed is controlled by SEED
- Results are deterministic with fixed seed, fixed model behavior, and stable environment conditions
- Mixed-population runs use deterministic shuffling under the configured seed

## Known practical caveats

- run_experiments.py contains a machine-specific path that should be updated before running in a new environment
- analyze_results_detailed.py writes its summary outside the three uploaded folders by default; adjust output path if you want all artifacts kept within uploaded scope

## Suggested GitHub description (optional)

LLM-based multi-agent simulation of public goods cooperation with sanctions, reputation, constitutional voting, and climate loss-and-damage risk-sharing.

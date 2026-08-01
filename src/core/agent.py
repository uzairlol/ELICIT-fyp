# agent.py

"""
This module defines the Agent class representing participants in the experiment.

Agents use Large Language Models (LLMs) via API calls to make their decisions.

Agents will:

- Choose institutions based on prompts sent to the LLM.

- Decide on contributions by generating prompts and parsing the LLM's responses.

- Assign punishments or rewards in the Sanctioning Institution (SI) based on LLM output.

The agent's internal monologue or reasoning is captured and stored under attributes:

- 'institution_reasoning' for institution choice

- 'contribution_reasoning' for contribution decision

- 'punishment_reasoning' for punishment and reward assignments

Dependencies:

- Requires OllamaClient for local LLM interaction.
"""

import logging
import random
from core import parameters
import os
import json
from core.utils import robust_json_loads, uses_climate_budget
from llm.retry import (
    RetryExhaustedError,
    build_failure_retry_prompt,
    request_with_retries,
)

logger = logging.getLogger(__name__)

from prompts.prompt_generator import (
    construct_institution_choice_prompt,
    construct_contribution_prompt,
    construct_punishment_prompt,
    get_past_actions_string
)

from parsing import (
    parse_institution_choice_response,
    parse_contribution_response_v2,
    parse_punishment_response,
    deanonymize_reasoning
)

def _schema_repair_prompt(base_prompt, stage_name, failure_reason=""):
    guidance = (
        "Use the exact key names from the Required JSON shape. "
        "Do not invent keys or omit required fields."
    )
    if 'unexpected labels' in str(failure_reason or '').lower():
        guidance = (
            "Remove every disallowed Agent label. Use ONLY the Allowed labels listed "
            "in the failure reason / target label list. Do not invent SFI or other Agent IDs."
        )
    return build_failure_retry_prompt(
        base_prompt,
        stage_name,
        failure_reason,
        fix_guidance=guidance,
    )


def _semantic_repair_prompt(base_prompt, stage_name, failure_reason=""):
    return build_failure_retry_prompt(
        base_prompt,
        stage_name,
        failure_reason,
        fix_guidance=(
            "CRITICAL CONSISTENCY RULE: numeric amounts in \"punishments\" / \"rewards\" "
            "must match what reasoning and justifications claim.\n"
            "- If you intend to punish free-riders, put positive INTEGER amounts under "
            "\"punishments\" for those Agent labels (within your Stage 2 budget).\n"
            "- If you intend to reward cooperators, put positive INTEGER amounts under "
            "\"rewards\" for those Agent labels.\n"
            "- If you choose not to punish anyone, set all punishment amounts to 0 and "
            "explicitly write that you are not punishing anyone / all punishment amounts "
            "are 0.\n"
            "- If you choose not to reward anyone, say so explicitly (e.g. no rewards).\n"
            "Do not describe punishing free-riders while leaving all punishment amounts at 0. "
            "Do not describe rewarding contributors while leaving all reward amounts at 0. "
            "Amounts must be integers (not decimals)."
        ),
    )


def _budget_repair_prompt(base_prompt, stage_name, budget, currency_name, failure_reason=""):
    return build_failure_retry_prompt(
        base_prompt,
        stage_name,
        failure_reason,
        fix_guidance=(
            f"Keep the same targets but reduce amounts so total spend fits within "
            f"{budget:,.0f} {currency_name}. Put the final amounts in the "
            "\"punishments\" object."
        ),
    )

class Agent:
    def __init__(self, agent_id, api_client):
        """
        Initialize an Agent.

        Parameters:
        - agent_id (int): Unique identifier for the agent.
        - api_client: The OllamaClient used for all LLM calls.
        """
        self.agent_id = agent_id
        self.api_client = api_client
        self.summary_api_client = api_client  # Alias for deanonymization calls (same client)
        self.initial_wealth = float(parameters.INITIAL_TOKENS)

        self.institution_choice = None  # 'SI' or 'SFI'
        self.contribution = 0
        self.cumulative_payoff = parameters.INITIAL_TOKENS  # Total accumulated payoff
        self.round_payoff = 0  # Payoff for the current round
        self.history = []
        self.current_group = None  # Reference to the institution/group the agent is currently in

        # Round-specific attributes
        self.received_punishments = 0
        self.received_rewards = 0
        self.assigned_punishments = {}  # Dict of agent_id: tokens assigned
        self.assigned_rewards = {}  # Dict of agent_id: tokens assigned

        # Additional attributes for LLM interaction
        self.round_number = 0  # Current round number

        # Add 'strategy' attribute for compatibility
        # Identify agent type for logging/analysis
        self.strategy = 'LLM'
        self.llm_persona = 'DEFAULT'

        # --- Phase 5: Heterogeneous climate profile ---
        self.agent_group = 'developing'
        self.wealth = float(parameters.INITIAL_TOKENS)
        self.vulnerability = float(parameters.DEVELOPING_VULNERABILITY)
        self.historical_emissions = float(parameters.DEVELOPING_HISTORICAL_EMISSIONS)
        self.contribution_capacity = float(parameters.DEVELOPING_CONTRIBUTION_CAPACITY)

        # Climate shock + LDF accounting
        self.climate_damage_taken_round = 0.0
        self.climate_damage_taken_cumulative = 0.0
        self.ldf_contribution_round = 0.0
        self.ldf_payout_round = 0.0
        self.net_climate_transfer_round = 0.0

        # Attributes to store reasoning
        self.institution_reasoning = ''
        self.contribution_reasoning = ''
        self.punishment_reasoning = ''
        self.institution_deepseek_think = ''
        self.contribution_deepseek_think = ''
        self.punishment_deepseek_think = ''
        self.institution_facts_used = []
        self.contribution_facts_used = []
        self.punishment_facts_used = []

        # Attribute to store anonymous data history
        self.anonymous_data_history = []  # List of dicts storing data for previous rounds
        self.current_round_anonymous_data = None  # Data collected in the current round

        # Add attribute to store mapping of anonymized IDs to actual agent IDs
        self.anonymized_id_mapping = {}  # Mapping of anonymized agent numbers to actual agent IDs for the current prompt

        # For deanonymized reasoning
        self.deanonymized_punishment_reasoning = ''  # Deanonymized version of punishment reasoning

        # Stable pseudonym mapping to prevent cross-round identity confusion
        self.pseudonym_mapping = {}  # {actual_agent_id: stable_pseudonym_integer}
        self.reverse_pseudonym_mapping = {} # {stable_pseudonym_integer: actual_agent_id}

        # --- Phase 4: Subsidy & Curiosity ---
        self.last_subsidy = 0       # tokens received in current round
        self.explored_params = set() # For curiosity module: unique parameters proposed
        self.history_institutions = [] # Track all past choices
        self.history_contributions = [] # Track last few contributions

        # --- Reliability tracking ---
        self.parsing_failures = 0
        self.rule_of_law_blocks = 0
        self.institution_parser_meta = {}
        self.contribution_parser_meta = {}
        self.punishment_parser_meta = {}

        # --- Phase 2: Theory of Mind & Reputation ---
        self.tom_scores = {}        # {other_agent_id: trust_score (1-10)} — updated each round
        self.reputation = 5.0       # Peer-average trust score (default = neutral)
        self.stated_intent = ''     # Saved contribution reasoning before the action (for ToM audit)
        self.tom_audit_log = []     # Log of all ToM audit entries this agent has made
        self.recent_gossip = ""     # Phase 2b: Gossip bulletin from the previous round

        # --- Belief Tracking (Working Memory / Scratchpad) ---
        self.belief_state = {
            "trust_levels": {},
            "institutional_strategy": "No prior experience — exploring options.",
            "observations": "No rounds played yet."
        }


        # Initialize pseudonyms for this agent to prevent the anonymization null-routing bug
        self._ensure_pseudonyms_initialized()

    def _uses_climate_budget(self):
        return uses_climate_budget()

    def get_stage1_contribution_cap(self):
        if self._uses_climate_budget():
            return max(parameters.MIN_CONTRIBUTION, int(self.wealth))
        return parameters.ENDOWMENT_STAGE_1

    def choose_institution(self, round_number):
        """
        Decide whether to join the Sanctioning Institution (SI) or the Sanction-Free Institution (SFI)
        by generating a prompt and sending it to the LLM.
        """
        self.round_number = round_number

        prompt = construct_institution_choice_prompt(self, round_number)
        temperature, top_p = self._persona_sampling_profile("institution")

        def parse_choice(raw_response):
            return parse_institution_choice_response(raw_response, self.agent_id)

        def validate_choice(parsed):
            choice, _reasoning, _facts, _think, meta = parsed
            if meta.get('fallback_used', False) or choice not in ('SI', 'SFI'):
                return meta.get('fallback_reason', 'invalid institution choice')
            return ''

        response = None
        try:
            response, parsed = request_with_retries(
                self.api_client,
                base_prompt=prompt,
                parse_response=parse_choice,
                validate_result=validate_choice,
                request_kwargs={
                    "model_name": self.api_client.deployment_name,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 768,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                max_attempts=getattr(parameters, 'LLM_DECISION_MAX_ATTEMPTS', 2),
                label=f"Agent {self.agent_id} institution choice",
                retry_prompt_factory=lambda base, _attempt, error: (
                    _schema_repair_prompt(base, "Institution Choice", error)
                ),
                logger=logger,
            )
            choice, reasoning, facts_used, deepseek_think, parser_meta = parsed
        except RetryExhaustedError as exc:
            last_err = str(exc.last_error or '')
            logger.warning(
                "Agent %s institution choice retries exhausted: %s. Falling back to SFI.",
                self.agent_id, last_err
            )
            choice = 'SFI'
            reasoning = f"Fallback institution choice due to retry exhaust: {last_err}"
            facts_used = []
            deepseek_think = ""
            parser_meta = {
                'fallback_used': True,
                'fallback_reason': f'retries exhausted: {last_err}'
            }

        self.institution_choice = choice
        self.institution_reasoning = reasoning
        self.institution_facts_used = facts_used
        self.institution_deepseek_think = deepseek_think
        self.institution_parser_meta = parser_meta
        
        if response is not None:
            self.log_debug(round_number, "stage_0_institution", prompt, response)

    def _ensure_pseudonyms_initialized(self):
        """
        Creates a stable, randomized mapping of actual agent IDs to pseudonyms (1..N).
        This ensures that 'Agent X' always refers to the same individual across all rounds
        for this specific observer, preventing history vs. current round confusion.
        """
        if not self.pseudonym_mapping:
            other_agents = [a for a in range(parameters.NUM_AGENTS) if a != self.agent_id]
            rng = random.Random(parameters.SEED + self.agent_id)
            rng.shuffle(other_agents)
            
            for i, actual_id in enumerate(other_agents):
                pseudonym = i + 1
                self.pseudonym_mapping[actual_id] = pseudonym
                self.reverse_pseudonym_mapping[pseudonym] = actual_id



    def decide_contribution(self, group_state):
        """
        Decide how much to contribute to the public good using the LLM.
        """
        prompt = construct_contribution_prompt(self, group_state)
        temperature, top_p = self._persona_sampling_profile("contribution")

        def parse_contribution(raw_response):
            return parse_contribution_response_v2(raw_response, self)

        def validate_contribution(parsed):
            contribution, _reasoning, _facts, _think, meta = parsed
            if meta.get('fallback_used', False) or contribution is None:
                return meta.get('fallback_reason', 'invalid contribution')
            return ''

        response = None
        try:
            response, parsed = request_with_retries(
                self.api_client,
                base_prompt=prompt,
                parse_response=parse_contribution,
                validate_result=validate_contribution,
                request_kwargs={
                    "model_name": self.api_client.deployment_name,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 768,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                max_attempts=getattr(parameters, 'LLM_DECISION_MAX_ATTEMPTS', 2),
                label=f"Agent {self.agent_id} contribution choice",
                retry_prompt_factory=lambda base, _attempt, error: (
                    _schema_repair_prompt(
                        base,
                        "Contribution Choice",
                        error,
                    )
                ),
                logger=logger,
            )
            contribution, llm_reasoning, facts_used, deepseek_think, parser_meta = parsed
        except RetryExhaustedError as exc:
            last_err = str(exc.last_error or '')
            logger.warning(
                "Agent %s contribution choice retries exhausted: %s. Falling back to MIN_CONTRIBUTION.",
                self.agent_id, last_err
            )
            contribution = parameters.MIN_CONTRIBUTION
            llm_reasoning = f"Fallback contribution choice due to retry exhaust: {last_err}"
            facts_used = []
            deepseek_think = ""
            parser_meta = {
                'fallback_used': True,
                'fallback_reason': f'retries exhausted: {last_err}'
            }

        # Enforce bounds
        contribution = max(parameters.MIN_CONTRIBUTION, min(contribution, self.get_stage1_contribution_cap()))

        self.contribution = contribution
        self.contribution_reasoning = llm_reasoning
        self.contribution_facts_used = facts_used
        self.contribution_deepseek_think = deepseek_think
        self.contribution_parser_meta = parser_meta

        if response is not None:
            self.log_debug(self.round_number, "stage_1_contribution", prompt, response)


    def assign_punishment(self, group_state):
        """
        Decide on assigning punishments or rewards via the LLM.
        """
        prompt = construct_punishment_prompt(self, group_state)
        temperature, top_p = self._persona_sampling_profile("punishment")

        def parse_punishment(raw_response):
            return parse_punishment_response(raw_response, group_state, self)

        def validate_punishment(parsed):
            meta = parsed[-1]
            if meta.get('fallback_used', False):
                return meta.get('fallback_reason', 'invalid punishment response')
            if meta.get('semantic_retry', False):
                detail = str(meta.get('semantic_retry_reason') or '').strip()
                if detail:
                    return f'punishment response is internally inconsistent: {detail}'
                return 'punishment response is internally inconsistent'
            return ''

        def punishment_retry_prompt(base, _attempt, last_error):
            if 'exceeds budget' in last_error:
                from core.scenario_config import get_scenario_config
                sc = get_scenario_config(parameters.SCENARIO)
                return _budget_repair_prompt(
                    base,
                    "Punishment and Reward Choice",
                    self.get_stage2_budget(),
                    sc['currency_name'],
                    last_error,
                )
            if 'internally inconsistent' in last_error:
                return _semantic_repair_prompt(
                    base,
                    "Punishment and Reward Choice",
                    last_error,
                )
            return _schema_repair_prompt(
                base,
                "Punishment and Reward Choice",
                last_error,
            )

        # No soft fallbacks: invalid Stage-2 JSON must be corrected via retries.
        max_punish_attempts = int(
            getattr(
                parameters,
                'LLM_PUNISHMENT_MAX_ATTEMPTS',
                getattr(parameters, 'LLM_DECISION_MAX_ATTEMPTS', 5),
            )
        )
        response, parsed = request_with_retries(
            self.api_client,
            base_prompt=prompt,
            parse_response=parse_punishment,
            validate_result=validate_punishment,
            request_kwargs={
                "model_name": self.api_client.deployment_name,
                "response_format": {"type": "json_object"},
                "max_tokens": 3000,
                "temperature": temperature,
                "top_p": top_p,
            },
            max_attempts=max_punish_attempts,
            label=f"Agent {self.agent_id} punishment choice",
            retry_prompt_factory=punishment_retry_prompt,
            logger=logger,
        )
        (
            punishment_allocations,
            reward_allocations,
            reasoning,
            deanonymized,
            justifications,
            facts_used,
            deepseek_think,
            parser_meta,
        ) = parsed

        self.log_debug(self.round_number, "stage_2_punishment", prompt, response)

        self.punishment_reasoning = reasoning
        self.deanonymized_punishment_reasoning = deanonymized
        self.punishment_justifications = justifications
        self.punishment_facts_used = facts_used
        self.punishment_deepseek_think = deepseek_think
        self.punishment_parser_meta = parser_meta
        self.assigned_punishments = punishment_allocations
        self.assigned_rewards = reward_allocations
        return punishment_allocations, reward_allocations


    def _persona_sampling_profile(self, stage_name):
        """Return sampling settings tuned to the current persona."""
        if self.llm_persona == "RANDOM":
            if stage_name == "punishment":
                return 1.0, 1.0
            return 0.95, 1.0

        if self.llm_persona == "GREEDY":
            return 0.15, 0.8

        return 0.5, 0.95



    def update_payoff(self, amount, is_subsidy=False):
        """
        Update the agent's cumulative and round payoffs.
        Args:
            amount (float): Payoff to add.
            is_subsidy (bool): Whether this payoff is from the subsidy pool.
        """
        if is_subsidy:
            self.last_subsidy += amount
            
        self.round_payoff += amount
        self.cumulative_payoff += amount



    def update_history(self, round_data):
        """
        Record the actions and outcomes of the round.
        Only the most recent round is kept (T-1) since agents now rely on
        their belief_state scratchpad for long-term memory.
        """
        self.history = [round_data]

    def update_beliefs(self, round_feedback, anonymous_data):
        """
        Belief Tracking: ask the LLM to reflect on the round that just
        ended and produce an updated structured belief state.

        This replaces the old sliding-window episodic memory with a
        compact, semantically rich working-memory scratchpad.
        """
        if not getattr(parameters, 'BELIEF_TRACKING_ENABLED', True):
            return

        from core.scenario_config import get_scenario_config
        sc = get_scenario_config(parameters.SCENARIO)

        # Build a compact peer summary — keep prompt tokens well under num_ctx.
        # Only include peers whose contribution differs significantly from average,
        # capped at the top-N most notable. Full detail causes context overflow with 26+ agents.
        observed_peer_ids = []
        compact_rows = []
        if anonymous_data:
            contribs = [e.get('contribution', 0) for e in anonymous_data if e.get('contribution') is not None]
            avg_c = (sum(contribs) / len(contribs)) if contribs else 0.0
            for entry in anonymous_data:
                pid = entry.get('actual_agent_id', '?')
                try:
                    observed_peer_ids.append(int(pid))
                except (TypeError, ValueError):
                    pass
                c = entry.get('contribution', 0)
                deviation = c - avg_c
                tag = "high" if deviation > 0.15 * avg_c else ("low" if deviation < -0.15 * avg_c else "avg")
                compact_rows.append((abs(deviation), pid, c, tag, entry.get('institution_choice', '?')))
            # Sort most-notable first, limit to 10 rows to cap prompt size
            compact_rows.sort(key=lambda r: r[0], reverse=True)
            compact_rows = compact_rows[:10]

        peer_lines = [
            f"Agent {pid}: {tag}-contrib ({c}), inst={inst}"
            for _, pid, c, tag, inst in compact_rows
        ]
        peer_block = "\n".join(peer_lines) if peer_lines else "No peer data."
        n_omitted = max(0, len(observed_peer_ids) - len(compact_rows))
        if n_omitted:
            peer_block += f"\n({n_omitted} avg-contribution peers omitted for brevity)"

        own_summary = (
            f"inst={round_feedback.get('institution_choice', '?')}, "
            f"contrib={round_feedback.get('contribution', 0)}, "
            f"payoff={round_feedback.get('payoff', 0):.1f}, "
            f"cumulative={round_feedback.get('cumulative_payoff', 0):.1f}, "
            f"rep={round_feedback.get('reputation', 5.0):.1f}"
        )

        # Keep the existing trust_levels from last round as a starting point;
        # only show the keys (labels) to avoid re-serialising a large object.
        prev_trust = self.belief_state.get('trust_levels') or {}
        prev_trust_compact = ", ".join(
            f"{k}:{v}" for k, v in list(prev_trust.items())[:8]
        ) or "none"

        allowed_ids_str = ", ".join(str(i) for i in sorted(observed_peer_ids))

        prompt = f"""Agent {self.agent_id} | Round {round_feedback.get('round_number', '?')} ended.
Your results: {own_summary}
Top notable peers this round (most-deviant contributions):
{peer_block}
Previous trust labels (sample): {prev_trust_compact}

Task: output an updated belief JSON. Be concise.
Allowed peer ids for trust_levels: [{allowed_ids_str}]
Rules:
- trust label = 1-2 words only (e.g. cooperative, free-rider, defector)
- institutional_strategy = 1 short sentence
- observations = 1 short sentence
- Do NOT repeat keys. Close the JSON after the last entry.

Required JSON:
{{
  "trust_levels": {{"<id>": "<label>", ...}},
  "institutional_strategy": "<one sentence>",
  "observations": "<one sentence>"
}}"""

        def parse_belief(raw_response):
            return robust_json_loads(raw_response)

        def validate_belief(parsed):
            if not isinstance(parsed, dict):
                return 'belief response must be a JSON object'
            required = ('trust_levels', 'institutional_strategy', 'observations')
            missing = [key for key in required if key not in parsed]
            if missing:
                return f"belief response missing keys: {', '.join(missing)}"
            if not isinstance(parsed.get('trust_levels'), dict):
                return 'trust_levels must be a JSON object'
            allowed_peer_ids = {str(pid) for pid in observed_peer_ids}
            trust_levels = parsed.get('trust_levels') or {}
            unexpected = sorted(str(key) for key in trust_levels.keys() if str(key) not in allowed_peer_ids)
            if unexpected:
                return (
                    f"trust_levels contains unexpected peer ids: {', '.join(unexpected)}. "
                    f"Allowed ids only: {', '.join(sorted(allowed_peer_ids)) if allowed_peer_ids else '(none)'}"
                )
            for key, value in trust_levels.items():
                label = str(value or '').strip()
                if not label:
                    return f"trust_levels[{key}] must be a non-empty short label"
                if len(label) > 40:
                    return f"trust_levels[{key}] is too long; keep labels to 1-2 words"
            if len(str(parsed.get('institutional_strategy', '') or '')) > 240:
                return 'institutional_strategy is too long; keep it to 1-2 short sentences'
            if len(str(parsed.get('observations', '') or '')) > 240:
                return 'observations is too long; keep it to 1-2 short sentences'
            return ''

        try:
            response, parsed = request_with_retries(
                self.api_client,
                base_prompt=prompt,
                parse_response=parse_belief,
                validate_result=validate_belief,
                request_kwargs={
                    "model_name": self.api_client.deployment_name,
                    "max_tokens": getattr(parameters, 'BELIEF_UPDATE_MAX_TOKENS', 384),
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
                max_attempts=getattr(parameters, 'LLM_DECISION_MAX_ATTEMPTS', 2),
                label=f"Agent {self.agent_id} belief update",
                retry_prompt_factory=lambda base, _attempt, error: (
                    _schema_repair_prompt(base, "Belief Update", error)
                ),
                logger=logger,
            )
        except RetryExhaustedError as exc:
            logger.warning(
                "[Belief Update] Agent %s round %s failed after retries; "
                "keeping previous belief state unchanged: %s",
                self.agent_id,
                round_feedback.get('round_number', '?'),
                exc.last_error,
            )
            return

        self.belief_state = {
            'trust_levels': parsed['trust_levels'],
            'institutional_strategy': str(parsed['institutional_strategy']),
            'observations': str(parsed['observations']),
        }
        self.log_debug(
            round_feedback.get('round_number', 0),
            "belief_update",
            prompt,
            response,
        )
        round_number = round_feedback.get('round_number', '?')
        strategy = self.belief_state.get('institutional_strategy', '')
        trust_levels = self.belief_state.get('trust_levels', {}) or {}
        trust_preview = ", ".join(sorted(map(str, trust_levels.keys()))[:3])
        trust_suffix = f"; peers={trust_preview}" if trust_preview else ""
        logger.debug(
            f"[Belief Update] Agent {self.agent_id} round {round_number}: "
            f"belief state updated (strategy={strategy!r}{trust_suffix})"
        )

    def reset_for_new_round(self):
        """
        Reset variables that are specific to a round.
        """
        # Move current round data to anonymous data history before resetting
        if hasattr(self, 'current_round_anonymous_data') and self.current_round_anonymous_data is not None:
            round_data = {
                'round_number': self.round_number,
                'anonymous_data': self.current_round_anonymous_data
            }
            self.anonymous_data_history.append(round_data)
            # Ensure the history does not exceed DISPLAY_PAST_ACTIONS
            if len(self.anonymous_data_history) > parameters.DISPLAY_PAST_ACTIONS:
                self.anonymous_data_history.pop(0)
            self.current_round_anonymous_data = None

        # Phase 4 Curiosity: snapshot choices BEFORE they are reset
        if self.institution_choice:
            self.history_institutions.append(self.institution_choice)
            if len(self.history_institutions) > 10:
                self.history_institutions.pop(0)
        self.history_contributions.append(self.contribution)
        if len(self.history_contributions) > 10:
            self.history_contributions.pop(0)

        # Reset other attributes
        self.contribution = 0
        self.received_punishments = 0
        self.received_rewards = 0
        self.assigned_punishments = {}
        self.assigned_rewards = {}
        self.current_group = None
        self.round_payoff = 0  # Reset current round's payoff

        # Reset reasoning attributes
        self.institution_reasoning = ''
        self.contribution_reasoning = ''
        self.punishment_reasoning = ''
        self.deanonymized_punishment_reasoning = ''
        self.institution_facts_used = []
        self.contribution_facts_used = []
        self.punishment_facts_used = []
        self.punishment_justifications = {}
        self.institution_deepseek_think = ''
        self.contribution_deepseek_think = ''
        self.punishment_deepseek_think = ''
        self.anonymized_id_mapping = {}
        self.last_subsidy = 0 # Reset for new round
        self.climate_damage_taken_round = 0.0
        self.ldf_contribution_round = 0.0
        self.ldf_payout_round = 0.0
        self.net_climate_transfer_round = 0.0
        self.institution_parser_meta = {}
        self.contribution_parser_meta = {}
        self.punishment_parser_meta = {}
        if hasattr(self, 'tom_audit_log'):
            self.tom_audit_log = []

    def receive_punishment(self, amount):
        """
        Record the amount of punishment received.
        Args:
        amount (float): The total punishment effect received.
        """
        self.received_punishments += amount

    def receive_reward(self, amount):
        """
        Record the amount of reward received.
        Args:
        amount (float): The total reward effect received.
        """
        self.received_rewards += amount

    def get_stage1_payoff(self, group_size, total_group_contribution):
        """
        Calculate the payoff from Stage 1.
        Args:
        group_size (int): The number of members in the group.
        total_group_contribution (float): The sum of contributions in the group.
        Returns:
        float: The payoff from Stage 1.
        """
        if group_size > 0:
            earnings_from_public_good = (parameters.PUBLIC_GOOD_MULTIPLIER * total_group_contribution) / group_size
        else:
            earnings_from_public_good = 0
            
        if self._uses_climate_budget():
            # In climate mode, return the net profit/loss
            stage1_payoff = earnings_from_public_good - self.contribution
        else:
            contribution_cap = self.get_stage1_contribution_cap()
            tokens_kept = contribution_cap - self.contribution
            stage1_payoff = tokens_kept + earnings_from_public_good
            
        return stage1_payoff

    def get_stage2_budget(self):
        """
        Sanction budget for stage 2.
        Abstract mode: fixed ENDOWMENT_STAGE_2 game tokens.
        Climate/LDF mode: 5% of current wealth (same scale as contributions), with a floor.
        """
        if self._uses_climate_budget():
            scaled = int(self.wealth * parameters.STAGE_2_WEALTH_FRACTION)
            return max(parameters.ENDOWMENT_STAGE_2, scaled)
        return parameters.ENDOWMENT_STAGE_2

    def get_max_punishment_tokens(self):
        """Max sanction amount assignable to a single peer in stage 2."""
        if self._uses_climate_budget():
            scaled = int(self.wealth * parameters.STAGE_2_WEALTH_FRACTION)
            return max(parameters.MAX_PUNISHMENT_TOKENS, scaled)
        return parameters.MAX_PUNISHMENT_TOKENS

    def get_stage2_payoff(self):
        """
        Calculate the net payoff from Stage 2, after considering assigned punishments and rewards.
        Returns:
        float: The payoff from Stage 2.
        """
        # Tokens used for assigning punishments and rewards
        tokens_spent = (
            sum(self.assigned_punishments.values()) * parameters.PUNISHMENT_COST +
            sum(self.assigned_rewards.values()) * parameters.REWARD_COST
        )

        # Effects of punishments and rewards received
        punishment_effect = self.received_punishments  # Already includes the punishment effect
        reward_effect = self.received_rewards  # Already includes the reward effect

        if self._uses_climate_budget():
            # In climate mode, return the net profit/loss (no free endowment, costs deducted from wealth)
            stage2_payoff = -tokens_spent + reward_effect - punishment_effect
        else:
            # Tokens remaining from the initial Stage 2 endowment
            tokens_remaining = parameters.ENDOWMENT_STAGE_2 - tokens_spent
            stage2_payoff = tokens_remaining + reward_effect - punishment_effect
        return stage2_payoff

    def __repr__(self):
        return f"Agent({self.agent_id}, Cumulative Payoff: {self.cumulative_payoff})"

    def log_debug(self, round_num, stage_name, prompt, response):
        """Helper to save LLM interactions for debugging (opt-in; large on disk/RAM)."""
        if not getattr(parameters, 'DEBUG_LLM_IO', False):
            return
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'debug_logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        filename = f"agent_{self.agent_id}_round_{round_num}_{stage_name}.json"
        with open(os.path.join(log_dir, filename), 'w', encoding='utf-8') as f:
            json.dump({'prompt': prompt, 'response': response}, f, indent=2)

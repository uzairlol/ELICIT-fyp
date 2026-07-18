# tom_module.py

"""
Theory of Mind (ToM) Module for ELICIT (Emergent LLM Institutions for Climate and International Treaties).

After each round, each agent silently "audits" every other agent for behavioural
consistency (hypocrisy detection):
  - Stated Intent  : the reasoning the agent gave *before* contributing
  - Objective Action: the actual contribution they made

The LLM scores each agent pair on a trustworthiness scale of 1-10.
These scores are stored on each Agent as `tom_scores` and averaged into a
`reputation` value, which feeds back into the RL observation vector and
future LLM prompts, closing the loop between social judgement and behaviour.

Audits are pairwise: one LLM call per evaluator-target pair.
"""

import logging
import time
from core import parameters
from core.scenario_config import get_scenario_config
from core.utils import robust_json_loads
from llm.retry import request_with_retries

logger = logging.getLogger(__name__)


class TomModule:
    """
    Performs Theory of Mind audits on behalf of a single evaluating agent.
    """

    def __init__(self, api_client):
        self.api_client = api_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def audit_round(self, evaluating_agent, all_agents, round_number):
        """
        For the given evaluating_agent, score every *other* agent's
        behavioural consistency this round via one LLM call per peer.

        Returns:
            dict: {other_agent_id (int): {'score': float, 'reasoning': str}}
        """
        scores = {}
        audit_started = time.monotonic()
        target_count = max(0, len(all_agents) - 1)
        logger.info(
            "[ToM] Evaluator Agent %s starting %s pairwise score(s) for Round %s.",
            evaluating_agent.agent_id,
            target_count,
            round_number,
        )
        if not hasattr(evaluating_agent, 'tom_audit_log'):
            evaluating_agent.tom_audit_log = []

        for target in all_agents:
            if target.agent_id == evaluating_agent.agent_id:
                continue

            score, reasoning = self._score_agent(
                evaluator=evaluating_agent,
                target=target,
                round_number=round_number,
            )
            if score is None:
                continue

            scores[target.agent_id] = {'score': score, 'reasoning': reasoning}

            if getattr(parameters, 'TOM_VERBOSE', False):
                logger.info(
                    f"[ToM] Agent {evaluating_agent.agent_id} scored Agent {target.agent_id}: "
                    f"{score:.1f}/10"
                )
            else:
                logger.debug(
                    f"[ToM Audit] Agent {evaluating_agent.agent_id} scored Agent {target.agent_id}: "
                    f"{score:.1f}/10"
                )

            evaluating_agent.tom_audit_log.append({
                'round': round_number,
                'target_agent': target.agent_id,
                'trust_score': score,
                'reasoning': reasoning,
            })

        logger.info(
            "[ToM] Evaluator Agent %s completed %s/%s score(s) in %.1fs.",
            evaluating_agent.agent_id,
            len(scores),
            target_count,
            time.monotonic() - audit_started,
        )
        return scores

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(text, limit=180):
        text = (text or "No reasoning provided.").strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _score_agent(self, evaluator, target, round_number):
        """Score one peer. Returns (score, reasoning) or (None, '') on failure."""
        base_prompt = self._build_pair_prompt(evaluator, target, round_number)
        label = f"ToM Agent {evaluator.agent_id} -> Agent {target.agent_id}"
        max_attempts = max(
            1,
            int(getattr(parameters, 'TOM_MAX_ATTEMPTS', 2)),
        )

        def retry_prompt(base, _attempt, _last_error):
            return (
                f"{base}\n\n"
                "IMPORTANT RETRY (ToM Audit): Your previous response was "
                "invalid or incomplete. Return ONLY one valid JSON object with "
                '"trust_score" as an integer from 1 to 10 and a short '
                '"reasoning" string. No extra text.'
            )

        def parse_score(response):
            return self._parse_score_response(response)


        def validate_score(parsed):
            _score, _reasoning, parse_error = parsed
            return parse_error

        attempt_started = time.monotonic()
        logger.info(
            "[ToM] Starting %s (maximum %s attempts).",
            label,
            max_attempts,
        )
        _response, parsed = request_with_retries(
            self.api_client,
            base_prompt=base_prompt,
            parse_response=parse_score,
            validate_result=validate_score,
            request_kwargs={
                "model_name": self.api_client.deployment_name,
                "max_tokens": 96,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            max_attempts=max_attempts,
            label=label,
            retry_prompt_factory=retry_prompt,
            logger=logger,
        )
        score, reasoning, _parse_error = parsed
        logger.info(
            "[ToM] Completed %s with score %.1f/10 in %.1fs.",
            label,
            score,
            time.monotonic() - attempt_started,
        )

        return score, reasoning

    def _build_pair_prompt(self, evaluator, target, round_number):
        sc = get_scenario_config(parameters.SCENARIO)
        currency_name = sc['currency_name']
        stated_intent = self._truncate(target.contribution_reasoning)
        contribution = target.contribution
        endowment = (
            target.get_stage1_contribution_cap()
            if hasattr(target, 'get_stage1_contribution_cap')
            else parameters.ENDOWMENT_STAGE_1
        )

        return f"""You are Agent {evaluator.agent_id} in a public goods experiment (Round {round_number}).

Task: Score the behavioral consistency of Agent {target.agent_id} this round.

**Stated intent before contributing:**
"{stated_intent}"

**Actual contribution:**
{contribution} / {endowment} {currency_name}

**Scoring scale:**
- 10 = action perfectly matched stated intent
- 5 = neutral / insufficient data
- 1 = action inconsistent with stated intent

**Required JSON shape:**
{{
  "trust_score": 5,
  "reasoning": "Brief explanation (max 2 sentences) of why you gave this score."
}}

**FINAL OUTPUT RULES:**
- trust_score MUST be an integer from 1 to 10.
- reasoning MUST be a short string (max 2 sentences).
- Return exactly ONE JSON object. No other keys. No text outside the JSON."""

    def _parse_score_response(self, response):
        """Parse a single trust score. Returns (score, reasoning, error_message)."""
        try:
            data = robust_json_loads(response)
            if 'trust_score' not in data:
                raise ValueError('Missing trust_score')
            score = float(data['trust_score'])
            score = max(1.0, min(10.0, score))
            reasoning = str(data.get('reasoning', '') or '').strip()
            return score, reasoning, ''
        except Exception as e:
            return None, '', str(e)

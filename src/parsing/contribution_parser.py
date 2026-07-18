import logging
from core import parameters
from parsing.response_parsing_utils import _unwrap_response_data, _make_parser_meta

logger = logging.getLogger(__name__)


def parse_contribution_response_v2(response, agent):
    """
    Parse the LLM's response to extract BOTH contribution amount and reasoning.
    Returns: (contribution, reasoning, facts_used, deepseek_think, parser_meta)
    """
    expected_keys = ['contribution', 'reasoning', 'facts_used', 'deepseek_think', 'deepseek_thought']
    try:
        data = _unwrap_response_data(response)

        if 'contribution' not in data:
            raise ValueError('The response did not contain the contribution key.')
        raw_contribution = data['contribution']
        if isinstance(raw_contribution, bool):
            raise ValueError('Contribution must be an integer.')
        numeric_contribution = float(raw_contribution)
        if not numeric_contribution.is_integer():
            raise ValueError('Contribution must be an integer.')
        contribution = int(numeric_contribution)
        contribution_cap = agent.get_stage1_contribution_cap()
        if not parameters.MIN_CONTRIBUTION <= contribution <= contribution_cap:
            raise ValueError(
                f'You returned contribution={contribution}, which is outside the '
                f'allowed range [{parameters.MIN_CONTRIBUTION}, {contribution_cap}]. '
                f'Choose an integer in that range.'
            )

        reasoning = data.get('reasoning', '')
        deepseek_thought = data.get('deepseek_thought', '')
        if deepseek_thought:
            reasoning = f"<think>\n{deepseek_thought}\n</think>\n" + reasoning
        deepseek_think = data.get('deepseek_think', '')
        facts_used = data.get('facts_used', [])
        return contribution, reasoning, facts_used, deepseek_think, _make_parser_meta(data, expected_keys)
    except Exception as e:
        logger.warning(f"agent_{agent.agent_id} failed to parse contribution: {e}")
        return None, '', [], '', _make_parser_meta({}, expected_keys, True, f'Contribution parse exception: {e}')

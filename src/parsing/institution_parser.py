from parsing.response_parsing_utils import _unwrap_response_data, _make_parser_meta


def parse_institution_choice_response(response, agent_id):
    """
    Parse the LLM's response to extract the institution choice and reasoning.
    Returns: (choice, reasoning, facts_used, deepseek_think, parser_meta)
    """
    expected_keys = ['institution_choice', 'reasoning', 'facts_used', 'deepseek_think', 'deepseek_thought']
    try:
        data = _unwrap_response_data(response)
        institution_choice = str(data.get('institution_choice', '')).strip().upper()
        reasoning = data.get('reasoning', '')
        deepseek_thought = data.get('deepseek_thought', '')
        if deepseek_thought:
            reasoning = f"<think>\n{deepseek_thought}\n</think>\n" + reasoning
        deepseek_think = data.get('deepseek_think', '')
        facts_used = data.get('facts_used', [])
        if institution_choice not in ('SI', 'SFI'):
            return '', reasoning, facts_used, deepseek_think, _make_parser_meta(
                data,
                expected_keys,
                True,
                'institution_choice must be exactly SI or SFI',
            )
        return institution_choice, reasoning, facts_used, deepseek_think, _make_parser_meta(data, expected_keys)
    except Exception as e:
        return '', '', [], '', _make_parser_meta({}, expected_keys, True, f'Institution parse exception: {e}')

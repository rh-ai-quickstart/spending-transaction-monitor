"""Rule Similarity Checker - Check if a new alert rule is similar to existing rules"""

from .prompts import load_prompt
from .utils import get_llm_client


def check_rule_similarity(new_rule: str, existing_rules: list[dict]) -> dict:
    """
    Check if a new alert rule is similar to any existing rules.

    Args:
        new_rule: The new alert rule text
        existing_rules: List of existing alert rules with their natural language queries

    Returns:
        dict: Similarity result with is_similar flag and details
    """
    if not existing_rules:
        return {
            'is_similar': False,
            'similarity_score': 0.0,
            'similar_rule': None,
            'reason': 'No existing rules to compare against',
        }

    # Extract natural language queries from existing rules
    existing_queries = [
        rule.get('natural_language_query', '')
        for rule in existing_rules
        if rule.get('natural_language_query')
    ]

    if not existing_queries:
        return {
            'is_similar': False,
            'similarity_score': 0.0,
            'similar_rule': None,
            'reason': 'No existing rule queries to compare against',
        }

    client = get_llm_client()

    # Format the existing rules list for the prompt
    existing_rules_list = '\n'.join([f'- {query}' for query in existing_queries])

    prompt = load_prompt(
        'rule_similarity_checker',
        'check_similarity',
        new_rule=new_rule,
        existing_rules_list=existing_rules_list,
    )

    try:
        response = client.invoke(prompt)
        content = (
            response.content
            if hasattr(response, 'content') and response.content
            else response
        )

        # Parse JSON response
        import json

        result = json.loads(content)

        # Ensure we have the required fields
        return {
            'is_similar': result.get('is_similar', False),
            'similarity_score': float(result.get('similarity_score', 0.0)),
            'similar_rule': result.get('similar_rule'),
            'reason': result.get('reason', 'No reason provided'),
        }

    except Exception as e:
        print(f'Error in similarity checking: {e}')
        return {
            'is_similar': False,
            'similarity_score': 0.0,
            'similar_rule': None,
            'reason': f'Error during similarity check: {str(e)}',
        }

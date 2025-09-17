"""Rule Similarity Checker - Check if a new alert rule is similar to existing rules"""

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

    prompt = f"""
You are an expert at analyzing alert rules for similarity. Your task is to determine if a new alert rule is similar to any existing rules.

Rules for similarity:
1. Rules are similar if they monitor the same type of condition (e.g., daily spending, merchant transactions, location-based)
2. Rules are similar if they have the same threshold type but different values (e.g., $500 vs $300 daily spending)
3. Rules are similar if they monitor the same merchant category or location
4. Rules are NOT similar if they monitor completely different conditions

New Rule: "{new_rule}"

Existing Rules:
{chr(10).join([f'- {query}' for query in existing_queries])}

Analyze each existing rule and determine:
1. Is it similar to the new rule? (true/false)
2. What is the similarity score? (0.0 to 1.0, where 1.0 is identical)
3. What is the most similar existing rule?
4. Why are they similar or different?

Respond with a JSON object in this exact format:
{{
    "is_similar": boolean,
    "similarity_score": number,
    "similar_rule": "the most similar existing rule text or null",
    "reason": "explanation of why they are similar or different"
}}

Only return the JSON object, no additional text.
"""

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

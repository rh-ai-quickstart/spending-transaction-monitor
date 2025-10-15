import uuid

from db.models import AlertType, NotificationMethod

from .utils import clean_and_parse_json_response, get_llm_client


def create_alert_rule(alert_text: str, user_id: str) -> dict:
    """
    Creates an AlertRule by classifying the alert text and generating a complete AlertRule object.

    Args:
        alert_text: Natural language description of the alert
        user_id: ID of the user this alert rule belongs to

    Returns:
        dict: A dictionary representation of the AlertRule with classified type and metadata
    """
    print('**** in create alert rule ***')
    prompt = f"""
You are an assistant that parses natural language alert text into a structured dictionary.

You must always output a JSON object with the following fields:

- name: A short name for the alert. Default to the alert text, truncated to 100 characters if longer.
- description: A clear description of the alert text in plain English.
- amount_threshold: A float representing the amount mentioned in the alert. If no explicit amount is found, use 0.0.
- merchant_category: The merchant category mentioned (e.g., "dining", "grocery"). If not specified, use "".
- merchant_name: The specific merchant name if mentioned (e.g., "Apple", "Amazon"). If not specified, use "".
- location: The location mentioned (e.g., "New York", "outside my home state"). If not specified, use "".
- timeframe: The time window or duration mentioned in the alert text (e.g., "last 30 days", "last hour", "one week"). If not specified, use "".
- recurring_interval_days: An integer number of days for recurring charge detection.
   - If the text mentions "every 30 days", "monthly", or similar → extract it as days (30). Add 5 days to it as a buffer for billing cycles.
   - If not specified, default to 35.
   - For the new recurring charge pattern, there should be only one previous transaction excluding the last transaction.

Rules:
- If multiple categories apply, choose the most specific one (e.g., "merchant" > "spending").
- Amount thresholds may be in dollars ("$20"), percentages ("40%"), or multipliers ("3x").
  Normalize them into numeric values: 
    - "$20" → 20.0
    - "40%" → 40.0
    - "3x" → 3.0
- Timeframes should be captured verbatim (e.g., "last 30 days", "past week") if present. Otherwise, return "".
- If no numeric threshold is mentioned, amount_threshold = 0.0.
- If no recurring interval is mentioned, set recurring_interval_days = 30.
- Always return valid JSON. No extra commentary.

---

Alert text: "{alert_text}"

Return the parsed dictionary as JSON.
"""
    client = get_llm_client()
    response = client.invoke(prompt)
    content = (
        response.content
        if hasattr(response, 'content') and response.content
        else response
    )

    content_json = clean_and_parse_json_response(content)
    classification = content_json.get('alert_type')

    classification_map = {
        'spending': AlertType.AMOUNT_THRESHOLD,
        'location': AlertType.LOCATION_BASED,
        'merchant': AlertType.MERCHANT_CATEGORY,
        'pattern': AlertType.PATTERN_BASED,
    }

    alert_type = classification_map.get(classification, AlertType.PATTERN_BASED)

    alert_rule_dict = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'name': content_json.get('name'),
        'description': content_json.get('description'),
        'is_active': True,
        'alert_type': alert_type,
        'natural_language_query': alert_text,
        'trigger_count': 0,
        'amount_threshold': content_json.get('amount_threshold'),
        'merchant_category': content_json.get('merchant_category'),
        'merchant_name': content_json.get('merchant_name'),
        'location': content_json.get('location'),
        'timeframe': content_json.get('timeframe'),
        'recurring_interval_days': content_json.get('recurring_interval_days', 30),
        'sql_query': None,
        'notification_methods': [
            NotificationMethod.EMAIL
        ],  # Default to email notifications
    }

    return alert_rule_dict

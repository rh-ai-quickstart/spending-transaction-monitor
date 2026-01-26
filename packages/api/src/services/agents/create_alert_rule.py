import uuid

from db.models import AlertType, NotificationMethod

from .prompts import load_prompt
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
    prompt = load_prompt('create_alert_rule', 'parse_alert', alert_text=alert_text)
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

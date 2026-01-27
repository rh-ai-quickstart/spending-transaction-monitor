from langchain_core.tools import tool

from .prompts import load_prompt
from .utils import extract_response, get_llm_client


@tool
def generate_alert_message(
    transaction: dict, query_result: str, alert_text: str, alert_rule: dict, user: dict
) -> dict:
    """
    Generate a user-facing alert notification message and subject using the full transaction JSON.

    Args:
        transaction: Full transaction record as a dictionary
        query_result: SQL query result that triggered the alert
        alert_text: Natural language alert rule description
        alert_rule: AlertRule metadata (including alert_type)
        user: Full user record as a dictionary

    Returns:
        Dict with 'subject' and 'message' keys
    """

    alert_type_enum = alert_rule.get('alert_type')
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')

    # Map AlertType to simplified categories
    alert_type_map = {
        'AMOUNT_THRESHOLD': 'spending',
        'LOCATION_BASED': 'location',
        'MERCHANT_CATEGORY': 'merchant',
        'MERCHANT_NAME': 'merchant',
        'PATTERN_BASED': 'pattern',
        'FREQUENCY_BASED': 'frequency',
        'CUSTOM_QUERY': 'custom',
    }
    alert_type = alert_type_map.get(str(alert_type_enum), 'general')

    prompt = load_prompt(
        'generate_alert_message',
        'generate_notification',
        alert_text=alert_text,
        alert_type=alert_type,
        query_result=query_result,
        transaction=transaction,
        user=user,
        first_name=first_name,
        last_name=last_name,
    )

    client = get_llm_client()
    response = client.invoke(prompt)
    if hasattr(response, 'content') and response.content:
        content = response.content
    else:
        content = response

    # Parse the response to extract subject and message
    response_text = extract_response(content)

    # Split by SUBJECT: and MESSAGE:
    subject = ''
    message = ''

    lines = response_text.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('SUBJECT:'):
            subject = line.replace('SUBJECT:', '').strip()
        elif line.strip().startswith('MESSAGE:'):
            # Get the rest of the text after MESSAGE:
            message = '\n'.join(lines[i:]).replace('MESSAGE:', '').strip()
            break

    # Fallback if parsing fails
    if not subject:
        subject = 'Transaction Alert'
    if not message:
        message = response_text

    return {'subject': subject, 'message': message}

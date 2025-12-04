from langchain_core.tools import tool

from .utils import extract_response, get_llm_client


@tool
def generate_alert_message(
    transaction: dict, query_result: str, alert_text: str, alert_rule: dict, user: dict
) -> str:
    """
    Generate a user-facing alert notification message using the full transaction JSON.

    Args:
        transaction: Full transaction record as a dictionary
        query_result: SQL query result that triggered the alert
        alert_text: Natural language alert rule description
        alert_rule: AlertRule metadata (including alert_type)
        user: Full user record as a dictionary
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

    prompt = f"""
You are generating a friendly user-facing alert notification. 
The alert HAS ALREADY BEEN TRIGGERED based on the SQL result below. 
Do NOT say "no alert" or "within expected range."

Alert Rule: "{alert_text}"
Alert Type: {alert_type}
SQL Result: {query_result}

Full Transaction JSON:
{transaction}

Full User JSON:
{user}

Instructions:
1. Use ONLY relevant fields from the transaction (amount, merchant_name, merchant_category, transaction_date, merchant_city, merchant_state, merchant_country).
2. Use ONLY relevant fields from the user (first_name, last_name, email, phone_number, address_street, address_city, address_state, address_country, address_zipcode).
2. Do NOT include technical fields like IDs, UUIDs, authorization codes, or system metadata.
3. Write a clear, concise 1–2 sentence message that explains:
   - Why the alert fired (reference the configured rule).
   - Which transaction caused it (merchant, amount, category, location, or timeframe).
4. Always use friendly, helpful, and human-readable language.
5. Use the first_name as {first_name} and last_name as {last_name} of the user to address them.


Return ONLY the final alert message text, nothing else.
"""

    client = get_llm_client()
    response = client.invoke(prompt)
    if hasattr(response, 'content') and response.content:
        content = response.content
    else:
        content = response
    return extract_response(content)

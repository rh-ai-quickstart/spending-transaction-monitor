# agents/alert_parser.py

from langchain.tools import tool

from .prompts import load_prompt
from .prompts.prompt_loader import load_schema
from .utils import extract_sql, get_llm_client


def build_prompt(
    last_transaction: dict, alert_text: str, alert_rule: dict, user: dict = None
) -> str:
    """Build the SQL generation prompt using external YAML templates."""
    user_id = last_transaction.get('user_id', '').strip()
    transaction_date = last_transaction.get('transaction_date', '')
    merchant_name = alert_rule.get('merchant_name', '').lower()
    merchant_category = alert_rule.get('merchant_category', '').lower()
    recurring_interval_days = alert_rule.get('recurring_interval_days', 35)

    # Build user context section if user data is provided
    user_context = ''
    if user:
        # Extract user location information
        home_city = user.get('address_city', 'Unknown')
        home_state = user.get('address_state', 'Unknown')
        home_country = user.get('address_country', 'Unknown')
        last_app_lat = user.get('last_app_location_latitude')
        last_app_lon = user.get('last_app_location_longitude')

        gps_location = (
            f'({last_app_lat:.6f}, {last_app_lon:.6f})'
            if last_app_lat and last_app_lon
            else 'Not available'
        )

        user_context = load_prompt(
            'alert_parser',
            'user_context',
            home_city=home_city,
            home_state=home_state,
            home_country=home_country,
            gps_location=gps_location,
        )

    # Load the shared schema
    schema = load_schema()

    # Load and render the main SQL generation prompt
    prompt = load_prompt(
        'alert_parser',
        'build_sql',
        user_id=user_id,
        transaction_date=transaction_date,
        merchant_name=merchant_name,
        merchant_category=merchant_category,
        recurring_interval_days=recurring_interval_days,
        user_context=user_context,
        last_transaction=last_transaction,
        schema=schema,
        alert_text=alert_text,
    )

    return prompt


@tool
def parse_alert_to_sql_with_context(
    transaction: dict, alert_text: str, alert_rule: dict, user: dict = None
) -> str:
    """
    Inputs: { "transaction": {dict}, "alert_text": str, "alert_rule": dict, "user": {dict} (optional) }
    Returns: SQL query
    """
    client = get_llm_client()
    prompt = build_prompt(transaction, alert_text, alert_rule, user)
    response = client.invoke(prompt)

    return extract_sql(str(response))

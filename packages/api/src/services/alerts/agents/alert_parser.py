# agents/alert_parser.py

from langchain.tools import tool

from .utils import extract_sql, get_llm_client


def build_prompt(last_transaction: dict, alert_text: str) -> str:
    user_id = last_transaction.get('user_id', '').strip()
    # Extract but don't assign unused variables
    _ = last_transaction.get('first_name', '').strip()
    _ = last_transaction.get('last_name', '').strip()
    transaction_date = last_transaction.get('transaction_date', '')
    _ = last_transaction.get('trans_num', '')

    schema = """
Table: transactions
Columns:
- id: primary key
- user_id : reference id of the user in the users table
- transaction_date: DateTime
- credit_card_num: text
- amount: float
- currency: text
- description: text
- merchant_name: text
- merchant_category: text
- merchant_city: text
- merchant_state: text
- merchant_country: text
- merchant_latitude: float
- merchant_longitude: float
- merchant_zipcode: text
- trans_num: text
- authorization_code: text

Table: users
Columns:
- id: text
- first_name: text
- last_name: text
- email: text
- phone_number: text
- address_street: text
- address_city: text
- address_state: text
- address_country: text 
- address_zipcode: integer
- last_app_location_latitude   float
- last_app_location_longitude  float
- last_app_location_timestamp  DateTime
- last_transaction_latitude   float
- last_merchant_longitude  float
- last_transaction_timestamp  DateTime
- last_merchant_city       text
- last_merchant_state      text
- last_merchant_country    text
"""

    prompt = f"""
You are a SQL assistant.
You must generate **PostgreSQL-compatible SQL** only.

❗ HARD RULES:
1. When checking for thresholds (like "more than N transactions"), 
    - Do NOT put the last transaction filter inside the same query as the COUNT.
    - Instead, compute the count in a CTE, then CROSS JOIN it with the last transaction.
    - That way, the count includes all relevant history, while the last transaction row is still returned for context.
2. Use values from last_transaction directly (e.g., 'NC' <> u.address_state).
3. Always filter by the current user: transactions.user_id = '{user_id}'.
4. For historical comparisons:
   - Only include rows with transaction_date < '{transaction_date}'.
   - Compute aggregates (AVG, SUM, COUNT) in a CTE, never inside WHERE.
5. Time-window alerts:
   - Anchor to last_transaction.transaction_date.
   - Use BETWEEN (TIMESTAMP '{transaction_date}' - INTERVAL 'X') AND TIMESTAMP '{transaction_date}'.
   - Always cast literals to TIMESTAMP before subtracting intervals.
6. Thresholds:
   - Dollar phrasing ("$20 more") → current_amount > avg_amount + 20.
   - Percentage phrasing ("20% more") → current_amount > avg_amount * 1.2.
7. Ratios:
   - Never divide by columns (e.g., current_amount / prev_amount).
   - Rewrite as multiplication and ensure prev_amount IS NOT NULL.
8. Window functions:
   - If using LAG/LEAD, do not mix with GROUP BY.
9. If GROUP BY is required:
   - Must include transactions.user_id.
   - All non-aggregated SELECT columns must be in GROUP BY.
10. Derived columns (aliases like distance, avg_amount):
    - Do not use them directly in WHERE.
    - If you need to filter by a derived column, wrap the SELECT in a subquery or CTE, then filter in the outer query.
11. In the outer SELECT, never reference table aliases (t., u.) from inside a CTE.
    - Only use the column names defined in the CTE’s SELECT list.
12. For exponentiation, always use POWER(x,2) instead of x^2.
13. If the alert can be expressed as a single SELECT (simple COUNT, SUM), do not wrap in a CTE unnecessarily.
14. Valid alerts involve: transaction amount, transaction_date, merchant info, location, or user profile.
15. If unrelated to transactions/users (e.g., weather, sports), return exactly "NOT_APPLICABLE".
16. Geospatial distance:
    - Preferred (if PostGIS is available): 
        ST_Distance(
            ST_SetSRID(ST_MakePoint(lon1, lat1), 4326)::geography,
            ST_SetSRID(ST_MakePoint(lon2, lat2), 4326)::geography
        ) / 1000
    - Fallback (if PostGIS is not available): Haversine formula in pure SQL:
        6371 * acos(
            cos(radians(lat1)) * cos(radians(lat2)) *
            cos(radians(lon2) - radians(lon1)) +
            sin(radians(lat1)) * sin(radians(lat2))
        )
    - Always return kilometers.
    - Never use ST_GeographyFromText or string concatenation with 'POINT(...)'.
19. Only use columns that exist in the provided schema. 
    - Never invent or assume extra fields (like merchant_zipcode) unless explicitly listed.
    - If a column is not present in the schema, exclude it from SELECT.
20. CTE and table aliases must be valid SQL identifiers:
    - Use snake_case (e.g., last_txn), never names with spaces.



last_transaction Input:
{last_transaction}

Schema:
{schema}

Natural language alert: "{alert_text}"

Generate a valid SQL query that evaluates only the last transaction.
SQL:
"""
    return prompt


@tool
def parse_alert_to_sql_with_context(transaction: dict, alert_text: str) -> str:
    """
    Inputs: { "transaction": {dict}, "alert_text": str }
    Returns: SQL query
    """
    client = get_llm_client()
    prompt = build_prompt(transaction, alert_text)
    response = client.invoke(prompt)

    return extract_sql(str(response))

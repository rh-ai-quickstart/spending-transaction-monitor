# agents/alert_parser.py

from langchain.tools import tool

from .utils import extract_sql, get_llm_client


def build_prompt(
    last_transaction: dict, alert_text: str, alert_rule: dict, user: dict = None
) -> str:
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

        user_context = f"""
---
USER LOCATION CONTEXT:
When the user refers to "this city", "my city", "my current location", "here", or similar:
- User's home address: {home_city}, {home_state}, {home_country}
- User's last known GPS location: {f'({last_app_lat:.6f}, {last_app_lon:.6f})' if last_app_lat and last_app_lon else 'Not available'}

To reference the user's location in SQL queries, JOIN to the users table:
  JOIN users u ON t.user_id = u.id

Examples:
- "transactions outside this city" → WHERE t.merchant_city != u.address_city
- "transactions outside my state" → WHERE t.merchant_state != u.address_state
- "transactions far from my location" → Use haversine_distance_km(u.last_app_location_latitude, u.last_app_location_longitude, t.merchant_latitude, t.merchant_longitude)

---
"""

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
{user_context}
❗ HARD RULES:
1. Always filter by the current user: transactions.user_id = '{user_id}'.
2. `last_txn` must ALWAYS include:
   - user_id
   - transaction_date
   - amount
   - merchant_name
   - merchant_category
   - trans_num
   - merchant_city
   - merchant_state
   - merchant_country
   - merchant_latitude
   - merchant_longitude
   - merchant_zipcode

   ```sql
   WITH last_txn AS (
     SELECT user_id, transaction_date, amount, merchant_name, merchant_category, trans_num
     FROM transactions
     WHERE user_id = '{user_id}'
       AND transaction_date = TIMESTAMP '{transaction_date}'
     LIMIT 1
   )
   ```
3. For aggregate comparisons (averages, thresholds, frequency counts, recurring charges):
   - If the alert involves a **specific merchant name** (e.g., "Apple"), you must:
     * Restrict `last_txn` to rows where LOWER(merchant_name) LIKE '%apple%'.
     * Compare the last transaction against the **average for its merchant_category** (e.g., electronics).
     * The final SELECT message must include the merchant name explicitly in the alert text.
     for example if the alert is: "Alert me if my transaction amount for Apple exceeds my typical electronics spend by 3x."
     then the last_txn should be:
     ```sql
     WITH last_txn AS (
      SELECT user_id, transaction_date, amount, merchant_name, merchant_category, trans_num,
            merchant_city, merchant_state, merchant_country, merchant_latitude, merchant_longitude, merchant_zipcode
      FROM transactions
      WHERE user_id = 'u-67890'
        AND transaction_date = TIMESTAMP '2025-09-18 23:08:16.189193+00:00'
        AND LOWER(merchant_name) LIKE '%apple%'
      LIMIT 1
    ) 
    ```
    and the historical should be:
    ```sql
    historical AS (
      SELECT COALESCE(AVG(t.amount), 0) AS avg_amount
      FROM transactions t
      CROSS JOIN last_txn lt
      WHERE t.user_id = lt.user_id
        AND LOWER(t.merchant_category) LIKE LOWER(lt.merchant_category)
        AND t.transaction_date >= lt.transaction_date - INTERVAL '30 days'
        AND t.transaction_date < lt.transaction_date
    )
    ```

   - If the alert involves only a **category** (e.g., dining), you must:
     * Restrict to rows where LOWER(merchant_category) LIKE '%dining%'.
     * Compare the transaction against that category’s average.
   - Always use LOWER() and LIKE with wildcards for merchant_name and merchant_category
     to handle cases like "Apple" vs "Apple Store".
   - CTEs like `historical` must always return a **single scalar aggregate** (e.g., AVG, SUM, COUNT).
   - Never return raw rows in aggregate CTEs.
   - Always use CROSS JOIN last_txn to bring in context.
   - Exclude the last transaction from history (`t.transaction_date < lt.transaction_date`).
   - Always wrap the final SELECT in a CASE ... ELSE so it returns exactly one row.

        ```sql
    historical AS (
      SELECT COALESCE(AVG(t.amount),0) AS avg_amount
      FROM transactions t
      CROSS JOIN last_txn lt
      WHERE t.user_id = lt.user_id
        AND t.merchant_category = lt.merchant_category
        AND t.transaction_date >= lt.transaction_date - INTERVAL '30 days'
        AND t.transaction_date < lt.transaction_date
    )
    SELECT CASE
      WHEN lt.amount > h.avg_amount * 1.4
        THEN 'ALERT: Dining expense exceeds 30-day average by >40%'
      ELSE 'NO_ALERT'
    END AS alert
    FROM last_txn lt
    CROSS JOIN historical h;
     ```
    - Distinguish between two types of **threshold alerts**:
      - **Transaction-based thresholds**: e.g., "Alert me if a single transaction exceeds $500".
       → Compare `last_txn.amount` directly to the threshold.
      ```sql
      lt.amount > 300
      ```
     - **Cumulative spend thresholds**: e.g., "Alert me if I spend more than $300 on dining".
       → Use `SUM(t.amount)` over the relevant time window (default: same calendar day as last_txn).
       ```sql
       SUM(t.amount) > 300
       ```
   - This ensures only one row is returned and avoids GROUPING errors.
4. For comparison alerts (exceeds average, more than $X above usual):
    - Historical aggregates must EXCLUDE the last transaction 
    ```sql
    (t.transaction_date < lt.transaction_date)
    ```

4. For cumulative/window alerts (e.g., daily/weekly spend totals):
   - The aggregate must INCLUDE the last transaction
     ```sql
     t.transaction_date BETWEEN (lt.transaction_date - INTERVAL 'X') AND lt.transaction_date
     ```

5. Time-window alerts:
   - Anchor to last_transaction.transaction_date = '{transaction_date}'.
   - Use BETWEEN (TIMESTAMP '{transaction_date}' - INTERVAL 'X') AND TIMESTAMP '{transaction_date}'.
   - Always cast literals to TIMESTAMP before subtracting intervals.
6. Recurring charge alerts:
   - If the user specifies an interval (e.g., "every 30 days", "every 90 days"):
     * Parse that interval (e.g., `interval_days = 30`).
     * Use it in SQL instead of a fixed 30 days. Add 5 days to it as a buffer for billing cycles.
     * Example:
       ```sql
       ABS(DATE_PART('day', (lt.transaction_date - prev.transaction_date)) - {recurring_interval_days}) <= 3
       ```
   - If no interval is provided, default to 30 days. Add 5 days to it as a buffer for billing cycles.
   - A "new recurring charge pattern" means:
     a) The last transaction’s merchant/category has no prior history before `(last_transaction_date - INTERVAL '{recurring_interval_days} days')`.
     b) The same merchant/category appears at least twice within the last `{recurring_interval_days}` days (including the last transaction).
  - For the new recurring charge pattern, there should be only one previous transaction excluding the last transaction.
    Historica count_transactions should be >=1 and count_prior should be 0.

7. Thresholds:
   - "$20 more" → last_txn.amount > COALESCE(h.avg_amount,0) + 20.
   - "20% more" → last_txn.amount > COALESCE(h.avg_amount,0) * 1.2.
8. Ratios:
   - Never divide by columns directly.
   - Rewrite as multiplication and ensure previous_amount IS NOT NULL.
9. Window functions:
   - If using LAG/LEAD, do not mix with GROUP BY.
10. If GROUP BY is required:
   - Must include transactions.user_id.
   - All non-aggregated SELECT columns must be in GROUP BY.
11. Derived columns:
   - Do not use them directly in WHERE.
   - Wrap in a subquery or CTE, then filter in the outer query.
12. In the outer SELECT, never reference table aliases from inside a CTE.
13. For exponentiation, always use POWER(x,2).
14. Valid alerts: transaction amount, transaction_date, merchant info, location, or user profile.
15. If unrelated (weather, sports, etc.), return exactly "NOT_APPLICABLE".
16. Geospatial distance:
   - If PostGIS is available:
     ```sql
     ST_Distance(
       ST_SetSRID(ST_MakePoint(lon1, lat1), 4326)::geography,
       ST_SetSRID(ST_MakePoint(lon2, lat2), 4326)::geography
     ) / 1000
     ```
   - If PostGIS is not available: use Haversine formula in pure SQL:
     ```sql
     6371 * acos(
       cos(radians(lat1)) * cos(radians(lat2)) *
       cos(radians(lon2) - radians(lon1)) +
       sin(radians(lat1)) * sin(radians(lat2))
     )
     ```
   - Always return kilometers.
17. Use only columns listed in schema.
18. CTE and table aliases must be valid identifiers in snake_case.
19. If the alert involves a merchant name or category, use the following:
   - merchant_name: {merchant_name}
   - merchant_category: {merchant_category}
20. Always fully qualify columns inside aggregates (e.g., t.amount).
21. Wrap aggregates in COALESCE with safe defaults to prevent NULL issues.
22. Normalize merchant_name and merchant_category with LOWER() in all comparisons.
23. For **same-merchant same-day alerts**:
   - You MUST join `transactions t` with `last_txn lt ON t.user_id = lt.user_id`.
   - Compare using `t.merchant_name = lt.merchant_name` AND `t.transaction_date::date = lt.transaction_date::date`.
   - Never reference `last_txn` columns directly without a join.

---

last_transaction Input:
{last_transaction}

Schema:
{schema}

Natural language alert: "{alert_text}"

Generate a valid SQL query that evaluates the alert.
SQL:
"""
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

"""SQL Description Generator - Generate plain English description of SQL queries"""

from .utils import get_llm_client


def generate_sql_description(alert_text: str, sql_query: str) -> str:
    """
    Generate a simple plain English description of what the SQL query does.

    Args:
        alert_text: The original natural language alert rule
        sql_query: The generated SQL query

    Returns:
        str: Plain English description of what the SQL query does,
             or a message that the alert is invalid if unrelated to financial transactions.
    """
    client = get_llm_client()

    prompt = f"""
You are an expert at explaining SQL queries in **plain English for non-technical users**.

❗ IMPORTANT RULES:
- Only generate explanations for **valid financial credit card transaction alerts** (spending, merchant, frequency, recurring, location, etc.).
- If the alert is NOT about financial transactions (e.g., weather, sports, temperature, news, or anything unrelated to credit card activity), simply respond:
  "This is not a valid financial alert rule. Alerts must be related to your credit card spending or transactions."
- Do NOT mention actual SQL, table names, or column names. 
- Use simple terms like "transactions", "spending", "amount", "category", "merchant", "location".
- Do NOT mention exact timestamps, user IDs, or system values. Instead, use phrases like "recent transactions", "within the last 30 days", "after 11 PM".
- Keep explanations generic and future-facing (alerts are for future transactions, not past samples).
- Do NOT output SQL keywords like 'ALERT' or 'NO_ALERT'.
- Do NOT mention specific users. Always explain in terms of "your transactions" or "your spending".

✅ For valid alerts, format the explanation as a numbered list:
1. What the alert monitors (spending, merchants, location, etc.)
2. What condition it is checking (e.g., more than $500, after 11 PM, multiple charges same day)
3. The timeframe (same day, past week, last 30 days, recurring interval)
4. What happens if the condition is met (e.g., you’ll receive a notification)

---

Alert Rule: "{alert_text}"

SQL Query:
{sql_query}

Now, generate the explanation.
"""

    try:
        response = client.invoke(prompt)
        content = (
            response.content
            if hasattr(response, 'content') and response.content
            else response
        )
        return content.strip()
    except Exception as e:
        print(f'Error generating SQL description: {e}')
        return f'Unable to generate description: {str(e)}'

"""SQL Description Generator - Generate plain English description of SQL queries"""

from .prompts import load_prompt
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

    prompt = load_prompt(
        'sql_description_generator',
        'explain_sql',
        alert_text=alert_text,
        sql_query=sql_query,
    )

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

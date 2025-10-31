import json
import os
import re

from .llamastack import LlamastackClient
from .llm import LLMClient
from .vertexai import VertexAIClient


def extract_response(response: str) -> str:
    # Match from SELECT ... until semicolon
    match = re.search(r'(.*)', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return response.strip()


def extract_sql(sql: str) -> str:
    # 1. Remove <think> blocks if present
    """Clean and normalize LLM SQL output."""
    # Remove reasoning tags
    if '</think>' in sql:
        sql = sql.split('</think>')[-1]

    # Extract from ```sql ... ``` block
    code_block = re.search(r'```sql(.*?)```', sql, re.DOTALL | re.IGNORECASE)
    if code_block:
        sql = code_block.group(1)

    sql = sql.strip()

    # 🔑 Safeguard: if query contains FROM ( but no WITH, wrap it as CTE
    if 'FROM (' in sql.upper() and not sql.strip().upper().startswith('WITH'):
        sql = f'WITH subquery AS ({sql}) SELECT * FROM subquery'

    return sql.strip()


def clean_and_parse_json_response(json_response: str):
    # Remove triple backticks and optional language hints (like ```json)
    cleaned = re.sub(
        r'^```[a-zA-Z]*\n?|```$', '', json_response.strip(), flags=re.MULTILINE
    )

    # Try parsing as JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {cleaned}')
        raise e


def get_llm_client():
    provider = os.getenv('LLM_PROVIDER', 'openai')
    if provider == 'vertexai':
        return VertexAIClient()
    elif provider == 'llamastack':
        return LlamastackClient()
    else:
        return LLMClient()

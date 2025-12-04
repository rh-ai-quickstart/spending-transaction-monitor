"""
Timestamp substitution utility for reusing saved SQL queries.
This allows us to reuse previously generated SQL by only updating the timestamp.
"""

import re
from typing import Any


def substitute_timestamp_in_sql(sql_query: str, new_timestamp: str) -> str:
    """
    Substitute the transaction timestamp in a saved SQL query.

    Args:
        sql_query: The saved SQL query with an existing timestamp
        new_timestamp: The new transaction timestamp to substitute

    Returns:
        SQL query with the new timestamp

    Examples:
        >>> sql = "WHERE transaction_date = TIMESTAMP '2025-09-21T07:34:44.691343+00:00'"
        >>> substitute_timestamp_in_sql(sql, '2025-09-22T10:15:30.123456+00:00')
        "WHERE transaction_date = TIMESTAMP '2025-09-22T10:15:30.123456+00:00'"
    """
    # Pattern to match TIMESTAMP 'YYYY-MM-DD...' or TIMESTAMP 'YYYY-MM-DDTHH:MM:SS...'
    # This captures various timestamp formats with or without timezone info
    pattern = r"TIMESTAMP\s+'[^']+'"

    # Replace all timestamp occurrences with the new one
    # This handles the transaction_date filter in the last_txn CTE
    substituted_sql = re.sub(
        pattern,
        f"TIMESTAMP '{new_timestamp}'",
        sql_query,
        count=1,  # Only replace the first occurrence (the transaction_date filter)
    )

    return substituted_sql


def substitute_timestamp(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node that substitutes timestamp in saved SQL query.

    This node is used when an alert rule already has a saved SQL query,
    allowing us to reuse it by only updating the transaction timestamp.

    Args:
        state: AppState containing:
            - alert_rule: dict with 'sql_query' field
            - transaction: dict with 'transaction_date' field

    Returns:
        Updated state with sql_query containing the new timestamp
    """
    alert_rule = state.get('alert_rule', {})
    transaction = state.get('transaction', {})

    saved_sql = alert_rule.get('sql_query')
    new_timestamp = transaction.get('transaction_date')

    if not saved_sql:
        raise ValueError('No saved SQL query found in alert_rule')

    if not new_timestamp:
        raise ValueError('No transaction_date found in transaction')

    # Substitute the timestamp
    updated_sql = substitute_timestamp_in_sql(saved_sql, new_timestamp)

    print(f'Substituted timestamp in SQL: {new_timestamp}')

    return {**state, 'sql_query': updated_sql}

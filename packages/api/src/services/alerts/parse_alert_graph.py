from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph

from .agents.alert_parser import parse_alert_to_sql_with_context
from .agents.create_alert_rule import create_alert_rule
from .agents.sql_executor import execute_sql


# Define app state
class AppState(dict):
    transaction: dict
    alert_text: str
    user: dict  # User profile data including location (optional)
    sql_query: str
    query_result: str
    valid_sql: bool
    alert_rule: dict  # Will store the AlertRule object


graph = StateGraph(AppState)

# Step 1: Parse alert
graph.add_node(
    'parse_alert',
    RunnableLambda(
        lambda state: {
            **state,
            'sql_query': parse_alert_to_sql_with_context.func(
                state['transaction'],
                state['alert_text'],
                state['alert_rule'],
                state.get('user'),  # Pass user for location context
            ),
        }
    ),
)

graph.add_node(
    'create_alert_rule',
    RunnableLambda(
        lambda state: {
            **state,
            'alert_rule': create_alert_rule(
                state['alert_text'], state['transaction']['user_id']
            ),
        }
    ),
)

# Step 2: Execute SQL
graph.add_node(
    'execute_sql',
    RunnableLambda(
        lambda state: {**state, 'query_result': execute_sql.func(state['sql_query'])}
    ),
)


def validate_sql(state):
    """Sets alert_triggered to True if query result indicates match."""
    result = state['query_result']
    try:
        # Naive check: if result has rows and doesn't start with "SQL Error"
        valid_sql = result and not result.startswith('SQL Error')
    except Exception:
        valid_sql = False
    print(' In generate alert ', valid_sql)
    return {**state, 'valid_sql': valid_sql}


# Step 2: Create Alert
graph.add_node('validate_sql', RunnableLambda(validate_sql))

# Edges
graph.set_entry_point('create_alert_rule')
graph.add_edge('create_alert_rule', 'parse_alert')
graph.add_edge('parse_alert', 'execute_sql')
graph.add_edge('execute_sql', 'validate_sql')

app = graph.compile()

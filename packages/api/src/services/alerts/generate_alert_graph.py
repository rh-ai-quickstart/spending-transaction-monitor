# app.py
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph

from .agents.alert_parser import parse_alert_to_sql_with_context
from .agents.create_alert_rule import create_alert_rule
from .agents.generate_alert_message import generate_alert_message
from .agents.sql_executor import execute_sql


# Define app state
class AppState(dict):
    transaction: dict
    user: dict
    alert_text: str
    sql_query: str
    query_result: str
    alert_triggered: bool
    alert_message: str
    alert_rule: dict  # Will store the AlertRule object


graph = StateGraph(AppState)


def generate_alert(state):
    """Sets alert_triggered to True if query result indicates match."""
    result = state['query_result']
    try:
        # Naive check: if result has rows and doesn't start with "SQL Error"
        alert_triggered = (
            result and not result.startswith('SQL Error') and result != '[]'
        )
    except Exception:
        alert_triggered = False
    print(' In generate alert ', alert_triggered)
    return {**state, 'alert_triggered': alert_triggered}


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

# Step 2: Create Alert
graph.add_node('create_alert', RunnableLambda(generate_alert))

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

graph.add_node(
    'generate_alert_message',
    RunnableLambda(
        lambda state: {
            **state,
            'alert_message': generate_alert_message.func(
                state['transaction'],
                state['query_result'],
                state['alert_text'],
                state['alert_rule'],
                state['user'],
            )
            if state.get('alert_triggered')
            else '',
        }
    ),
)

# Edges
graph.set_entry_point('create_alert_rule')
graph.add_edge('create_alert_rule', 'parse_alert')
graph.add_edge('parse_alert', 'execute_sql')
graph.add_edge('execute_sql', 'create_alert')
graph.add_edge('create_alert', 'generate_alert_message')

app = graph.compile()

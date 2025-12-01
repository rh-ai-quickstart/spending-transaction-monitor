# app.py
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph

from .agents.alert_parser import parse_alert_to_sql_with_context
from .agents.create_alert_rule import create_alert_rule
from .agents.generate_alert_message import generate_alert_message
from .agents.sql_executor import execute_sql
from .agents.timestamp_substitutor import substitute_timestamp


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


def should_use_saved_sql(state):
    """
    Conditional routing: decides whether to use saved SQL or generate new SQL.
    Returns 'substitute_timestamp' if SQL exists, 'parse_alert' otherwise.
    """
    alert_rule = state.get('alert_rule', {})
    saved_sql = alert_rule.get('sql_query')

    if saved_sql and saved_sql.strip():
        print('Using saved SQL query - substituting timestamp only')
        return 'substitute_timestamp'
    else:
        print('No saved SQL - generating new query')
        return 'parse_alert'


# Conditional entry node - decides routing
graph.add_node(
    'route_sql_generation',
    RunnableLambda(lambda state: state),  # Pass-through node for routing
)

# Step 1a: Parse alert (for new rules without saved SQL)
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

# Step 1b: Substitute timestamp (for existing rules with saved SQL)
graph.add_node('substitute_timestamp', RunnableLambda(substitute_timestamp))

# Step 2: Execute SQL
graph.add_node(
    'execute_sql',
    RunnableLambda(
        lambda state: {**state, 'query_result': execute_sql.func(state['sql_query'])}
    ),
)

# Step 3: Create Alert
graph.add_node('create_alert', RunnableLambda(generate_alert))

# Optional: Create Alert Rule (only for validation flow)
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

# Step 4: Generate alert message
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

# Edges - Two possible flows:
# Flow 1: Validation (no alert_rule exists yet)
#   create_alert_rule → parse_alert → execute_sql → create_alert → generate_alert_message
# Flow 2: Trigger (alert_rule exists with saved SQL)
#   route_sql_generation → substitute_timestamp → execute_sql → create_alert → generate_alert_message
# Flow 3: Trigger (alert_rule exists without saved SQL - fallback)
#   route_sql_generation → parse_alert → execute_sql → create_alert → generate_alert_message

# Set conditional entry point based on whether alert_rule exists
graph.set_entry_point('create_alert_rule')

# From create_alert_rule, always parse (validation flow)
graph.add_edge('create_alert_rule', 'parse_alert')

# Add routing node path
graph.add_conditional_edges(
    'route_sql_generation',
    should_use_saved_sql,
    {'substitute_timestamp': 'substitute_timestamp', 'parse_alert': 'parse_alert'},
)

# Both parse_alert and substitute_timestamp lead to execute_sql
graph.add_edge('parse_alert', 'execute_sql')
graph.add_edge('substitute_timestamp', 'execute_sql')

# Continue with common path
graph.add_edge('execute_sql', 'create_alert')
graph.add_edge('create_alert', 'generate_alert_message')

app = graph.compile()

# Create a separate graph for triggering alerts with existing rules
trigger_graph = StateGraph(AppState)

# Add the same nodes
trigger_graph.add_node('route_sql_generation', RunnableLambda(lambda state: state))
trigger_graph.add_node(
    'parse_alert',
    RunnableLambda(
        lambda state: {
            **state,
            'sql_query': parse_alert_to_sql_with_context(
                {
                    'transaction': state['transaction'],
                    'alert_text': state['alert_text'],
                    'alert_rule': state['alert_rule'],
                }
            ),
        }
    ),
)
trigger_graph.add_node('substitute_timestamp', RunnableLambda(substitute_timestamp))
trigger_graph.add_node(
    'execute_sql',
    RunnableLambda(
        lambda state: {**state, 'query_result': execute_sql(state['sql_query'])}
    ),
)
trigger_graph.add_node('create_alert', RunnableLambda(generate_alert))
trigger_graph.add_node(
    'generate_alert_message',
    RunnableLambda(
        lambda state: {
            **state,
            'alert_message': generate_alert_message(
                {
                    'transaction': state['transaction'],
                    'query_result': state['query_result'],
                    'alert_text': state['alert_text'],
                    'alert_rule': state['alert_rule'],
                    'user': state['user'],
                }
            )
            if state.get('alert_triggered')
            else '',
        }
    ),
)

# Set entry point to routing node
trigger_graph.set_entry_point('route_sql_generation')

# Add conditional routing
trigger_graph.add_conditional_edges(
    'route_sql_generation',
    should_use_saved_sql,
    {'substitute_timestamp': 'substitute_timestamp', 'parse_alert': 'parse_alert'},
)

# Both paths converge at execute_sql
trigger_graph.add_edge('parse_alert', 'execute_sql')
trigger_graph.add_edge('substitute_timestamp', 'execute_sql')
trigger_graph.add_edge('execute_sql', 'create_alert')
trigger_graph.add_edge('create_alert', 'generate_alert_message')

# Compile the trigger graph
trigger_app = trigger_graph.compile()

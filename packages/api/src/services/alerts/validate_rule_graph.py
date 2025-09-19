# validate_rule_graph.py
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph

from .agents.alert_parser import parse_alert_to_sql_with_context
from .agents.create_alert_rule import create_alert_rule
from .agents.rule_similarity_checker import check_rule_similarity
from .agents.sql_description_generator import generate_sql_description
from .agents.sql_executor import execute_sql


# Define app state for validation
class ValidationState(dict):
    transaction: dict
    alert_text: str
    user_id: str
    existing_rules: list[dict]
    sql_query: str
    query_result: str
    valid_sql: bool
    rule_applicable: bool
    alert_rule: dict
    similarity_result: dict
    sql_description: str
    validation_status: str  # 'valid', 'warning', 'invalid'
    validation_message: str


graph = StateGraph(ValidationState)


def create_alert_rule_node(state):
    """Create alert rule object from natural language text"""
    return {
        **state,
        'alert_rule': create_alert_rule(state['alert_text'], state['user_id']),
    }


def parse_alert_node(state):
    """Parse alert text to SQL query"""
    return {
        **state,
        'sql_query': parse_alert_to_sql_with_context(
            {
                'transaction': state['transaction'],
                'alert_text': state['alert_text'],
                'alert_rule': state['alert_rule'],
            }
        ),
    }


def execute_sql_node(state):
    """Execute SQL query to validate it works"""
    return {**state, 'query_result': execute_sql(state['sql_query'])}


def validate_sql_node(state):
    """Validate that SQL query executed successfully and rule is applicable"""
    result = state['query_result']
    try:
        # Check for SQL errors
        if not result or result.startswith('SQL Error'):
            valid_sql = False
            rule_applicable = False
        # Check for NOT_APPLICABLE (rule doesn't make sense)
        elif 'NOT_APPLICABLE' in result:
            valid_sql = True  # SQL executed fine
            rule_applicable = False  # But rule is not applicable
        # Check for NO_ALERT or empty results (valid rule, just no matches)
        # Note: SQL executor converts NO_ALERT to '[]', so we check for both
        elif 'NO_ALERT' in result or result == '[]' or result.strip() == '':
            valid_sql = True
            rule_applicable = True
        # Any other result means rule is valid and applicable
        else:
            valid_sql = True
            rule_applicable = True
    except Exception:
        valid_sql = False
        rule_applicable = False

    print(
        f"SQL Validation - Result: '{result}', Valid SQL: {valid_sql}, Rule Applicable: {rule_applicable}"
    )

    return {**state, 'valid_sql': valid_sql, 'rule_applicable': rule_applicable}


def check_similarity_node(state):
    """Check if the new rule is similar to existing rules"""
    return {
        **state,
        'similarity_result': check_rule_similarity(
            state['alert_text'], state['existing_rules']
        ),
    }


def generate_description_node(state):
    """Generate plain English description of what the SQL query does"""
    return {
        **state,
        'sql_description': generate_sql_description(
            state['alert_text'], state['sql_query']
        ),
    }


def determine_validation_status(state):
    """Determine final validation status based on all checks"""
    print(
        f'Final validation - Valid SQL: {state.get("valid_sql")}, Rule Applicable: {state.get("rule_applicable")}'
    )

    # Check if SQL is valid
    if not state.get('valid_sql', False):
        print('Validation failed: Invalid SQL')
        alert_text = state.get('alert_text', 'Unknown alert rule')
        return {
            **state,
            'validation_status': 'invalid',
            'validation_message': f'Invalid Alert Rule: "{alert_text}" — Only Financial Transaction Alerts Are Supported.',
        }

    # Check if rule is applicable
    if not state.get('rule_applicable', False):
        print('Validation failed: Rule not applicable')
        alert_text = state.get('alert_text', 'Unknown alert rule')
        return {
            **state,
            'validation_status': 'invalid',
            'validation_message': f'The alert rule "{alert_text}" is not applicable to your transaction data. Please try a different rule.',
        }

    # Check for similar rules
    similarity = state.get('similarity_result', {})
    if similarity.get('is_similar', False):
        print('Validation warning: Similar rule detected')
        return {
            **state,
            'validation_status': 'warning',
            'validation_message': f"Similar rule detected: '{similarity.get('similar_rule', '')}'. This rule may be redundant.",
        }

    print('Validation successful: Rule is valid')
    return {
        **state,
        'validation_status': 'valid',
        'validation_message': 'Alert rule validated successfully and ready to create.',
    }


# Add nodes to graph
graph.add_node('create_alert_rule', RunnableLambda(create_alert_rule_node))
graph.add_node('parse_alert', RunnableLambda(parse_alert_node))
graph.add_node('execute_sql', RunnableLambda(execute_sql_node))
graph.add_node('validate_sql', RunnableLambda(validate_sql_node))
graph.add_node('check_similarity', RunnableLambda(check_similarity_node))
graph.add_node('generate_description', RunnableLambda(generate_description_node))
graph.add_node('determine_status', RunnableLambda(determine_validation_status))

# Define edges
graph.set_entry_point('create_alert_rule')
graph.add_edge('create_alert_rule', 'parse_alert')
graph.add_edge('parse_alert', 'execute_sql')
graph.add_edge('execute_sql', 'validate_sql')
graph.add_edge('validate_sql', 'check_similarity')
graph.add_edge('check_similarity', 'generate_description')
graph.add_edge('generate_description', 'determine_status')

app = graph.compile()

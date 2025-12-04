"""
E2E tests for location-based alert rules with user context

Tests that the LLM receives proper user location context when processing
natural language queries that reference "this city", "my location", etc.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import AlertType, Transaction, User
from services.alerts.alert_rule_service import AlertRuleService


@pytest.fixture
def mock_session_with_user():
    """Create a mock database session with user data"""
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()

    # Mock user with location data
    mock_user = MagicMock(spec=User)
    mock_user.id = 'user-123'
    mock_user.first_name = 'John'
    mock_user.last_name = 'Doe'
    mock_user.email = 'john.doe@example.com'
    mock_user.address_city = 'San Francisco'
    mock_user.address_state = 'CA'
    mock_user.address_country = 'US'
    mock_user.address_zipcode = '94102'
    mock_user.last_app_location_latitude = 37.7749
    mock_user.last_app_location_longitude = -122.4194
    mock_user.last_app_location_timestamp = datetime(2024, 1, 15, 10, 0, 0)

    # Mock transaction
    mock_transaction = MagicMock(spec=Transaction)
    mock_transaction.id = 'tx-456'
    mock_transaction.user_id = 'user-123'
    mock_transaction.amount = Decimal('150.00')
    mock_transaction.currency = 'USD'
    mock_transaction.merchant_name = 'Coffee Shop'
    mock_transaction.merchant_category = 'Dining'
    mock_transaction.merchant_city = 'Los Angeles'  # Different city
    mock_transaction.merchant_state = 'CA'
    mock_transaction.merchant_country = 'US'
    mock_transaction.merchant_latitude = 34.0522
    mock_transaction.merchant_longitude = -118.2437
    mock_transaction.transaction_date = datetime(2024, 1, 15, 14, 30, 0)
    mock_transaction.trans_num = 'trans-789'

    # Configure execute to return different results based on the query
    async def mock_execute(query):
        result = MagicMock()
        # Check if it's a user query or transaction query
        if hasattr(query, '__dict__') and 'froms' in dir(query):
            # Simplified check - in reality would inspect the query more carefully
            result.scalar_one_or_none.return_value = mock_user
            result.scalars.return_value.all.return_value = []  # Empty alert rules
        result.first.return_value = None
        return result

    session.execute.side_effect = mock_execute

    return session, mock_user, mock_transaction


@pytest.mark.asyncio
async def test_validate_alert_rule_with_user_location_context(mock_session_with_user):
    """Test that user location context is passed to LLM when validating alert rules"""
    session, mock_user, mock_transaction = mock_session_with_user

    alert_service = AlertRuleService()

    # Mock the transaction service to return our mock transaction
    alert_service.transaction_service.get_latest_transaction = AsyncMock(
        return_value=mock_transaction
    )

    # Patch the validate_rule_graph to capture what gets passed to it
    with patch('services.alerts.alert_rule_service.validate_rule_graph') as mock_graph:
        mock_graph.invoke.return_value = {
            'validation_status': 'valid',
            'validation_message': 'Alert rule validated successfully',
            'alert_rule': {
                'alert_type': AlertType.LOCATION_BASED,
                'name': 'Alert for transactions outside my city',
                'description': 'Notify when spending occurs outside my home city',
            },
            'sql_query': "SELECT * FROM transactions WHERE merchant_city != 'San Francisco'",
            'sql_description': 'Alerts for transactions outside San Francisco',
            'similarity_result': {'is_similar': False},
            'valid_sql': True,
        }

        # Call validate_alert_rule with a location-based alert
        result = await alert_service.validate_alert_rule(
            rule='Alert me of transactions that take place outside this city',
            user_id='user-123',
            session=session,
        )

        # Verify that validate_rule_graph was called
        assert mock_graph.invoke.called

        # Get the arguments passed to validate_rule_graph
        call_args = mock_graph.invoke.call_args[0][0]

        # Verify that user data was included
        assert 'user' in call_args
        assert call_args['user'] is not None

        # Verify user location data is present
        user_data = call_args['user']
        assert user_data.get('address_city') == 'San Francisco'
        assert user_data.get('address_state') == 'CA'
        assert user_data.get('last_app_location_latitude') == 37.7749
        assert user_data.get('last_app_location_longitude') == -122.4194

        # Verify the result
        assert result['status'] == 'valid'


@pytest.mark.asyncio
async def test_user_location_context_in_prompt():
    """Test that build_prompt includes user location context when user data is provided"""
    from services.agents.alert_parser import build_prompt

    transaction = {
        'user_id': 'user-123',
        'transaction_date': '2024-01-15 14:30:00',
        'amount': 150.00,
        'merchant_name': 'Coffee Shop',
        'merchant_category': 'Dining',
        'merchant_city': 'Los Angeles',
    }

    alert_text = 'Alert me of transactions outside this city'

    alert_rule = {
        'merchant_name': '',
        'merchant_category': '',
        'recurring_interval_days': 35,
    }

    user = {
        'id': 'user-123',
        'address_city': 'San Francisco',
        'address_state': 'CA',
        'address_country': 'US',
        'last_app_location_latitude': 37.7749,
        'last_app_location_longitude': -122.4194,
    }

    # Build prompt with user context
    prompt = build_prompt(transaction, alert_text, alert_rule, user)

    # Verify that the prompt includes user location context
    assert 'USER LOCATION CONTEXT' in prompt
    assert 'San Francisco' in prompt
    assert 'this city' in prompt.lower() or 'my city' in prompt.lower()
    assert '37.7749' in prompt  # Latitude
    assert '-122.4194' in prompt  # Longitude

    # Verify examples are provided
    assert 'transactions outside this city' in prompt.lower()
    assert 'address_city' in prompt


@pytest.mark.asyncio
async def test_build_prompt_without_user_context():
    """Test that build_prompt works without user data (backward compatibility)"""
    from services.agents.alert_parser import build_prompt

    transaction = {
        'user_id': 'user-123',
        'transaction_date': '2024-01-15 14:30:00',
        'amount': 150.00,
        'merchant_name': 'Coffee Shop',
        'merchant_category': 'Dining',
    }

    alert_text = 'Alert me if transaction amount exceeds $200'

    alert_rule = {
        'merchant_name': '',
        'merchant_category': '',
        'recurring_interval_days': 35,
    }

    # Build prompt without user context
    prompt = build_prompt(transaction, alert_text, alert_rule, user=None)

    # Verify that the prompt still works
    assert 'You are a SQL assistant' in prompt
    assert 'user-123' in prompt
    assert 'USER LOCATION CONTEXT' not in prompt


@pytest.mark.asyncio
async def test_location_context_various_phrases():
    """Test that user context helps with various location reference phrases"""
    from services.agents.alert_parser import build_prompt

    user = {
        'id': 'user-123',
        'address_city': 'New York',
        'address_state': 'NY',
        'address_country': 'US',
        'last_app_location_latitude': 40.7128,
        'last_app_location_longitude': -74.0060,
    }

    transaction = {
        'user_id': 'user-123',
        'transaction_date': '2024-01-15 14:30:00',
        'amount': 150.00,
    }

    alert_rule = {
        'merchant_name': '',
        'merchant_category': '',
        'recurring_interval_days': 35,
    }

    # Test various location reference phrases
    test_phrases = [
        'Alert me of transactions outside this city',
        'Notify me when spending happens in my city',
        'Alert for purchases outside my current location',
        'Transactions far from here should trigger an alert',
        'Alert me when I spend outside my state',
    ]

    for phrase in test_phrases:
        prompt = build_prompt(transaction, phrase, alert_rule, user)

        # All prompts should include user location context
        assert 'USER LOCATION CONTEXT' in prompt
        assert 'New York' in prompt
        assert '40.7128' in prompt

        # Verify guidance for location references
        assert 'this city' in prompt.lower() or 'my city' in prompt.lower()


@pytest.mark.asyncio
async def test_location_context_with_missing_gps():
    """Test that prompt handles cases where GPS location is not available"""
    from services.agents.alert_parser import build_prompt

    user = {
        'id': 'user-123',
        'address_city': 'Boston',
        'address_state': 'MA',
        'address_country': 'US',
        'last_app_location_latitude': None,  # GPS not available
        'last_app_location_longitude': None,
    }

    transaction = {
        'user_id': 'user-123',
        'transaction_date': '2024-01-15 14:30:00',
        'amount': 150.00,
    }

    alert_rule = {
        'merchant_name': '',
        'merchant_category': '',
        'recurring_interval_days': 35,
    }

    prompt = build_prompt(
        transaction, 'Alert me of transactions outside this city', alert_rule, user
    )

    # Should still include user context with address
    assert 'USER LOCATION CONTEXT' in prompt
    assert 'Boston' in prompt

    # Should indicate GPS is not available
    assert 'Not available' in prompt or 'not available' in prompt.lower()

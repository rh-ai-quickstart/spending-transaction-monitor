"""Tests for core alert rule CRUD operations

Note: This file focuses on the most critical alert rule endpoints.
Full coverage of all 21 endpoints would require additional test files.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertRule, AlertType, NotificationMethod
from src.routes.alerts import (
    AlertRuleCreateRequest,
    create_alert_rule,
    delete_alert_rule,
    get_alert_rule,
    get_alert_rules,
    update_alert_rule,
)
from src.schemas.alert import AlertRuleUpdate

# ==============================================================================
# GET /rules - Get all alert rules
# ==============================================================================


@pytest.mark.asyncio
async def test_get_alert_rules_as_regular_user():
    """Test that regular users only see their own rules"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock alert rule
    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.name = 'Large Transaction Alert'
    rule.description = 'Alert on large transactions'
    rule.is_active = True
    rule.alert_type = AlertType.AMOUNT_THRESHOLD
    rule.amount_threshold = Decimal('100.00')
    rule.merchant_category = None
    rule.merchant_name = None
    rule.location = None
    rule.timeframe = None
    rule.natural_language_query = 'Alert me when transactions exceed $100'
    rule.notification_methods = [NotificationMethod.EMAIL]
    rule.created_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.last_triggered = None
    rule.trigger_count = 0

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [rule]
    session.execute.return_value = mock_result

    # Execute
    result = await get_alert_rules(
        user_id=None, is_active=None, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == 'rule-1'
    assert result[0].user_id == 'user-123'
    assert result[0].name == 'Large Transaction Alert'
    assert result[0].amount_threshold == 100.00


@pytest.mark.asyncio
async def test_get_alert_rules_as_admin_with_filter():
    """Test that admins can filter by user_id"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    # Execute - admin filtering by specific user
    result = await get_alert_rules(
        user_id='user-456', is_active=True, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 0
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_alert_rules_with_active_filter():
    """Test filtering alert rules by active status"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock active rule
    active_rule = MagicMock(spec=AlertRule)
    active_rule.id = 'rule-active'
    active_rule.user_id = 'user-123'
    active_rule.name = 'Active Rule'
    active_rule.description = 'Active alert'
    active_rule.is_active = True
    active_rule.alert_type = AlertType.AMOUNT_THRESHOLD
    active_rule.amount_threshold = Decimal('50.00')
    active_rule.merchant_category = None
    active_rule.merchant_name = None
    active_rule.location = None
    active_rule.timeframe = None
    active_rule.natural_language_query = 'Test query'
    active_rule.notification_methods = []
    active_rule.created_at = datetime(2024, 1, 1, 0, 0, 0)
    active_rule.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    active_rule.last_triggered = None
    active_rule.trigger_count = 0

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [active_rule]
    session.execute.return_value = mock_result

    # Execute
    result = await get_alert_rules(
        user_id=None, is_active=True, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 1
    assert result[0].is_active is True


# ==============================================================================
# GET /rules/{rule_id} - Get single alert rule
# ==============================================================================


@pytest.mark.asyncio
async def test_get_alert_rule_success():
    """Test getting a specific alert rule successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.name = 'Test Rule'
    rule.description = 'Test Description'
    rule.is_active = True
    rule.alert_type = AlertType.MERCHANT_CATEGORY
    rule.amount_threshold = None
    rule.merchant_category = 'Retail'
    rule.merchant_name = None
    rule.location = None
    rule.timeframe = None
    rule.natural_language_query = 'Alert on Retail purchases'
    rule.sql_query = 'SELECT * FROM transactions WHERE category = Retail'
    rule.notification_methods = [NotificationMethod.EMAIL, NotificationMethod.SMS]
    rule.created_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.last_triggered = datetime(2024, 1, 5, 10, 0, 0)
    rule.trigger_count = 5

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = rule
    session.execute.return_value = mock_result

    # Execute
    result = await get_alert_rule(
        rule_id='rule-1', session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'rule-1'
    assert result.name == 'Test Rule'
    assert result.merchant_category == 'Retail'
    assert result.trigger_count == 5
    assert result.sql_query == 'SELECT * FROM transactions WHERE category = Retail'


@pytest.mark.asyncio
async def test_get_alert_rule_not_found():
    """Test getting a non-existent alert rule"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_alert_rule(
            rule_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Alert rule not found'


# ==============================================================================
# POST /rules - Create alert rule
# ==============================================================================


@pytest.mark.asyncio
async def test_create_alert_rule_success():
    """Test creating an alert rule successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    payload = AlertRuleCreateRequest(
        alert_rule={
            'name': 'New Alert',
            'description': 'Test alert',
            'alert_type': AlertType.AMOUNT_THRESHOLD,
            'amount_threshold': 200.0,
        },
        sql_query='SELECT * FROM transactions WHERE amount > 200',
        natural_language_query='Alert when amount exceeds $200',
        notification_methods=[NotificationMethod.EMAIL],
    )

    # Mock session.refresh to set timestamps and trigger_count on the rule
    async def mock_refresh(obj):
        from datetime import UTC, datetime

        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)
        obj.trigger_count = 0
        obj.last_triggered = None

    session.refresh = AsyncMock(side_effect=mock_refresh)

    # Mock recommendation service check
    with patch(
        'src.routes.alerts.background_recommendation_service'
    ) as mock_bg_service:
        mock_bg_service.enqueue_rule_generation = AsyncMock()

        # Execute
        result = await create_alert_rule(
            payload=payload, session=session, current_user=current_user
        )

        # Assert
        assert result.user_id == 'user-123'
        assert result.name == 'New Alert'
        assert result.is_active is True
        session.add.assert_called_once()
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_alert_rule_missing_data():
    """Test creating alert rule without required data"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    payload = AlertRuleCreateRequest(
        alert_rule={},  # Empty rule data
        sql_query='',
        natural_language_query='Test query',
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_alert_rule(
            payload=payload, session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 400
    assert 'Alert rule data not provided' in exc_info.value.detail


# ==============================================================================
# PUT /rules/{rule_id} - Update alert rule
# ==============================================================================


@pytest.mark.asyncio
async def test_update_alert_rule_success():
    """Test updating an alert rule successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock existing rule
    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.name = 'Old Name'
    rule.description = 'Old Description'
    rule.is_active = True
    rule.alert_type = AlertType.AMOUNT_THRESHOLD
    rule.amount_threshold = Decimal('100.00')
    rule.merchant_category = None
    rule.merchant_name = None
    rule.location = None
    rule.timeframe = None
    rule.natural_language_query = 'Old query'
    rule.sql_query = 'Old SQL'
    rule.notification_methods = [NotificationMethod.EMAIL]
    rule.created_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.last_triggered = None
    rule.trigger_count = 0

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = rule
    session.execute.return_value = mock_result

    payload = AlertRuleUpdate(name='Updated Name', description='Updated Description')

    # Execute
    result = await update_alert_rule(
        rule_id='rule-1', payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'rule-1'
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_alert_rule_not_found():
    """Test updating a non-existent alert rule"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    payload = AlertRuleUpdate(name='Updated Name')

    with pytest.raises(HTTPException) as exc_info:
        await update_alert_rule(
            rule_id='nonexistent',
            payload=payload,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Alert rule not found'


@pytest.mark.asyncio
async def test_update_alert_rule_toggle_active():
    """Test toggling alert rule active status"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.is_active = True
    rule.name = 'Test Rule'
    rule.description = 'Test'
    rule.alert_type = AlertType.AMOUNT_THRESHOLD
    rule.amount_threshold = Decimal('100.00')
    rule.merchant_category = None
    rule.merchant_name = None
    rule.location = None
    rule.timeframe = None
    rule.natural_language_query = 'Test'
    rule.sql_query = 'Test'
    rule.notification_methods = []
    rule.created_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    rule.last_triggered = None
    rule.trigger_count = 0

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = rule
    session.execute.return_value = mock_result

    # Mock session.refresh to update the rule's is_active field
    async def mock_refresh(obj):
        obj.is_active = False

    session.refresh = AsyncMock(side_effect=mock_refresh)

    payload = AlertRuleUpdate(is_active=False)

    # Execute
    result = await update_alert_rule(
        rule_id='rule-1', payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result.is_active is False


# ==============================================================================
# DELETE /rules/{rule_id} - Delete alert rule
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_alert_rule_success():
    """Test deleting an alert rule successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'

    # Mock the select query result (for finding the rule)
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = rule

    # Mock the delete query result (for deleting notifications)
    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 0  # No notifications to delete

    # Configure session.execute to return different results based on call order
    session.execute.side_effect = [mock_select_result, mock_delete_result]

    # Execute
    result = await delete_alert_rule(
        rule_id='rule-1', session=session, current_user=current_user
    )

    # Assert
    assert (
        result['message']
        == 'Alert rule deleted successfully. 0 associated notifications were also deleted.'
    )
    session.delete.assert_called_once_with(rule)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_alert_rule_not_found():
    """Test deleting a non-existent alert rule"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await delete_alert_rule(
            rule_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Alert rule not found'


@pytest.mark.asyncio
async def test_delete_alert_rule_with_notifications():
    """Test deleting an alert rule that has associated notifications"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.notifications = [MagicMock(), MagicMock()]  # Has 2 notifications

    # Mock the select query result (for finding the rule)
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = rule

    # Mock the delete query result (for deleting notifications)
    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 2  # 2 notifications deleted

    # Configure session.execute to return different results based on call order
    session.execute.side_effect = [mock_select_result, mock_delete_result]

    # Execute
    result = await delete_alert_rule(
        rule_id='rule-1', session=session, current_user=current_user
    )

    # Assert - should delete successfully (cascade)
    assert (
        result['message']
        == 'Alert rule deleted successfully. 2 associated notifications were also deleted.'
    )
    session.delete.assert_called_once_with(rule)

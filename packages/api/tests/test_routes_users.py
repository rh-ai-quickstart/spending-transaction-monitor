"""Tests for user routes"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertRule, AlertType, CreditCard, Transaction, User
from src.routes.users import (
    LocationUpdateRequest,
    UserCreate,
    UserUpdate,
    activate_user,
    create_user,
    deactivate_user,
    delete_user,
    get_current_user_profile,
    get_user,
    get_user_credit_cards,
    get_user_rules,
    get_user_transactions,
    get_users,
    update_user,
    update_user_location,
)
from src.schemas.transaction import TransactionStatus, TransactionType

# ==============================================================================
# GET / - Get all users (admin only)
# ==============================================================================


@pytest.mark.asyncio
async def test_get_users_as_admin():
    """Test that admins can get all users"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    # Mock user
    user1 = MagicMock(spec=User)
    user1.id = 'user-1'
    user1.email = 'user1@test.com'
    user1.first_name = 'John'
    user1.last_name = 'Doe'
    user1.phone_number = '+1234567890'
    user1.sms_notifications_enabled = True
    user1.is_active = True
    user1.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user1.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    user1.creditCards = []
    user1.transactions = []

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user1]
    session.execute.return_value = mock_result

    # Execute
    result = await get_users(
        is_active=None, limit=100, offset=0, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 'user-1'
    assert result[0]['email'] == 'user1@test.com'
    assert result[0]['credit_cards_count'] == 0
    assert result[0]['transactions_count'] == 0


@pytest.mark.asyncio
async def test_get_users_with_filter():
    """Test filtering users by is_active"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    # Execute
    result = await get_users(
        is_active=True, limit=50, offset=10, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 0
    session.execute.assert_called_once()


# ==============================================================================
# GET /profile - Get current user profile
# ==============================================================================


@pytest.mark.asyncio
async def test_get_current_user_profile_success():
    """Test getting current user profile successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user
    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.email = 'user@test.com'
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    user.location_consent_given = True
    user.last_app_location_latitude = 37.7749
    user.last_app_location_longitude = -122.4194
    user.last_app_location_timestamp = datetime(2024, 2, 1, 12, 0, 0)
    user.last_app_location_accuracy = 10.0
    user.last_transaction_latitude = None
    user.last_transaction_longitude = None
    user.last_transaction_timestamp = None
    user.last_transaction_city = None
    user.last_transaction_state = None
    user.last_transaction_country = None

    # Mock database responses
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    cc_count_result = MagicMock()
    cc_count_result.scalar.return_value = 2

    tx_count_result = MagicMock()
    tx_count_result.scalar.return_value = 10

    session.execute.side_effect = [user_result, cc_count_result, tx_count_result]

    # Execute
    result = await get_current_user_profile(session=session, current_user=current_user)

    # Assert
    assert result['id'] == 'user-123'
    assert result['email'] == 'user@test.com'
    assert result['credit_cards_count'] == 2
    assert result['transactions_count'] == 10
    assert result['location_consent_given'] is True


@pytest.mark.asyncio
async def test_get_current_user_profile_not_found():
    """Test getting profile when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'nonexistent', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_profile(session=session, current_user=current_user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User profile not found'


# ==============================================================================
# GET /{user_id} - Get specific user
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_success():
    """Test getting a specific user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.email = 'user@test.com'
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    user.creditCards = []
    user.transactions = []
    user.location_consent_given = False
    user.last_app_location_latitude = None
    user.last_app_location_longitude = None
    user.last_app_location_timestamp = None
    user.last_app_location_accuracy = None
    user.last_transaction_latitude = None
    user.last_transaction_longitude = None
    user.last_transaction_timestamp = None
    user.last_transaction_city = None
    user.last_transaction_state = None
    user.last_transaction_country = None

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Execute
    result = await get_user(
        user_id='user-123', session=session, current_user=current_user
    )

    # Assert
    assert result['id'] == 'user-123'
    assert result['email'] == 'user@test.com'


@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test getting a non-existent user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user(
            user_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_user_access_denied():
    """Test that users cannot access other users"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-456'

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user(user_id='user-456', session=session, current_user=current_user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


@pytest.mark.asyncio
async def test_get_user_admin_can_access_any():
    """Test that admins can access any user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user = MagicMock(spec=User)
    user.id = 'user-456'
    user.email = 'user@test.com'
    user.first_name = 'Jane'
    user.last_name = 'Smith'
    user.phone_number = None
    user.sms_notifications_enabled = False
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    user.creditCards = []
    user.transactions = []
    user.location_consent_given = False
    user.last_app_location_latitude = None
    user.last_app_location_longitude = None
    user.last_app_location_timestamp = None
    user.last_app_location_accuracy = None
    user.last_transaction_latitude = None
    user.last_transaction_longitude = None
    user.last_transaction_timestamp = None
    user.last_transaction_city = None
    user.last_transaction_state = None
    user.last_transaction_country = None

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Execute
    result = await get_user(
        user_id='user-456', session=session, current_user=current_user
    )

    # Assert
    assert result['id'] == 'user-456'
    assert result['first_name'] == 'Jane'


# ==============================================================================
# POST / - Create user (admin only)
# ==============================================================================


@pytest.mark.asyncio
async def test_create_user_success():
    """Test creating a user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    # Mock no existing user
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    session.execute.return_value = existing_result

    # Mock refresh to add timestamps
    def mock_refresh(user):
        user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        user.updated_at = datetime(2024, 1, 1, 0, 0, 0)
        user.is_active = True
        user.location_consent_given = False
        user.last_app_location_latitude = None
        user.last_app_location_longitude = None
        user.last_app_location_timestamp = None
        user.last_app_location_accuracy = None
        user.last_transaction_latitude = None
        user.last_transaction_longitude = None
        user.last_transaction_timestamp = None
        user.last_transaction_city = None
        user.last_transaction_state = None
        user.last_transaction_country = None

    session.refresh.side_effect = mock_refresh

    payload = UserCreate(
        email='newuser@test.com',
        first_name='New',
        last_name='User',
        phone_number='+1234567890',
    )

    # Execute
    result = await create_user(
        payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result['email'] == 'newuser@test.com'
    assert result['first_name'] == 'New'
    assert result['last_name'] == 'User'
    assert result['credit_cards_count'] == 0
    assert result['transactions_count'] == 0
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_email_exists():
    """Test creating a user with an existing email"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    # Mock existing user
    existing_user = MagicMock(spec=User)
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_user
    session.execute.return_value = existing_result

    payload = UserCreate(
        email='existing@test.com',
        first_name='Test',
        last_name='User',
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_user(payload=payload, session=session, current_user=current_user)

    assert exc_info.value.status_code == 400
    assert 'already exists' in exc_info.value.detail


# ==============================================================================
# PUT /{user_id} - Update user
# ==============================================================================


@pytest.mark.asyncio
async def test_update_user_success():
    """Test updating a user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.email = 'user@test.com'
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 0, 0, 0)
    user.updated_at = datetime(2024, 1, 1, 0, 0, 0)
    user.creditCards = []
    user.transactions = []
    user.location_consent_given = False
    user.last_app_location_latitude = None
    user.last_app_location_longitude = None
    user.last_app_location_timestamp = None
    user.last_app_location_accuracy = None
    user.last_transaction_latitude = None
    user.last_transaction_longitude = None
    user.last_transaction_timestamp = None
    user.last_transaction_city = None
    user.last_transaction_state = None
    user.last_transaction_country = None

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    payload = UserUpdate(first_name='Jane', phone_number='+9876543210')

    # Execute
    result = await update_user(
        user_id='user-123', payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result['id'] == 'user-123'
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found():
    """Test updating a non-existent user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    payload = UserUpdate(first_name='Jane')

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            user_id='nonexistent',
            payload=payload,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_update_user_access_denied():
    """Test that users cannot update other users"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-456'

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    payload = UserUpdate(first_name='Jane')

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            user_id='user-456',
            payload=payload,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


@pytest.mark.asyncio
async def test_update_user_email_conflict():
    """Test updating email to one that already exists"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.email = 'user@test.com'

    existing_user = MagicMock(spec=User)
    existing_user.email = 'existing@test.com'

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_user

    session.execute.side_effect = [user_result, existing_result]

    payload = UserUpdate(email='existing@test.com')

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            user_id='user-123',
            payload=payload,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 400
    assert 'already exists' in exc_info.value.detail


# ==============================================================================
# DELETE /{user_id} - Delete user (admin only)
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_user_success():
    """Test deleting a user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user = MagicMock(spec=User)
    user.id = 'user-123'

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Execute
    result = await delete_user(
        user_id='user-123', session=session, current_user=current_user
    )

    # Assert
    assert result['message'] == 'User deleted successfully'
    session.delete.assert_called_once_with(user)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_not_found():
    """Test deleting a non-existent user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await delete_user(
            user_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


# ==============================================================================
# GET /{user_id}/rules - Get user's alert rules
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_rules_success():
    """Test getting user's alert rules"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    rule = MagicMock(spec=AlertRule)
    rule.id = 'rule-1'
    rule.user_id = 'user-123'
    rule.name = 'Test Rule'
    rule.description = 'Test Description'
    rule.is_active = True
    rule.alert_type = AlertType.AMOUNT_THRESHOLD
    rule.notification_methods = []

    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = [rule]
    session.execute.return_value = rules_result

    # Execute
    result = await get_user_rules(
        user_id='user-123', session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 'rule-1'
    assert result[0]['name'] == 'Test Rule'


@pytest.mark.asyncio
async def test_get_user_rules_access_denied():
    """Test that users cannot access other users' rules"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_rules(
            user_id='user-456', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


# ==============================================================================
# GET /{user_id}/transactions - Get user's transactions
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_transactions_success():
    """Test getting user's transactions"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock transaction
    tx = MagicMock(spec=Transaction)
    tx.id = 'tx-1'
    tx.amount = 100.50
    tx.currency = 'USD'
    tx.description = 'Test transaction'
    tx.merchant_name = 'Test Store'
    tx.merchant_category = 'Retail'
    tx.transaction_date = datetime(2024, 1, 15, 10, 30, 0)
    tx.transaction_type = TransactionType.PURCHASE
    tx.status = TransactionStatus.APPROVED

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]

    session.execute.side_effect = [user_result, tx_result]

    # Execute
    result = await get_user_transactions(
        user_id='user-123',
        limit=50,
        offset=0,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 'tx-1'
    assert result[0]['amount'] == 100.50


@pytest.mark.asyncio
async def test_get_user_transactions_user_not_found():
    """Test getting transactions when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_transactions(
            user_id='user-123',
            limit=50,
            offset=0,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_user_transactions_access_denied():
    """Test that users cannot access other users' transactions"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_transactions(
            user_id='user-456',
            limit=50,
            offset=0,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


# ==============================================================================
# GET /{user_id}/credit-cards - Get user's credit cards
# ==============================================================================


@pytest.mark.asyncio
async def test_get_user_credit_cards_success():
    """Test getting user's credit cards"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock credit card
    card = MagicMock(spec=CreditCard)
    card.id = 'card-1'
    card.card_number = '****1234'
    card.card_type = 'VISA'
    card.bank_name = 'Test Bank'
    card.card_holder_name = 'John Doe'
    card.expiry_month = 12
    card.expiry_year = 2025
    card.is_active = True
    card.created_at = datetime(2024, 1, 1, 0, 0, 0)
    card.updated_at = datetime(2024, 1, 1, 0, 0, 0)

    card_result = MagicMock()
    card_result.scalars.return_value.all.return_value = [card]

    session.execute.side_effect = [user_result, card_result]

    # Execute
    result = await get_user_credit_cards(
        user_id='user-123', is_active=None, session=session, current_user=current_user
    )

    # Assert
    assert len(result) == 1
    assert result[0]['id'] == 'card-1'
    assert result[0]['card_type'] == 'VISA'


@pytest.mark.asyncio
async def test_get_user_credit_cards_user_not_found():
    """Test getting credit cards when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_credit_cards(
            user_id='user-123',
            is_active=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_user_credit_cards_access_denied():
    """Test that users cannot access other users' credit cards"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_credit_cards(
            user_id='user-456',
            is_active=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


# ==============================================================================
# PATCH /{user_id}/deactivate - Deactivate user
# ==============================================================================


@pytest.mark.asyncio
async def test_deactivate_user_success():
    """Test deactivating a user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.is_active = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Execute
    result = await deactivate_user(
        user_id='user-123', session=session, current_user=current_user
    )

    # Assert
    assert result['message'] == 'User deactivated successfully'
    assert result['is_active'] is False
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_user_not_found():
    """Test deactivating a non-existent user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await deactivate_user(
            user_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


# ==============================================================================
# PATCH /{user_id}/activate - Activate user
# ==============================================================================


@pytest.mark.asyncio
async def test_activate_user_success():
    """Test activating a user successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.is_active = False

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Execute
    result = await activate_user(
        user_id='user-123', session=session, current_user=current_user
    )

    # Assert
    assert result['message'] == 'User activated successfully'
    assert result['is_active'] is True
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_activate_user_not_found():
    """Test activating a non-existent user"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await activate_user(
            user_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


# ==============================================================================
# POST /location - Update user location
# ==============================================================================


@pytest.mark.asyncio
async def test_update_user_location_success():
    """Test updating user location successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-123'

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    payload = LocationUpdateRequest(
        location_consent_given=True,
        last_app_location_latitude=37.7749,
        last_app_location_longitude=-122.4194,
        last_app_location_accuracy=10.0,
    )

    # Execute
    result = await update_user_location(
        payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result['success'] is True
    assert 'Location updated successfully' in result['message']
    assert result['location']['latitude'] == 37.7749
    assert result['location']['longitude'] == -122.4194
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_location_user_not_found():
    """Test updating location when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'nonexistent', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    payload = LocationUpdateRequest(
        location_consent_given=True,
        last_app_location_latitude=37.7749,
        last_app_location_longitude=-122.4194,
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_user_location(
            payload=payload, session=session, current_user=current_user
        )

    # The update_user_location function catches HTTPException and re-raises as 500
    assert exc_info.value.status_code == 500
    assert 'Unexpected error' in exc_info.value.detail
    session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_location_database_error():
    """Test handling database errors during location update"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock database error
    session.execute.side_effect = SQLAlchemyError('Database connection failed')

    payload = LocationUpdateRequest(
        location_consent_given=True,
        last_app_location_latitude=37.7749,
        last_app_location_longitude=-122.4194,
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_user_location(
            payload=payload, session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 500
    assert 'Database error' in exc_info.value.detail
    session.rollback.assert_called_once()

"""Tests for transaction routes"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CreditCard, Transaction, User
from src.routes.transactions import (
    create_credit_card,
    create_transaction,
    delete_credit_card,
    delete_transaction,
    get_category_spending,
    get_credit_card,
    get_credit_cards,
    get_transaction,
    get_transaction_summary,
    get_transactions,
    update_credit_card,
)
from src.schemas.transaction import (
    CreditCardCreate,
    CreditCardUpdate,
    TransactionCreate,
    TransactionStatus,
    TransactionType,
)

# ==============================================================================
# GET /transactions - Get all transactions with filtering
# ==============================================================================


@pytest.mark.asyncio
async def test_get_transactions_as_regular_user():
    """Test that regular users only see their own transactions"""
    # Setup
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock transaction
    tx1 = MagicMock(spec=Transaction)
    tx1.id = 'tx-1'
    tx1.user_id = 'user-123'
    tx1.credit_card_num = 'card-123'
    tx1.amount = Decimal('100.50')
    tx1.currency = 'USD'
    tx1.description = 'Test purchase'
    tx1.merchant_name = 'Test Store'
    tx1.merchant_category = 'Retail'
    tx1.transaction_date = datetime(2024, 1, 15, 10, 30, 0)
    tx1.transaction_type = TransactionType.PURCHASE
    tx1.merchant_latitude = None
    tx1.merchant_longitude = None
    tx1.merchant_city = 'San Francisco'
    tx1.merchant_state = 'CA'
    tx1.merchant_country = 'USA'
    tx1.merchant_zipcode = '94102'
    tx1.status = TransactionStatus.APPROVED
    tx1.authorization_code = 'AUTH123'
    tx1.trans_num = 'TRANS123'
    tx1.created_at = datetime(2024, 1, 15, 10, 30, 0)
    tx1.updated_at = datetime(2024, 1, 15, 10, 30, 0)

    # Mock query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx1]
    session.execute.return_value = mock_result

    # Execute
    result = await get_transactions(
        user_id=None,
        credit_card_id=None,
        merchant_category=None,
        min_amount=None,
        max_amount=None,
        start_date=None,
        end_date=None,
        limit=100,
        offset=0,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == 'tx-1'
    assert result[0].user_id == 'user-123'
    assert result[0].amount == 100.50


@pytest.mark.asyncio
async def test_get_transactions_as_admin_with_user_filter():
    """Test that admins can filter by user_id"""
    # Setup
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    tx1 = MagicMock(spec=Transaction)
    tx1.id = 'tx-1'
    tx1.user_id = 'user-456'
    tx1.credit_card_num = 'card-123'
    tx1.amount = Decimal('200.00')
    tx1.currency = 'USD'
    tx1.description = 'Admin view'
    tx1.merchant_name = 'Store'
    tx1.merchant_category = 'Shopping'
    tx1.transaction_date = datetime(2024, 2, 1, 12, 0, 0)
    tx1.transaction_type = TransactionType.PURCHASE
    tx1.merchant_latitude = None
    tx1.merchant_longitude = None
    tx1.merchant_city = None
    tx1.merchant_state = None
    tx1.merchant_country = None
    tx1.merchant_zipcode = None
    tx1.status = TransactionStatus.APPROVED
    tx1.authorization_code = None
    tx1.trans_num = None
    tx1.created_at = datetime(2024, 2, 1, 12, 0, 0)
    tx1.updated_at = datetime(2024, 2, 1, 12, 0, 0)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tx1]
    session.execute.return_value = mock_result

    # Execute
    result = await get_transactions(
        user_id='user-456',
        credit_card_id=None,
        merchant_category=None,
        min_amount=None,
        max_amount=None,
        start_date=None,
        end_date=None,
        limit=100,
        offset=0,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 1
    assert result[0].user_id == 'user-456'


@pytest.mark.asyncio
async def test_get_transactions_with_filters():
    """Test filtering transactions by multiple criteria"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    # Execute
    result = await get_transactions(
        user_id=None,
        credit_card_id='card-123',
        merchant_category='Retail',
        min_amount=50.0,
        max_amount=200.0,
        start_date='2024-01-01T00:00:00Z',
        end_date='2024-12-31T23:59:59Z',
        limit=50,
        offset=0,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 0
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_transactions_with_invalid_start_date():
    """Test that invalid start date format raises HTTPException"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_transactions(
            user_id=None,
            credit_card_id=None,
            merchant_category=None,
            min_amount=None,
            max_amount=None,
            start_date='invalid-date',
            end_date=None,
            limit=100,
            offset=0,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 400
    assert 'Invalid start date format' in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_transactions_with_invalid_end_date():
    """Test that invalid end date format raises HTTPException"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_transactions(
            user_id=None,
            credit_card_id=None,
            merchant_category=None,
            min_amount=None,
            max_amount=None,
            start_date=None,
            end_date='not-a-date',
            limit=100,
            offset=0,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 400
    assert 'Invalid end date format' in exc_info.value.detail


# ==============================================================================
# GET /transactions/{transaction_id} - Get single transaction
# ==============================================================================


@pytest.mark.asyncio
async def test_get_transaction_success():
    """Test getting a specific transaction successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    tx = MagicMock(spec=Transaction)
    tx.id = 'tx-1'
    tx.user_id = 'user-123'
    tx.credit_card_num = 'card-123'
    tx.amount = Decimal('150.00')
    tx.currency = 'USD'
    tx.description = 'Test'
    tx.merchant_name = 'Store'
    tx.merchant_category = 'Retail'
    tx.transaction_date = datetime(2024, 1, 15, 10, 30, 0)
    tx.transaction_type = TransactionType.PURCHASE
    tx.merchant_latitude = None
    tx.merchant_longitude = None
    tx.merchant_city = None
    tx.merchant_state = None
    tx.merchant_country = None
    tx.merchant_zipcode = None
    tx.status = TransactionStatus.APPROVED
    tx.authorization_code = None
    tx.trans_num = None
    tx.created_at = datetime(2024, 1, 15, 10, 30, 0)
    tx.updated_at = datetime(2024, 1, 15, 10, 30, 0)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tx
    session.execute.return_value = mock_result

    # Execute
    result = await get_transaction(
        transaction_id='tx-1', session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'tx-1'
    assert result.user_id == 'user-123'


@pytest.mark.asyncio
async def test_get_transaction_not_found():
    """Test getting a non-existent transaction"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_transaction(
            transaction_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Transaction not found'


@pytest.mark.asyncio
async def test_get_transaction_access_denied():
    """Test that users cannot access other users' transactions"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    tx = MagicMock(spec=Transaction)
    tx.user_id = 'user-456'  # Different user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tx
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_transaction(
            transaction_id='tx-1', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


@pytest.mark.asyncio
async def test_get_transaction_admin_can_access_any():
    """Test that admins can access any user's transaction"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'admin-123', 'roles': ['admin']}

    tx = MagicMock(spec=Transaction)
    tx.id = 'tx-1'
    tx.user_id = 'user-456'
    tx.credit_card_num = 'card-123'
    tx.amount = Decimal('100.00')
    tx.currency = 'USD'
    tx.description = 'Test'
    tx.merchant_name = 'Store'
    tx.merchant_category = 'Retail'
    tx.transaction_date = datetime(2024, 1, 15, 10, 30, 0)
    tx.transaction_type = TransactionType.PURCHASE
    tx.merchant_latitude = None
    tx.merchant_longitude = None
    tx.merchant_city = None
    tx.merchant_state = None
    tx.merchant_country = None
    tx.merchant_zipcode = None
    tx.status = TransactionStatus.APPROVED
    tx.authorization_code = None
    tx.trans_num = None
    tx.created_at = datetime(2024, 1, 15, 10, 30, 0)
    tx.updated_at = datetime(2024, 1, 15, 10, 30, 0)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tx
    session.execute.return_value = mock_result

    # Execute
    result = await get_transaction(
        transaction_id='tx-1', session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'tx-1'
    assert result.user_id == 'user-456'


# ==============================================================================
# POST /transactions - Create transaction
# ==============================================================================


@pytest.mark.asyncio
async def test_create_transaction_success():
    """Test creating a transaction successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}
    background_tasks = MagicMock()

    # Mock user exists
    user = MagicMock(spec=User)
    user.id = 'user-123'
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock transaction creation
    session.execute.return_value = user_result

    # Mock refresh to add timestamps to the transaction
    def mock_refresh(tx):
        tx.created_at = datetime(2024, 1, 15, 10, 30, 0)
        tx.updated_at = datetime(2024, 1, 15, 10, 30, 0)

    session.refresh.side_effect = mock_refresh

    payload = TransactionCreate(
        id='tx-new-123',
        user_id='user-123',
        credit_card_num='card-123',
        amount=150.00,
        currency='USD',
        description='Test purchase',
        merchant_name='Test Store',
        merchant_category='Retail',
        transaction_date='2024-01-15T10:30:00Z',
        transaction_type=TransactionType.PURCHASE,
        merchant_latitude=None,
        merchant_longitude=None,
        merchant_city='SF',
        merchant_state='CA',
        merchant_country='USA',
        merchant_zipcode='94102',
        status=TransactionStatus.APPROVED,
        authorization_code='AUTH123',
        trans_num='TRANS123',
    )

    # Execute
    with patch(
        'src.routes.transactions.background_alert_service'
    ) as _mock_alert_service:
        result = await create_transaction(
            payload=payload,
            background_tasks=background_tasks,
            session=session,
            current_user=current_user,
        )

    # Assert
    assert result.user_id == 'user-123'
    assert result.amount == 150.00
    assert result.merchant_name == 'Test Store'
    session.add.assert_called_once()
    session.commit.assert_called_once()
    background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_create_transaction_user_not_found():
    """Test creating a transaction when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'nonexistent-user', 'roles': []}
    background_tasks = MagicMock()

    # Mock user not found
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    payload = TransactionCreate(
        id='tx-new-123',
        user_id='nonexistent-user',
        credit_card_num='card-123',
        amount=150.00,
        currency='USD',
        description='Test',
        merchant_name='Store',
        merchant_category='Retail',
        transaction_date='2024-01-15T10:30:00Z',
        transaction_type=TransactionType.PURCHASE,
        status=TransactionStatus.APPROVED,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_transaction(
            payload=payload,
            background_tasks=background_tasks,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_create_transaction_invalid_date():
    """Test creating a transaction with invalid date format"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}
    background_tasks = MagicMock()

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    payload = TransactionCreate(
        id='tx-new-123',
        user_id='user-123',
        credit_card_num='card-123',
        amount=150.00,
        currency='USD',
        description='Test',
        merchant_name='Store',
        merchant_category='Retail',
        transaction_date='invalid-date',
        transaction_type=TransactionType.PURCHASE,
        status=TransactionStatus.APPROVED,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_transaction(
            payload=payload,
            background_tasks=background_tasks,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 400
    assert 'Invalid transaction date format' in exc_info.value.detail


# ==============================================================================
# DELETE /transactions/{transaction_id} - Delete transaction
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_transaction_success():
    """Test deleting a transaction successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    tx = MagicMock(spec=Transaction)
    tx.id = 'tx-1'

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tx
    session.execute.return_value = mock_result

    # Execute
    result = await delete_transaction(
        transaction_id='tx-1', session=session, current_user=current_user
    )

    # Assert
    assert result['message'] == 'Transaction deleted successfully'
    session.delete.assert_called_once_with(tx)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_transaction_not_found():
    """Test deleting a non-existent transaction"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await delete_transaction(
            transaction_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Transaction not found'


# ==============================================================================
# Credit Card Endpoints Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_credit_cards_with_filters():
    """Test getting credit cards with filters"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    card = MagicMock(spec=CreditCard)
    card.id = 'card-1'
    card.user_id = 'user-123'
    card.card_number = '****1234'
    card.card_type = 'VISA'
    card.bank_name = 'Test Bank'
    card.card_holder_name = 'John Doe'
    card.expiry_month = 12
    card.expiry_year = 2025
    card.is_active = True
    card.created_at = datetime(2024, 1, 1, 0, 0, 0)
    card.updated_at = datetime(2024, 1, 1, 0, 0, 0)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [card]
    session.execute.return_value = mock_result

    # Execute
    result = await get_credit_cards(
        user_id='user-123',
        is_active=True,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == 'card-1'
    assert result[0].card_type == 'VISA'


@pytest.mark.asyncio
async def test_get_credit_card_success():
    """Test getting a specific credit card"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    card = MagicMock(spec=CreditCard)
    card.id = 'card-1'
    card.user_id = 'user-123'
    card.card_number = '****1234'
    card.card_type = 'VISA'
    card.bank_name = 'Test Bank'
    card.card_holder_name = 'John Doe'
    card.expiry_month = 12
    card.expiry_year = 2025
    card.is_active = True
    card.created_at = datetime(2024, 1, 1, 0, 0, 0)
    card.updated_at = datetime(2024, 1, 1, 0, 0, 0)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = card
    session.execute.return_value = mock_result

    # Execute
    result = await get_credit_card(
        card_id='card-1', session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'card-1'
    assert result.card_type == 'VISA'


@pytest.mark.asyncio
async def test_get_credit_card_not_found():
    """Test getting a non-existent credit card"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_credit_card(
            card_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Credit card not found'


@pytest.mark.asyncio
async def test_create_credit_card_success():
    """Test creating a credit card successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user.id = 'user-123'
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Mock refresh to add timestamps to the card
    def mock_refresh(card):
        card.created_at = datetime(2024, 1, 1, 0, 0, 0)
        card.updated_at = datetime(2024, 1, 1, 0, 0, 0)

    session.refresh.side_effect = mock_refresh

    payload = CreditCardCreate(
        user_id='user-123',
        card_number='1234567890123456',
        card_type='VISA',
        bank_name='Test Bank',
        card_holder_name='John Doe',
        expiry_month=12,
        expiry_year=2025,
        is_active=True,
    )

    # Execute
    result = await create_credit_card(
        payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result.user_id == 'user-123'
    assert result.card_type == 'VISA'
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_credit_card_user_not_found():
    """Test creating a credit card when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user not found
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    payload = CreditCardCreate(
        user_id='nonexistent-user',
        card_number='1234567890123456',
        card_type='VISA',
        bank_name='Test Bank',
        card_holder_name='John Doe',
        expiry_month=12,
        expiry_year=2025,
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_credit_card(
            payload=payload, session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_update_credit_card_success():
    """Test updating a credit card successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    card = MagicMock(spec=CreditCard)
    card.id = 'card-1'
    card.user_id = 'user-123'
    card.card_number = '****1234'
    card.card_type = 'VISA'
    card.bank_name = 'Test Bank'
    card.card_holder_name = 'John Doe'
    card.expiry_month = 12
    card.expiry_year = 2025
    card.is_active = True
    card.created_at = datetime(2024, 1, 1, 0, 0, 0)
    card.updated_at = datetime(2024, 1, 1, 0, 0, 0)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = card
    session.execute.return_value = mock_result

    payload = CreditCardUpdate(is_active=False)

    # Execute
    result = await update_credit_card(
        card_id='card-1', payload=payload, session=session, current_user=current_user
    )

    # Assert
    assert result.id == 'card-1'
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_credit_card_not_found():
    """Test updating a non-existent credit card"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    payload = CreditCardUpdate(is_active=False)

    with pytest.raises(HTTPException) as exc_info:
        await update_credit_card(
            card_id='nonexistent',
            payload=payload,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Credit card not found'


@pytest.mark.asyncio
async def test_delete_credit_card_success():
    """Test deleting a credit card successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    card = MagicMock(spec=CreditCard)
    card.id = 'card-1'

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = card
    session.execute.return_value = mock_result

    # Execute
    result = await delete_credit_card(
        card_id='card-1', session=session, current_user=current_user
    )

    # Assert
    assert result['message'] == 'Credit card deleted successfully'
    session.delete.assert_called_once_with(card)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_credit_card_not_found():
    """Test deleting a non-existent credit card"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await delete_credit_card(
            card_id='nonexistent', session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'Credit card not found'


# ==============================================================================
# Analysis Endpoints Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_transaction_summary_success():
    """Test getting transaction summary successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock transactions
    tx1 = MagicMock(spec=Transaction)
    tx1.amount = Decimal('100.00')
    tx2 = MagicMock(spec=Transaction)
    tx2.amount = Decimal('200.00')
    tx3 = MagicMock(spec=Transaction)
    tx3.amount = Decimal('50.00')

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx1, tx2, tx3]

    session.execute.side_effect = [user_result, tx_result]

    # Execute
    result = await get_transaction_summary(
        user_id='user-123',
        start_date=None,
        end_date=None,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert result.totalTransactions == 3
    assert result.totalAmount == 350.0
    assert result.averageAmount == pytest.approx(116.67, rel=0.01)
    assert result.largestTransaction == 200.0
    assert result.smallestTransaction == 50.0


@pytest.mark.asyncio
async def test_get_transaction_summary_no_transactions():
    """Test getting summary when user has no transactions"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock no transactions
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = []

    session.execute.side_effect = [user_result, tx_result]

    # Execute
    result = await get_transaction_summary(
        user_id='user-123',
        start_date=None,
        end_date=None,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert result.totalTransactions == 0
    assert result.totalAmount == 0.0
    assert result.averageAmount == 0.0
    assert result.largestTransaction == 0.0
    assert result.smallestTransaction == 0.0


@pytest.mark.asyncio
async def test_get_transaction_summary_user_not_found():
    """Test getting summary when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user not found
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_transaction_summary(
            user_id='user-123',
            start_date=None,
            end_date=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_transaction_summary_access_denied():
    """Test that users cannot access other users' summaries"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_transaction_summary(
            user_id='user-456',
            start_date=None,
            end_date=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'


@pytest.mark.asyncio
async def test_get_category_spending_success():
    """Test getting category spending breakdown successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user exists
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # Mock transactions in different categories
    tx1 = MagicMock(spec=Transaction)
    tx1.merchant_category = 'Retail'
    tx1.amount = Decimal('100.00')

    tx2 = MagicMock(spec=Transaction)
    tx2.merchant_category = 'Retail'
    tx2.amount = Decimal('50.00')

    tx3 = MagicMock(spec=Transaction)
    tx3.merchant_category = 'Dining'
    tx3.amount = Decimal('75.00')

    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx1, tx2, tx3]

    session.execute.side_effect = [user_result, tx_result]

    # Execute
    result = await get_category_spending(
        user_id='user-123',
        start_date=None,
        end_date=None,
        session=session,
        current_user=current_user,
    )

    # Assert
    assert len(result) == 2
    retail = next(r for r in result if r.category == 'Retail')
    assert retail.totalAmount == 150.0
    assert retail.transactionCount == 2
    assert retail.averageAmount == 75.0

    dining = next(r for r in result if r.category == 'Dining')
    assert dining.totalAmount == 75.0
    assert dining.transactionCount == 1
    assert dining.averageAmount == 75.0


@pytest.mark.asyncio
async def test_get_category_spending_user_not_found():
    """Test getting category spending when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user not found
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_category_spending(
            user_id='user-123',
            start_date=None,
            end_date=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_category_spending_access_denied():
    """Test that users cannot access other users' category data"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    with pytest.raises(HTTPException) as exc_info:
        await get_category_spending(
            user_id='user-456',
            start_date=None,
            end_date=None,
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == 'Access denied'

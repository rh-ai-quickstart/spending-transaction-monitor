"""Test cases for TransactionService"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.models import Transaction
from services.transactions.transaction_service import TransactionService


class TestTransactionService:
    """Test suite for TransactionService"""

    @pytest.fixture
    def transaction_service(self):
        """Create a TransactionService instance for testing"""
        return TransactionService()

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction object"""
        transaction = MagicMock(spec=Transaction)
        transaction.id = 'tx-123'
        transaction.user_id = 'user-456'
        transaction.amount = Decimal('150.00')
        transaction.currency = 'USD'
        transaction.merchant_name = 'Test Store'
        transaction.merchant_category = 'Retail'
        transaction.credit_card_num = '1234567890'
        transaction.transaction_date = datetime(2024, 1, 15, 14, 30, 0)
        transaction.trans_num = 'trans-789'
        transaction.__dict__ = {
            'id': transaction.id,
            'user_id': transaction.user_id,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'merchant_name': transaction.merchant_name,
            'merchant_category': transaction.merchant_category,
            'transaction_date': transaction.transaction_date,
        }
        return transaction

    @pytest.fixture
    def multiple_transactions(self):
        """Create multiple transaction objects for testing pagination"""
        transactions = []
        for i in range(5):
            transaction = MagicMock(spec=Transaction)
            transaction.id = f'tx-{i}'
            transaction.user_id = 'user-456'
            transaction.amount = Decimal(f'{100 + i * 10}.00')
            transaction.transaction_date = datetime(2024, 1, 15 + i, 14, 30, 0)
            transactions.append(transaction)
        return transactions

    @pytest.mark.asyncio
    async def test_get_latest_transaction_success(
        self, transaction_service, mock_session, sample_transaction
    ):
        """Test successfully getting the latest transaction for a user"""
        # Arrange - Create a simple transaction object instead of using the MagicMock fixture
        from types import SimpleNamespace

        simple_transaction = SimpleNamespace(
            id='tx-123',
            user_id='user-456',
            amount=Decimal('150.00'),
            currency='USD',
            merchant_name='Test Store',
            trans_num='trans-789',
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = simple_transaction
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_latest_transaction(
            'user-456', mock_session
        )

        # Assert
        assert result == simple_transaction
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_transaction_not_found(
        self, transaction_service, mock_session
    ):
        """Test getting latest transaction when user has no transactions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_latest_transaction(
            'user-456', mock_session
        )

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_transactions_success(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test successfully getting user transactions with pagination"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions[:3]
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_user_transactions(
            'user-456', mock_session, limit=3, offset=0
        )

        # Assert
        assert result == multiple_transactions[:3]
        assert len(result) == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_transactions_empty_result(
        self, transaction_service, mock_session
    ):
        """Test getting user transactions when user has no transactions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_user_transactions(
            'user-456', mock_session
        )

        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transactions_with_filters_all_filters(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test getting transactions with all filters applied"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions[:2]
        mock_session.execute.return_value = mock_result

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # Act
        result = await transaction_service.get_transactions_with_filters(
            mock_session,
            user_id='user-456',
            credit_card_id='1234567890',
            merchant_category='Retail',
            min_amount=50.0,
            max_amount=200.0,
            start_date=start_date,
            end_date=end_date,
            limit=10,
            offset=0,
        )

        # Assert
        assert result == multiple_transactions[:2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transactions_with_filters_no_filters(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test getting transactions with no filters (all transactions)"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_transactions_with_filters(mock_session)

        # Assert
        assert result == multiple_transactions
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_success(
        self, transaction_service, mock_session, sample_transaction
    ):
        """Test successfully getting a transaction by ID"""
        # Arrange - Create a simple transaction object instead of using the MagicMock fixture
        from types import SimpleNamespace

        simple_transaction = SimpleNamespace(
            id='tx-123',
            user_id='user-456',
            amount=Decimal('150.00'),
            currency='USD',
            merchant_name='Test Store',
            trans_num='trans-789',
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = simple_transaction
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_transaction_by_id('tx-123', mock_session)

        # Assert
        assert result == simple_transaction
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_not_found(
        self, transaction_service, mock_session
    ):
        """Test getting transaction by ID when transaction doesn't exist"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_transaction_by_id(
            'tx-nonexistent', mock_session
        )

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_has_transactions_true(
        self, transaction_service, mock_session, sample_transaction
    ):
        """Test user_has_transactions returns True when user has transactions"""
        # Arrange - Create a simple transaction object instead of using the MagicMock fixture
        from types import SimpleNamespace

        simple_transaction = SimpleNamespace(
            id='tx-123',
            user_id='user-456',
            amount=Decimal('150.00'),
            currency='USD',
            merchant_name='Test Store',
            trans_num='trans-789',
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = simple_transaction
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.user_has_transactions(
            'user-456', mock_session
        )

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_has_transactions_false(self, transaction_service, mock_session):
        """Test user_has_transactions returns False when user has no transactions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.user_has_transactions(
            'user-456', mock_session
        )

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()

    def test_get_dummy_transaction(self, transaction_service):
        """Test getting a dummy transaction"""
        # Act
        result = transaction_service.get_dummy_transaction('user-456')

        # Assert
        assert isinstance(result, dict)
        assert result['user_id'] == 'user-456'
        assert result['amount'] == 100.00
        assert result['currency'] == 'USD'
        assert result['merchant_name'] == 'Dummy merchant'
        assert result['merchant_category'] == 'Dummy category'
        assert 'transaction_date' in result
        assert 'created_at' in result
        assert 'updated_at' in result

    @pytest.mark.asyncio
    async def test_get_user_transactions_with_pagination(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test getting user transactions with different pagination parameters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions[2:4]
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_user_transactions(
            'user-456', mock_session, limit=2, offset=2
        )

        # Assert
        assert result == multiple_transactions[2:4]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transactions_with_amount_filters_only(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test getting transactions with only amount filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions[1:3]
        mock_session.execute.return_value = mock_result

        # Act
        result = await transaction_service.get_transactions_with_filters(
            mock_session, min_amount=100.0, max_amount=150.0
        )

        # Assert
        assert result == multiple_transactions[1:3]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transactions_with_date_filters_only(
        self, transaction_service, mock_session, multiple_transactions
    ):
        """Test getting transactions with only date filters"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multiple_transactions[0:2]
        mock_session.execute.return_value = mock_result

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 17)

        # Act
        result = await transaction_service.get_transactions_with_filters(
            mock_session, start_date=start_date, end_date=end_date
        )

        # Assert
        assert result == multiple_transactions[0:2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(self, transaction_service, mock_session):
        """Test handling of database errors"""
        # Arrange
        mock_session.execute.side_effect = Exception('Database connection error')

        # Act & Assert
        with pytest.raises(Exception, match='Database connection error'):
            await transaction_service.get_latest_transaction('user-456', mock_session)

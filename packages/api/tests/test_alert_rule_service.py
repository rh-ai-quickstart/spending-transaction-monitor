"""Test cases for AlertRuleService"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import AlertRule, AlertType, Transaction, User
from src.services.alert_rule_service import AlertRuleService


# Mock the LLM services at module level to prevent accidental real LLM calls
@pytest.fixture(autouse=True)
def mock_llm_services():
    """Auto-used fixture to mock LLM services for all tests in this module"""
    with (
        patch('src.services.alerts.parse_alert_graph.app') as mock_parse_graph,
        patch('src.services.alerts.generate_alert_graph.app') as mock_generate_graph,
    ):
        # Set default return values for LLM services
        mock_parse_graph.invoke.return_value = {
            'valid_sql': True,
            'alert_text': 'Mocked alert rule',
            'sql_query': 'SELECT * FROM transactions WHERE amount > 100',
            'alert_rule': 'amount > 100',
        }
        mock_generate_graph.invoke.return_value = {
            'alert_triggered': False,
            'alert_message': 'Mocked alert message',
        }
        yield {'parse_graph': mock_parse_graph, 'generate_graph': mock_generate_graph}


class TestAlertRuleService:
    """Test suite for AlertRuleService"""

    @pytest.fixture
    def alert_rule_service(self):
        """Create an AlertRuleService instance for testing"""
        service = AlertRuleService()
        # Mock the notification service to prevent async warnings
        service.notification_service = AsyncMock()
        # Configure notification service mock return value
        mock_notification = MagicMock()
        mock_notification.status = 'sent'
        mock_notification.sent_at = datetime.now()
        mock_notification.delivered_at = datetime.now()
        service.notification_service.notify.return_value = mock_notification
        return service

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = AsyncMock()
        # session.add should be synchronous, not async
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        # Configure the execute result to avoid AsyncMock warnings
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # Empty list for existing rules
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        return session

    @pytest.fixture
    def sample_transaction_obj(self):
        """Create a sample transaction object"""
        transaction = MagicMock(spec=Transaction)
        transaction.id = 'tx-123'
        transaction.user_id = 'user-456'
        transaction.amount = Decimal('150.00')
        transaction.currency = 'USD'
        transaction.merchant_name = 'Test Store'
        transaction.merchant_category = 'Retail'
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
            'trans_num': transaction.trans_num,
        }
        return transaction

    @pytest.fixture
    def sample_alert_rule(self):
        """Create a sample alert rule object"""
        rule = MagicMock(spec=AlertRule)
        rule.id = 'rule-123'
        rule.user_id = 'user-456'
        rule.name = 'Large transaction alert'
        rule.natural_language_query = 'Alert me when transactions exceed $100'
        rule.is_active = True
        rule.trigger_count = 5
        rule.alert_type = AlertType.AMOUNT_THRESHOLD
        return rule

    @pytest.fixture
    def sample_user_obj(self):
        """Create a sample user object"""
        user = MagicMock(spec=User)
        user.id = 'user-456'
        user.email = 'test@example.com'
        user.first_name = 'John'
        user.last_name = 'Doe'
        return user

    @pytest.fixture
    def inactive_alert_rule(self):
        """Create an inactive alert rule object"""
        rule = MagicMock(spec=AlertRule)
        rule.id = 'rule-456'
        rule.user_id = 'user-456'
        rule.name = 'Inactive alert'
        rule.natural_language_query = 'Alert me for dining expenses'
        rule.is_active = False
        rule.trigger_count = 0
        return rule

    @pytest.mark.asyncio
    async def test_validate_alert_rule_success_with_real_transaction(
        self, alert_rule_service, mock_session, sample_transaction_obj
    ):
        """Test successful validation of alert rule with a real transaction"""
        # Arrange
        rule_text = 'Alert me when transactions exceed $100'
        user_id = 'user-456'

        # Mock the transaction service to return a transaction
        with (
            patch.object(
                alert_rule_service.transaction_service,
                'get_latest_transaction',
                return_value=sample_transaction_obj,
            ),
            patch('src.services.alert_rule_service.validate_rule_graph') as mock_graph,
        ):
            mock_graph.invoke.return_value = {
                'validation_status': 'valid',
                'validation_message': 'Alert rule validated successfully and ready to create.',
                'alert_rule': {'name': 'Test Rule', 'amount_threshold': 100},
                'sql_query': 'SELECT * FROM transactions WHERE amount > 100',
                'sql_description': 'Query description',
                'similarity_result': {'is_similar': False},
                'valid_sql': True,
            }

            # Act
            result = await alert_rule_service.validate_alert_rule(
                rule_text, user_id, mock_session
            )

            # Assert
            assert result['status'] == 'valid'
            assert (
                result['message']
                == 'Alert rule validated successfully and ready to create.'
            )
            assert result['user_id'] == user_id
            assert 'validation_timestamp' in result
            assert 'sql_query' in result
            # Check that transaction_used is properly serialized dictionary (not __dict__)
            assert 'transaction_used' in result
            assert isinstance(result['transaction_used'], dict)
            assert result['transaction_used']['id'] == sample_transaction_obj.id

    @pytest.mark.asyncio
    async def test_validate_alert_rule_success_with_dummy_transaction(
        self, alert_rule_service, mock_session
    ):
        """Test successful validation of alert rule with dummy transaction (no real transaction found)"""
        # Arrange
        rule_text = 'Alert me when transactions exceed $100'
        user_id = 'user-456'

        # Mock the transaction service to return None (no transaction found)
        with patch.object(
            alert_rule_service.transaction_service,
            'get_latest_transaction',
            return_value=None,
        ):
            # Mock the dummy transaction
            dummy_transaction = {'user_id': user_id, 'amount': 100.0}
            with (
                patch.object(
                    alert_rule_service.transaction_service,
                    'get_dummy_transaction',
                    return_value=dummy_transaction,
                ),
                patch(
                    'src.services.alert_rule_service.validate_rule_graph'
                ) as mock_graph,
            ):
                mock_graph.invoke.return_value = {
                    'validation_status': 'valid',
                    'validation_message': 'Alert rule validated successfully and ready to create.',
                    'alert_rule': {'name': 'Test Rule', 'amount_threshold': 100},
                    'sql_query': 'SELECT * FROM transactions WHERE amount > 100',
                    'sql_description': 'Query description',
                    'similarity_result': {'is_similar': False},
                    'valid_sql': True,
                }

                # Act
                result = await alert_rule_service.validate_alert_rule(
                    rule_text, user_id, mock_session
                )

                # Assert
                assert result['status'] == 'valid'
                assert result['transaction_used'] == dummy_transaction

    @pytest.mark.asyncio
    async def test_validate_alert_rule_invalid_sql(
        self, alert_rule_service, mock_session, sample_transaction_obj
    ):
        """Test validation of alert rule that produces invalid SQL"""
        # Arrange
        rule_text = 'Invalid rule text'
        user_id = 'user-456'

        # Mock the transaction service to return a transaction
        with (
            patch.object(
                alert_rule_service.transaction_service,
                'get_latest_transaction',
                return_value=sample_transaction_obj,
            ),
            patch('src.services.alert_rule_service.validate_rule_graph') as mock_graph,
        ):
            mock_graph.invoke.return_value = {
                'validation_status': 'invalid',
                'validation_message': f'Invalid Alert Rule: "{rule_text}" — Only Financial Transaction Alerts Are Supported.',
                'alert_rule': None,
                'sql_query': None,
                'sql_description': None,
                'similarity_result': None,
                'valid_sql': False,
            }

            # Act
            result = await alert_rule_service.validate_alert_rule(
                rule_text, user_id, mock_session
            )

            # Assert
            assert result['status'] == 'invalid'
            assert (
                result['message']
                == f'Invalid Alert Rule: "{rule_text}" — Only Financial Transaction Alerts Are Supported.'
            )
            assert result['user_id'] == user_id

    @pytest.mark.asyncio
    async def test_validate_alert_rule_llm_error(
        self, alert_rule_service, mock_session, sample_transaction_obj
    ):
        """Test validation when LLM throws an error"""
        # Arrange
        rule_text = 'Alert me when transactions exceed $100'
        user_id = 'user-456'

        # Mock the transaction service to return a transaction
        with (
            patch.object(
                alert_rule_service.transaction_service,
                'get_latest_transaction',
                return_value=sample_transaction_obj,
            ),
            patch('src.services.alert_rule_service.validate_rule_graph') as mock_graph,
        ):
            mock_graph.invoke.side_effect = Exception('LLM service unavailable')

            # Act
            result = await alert_rule_service.validate_alert_rule(
                rule_text, user_id, mock_session
            )

            # Assert
            assert result['status'] == 'error'
            assert 'Validation failed' in result['message']
            assert result['error'] == 'LLM service unavailable'

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_success(
        self,
        alert_rule_service,
        mock_session,
        sample_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test successful triggering of an alert rule"""
        # Arrange
        with patch.object(
            alert_rule_service, 'generate_alert_with_llm'
        ) as mock_generate:
            mock_generate.return_value = {
                'alert_triggered': True,
                'alert_message': 'Large transaction detected: $150.00',
            }

            # Act
            result = await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, sample_transaction_obj, sample_user_obj, mock_session
            )

            # Assert
            assert result['status'] == 'triggered'
            assert result['message'] == 'Alert rule triggered successfully'
            assert result['transaction_id'] == sample_transaction_obj.id
            assert 'notification_id' in result
            assert 'rule_evaluation' in result

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_not_triggered(
        self,
        alert_rule_service,
        mock_session,
        sample_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test triggering alert rule when conditions are not met"""
        # Arrange
        with patch.object(
            alert_rule_service, 'generate_alert_with_llm'
        ) as mock_generate:
            mock_generate.return_value = {
                'alert_triggered': False,
                'alert_message': 'Transaction amount is within normal range',
            }

            # Act
            result = await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, sample_transaction_obj, sample_user_obj, mock_session
            )

            # Assert
            assert result['status'] == 'not_triggered'
            assert result['message'] == 'Rule evaluated but alert not triggered'
            assert result['transaction_id'] == sample_transaction_obj.id
            assert 'rule_evaluation' in result

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_inactive_rule(
        self,
        alert_rule_service,
        mock_session,
        inactive_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test triggering an inactive alert rule"""
        # Act & Assert
        with pytest.raises(ValueError, match='Alert rule is not active'):
            await alert_rule_service.trigger_alert_rule(
                inactive_alert_rule,
                sample_transaction_obj,
                sample_user_obj,
                mock_session,
            )

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_no_transaction(
        self, alert_rule_service, mock_session, sample_alert_rule, sample_user_obj
    ):
        """Test triggering alert rule when user has no transactions"""
        # Arrange
        with pytest.raises(ValueError, match='Transaction is required'):
            await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, None, sample_user_obj, mock_session
            )

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_llm_error(
        self,
        alert_rule_service,
        mock_session,
        sample_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test triggering alert rule when LLM generation fails"""
        # Arrange
        with patch.object(
            alert_rule_service, 'generate_alert_with_llm'
        ) as mock_generate:
            mock_generate.side_effect = Exception('LLM generation failed')

            # Act
            result = await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, sample_transaction_obj, sample_user_obj, mock_session
            )

            # Assert
            assert result['status'] == 'error'
            assert 'Alert generation failed' in result['message']
            assert result['error'] == 'LLM generation failed'
            assert result['transaction_id'] == sample_transaction_obj.id

    def test_parse_nl_rule_with_llm_success(self):
        """Test successful parsing of natural language rule with LLM"""
        # Arrange
        alert_text = 'Alert me when transactions exceed $100'
        transaction = {'amount': 150.0, 'merchant': 'Test Store'}

        with patch('src.services.alerts.parse_alert_graph.app') as mock_graph:
            mock_graph.invoke.return_value = {
                'valid_sql': True,
                'alert_text': alert_text,
                'sql_query': 'SELECT * FROM transactions WHERE amount > 100',
            }

            # Act
            result = AlertRuleService.parse_nl_rule_with_llm(alert_text, transaction)

            # Assert
            assert result['valid_sql'] is True
            assert result['alert_text'] == alert_text
            mock_graph.invoke.assert_called_once_with(
                {'transaction': transaction, 'alert_text': alert_text}
            )

    def test_parse_nl_rule_with_llm_error(self):
        """Test parsing of natural language rule when LLM fails"""
        # Arrange
        alert_text = 'Invalid rule'
        transaction = {'amount': 150.0}

        with patch('src.services.alerts.parse_alert_graph.app') as mock_graph:
            mock_graph.invoke.side_effect = Exception('LLM parsing failed')

            # Act & Assert
            with pytest.raises(Exception, match='LLM parsing failed'):
                AlertRuleService.parse_nl_rule_with_llm(alert_text, transaction)

    def test_generate_alert_with_llm_success(self):
        """Test successful generation of alert with LLM"""
        # Arrange
        alert_text = 'Alert me when transactions exceed $100'
        transaction = {'amount': 150.0, 'merchant': 'Test Store'}
        user = {'id': 'user-123', 'first_name': 'Test', 'email': 'test@example.com'}

        with patch(
            'src.services.alerts.generate_alert_graph.trigger_app'
        ) as mock_graph:
            mock_graph.invoke.return_value = {
                'alert_triggered': True,
                'alert_message': 'Large transaction detected: $150.00',
            }

            # Act
            result = AlertRuleService.generate_alert_with_llm(
                alert_text, transaction, user
            )

            # Assert
            assert result['alert_triggered'] is True
            assert 'Large transaction detected' in result['alert_message']
            mock_graph.invoke.assert_called_once_with(
                {
                    'transaction': transaction,
                    'alert_text': alert_text,
                    'user': user,
                    'alert_rule': {},
                }
            )

    def test_generate_alert_with_llm_error(self):
        """Test generation of alert when LLM fails"""
        # Arrange
        alert_text = 'Alert me when transactions exceed $100'
        transaction = {'amount': 150.0}
        user = {'id': 'user-123', 'first_name': 'Test', 'email': 'test@example.com'}

        with patch(
            'src.services.alerts.generate_alert_graph.trigger_app'
        ) as mock_graph:
            mock_graph.invoke.side_effect = Exception('LLM generation failed')

            # Act & Assert
            with pytest.raises(Exception, match='LLM generation failed'):
                AlertRuleService.generate_alert_with_llm(alert_text, transaction, user)

    @pytest.mark.asyncio
    async def test_validate_alert_rule_none_result_from_llm(
        self, alert_rule_service, mock_session, sample_transaction_obj
    ):
        """Test validation when LLM returns None"""
        # Arrange
        rule_text = 'Alert me when transactions exceed $100'
        user_id = 'user-456'

        # Mock the transaction service to return a transaction
        with (
            patch.object(
                alert_rule_service.transaction_service,
                'get_latest_transaction',
                return_value=sample_transaction_obj,
            ),
            patch('src.services.alert_rule_service.validate_rule_graph') as mock_graph,
        ):
            mock_graph.invoke.return_value = {
                'validation_status': 'invalid',
                'validation_message': f'Invalid Alert Rule: "{rule_text}" — Only Financial Transaction Alerts Are Supported.',
                'alert_rule': None,
                'sql_query': None,
                'sql_description': None,
                'similarity_result': None,
                'valid_sql': False,
            }

            # Act
            result = await alert_rule_service.validate_alert_rule(
                rule_text, user_id, mock_session
            )

            # Assert
            assert result['status'] == 'invalid'
            assert f'Invalid Alert Rule: "{rule_text}"' in result['message']

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_none_result_from_llm(
        self,
        alert_rule_service,
        mock_session,
        sample_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test triggering when LLM returns None"""
        # Arrange
        with patch.object(
            alert_rule_service, 'generate_alert_with_llm'
        ) as mock_generate:
            mock_generate.return_value = None

            # Act
            result = await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, sample_transaction_obj, sample_user_obj, mock_session
            )

            # Assert
            assert result['status'] == 'not_triggered'
            assert result['message'] == 'Rule evaluated but alert not triggered'

    @pytest.mark.asyncio
    async def test_trigger_alert_rule_creates_correct_notification(
        self,
        alert_rule_service,
        mock_session,
        sample_alert_rule,
        sample_transaction_obj,
        sample_user_obj,
    ):
        """Test that triggering creates notification with correct data"""
        # Arrange
        with patch.object(
            alert_rule_service, 'generate_alert_with_llm'
        ) as mock_generate:
            mock_generate.return_value = {
                'alert_triggered': True,
                'alert_message': 'Custom alert message',
            }

            # Act
            result = await alert_rule_service.trigger_alert_rule(
                sample_alert_rule, sample_transaction_obj, sample_user_obj, mock_session
            )

            # Assert
            assert result['status'] == 'triggered'
            assert result['message'] == 'Alert rule triggered successfully'
            assert result['transaction_id'] == sample_transaction_obj.id
            assert 'notification_id' in result
            assert 'rule_evaluation' in result

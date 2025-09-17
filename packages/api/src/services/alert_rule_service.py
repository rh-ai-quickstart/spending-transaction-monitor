"""Alert Rule Service - Business logic for alert rule operations"""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AlertNotification,
    AlertRule,
    NotificationMethod,
    NotificationStatus,
    Transaction,
    User,
)
from src.services.notification_service import NotificationService

from .alerts.validate_rule_graph import app as validate_rule_graph
from .transaction_service import TransactionService
from .user_service import UserService


class AlertRuleService:
    """Service class for alert rule business logic"""

    def __init__(self):
        self.transaction_service = TransactionService()
        self.user_service = UserService()
        self.notification_service = NotificationService()

    @staticmethod
    def _transaction_to_dict(transaction: Transaction) -> dict[str, Any]:
        """Convert SQLAlchemy Transaction model to a clean dictionary"""

        # Handle datetime conversion safely
        def safe_datetime_convert(dt_obj):
            if dt_obj is None:
                return None
            if hasattr(dt_obj, 'isoformat'):
                return dt_obj.isoformat()
            return str(dt_obj)

        # Handle enum conversion safely
        def safe_enum_convert(enum_obj):
            if enum_obj is None:
                return None
            if hasattr(enum_obj, 'value'):
                return enum_obj.value
            return str(enum_obj)

        # Handle numeric conversion safely
        def safe_float_convert(num_obj):
            if num_obj is None:
                return None
            try:
                return float(num_obj)
            except (ValueError, TypeError):
                return None

        return {
            'id': getattr(transaction, 'id', None),
            'user_id': getattr(transaction, 'user_id', None),
            'credit_card_num': getattr(transaction, 'credit_card_num', None),
            'amount': safe_float_convert(getattr(transaction, 'amount', None)),
            'currency': getattr(transaction, 'currency', 'USD'),
            'description': getattr(transaction, 'description', None),
            'merchant_name': getattr(transaction, 'merchant_name', None),
            'merchant_category': getattr(transaction, 'merchant_category', None),
            'transaction_date': safe_datetime_convert(
                getattr(transaction, 'transaction_date', None)
            ),
            'transaction_type': safe_enum_convert(
                getattr(transaction, 'transaction_type', None)
            ),
            'merchant_latitude': safe_float_convert(
                getattr(transaction, 'merchant_latitude', None)
            ),
            'merchant_longitude': safe_float_convert(
                getattr(transaction, 'merchant_longitude', None)
            ),
            'merchant_zipcode': getattr(transaction, 'merchant_zipcode', None),
            'merchant_city': getattr(transaction, 'merchant_city', None),
            'merchant_state': getattr(transaction, 'merchant_state', None),
            'merchant_country': getattr(transaction, 'merchant_country', None),
            'status': safe_enum_convert(getattr(transaction, 'status', None)),
            'authorization_code': getattr(transaction, 'authorization_code', None),
            'trans_num': getattr(transaction, 'trans_num', None),
            'created_at': safe_datetime_convert(
                getattr(transaction, 'created_at', None)
            ),
            'updated_at': safe_datetime_convert(
                getattr(transaction, 'updated_at', None)
            ),
        }

    @staticmethod
    def parse_nl_rule_with_llm(
        alert_text: str, transaction: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse natural language rule using LLM."""
        try:
            # Import here to avoid event loop binding issues
            from .alerts.parse_alert_graph import app as parse_alert_graph

            # Run actual LangGraph app here
            result = parse_alert_graph.invoke(
                {'transaction': transaction, 'alert_text': alert_text}
            )
            return result
        except Exception as e:
            print('LLM parsing error:', e)
            raise e

    @staticmethod
    def generate_alert_with_llm(
        alert_text: str, transaction: dict[str, Any], user: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate alert message using LLM."""
        try:
            # Import here to avoid event loop binding issues
            from .alerts.generate_alert_graph import app as generate_alert_graph

            print(f'DEBUG: Starting LangGraph invoke with alert_text: {alert_text}')
            print(f'DEBUG: Transaction keys: {list(transaction.keys())}')
            print(f'DEBUG: User keys: {list(user.keys())}')

            # Use synchronous invoke for LangGraph to avoid event loop issues
            result = generate_alert_graph.invoke(
                {'transaction': transaction, 'alert_text': alert_text, 'user': user}
            )

            print(f'DEBUG: LangGraph result: {result}')
            return result
        except Exception as e:
            print('LLM parsing error:', e)
            import traceback

            traceback.print_exc()
            raise e

    async def validate_alert_rule(
        self, rule: str, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """
        Validate an alert rule with similarity checking against existing rules.
        Returns detailed validation results including similarity analysis and SQL description.
        """
        print('Validating rule:', rule)

        # Get latest transaction for validation
        transaction = await self.transaction_service.get_latest_transaction(
            user_id, session
        )
        transaction_dict = (
            self._transaction_to_dict(transaction)
            if transaction is not None
            else self.transaction_service.get_dummy_transaction(user_id)
        )

        # Get existing rules for similarity checking
        from sqlalchemy import select

        try:
            result = await session.execute(
                select(AlertRule).where(AlertRule.user_id == user_id)
            )
            existing_rules = result.scalars().all()
            existing_rules_dict = [
                {
                    'id': rule.id,
                    'natural_language_query': rule.natural_language_query,
                    'name': rule.name,
                    'description': rule.description,
                }
                for rule in existing_rules
            ]
        except Exception as e:
            print(f'Error fetching existing rules: {e}')
            # Fallback to empty list if fetching existing rules fails
            existing_rules_dict = []

        try:
            # Run the validation graph
            validation_result = validate_rule_graph.invoke(
                {
                    'transaction': transaction_dict,
                    'alert_text': rule,
                    'user_id': user_id,
                    'existing_rules': existing_rules_dict,
                }
            )

            result = {
                'status': validation_result.get('validation_status', 'error'),
                'message': validation_result.get(
                    'validation_message', 'Validation completed'
                ),
                'alert_rule': validation_result.get('alert_rule'),
                'sql_query': validation_result.get('sql_query'),
                'sql_description': validation_result.get('sql_description'),
                'similarity_result': validation_result.get('similarity_result'),
                'valid_sql': validation_result.get('valid_sql', False),
                'transaction_used': transaction_dict,
                'user_id': user_id,
                'validation_timestamp': datetime.now().isoformat(),
            }
            print(f'Alert rule service returning validation result: {result}')
            return result

        except Exception as e:
            print(f'Error in rule validation: {e}')
            return {
                'status': 'error',
                'message': f'Validation failed: {str(e)}',
                'error': str(e),
                'transaction_used': transaction_dict,
                'user_id': user_id,
                'validation_timestamp': datetime.now().isoformat(),
            }

    async def create_notification(
        self,
        rule: AlertRule,
        transaction: Transaction,
        user: User,
        session: AsyncSession,
        alert_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a notification for an alert rule"""

        notification = AlertNotification(
            id=str(uuid.uuid4()),
            user_id=user.id,
            alert_rule_id=rule.id,
            title=alert_result.get('alert_title', 'Alert triggered'),
            transaction_id=transaction.id,
            message=alert_result.get('alert_message', 'Alert triggered'),
            status=NotificationStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            notification_method=NotificationMethod.EMAIL,
        )
        print(f'DEBUG: Creating notification: {notification}')
        session.add(notification)
        await session.flush()  # writes to DB, no commit
        return notification

    async def send_notification(
        self, notification: AlertNotification, session: AsyncSession
    ) -> AlertNotification:
        try:
            updated_notification = await self.notification_service.notify(
                notification, session
            )
            notification.status = updated_notification.status
            notification.sent_at = updated_notification.sent_at
            notification.delivered_at = updated_notification.delivered_at
            notification.read_at = updated_notification.read_at
            notification.updated_at = datetime.now(UTC)
            session.add(notification)
            await session.commit()
            await session.refresh(notification)

        except Exception as e:
            print(f'DEBUG: Error sending notification: {e}')
            notification.status = NotificationStatus.FAILED
            notification.updated_at = datetime.now(UTC)
            session.add(notification)
            await session.commit()
            await session.refresh(notification)

        return notification

    async def trigger_alert_rule(
        self,
        rule: AlertRule,
        transaction: Transaction,
        user: User,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """
        Trigger an alert rule and create notification if conditions are met.

        Args:
            rule: The AlertRule object to trigger
            transaction: The transaction to evaluate against the rule
            user: The user who owns the rule
            session: Database session

        Returns:
            Dict with trigger results
        """
        if not rule.is_active:
            raise ValueError('Alert rule is not active')

        if transaction is None:
            raise ValueError('Transaction is required')

        if user is None:
            raise ValueError('User is required')
        transaction_id = transaction.id
        try:
            print('DEBUG: About to call generate_alert_with_llm')
            alert_result = self.generate_alert_with_llm(
                rule.natural_language_query, transaction.__dict__, user.__dict__
            )
            print(f'DEBUG: generate_alert_with_llm completed, result: {alert_result}')

            if alert_result and alert_result.get('alert_triggered', False):
                print('DEBUG: Alert was triggered - using working simplified version')
                trigger_count = rule.trigger_count

                # For now, use the simplified version that works
                try:
                    notification = await self.create_notification(
                        rule, transaction, user, session, alert_result
                    )
                    await session.refresh(rule)
                    rule.trigger_count = trigger_count + 1
                    rule.last_triggered = datetime.now(UTC)
                    session.add(rule)
                    await session.commit()
                    await session.refresh(rule)
                except Exception as e:
                    print(f'DEBUG: Error creating notification: {e}')
                    raise e

                await session.refresh(notification)
                notification = await self.send_notification(notification, session)

                return {
                    'status': 'triggered',
                    'message': 'Alert rule triggered successfully',
                    'trigger_count': trigger_count,
                    'rule_evaluation': alert_result,
                    'transaction_id': transaction_id,
                    'notification_status': notification.status,
                    'notification_id': str(uuid.uuid4()),  # Generate a fake ID for now
                }
            else:
                return {
                    'status': 'not_triggered',
                    'message': 'Rule evaluated but alert not triggered',
                    'rule_evaluation': alert_result,
                    'transaction_id': transaction_id,
                }

        except Exception as e:
            print('Alert generation failed:', e)
            transaction_id = transaction.id if transaction else 'unknown'
            return {
                'status': 'error',
                'message': f'Alert generation failed: {str(e)}',
                'error': str(e),
                'transaction_id': transaction_id,
            }

"""Alert Rule Service - Business logic for alert rule operations"""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AlertNotification,
    AlertRule,
    NotificationMethod,
    NotificationStatus,
)

from .alerts.generate_alert_graph import app as generate_alert_graph
from .alerts.parse_alert_graph import app as parse_alert_graph
from .notifications import Context, SmtpStrategy
from .transaction_service import TransactionService
from .user_service import UserService


class AlertRuleService:
    """Service class for alert rule business logic"""

    def __init__(self):
        self.transaction_service = TransactionService()
        self.user_service = UserService()

    @staticmethod
    def parse_nl_rule_with_llm(
        alert_text: str, transaction: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse natural language rule using LLM."""
        try:
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
            result = generate_alert_graph.invoke(
                {'transaction': transaction, 'alert_text': alert_text, 'user': user}
            )
            return result
        except Exception as e:
            print('LLM parsing error:', e)
            raise e

    async def validate_alert_rule(
        self, rule: str, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """
        Validate an alert rule using the latest transaction for a user.
        Returns the parsed rule structure and validation results.
        """
        print('Validating rule:', rule)
        transaction = await self.transaction_service.get_latest_transaction(
            user_id, session
        )
        transaction_dict = (
            transaction.__dict__
            if transaction is not None
            else self.transaction_service.get_dummy_transaction(user_id)
        )

        try:
            parsed_rule = self.parse_nl_rule_with_llm(rule, transaction_dict)

            if parsed_rule and parsed_rule.get('valid_sql'):
                return {
                    'status': 'valid',
                    'message': 'Alert rule validated successfully',
                    'transaction_used': transaction_dict,
                    'user_id': user_id,
                    'validation_timestamp': datetime.now().isoformat(),
                    'alert_text': parsed_rule.get('alert_text'),
                    'sql_query': parsed_rule.get('sql_query'),
                    'alert_rule': parsed_rule.get('alert_rule'),
                }
            else:
                return {
                    'status': 'invalid',
                    'transaction_used': transaction_dict,
                    'user_id': user_id,
                    'message': 'Rule could not be parsed or validated',
                    'error': 'LLM could not parse rule structure',
                    'alert_text': parsed_rule.get('alert_text')
                    if parsed_rule
                    else None,
                    'validation_timestamp': datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Validation failed: {str(e)}',
                'error': str(e),
            }

    async def trigger_alert_rule(
        self, rule: AlertRule, session: AsyncSession
    ) -> dict[str, Any]:
        """
        Trigger an alert rule and create notification if conditions are met.

        Args:
            rule: The AlertRule object to trigger
            session: Database session

        Returns:
            Dict with trigger results
        """
        if not rule.is_active:
            raise ValueError('Alert rule is not active')

        transaction = await self.transaction_service.get_latest_transaction(
            rule.user_id, session
        )
        if transaction is None:
            raise ValueError('No transaction found for user')

        # Get user data for alert generation
        user_data = await self.user_service.get_user_summary(rule.user_id, session)
        if user_data is None:
            # Fallback to dummy user data for testing
            raise ValueError('User data not found')

        try:
            alert_result = self.generate_alert_with_llm(
                rule.natural_language_query, transaction.__dict__, user_data
            )

            if alert_result and alert_result.get('alert_triggered', False):
                # Store trigger count before commit (to avoid detached instance issues)
                new_trigger_count = rule.trigger_count + 1

                # Create AlertNotification object
                notification = AlertNotification(
                    id=str(uuid.uuid4()),
                    user_id=rule.user_id,
                    alert_rule_id=rule.id,
                    transaction_id=transaction.id,
                    title=f'Alert: {rule.name}',
                    message=alert_result.get('alert_message', 'Alert triggered'),
                    notification_method=NotificationMethod.EMAIL,
                    status=NotificationStatus.PENDING,
                )

                # Send email notification
                try:
                    strategy = SmtpStrategy()
                    ctx = Context(strategy)
                    sent_notification = await ctx.send_notification(
                        notification, session
                    )
                    session.add(sent_notification)
                except Exception as e:
                    print(f'Failed to send email notification: {e}')
                    # Still add the notification to session with failed status
                    notification.status = NotificationStatus.FAILED
                    session.add(notification)

                # Update trigger count and last triggered time
                await session.execute(
                    update(AlertRule)
                    .where(AlertRule.id == rule.id)
                    .values(
                        trigger_count=new_trigger_count,
                        last_triggered=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )
                await session.commit()
                await session.refresh(rule)
                await session.refresh(notification)
                await session.refresh(transaction)
                return {
                    'status': 'triggered',
                    'message': 'Alert rule triggered successfully',
                    'trigger_count': rule.trigger_count,
                    'rule_evaluation': alert_result,
                    'transaction_id': transaction.id,
                    'notification_id': notification.id,
                }
            else:
                return {
                    'status': 'not_triggered',
                    'message': 'Rule evaluated but alert not triggered',
                    'rule_evaluation': alert_result,
                    'transaction_id': transaction.id,
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

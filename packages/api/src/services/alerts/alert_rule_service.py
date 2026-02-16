"""Alert Rule Service - Business logic for alert rule operations"""

from datetime import UTC, datetime
from typing import Any, cast
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
from services.notifications.notification_service import NotificationService
from services.transactions.transaction_service import TransactionService
from services.users.user_service import UserService

from .validate_rule_graph import app as validate_rule_graph


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
    def _user_to_dict(user: User) -> dict[str, Any]:
        """Convert SQLAlchemy User model to a clean dictionary (column values only, no relationships)."""

        def safe_datetime_convert(dt_obj):
            if dt_obj is None:
                return None
            if hasattr(dt_obj, 'isoformat'):
                return dt_obj.isoformat()
            return str(dt_obj)

        def safe_float_convert(num_obj):
            if num_obj is None:
                return None
            try:
                return float(num_obj)
            except (ValueError, TypeError):
                return None

        return {
            'id': getattr(user, 'id', None),
            'email': getattr(user, 'email', None),
            'keycloak_id': getattr(user, 'keycloak_id', None),
            'first_name': getattr(user, 'first_name', None),
            'last_name': getattr(user, 'last_name', None),
            'phone_number': getattr(user, 'phone_number', None),
            'sms_notifications_enabled': getattr(
                user, 'sms_notifications_enabled', True
            ),
            'created_at': safe_datetime_convert(getattr(user, 'created_at', None)),
            'updated_at': safe_datetime_convert(getattr(user, 'updated_at', None)),
            'is_active': getattr(user, 'is_active', True),
            'address_street': getattr(user, 'address_street', None),
            'address_city': getattr(user, 'address_city', None),
            'address_state': getattr(user, 'address_state', None),
            'address_zipcode': getattr(user, 'address_zipcode', None),
            'address_country': getattr(user, 'address_country', None),
            'credit_limit': safe_float_convert(getattr(user, 'credit_limit', None)),
            'credit_balance': safe_float_convert(getattr(user, 'credit_balance', None)),
            'location_consent_given': getattr(user, 'location_consent_given', False),
            'last_app_location_latitude': safe_float_convert(
                getattr(user, 'last_app_location_latitude', None)
            ),
            'last_app_location_longitude': safe_float_convert(
                getattr(user, 'last_app_location_longitude', None)
            ),
            'last_app_location_timestamp': safe_datetime_convert(
                getattr(user, 'last_app_location_timestamp', None)
            ),
            'last_app_location_accuracy': safe_float_convert(
                getattr(user, 'last_app_location_accuracy', None)
            ),
            'last_transaction_latitude': safe_float_convert(
                getattr(user, 'last_transaction_latitude', None)
            ),
            'last_transaction_longitude': safe_float_convert(
                getattr(user, 'last_transaction_longitude', None)
            ),
            'last_transaction_timestamp': safe_datetime_convert(
                getattr(user, 'last_transaction_timestamp', None)
            ),
            'last_transaction_city': getattr(user, 'last_transaction_city', None),
            'last_transaction_state': getattr(user, 'last_transaction_state', None),
            'last_transaction_country': getattr(user, 'last_transaction_country', None),
        }

    @staticmethod
    def parse_nl_rule_with_llm(
        alert_text: str, transaction: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse natural language rule using LLM."""
        try:
            # Import here to avoid event loop binding issues
            from .parse_alert_graph import app as parse_alert_graph

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
        alert_text: str,
        transaction: dict[str, Any],
        user: dict[str, Any],
        alert_rule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate alert message using LLM.

        Args:
            alert_text: Natural language alert description
            transaction: Transaction data
            user: User data
            alert_rule: Optional alert rule with saved SQL query

        Returns:
            Dict with alert_triggered, alert_message, and other results
        """
        try:
            # Import here to avoid event loop binding issues
            from .generate_alert_graph import trigger_app

            print(f'DEBUG: Starting LangGraph invoke with alert_text: {alert_text}')
            print(f'DEBUG: Transaction keys: {list(transaction.keys())}')
            print(f'DEBUG: User keys: {list(user.keys())}')

            if alert_rule:
                print(
                    f'DEBUG: Using existing alert_rule with SQL: {alert_rule.get("sql_query") is not None}'
                )

            # Use the trigger_app which supports both saved SQL and new generation
            result = trigger_app.invoke(
                {
                    'transaction': transaction,
                    'alert_text': alert_text,
                    'user': user,
                    'alert_rule': alert_rule or {},
                }
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

        # Get user data for location context
        from sqlalchemy import select

        user_dict = {}
        try:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                user_dict = {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'address_city': user.address_city,
                    'address_state': user.address_state,
                    'address_country': user.address_country,
                    'address_zipcode': user.address_zipcode,
                    'last_app_location_latitude': user.last_app_location_latitude,
                    'last_app_location_longitude': user.last_app_location_longitude,
                    'last_app_location_timestamp': user.last_app_location_timestamp.isoformat()
                    if user.last_app_location_timestamp
                    else None,
                }
        except Exception as e:
            print(f'Error fetching user data: {e}')
            # Continue with empty user_dict if fetching fails

        # Get existing rules for similarity checking
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
            validation_result = cast(
                dict[str, Any],
                validate_rule_graph.invoke(
                    {
                        'transaction': transaction_dict,
                        'alert_text': rule,
                        'user_id': user_id,
                        'user': user_dict,  # Pass user for location context
                        'existing_rules': existing_rules_dict,
                    }
                ),
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
            import traceback

            print(f'Error in rule validation: {e}')
            print(f'Full traceback: {traceback.format_exc()}')
            return {
                'status': 'error',
                'message': f'Validation failed: {str(e)}',
                'error': str(e),
                'transaction_used': transaction_dict,
                'user_id': user_id,
                'validation_timestamp': datetime.now().isoformat(),
            }

    async def create_notification_from_ids(
        self,
        user_id: str,
        rule_id: str,
        transaction_id: str,
        session: AsyncSession,
        alert_result: dict[str, Any],
        notification_method: NotificationMethod,
    ) -> AlertNotification:
        """Create a notification using primitive IDs (avoids ORM object access after commits)"""

        notification = AlertNotification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            alert_rule_id=rule_id,
            title=alert_result.get('alert_title', 'Alert triggered'),
            transaction_id=transaction_id,
            message=alert_result.get('alert_message', 'Alert triggered'),
            status=NotificationStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            notification_method=notification_method,
        )
        print(
            f'DEBUG: Creating notification with method {notification_method}: id={notification.id}'
        )
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
            # Update the notification object with the results
            notification.status = updated_notification.status
            notification.sent_at = updated_notification.sent_at
            notification.delivered_at = updated_notification.delivered_at
            notification.read_at = updated_notification.read_at
            notification.updated_at = datetime.now(UTC)
            session.add(notification)
            await session.commit()
            # Note: Don't refresh after commit - the object is detached and we've
            # already set all needed attributes manually above

        except Exception as e:
            print(f'DEBUG: Error sending notification: {e}')
            notification.status = NotificationStatus.FAILED
            notification.updated_at = datetime.now(UTC)
            session.add(notification)
            await session.commit()

        return notification

    def _send_notification_sync(
        self, notification: AlertNotification, sync_session, user_id: str
    ) -> None:
        """
        Send notification using synchronous operations.
        This avoids all greenlet/async context issues.
        """
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import logging
        import smtplib

        from sqlalchemy import select

        from core.config import settings

        logger = logging.getLogger(__name__)

        if notification.notification_method == NotificationMethod.EMAIL:
            # Get user email
            result = sync_session.execute(select(User.email).where(User.id == user_id))
            user_email = result.scalar_one_or_none()
            if not user_email:
                logger.error(f'User email not found for user {user_id}')
                notification.status = NotificationStatus.FAILED
                return

            try:
                # Create email message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = notification.title
                msg['From'] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
                msg['To'] = user_email

                if settings.SMTP_REPLY_TO_EMAIL:
                    msg['Reply-To'] = settings.SMTP_REPLY_TO_EMAIL

                text_part = MIMEText(notification.message, 'plain')
                msg.attach(text_part)

                # Send via SMTP
                logger.info(
                    f'🔌 Attempting SMTP connection to {settings.SMTP_HOST}:{settings.SMTP_PORT}'
                )
                if settings.SMTP_USE_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                    if settings.SMTP_USE_TLS:
                        server.starttls()

                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

                server.send_message(msg)
                server.quit()

                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(UTC)
                logger.info(f'✅ Email sent successfully to {user_email}')

            except Exception as e:
                logger.error(f'Failed to send email: {e}')
                notification.status = NotificationStatus.FAILED

        elif notification.notification_method == NotificationMethod.SMS:
            # SMS sending - requires Twilio credentials
            try:
                from twilio.rest import Client as TwilioClient

                if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                    logger.error('Twilio credentials not configured')
                    notification.status = NotificationStatus.FAILED
                    return

                # Get user phone
                result = sync_session.execute(
                    select(User.phone_number).where(User.id == user_id)
                )
                phone = result.scalar_one_or_none()
                if not phone:
                    logger.error(f'User phone not found for user {user_id}')
                    notification.status = NotificationStatus.FAILED
                    return

                client = TwilioClient(
                    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
                )
                client.messages.create(
                    body=notification.message,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=phone,
                )
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(UTC)
                logger.info(f'✅ SMS sent successfully to {phone}')

            except Exception as e:
                logger.error(f'Failed to send SMS: {e}')
                notification.status = NotificationStatus.FAILED
        else:
            # Unsupported method
            notification.status = NotificationStatus.FAILED

        notification.updated_at = datetime.now(UTC)

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

            # Convert rule to dict for the graph
            alert_rule_dict = {
                'id': rule.id,
                'user_id': rule.user_id,
                'name': rule.name,
                'description': rule.description,
                'alert_type': rule.alert_type.value
                if hasattr(rule.alert_type, 'value')
                else str(rule.alert_type),
                'natural_language_query': rule.natural_language_query,
                'sql_query': rule.sql_query,  # This is the saved SQL query
                'merchant_name': rule.merchant_name,
                'merchant_category': rule.merchant_category,
                'amount_threshold': float(rule.amount_threshold)
                if rule.amount_threshold
                else None,
                'location': rule.location,
                'timeframe': rule.timeframe,
            }

            # Serialize to column-only dicts so no SQLAlchemy relationships are
            # passed into the sync LangGraph (avoids greenlet/async lazy-load errors)
            transaction_dict = self._transaction_to_dict(transaction)
            user_dict = self._user_to_dict(user)

            # Extract primitive IDs now - we'll use these instead of ORM objects
            # after session commits to avoid expired object access / lazy loads
            user_id = user.id
            rule_id = rule.id
            transaction_id = transaction.id

            # Extract trigger_count BEFORE calling LangGraph (while session is clean)
            trigger_count = rule.trigger_count
            notification_methods = rule.notification_methods or [
                NotificationMethod.EMAIL,
                NotificationMethod.SMS,
            ]

            # Run the synchronous LangGraph directly - it uses its own sync DB connection
            # for SQL execution (psycopg2), so it doesn't affect our async session.
            alert_result = self.generate_alert_with_llm(
                rule.natural_language_query,
                transaction_dict,
                user_dict,
                alert_rule_dict,
            )
            print(f'DEBUG: generate_alert_with_llm completed, result: {alert_result}')

            if alert_result and alert_result.get('alert_triggered', False):
                print(
                    'DEBUG: Alert was triggered - creating notifications with sync DB'
                )
                print(f'DEBUG: Notification methods for alert: {notification_methods}')

                # Use SYNCHRONOUS database operations for notification creation.
                # This avoids all greenlet/async context issues because we're using
                # the same approach as sql_executor.py (psycopg2 sync driver).
                from sqlalchemy import create_engine
                from sqlalchemy import update as sql_update
                from sqlalchemy.orm import sessionmaker

                from core.config import settings

                # Create sync engine (same pattern as sql_executor.py)
                sync_db_url = settings.DATABASE_URL.replace(
                    'postgresql+asyncpg://', 'postgresql+psycopg2://'
                )
                sync_engine = create_engine(sync_db_url, echo=False)
                SyncSession = sessionmaker(
                    autocommit=False, autoflush=False, bind=sync_engine
                )

                # Store primitive values, not ORM objects (which become detached after session closes)
                notification_ids = []
                notification_statuses = []

                with SyncSession() as sync_session:
                    try:
                        for method in notification_methods:
                            notification_id = str(uuid.uuid4())
                            notification = AlertNotification(
                                id=notification_id,
                                user_id=user_id,
                                alert_rule_id=rule_id,
                                title=alert_result.get(
                                    'alert_title', 'Alert triggered'
                                ),
                                transaction_id=transaction_id,
                                message=alert_result.get(
                                    'alert_message', 'Alert triggered'
                                ),
                                status=NotificationStatus.PENDING,
                                created_at=datetime.now(UTC),
                                updated_at=datetime.now(UTC),
                                notification_method=method,
                            )
                            print(
                                f'DEBUG: Creating notification {notification_id} for method {method}'
                            )
                            sync_session.add(notification)
                            sync_session.flush()

                            # Send notification using sync SMTP/SMS (no async needed)
                            try:
                                self._send_notification_sync(
                                    notification, sync_session, user_id
                                )
                            except Exception as send_err:
                                print(f'DEBUG: Error sending notification: {send_err}')
                                notification.status = NotificationStatus.FAILED
                                notification.updated_at = datetime.now(UTC)

                            # Store primitive values BEFORE session closes
                            notification_ids.append(notification_id)
                            notification_statuses.append(notification.status)

                        # Update rule trigger count
                        sync_session.execute(
                            sql_update(AlertRule)
                            .where(AlertRule.id == rule_id)
                            .values(
                                trigger_count=trigger_count + 1,
                                last_triggered=datetime.now(UTC),
                            )
                        )
                        sync_session.commit()
                        print(
                            'DEBUG: Notifications created and rule updated successfully'
                        )

                    except Exception as e:
                        sync_session.rollback()
                        print(f'DEBUG: Error in sync notification creation: {e}')
                        raise e

                return {
                    'status': 'triggered',
                    'message': 'Alert rule triggered successfully',
                    'trigger_count': trigger_count + 1,
                    'rule_evaluation': alert_result,
                    'transaction_id': transaction_id,
                    'notification_status': notification_statuses[0]
                    if notification_statuses
                    else NotificationStatus.FAILED,
                    'notification_id': notification_ids[0]
                    if notification_ids
                    else str(uuid.uuid4()),
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

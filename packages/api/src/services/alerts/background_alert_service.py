"""Background Alert Processing Service"""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal
from db.models import AlertRule, Transaction, User

from .alert_rule_service import AlertRuleService

logger = logging.getLogger(__name__)


class BackgroundAlertService:
    """Service for processing alert rules in the background"""

    def __init__(self):
        self.alert_rule_service = AlertRuleService()

    async def process_alert_rules_async(
        self,
        user_id: str,
        transaction_id: str,
        alert_rule_ids: list[str] = None,
        session: 'AsyncSession | None' = None,
    ) -> dict[str, Any]:
        """
        Process alert rules for a transaction in the background.

        Args:
            user_id: ID of the user who owns the transaction
            transaction_id: ID of the transaction to evaluate
            alert_rule_ids: Optional list of specific alert rule IDs to process
            session: Optional externally managed AsyncSession. If None, a new one is created.

        Returns:
            Dict with processing results
        """
        from sqlalchemy import select

        try:
            # Use provided session or create a new one
            owns_session = False
            if session is None:
                owns_session = True
                session_ctx = SessionLocal()
                session = await session_ctx.__aenter__()

            try:
                # --- Transaction lookup ---
                transaction_result = await session.execute(
                    select(Transaction).where(Transaction.id == transaction_id)
                )
                transaction = transaction_result.scalar_one_or_none()
                if not transaction:
                    logger.error(f'Transaction {transaction_id} not found')
                    return {'status': 'error', 'message': 'Transaction not found'}

                # --- User lookup ---
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.error(f'User {user_id} not found')
                    return {'status': 'error', 'message': 'User not found'}

                # --- Alert rules ---
                if alert_rule_ids:
                    alerts_result = await session.execute(
                        select(AlertRule).where(
                            AlertRule.id.in_(alert_rule_ids),
                            AlertRule.user_id == user_id,
                            AlertRule.is_active,
                        )
                    )
                else:
                    alerts_result = await session.execute(
                        select(AlertRule).where(
                            AlertRule.user_id == user_id, AlertRule.is_active
                        )
                    )
                alerts = alerts_result.scalars().all()

                if not alerts:
                    logger.info(f'No active alert rules found for user {user_id}')
                    return {
                        'status': 'success',
                        'message': 'No alert rules to process',
                        'processed_count': 0,
                    }

                # --- Process each alert rule ---
                processed_count = 0
                error_count = 0
                results = []

                for alert in alerts:
                    try:
                        result = await self.alert_rule_service.trigger_alert_rule(
                            rule=alert,
                            transaction=transaction,
                            user=user,
                            session=session,
                        )
                        results.append({'alert_rule_id': alert.id, 'result': result})
                        processed_count += 1

                        if result.get('status') == 'triggered':
                            logger.info(
                                f'Alert rule {alert.id} triggered for transaction {transaction_id}'
                            )
                        else:
                            logger.debug(
                                f'Alert rule {alert.id} did not trigger for transaction {transaction_id}'
                            )
                    except Exception as e:
                        logger.error(
                            f'Error processing alert rule {alert.id}: {str(e)}'
                        )
                        error_count += 1
                        results.append({'alert_rule_id': alert.id, 'error': str(e)})

                return {
                    'status': 'success',
                    'message': f'Processed {processed_count} alert rules',
                    'processed_count': processed_count,
                    'error_count': error_count,
                    'results': results,
                }

            finally:
                if owns_session:
                    await session_ctx.__aexit__(None, None, None)

        except Exception as e:
            logger.error(f'Background alert processing failed: {str(e)}', exc_info=True)
            return {
                'status': 'error',
                'message': f'Background processing failed: {str(e)}',
            }

    def _process_alert_rules_with_service(
        self,
        alert_service: AlertRuleService,
        user_id: str,
        transaction_id: str,
        alert_rule_ids: list[str] = None,
    ) -> dict[str, Any]:
        """
        Process alert rules using a provided AlertRuleService instance.
        This method is designed to be called synchronously to avoid event loop conflicts.
        """
        try:
            # Use synchronous database operations to avoid event loop conflicts
            import os

            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import sessionmaker

            # Create a synchronous database connection
            database_url = os.getenv(
                'DATABASE_URL',
                'postgresql://user:password@localhost:5432/spending_monitor',
            )
            print(
                f'DEBUG: Creating synchronous engine with database URL: {database_url}'
            )
            engine = create_engine(database_url, pool_pre_ping=True)
            SessionLocalSync = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )

            with SessionLocalSync() as session:
                # Get the transaction
                transaction_result = session.execute(
                    select(Transaction).where(Transaction.id == transaction_id)
                )
                transaction = transaction_result.scalar_one_or_none()

                if not transaction:
                    logger.error(f'Transaction {transaction_id} not found')
                    return {'status': 'error', 'message': 'Transaction not found'}

                # Get the user
                user_result = session.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()

                if not user:
                    logger.error(f'User {user_id} not found')
                    return {'status': 'error', 'message': 'User not found'}

                # Get alert rules
                if alert_rule_ids:
                    # Process specific alert rules
                    alerts_result = session.execute(
                        select(AlertRule).where(
                            AlertRule.id.in_(alert_rule_ids),
                            AlertRule.user_id == user_id,
                            AlertRule.is_active,
                        )
                    )
                    alerts = alerts_result.scalars().all()
                else:
                    # Process all active alert rules for the user
                    alerts_result = session.execute(
                        select(AlertRule).where(
                            AlertRule.user_id == user_id, AlertRule.is_active
                        )
                    )
                    alerts = alerts_result.scalars().all()

                if not alerts:
                    logger.info(f'No active alert rules found for user {user_id}')
                    return {
                        'status': 'success',
                        'message': 'No active alert rules to process',
                        'processed_count': 0,
                    }

                # Process each alert rule
                processed_count = 0
                error_count = 0
                results = []

                for alert in alerts:
                    try:
                        # Use the synchronous generate_alert_with_llm method directly
                        # to avoid async event loop conflicts
                        alert_result = alert_service.generate_alert_with_llm(
                            alert.natural_language_query,
                            transaction.__dict__,
                            user.__dict__,
                        )

                        if alert_result and alert_result.get('alert_triggered', False):
                            logger.info(
                                f'Alert rule {alert.id} triggered for transaction {transaction_id}'
                            )
                            result = {
                                'status': 'triggered',
                                'message': 'Alert rule triggered successfully',
                                'rule_evaluation': alert_result,
                                'transaction_id': transaction.id,
                            }
                        else:
                            logger.debug(
                                f'Alert rule {alert.id} did not trigger for transaction {transaction_id}'
                            )
                            result = {
                                'status': 'not_triggered',
                                'message': 'Rule evaluated but alert not triggered',
                                'rule_evaluation': alert_result,
                                'transaction_id': transaction.id,
                            }

                        results.append({'alert_rule_id': alert.id, 'result': result})
                        processed_count += 1

                    except Exception as e:
                        logger.error(
                            f'Error processing alert rule {alert.id}: {str(e)}'
                        )
                        results.append({'alert_rule_id': alert.id, 'error': str(e)})
                        error_count += 1

                return {
                    'status': 'success',
                    'message': f'Processed {processed_count} alert rules, {error_count} errors',
                    'processed_count': processed_count,
                    'error_count': error_count,
                    'results': results,
                }

        except Exception as e:
            logger.error(f'Background alert processing failed: {str(e)}')
            return {
                'status': 'error',
                'message': f'Background processing failed: {str(e)}',
            }

    def process_alert_rules_background(
        self, user_id: str, transaction_id: str, alert_rule_ids: list[str] = None
    ) -> None:
        """
        Pure sync wrapper for FastAPI BackgroundTasks.
        Spawns a new thread with its own event loop and async engine/session.
        """
        import os
        import threading

        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        def runner():
            try:
                db_url = os.getenv(
                    'DATABASE_URL',
                    'postgresql+asyncpg://user:password@localhost:5432/spending-monitor',
                )
                engine = create_async_engine(db_url, echo=False, future=True)
                SessionLocalThread = async_sessionmaker(engine, expire_on_commit=False)

                async def task():
                    async with SessionLocalThread() as session:
                        return await self.process_alert_rules_async(
                            user_id, transaction_id, alert_rule_ids, session=session
                        )

                result = asyncio.run(task())
                logger.info(f'Background alert processing completed: {result}')

            except Exception as e:
                logger.error(f'Background alert processing failed: {e}', exc_info=True)

        threading.Thread(target=runner, daemon=True).start()


# Global instance
background_alert_service = BackgroundAlertService()

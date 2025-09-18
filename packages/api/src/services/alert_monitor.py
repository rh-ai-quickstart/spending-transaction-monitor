"""Alert monitoring service for continuous transaction monitoring"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import AlertRule, Transaction

from .alert_rule_service import AlertRuleService

logger = logging.getLogger(__name__)


class AlertMonitorService:
    """Service for continuously monitoring transactions against alert rules"""

    def __init__(self):
        self.alert_rule_service = AlertRuleService()
        self._running = False

    async def start_monitoring(self, check_interval: int = 30):
        """Start the continuous monitoring process"""
        self._running = True
        logger.info('Starting alert monitoring service...')

        while self._running:
            try:
                await self._check_transactions_against_rules()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f'Error in monitoring loop: {e}')
                await asyncio.sleep(check_interval)

    def stop_monitoring(self):
        """Stop the monitoring process"""
        self._running = False
        logger.info('Stopping alert monitoring service...')

    async def _check_transactions_against_rules(self):
        """Check recent transactions against all active alert rules"""
        session_gen = get_db()
        session = await session_gen.__anext__()

        try:
            # Get all active alert rules
            result = await session.execute(select(AlertRule).where(AlertRule.is_active))
            active_rules = result.scalars().all()

            if not active_rules:
                logger.debug('No active alert rules found')
                return

            logger.info(f'Checking {len(active_rules)} active alert rules')

            # Process each rule
            for rule in active_rules:
                try:
                    await self._process_rule_for_new_transactions(rule, session)
                except Exception as e:
                    logger.error(f'Error processing rule {rule.id}: {e}')

            await session.commit()

        except Exception as e:
            logger.error(f'Error in transaction checking: {e}')
            await session.rollback()
        finally:
            await session.close()

    async def _process_rule_for_new_transactions(
        self, rule: AlertRule, session: AsyncSession
    ):
        """Process a specific rule against new transactions"""

        # Get transactions since last rule trigger or creation
        since_time = rule.last_triggered or rule.created_at

        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == rule.user_id)
            .where(Transaction.transaction_date > since_time)
            .order_by(Transaction.transaction_date.desc())
        )

        new_transactions = result.scalars().all()

        if not new_transactions:
            logger.debug(f'No new transactions for rule {rule.id}')
            return

        logger.info(
            f'Found {len(new_transactions)} new transactions for rule {rule.id}'
        )

        # For each new transaction, trigger the alert rule using the existing service
        try:
            trigger_result = await self.alert_rule_service.trigger_alert_rule(
                rule, session
            )

            if trigger_result.get('status') == 'triggered':
                logger.info(f'Alert {rule.id} triggered successfully')
            elif trigger_result.get('status') == 'not_triggered':
                logger.debug(f'Alert {rule.id} evaluated but not triggered')
            else:
                logger.warning(
                    f'Alert {rule.id} evaluation returned: {trigger_result.get("status")}'
                )

        except ValueError as e:
            logger.warning(f'Alert rule {rule.id} could not be triggered: {e}')
        except Exception as e:
            logger.error(f'Error triggering alert rule {rule.id}: {e}')


# Global monitor instance
alert_monitor = AlertMonitorService()


async def start_alert_monitoring():
    """Start the alert monitoring service"""
    await alert_monitor.start_monitoring()


def stop_alert_monitoring():
    """Stop the alert monitoring service"""
    alert_monitor.stop_monitoring()

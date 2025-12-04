"""Notification service for sending alert notifications"""

from datetime import UTC, datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AlertNotification,
    NotificationMethod,
    NotificationStatus,
)

from .notifications import Context, NoopStrategy, SmtpStrategy

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending alert notifications via various channels"""

    def __init__(self):
        self.strategies = {
            NotificationMethod.EMAIL: SmtpStrategy(),
            NotificationMethod.SMS: NoopStrategy(),  # TODO: Implement SMS strategy
            NotificationMethod.PUSH: NoopStrategy(),  # TODO: Implement push strategy
            NotificationMethod.WEBHOOK: NoopStrategy(),  # TODO: Implement webhook strategy
        }

    async def notify(
        self,
        notification: AlertNotification,
        session: AsyncSession,
    ) -> AlertNotification:
        """
        Send a notification for a triggered alert

        Args:
            notification: The notification to send
            session: Database session

        Returns:
            Updated notification with status and timestamps
        """
        try:
            # Update notification status to processing
            notification.status = NotificationStatus.PENDING
            notification.updated_at = datetime.now(UTC)

            # Get strategy for the notification method
            strategy = self.strategies.get(
                notification.notification_method, NoopStrategy()
            )

            # Send notification using the appropriate strategy
            ctx = Context(strategy)
            updated_notification = await ctx.send_notification(notification, session)

            # Update the original notification with the result
            notification.status = updated_notification.status
            notification.sent_at = updated_notification.sent_at
            notification.delivered_at = updated_notification.delivered_at
            notification.updated_at = datetime.now(UTC)

            logger.info(
                f'Notification sent via {notification.notification_method} '
                f'for alert {notification.alert_rule_id} - Status: {notification.status}'
            )

            return updated_notification

        except Exception as e:
            # Mark notification as failed
            notification.status = NotificationStatus.FAILED
            notification.updated_at = datetime.now(UTC)

            logger.error(
                f'Error sending notification via {notification.notification_method} '
                f'for alert {notification.alert_rule_id}: {e}'
            )
            return notification

    async def notify_batch(
        self,
        notifications: list[AlertNotification],
        session: AsyncSession,
    ) -> list[AlertNotification]:
        """
        Send multiple notifications in batch

        Args:
            notifications: List of notifications to send
            session: Database session

        Returns:
            List of updated notifications
        """
        results = []

        for notification in notifications:
            try:
                result = await self.notify(notification, session)
                results.append(result)
            except Exception as e:
                logger.error(f'Failed to send notification {notification.id}: {e}')
                # Add failed notification to results
                notification.status = NotificationStatus.FAILED
                notification.updated_at = datetime.now(UTC)
                results.append(notification)

        return results

    async def get_user_notifications(
        self,
        user_id: str,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        status: NotificationStatus | None = None,
    ) -> list[AlertNotification]:
        """
        Get notifications for a user

        Args:
            user_id: User ID
            session: Database session
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip
            status: Filter by notification status

        Returns:
            List of notifications
        """
        query = select(AlertNotification).where(AlertNotification.user_id == user_id)

        if status:
            query = query.where(AlertNotification.status == status)

        query = query.order_by(AlertNotification.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_notification_as_read(
        self,
        notification_id: str,
        session: AsyncSession,
    ) -> AlertNotification | None:
        """
        Mark a notification as read

        Args:
            notification_id: Notification ID
            session: Database session

        Returns:
            Updated notification or None if not found
        """
        result = await session.execute(
            select(AlertNotification).where(AlertNotification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if notification:
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now(UTC)
            notification.updated_at = datetime.now(UTC)

            logger.info(f'Notification {notification_id} marked as read')

        return notification

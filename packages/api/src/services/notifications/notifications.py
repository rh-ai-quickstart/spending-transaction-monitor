from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertNotification

from .smtp import send_smtp_notification


class Context:
    def __init__(self, strategy: NotificationStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> NotificationStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: NotificationStrategy) -> None:
        self._strategy = strategy

    async def send_notification(
        self, notification: AlertNotification, session: AsyncSession
    ) -> AlertNotification:
        return await self._strategy.send_notification(notification, session)


class NotificationStrategy(ABC):
    @abstractmethod
    async def send_notification(
        self, notification: AlertNotification, session: AsyncSession
    ) -> AlertNotification:
        pass


class NoopStrategy(NotificationStrategy):
    async def send_notification(
        self, notification: AlertNotification, session: AsyncSession
    ) -> AlertNotification:
        # Do nothing with the notification
        return notification


class SmtpStrategy(NotificationStrategy):
    async def send_notification(
        self, notification: AlertNotification, session: AsyncSession
    ) -> AlertNotification:
        return await send_smtp_notification(notification, session)

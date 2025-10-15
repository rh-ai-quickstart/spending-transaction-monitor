from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertNotification, NotificationStatus, User

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailNotification(BaseModel):
    to_emails: list[EmailStr]
    subject: str
    body: str
    html_body: str | None = None
    from_email: str | None = None
    reply_to: str | None = None


async def send_smtp_notification(
    notification: AlertNotification,
    session: AsyncSession,
):
    """Send email notification"""

    try:
        user_email_result = await session.execute(
            select(User.email).where(User.id == notification.user_id)
        )
        user_email = user_email_result.scalar_one_or_none()
        if not user_email:
            raise HTTPException(status_code=404, detail='User email not found')

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = notification.title
        msg['From'] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

        if settings.SMTP_REPLY_TO_EMAIL:
            msg['Reply-To'] = settings.SMTP_REPLY_TO_EMAIL

        # Add plain text body
        text_part = MIMEText(notification.message, 'plain')
        msg.attach(text_part)

        # Add HTML body if provided
        # if notification.html_body:
        #     html_part = MIMEText(notification.html_body, 'html')
        #     msg.attach(html_part)

        # Connect to SMTP server
        logger.info(
            f'🔌 Attempting SMTP connection to {settings.SMTP_HOST}:{settings.SMTP_PORT} (SSL={settings.SMTP_USE_SSL}, TLS={settings.SMTP_USE_TLS})'
        )
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_USE_TLS:
                server.starttls()
        logger.info('✅ Successfully connected to SMTP server')

        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

        # Send email
        try:
            msg['To'] = user_email
            server.send_message(msg)
            logger.info(f'Email sent successfully to {user_email}')
        except Exception as e:
            logger.error(f'Failed to send email to {user_email}: {str(e)}')

        server.quit()

    except Exception as e:
        logger.error(f'Failed to send notifications: {str(e)}')
        raise HTTPException(
            status_code=500, detail=f'Failed to send notifications: {str(e)}'
        ) from e

    finished_at = datetime.now()

    notification.sent_at = finished_at
    notification.status = NotificationStatus.SENT
    return notification

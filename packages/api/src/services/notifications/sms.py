from datetime import datetime
import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from core.config import settings
from db.models import AlertNotification, NotificationStatus, User

logger = logging.getLogger(__name__)


async def send_sms_notification(
    notification: AlertNotification,
    session: AsyncSession,
):
    """Send SMS notification via Twilio"""

    try:
        # Get user's phone number
        user_phone_result = await session.execute(
            select(User.phone_number).where(User.id == notification.user_id)
        )
        user_phone = user_phone_result.scalar_one_or_none()

        if not user_phone:
            logger.warning(f'User {notification.user_id} does not have a phone number')
            raise HTTPException(status_code=404, detail='User phone number not found')

        # Validate Twilio configuration
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.error('Twilio credentials not configured')
            raise HTTPException(status_code=500, detail='SMS service not configured')

        if not settings.TWILIO_PHONE_NUMBER:
            logger.error('Twilio phone number not configured')
            raise HTTPException(
                status_code=500, detail='SMS service phone number not configured'
            )

        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Format the SMS message
        # Keep it concise for SMS (160 character limit for single SMS)
        sms_body = f'{notification.title}\n\n{notification.message}'

        # Truncate if too long (allowing some buffer for carrier info)
        if len(sms_body) > 1500:  # Allowing for multi-part SMS
            sms_body = sms_body[:1497] + '...'

        # Send SMS via Twilio
        logger.info(
            f'📱 Sending SMS to {user_phone} from {settings.TWILIO_PHONE_NUMBER}'
        )

        try:
            message = client.messages.create(
                body=sms_body, from_=settings.TWILIO_PHONE_NUMBER, to=user_phone
            )

            logger.info(
                f'✅ SMS sent successfully to {user_phone}. '
                f'Message SID: {message.sid}, Status: {message.status}'
            )

            # Update notification status
            notification.sent_at = datetime.now()
            notification.status = NotificationStatus.SENT

        except TwilioRestException as e:
            logger.error(
                f'❌ Twilio API error sending SMS to {user_phone}: '
                f'Code: {e.code}, Message: {e.msg}'
            )
            raise HTTPException(
                status_code=500, detail=f'Failed to send SMS: {e.msg}'
            ) from e

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f'Failed to send SMS notification: {str(e)}')
        raise HTTPException(
            status_code=500, detail=f'Failed to send SMS notification: {str(e)}'
        ) from e

    return notification

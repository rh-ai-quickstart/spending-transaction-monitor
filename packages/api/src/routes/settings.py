import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import User
from ..auth.middleware import require_authentication
from ..schemas.settings import SMSSettingsResponse, SMSSettingsUpdate, SMTPConfigResponse

router = APIRouter()


@router.get('/smtp', response_model=SMTPConfigResponse)
async def get_smtp_settings(
    current_user: dict = Depends(require_authentication)
) -> SMTPConfigResponse:
    """
    Get SMTP configuration settings (read-only, sensitive data masked).
    Returns the current SMTP configuration without exposing credentials.
    """
    # Read SMTP configuration from environment variables
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_from_email = os.getenv('SMTP_FROM_EMAIL', '')
    smtp_reply_to_email = os.getenv('SMTP_REPLY_TO_EMAIL')
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'

    # Check if SMTP is configured (credentials exist)
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    is_configured = bool(smtp_username and smtp_password)

    return SMTPConfigResponse(
        host=smtp_host,
        port=smtp_port,
        from_email=smtp_from_email,
        reply_to_email=smtp_reply_to_email,
        use_tls=smtp_use_tls,
        use_ssl=smtp_use_ssl,
        is_configured=is_configured
    )


@router.get('/sms', response_model=SMSSettingsResponse)
async def get_sms_settings(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication)
) -> SMSSettingsResponse:
    """
    Get SMS settings for the current user.
    Returns the user's SMS preferences and Twilio configuration status.
    """
    try:
        # Get the current user from the database
        result = await session.execute(
            select(User).where(User.id == current_user['id'])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if Twilio is configured
        twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_configured = bool(twilio_account_sid and twilio_auth_token)

        return SMSSettingsResponse(
            phone_number=user.phone_number,
            sms_notifications_enabled=user.sms_notifications_enabled,
            twilio_configured=twilio_configured
        )

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put('/sms', response_model=SMSSettingsResponse)
async def update_sms_settings(
    settings: SMSSettingsUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication)
) -> SMSSettingsResponse:
    """
    Update SMS settings for the current user.
    Users can only update their own SMS preferences.
    """
    try:
        # Get the current user from the database
        result = await session.execute(
            select(User).where(User.id == current_user['id'])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update the user's SMS settings
        if settings.phone_number is not None:
            user.phone_number = settings.phone_number

        user.sms_notifications_enabled = settings.sms_notifications_enabled

        await session.commit()
        await session.refresh(user)

        # Check if Twilio is configured
        twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_configured = bool(twilio_account_sid and twilio_auth_token)

        return SMSSettingsResponse(
            phone_number=user.phone_number,
            sms_notifications_enabled=user.sms_notifications_enabled,
            twilio_configured=twilio_configured
        )

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
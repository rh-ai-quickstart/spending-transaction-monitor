"""Tests for settings routes"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from src.routes.settings import get_sms_settings, get_smtp_settings, update_sms_settings
from src.schemas.settings import SMSSettingsUpdate

# ==============================================================================
# GET /smtp - Get SMTP settings
# ==============================================================================


@pytest.mark.asyncio
async def test_get_smtp_settings_fully_configured():
    """Test getting SMTP settings when fully configured"""
    current_user = {'id': 'user-123', 'roles': []}

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        # Mock environment variables
        env_vars = {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_FROM_EMAIL': 'noreply@example.com',
            'SMTP_REPLY_TO_EMAIL': 'support@example.com',
            'SMTP_USE_TLS': 'true',
            'SMTP_USE_SSL': 'false',
            'SMTP_USERNAME': 'user@example.com',
            'SMTP_PASSWORD': 'secret_password',
        }
        mock_getenv.side_effect = lambda key, default='': env_vars.get(key, default)

        # Execute
        result = await get_smtp_settings(current_user=current_user)

        # Assert
        assert result.host == 'smtp.gmail.com'
        assert result.port == 587
        assert result.from_email == 'noreply@example.com'
        assert result.reply_to_email == 'support@example.com'
        assert result.use_tls is True
        assert result.use_ssl is False
        assert result.is_configured is True


@pytest.mark.asyncio
async def test_get_smtp_settings_not_configured():
    """Test getting SMTP settings when not configured (no credentials)"""
    current_user = {'id': 'user-123', 'roles': []}

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        # Mock environment variables without credentials
        env_vars = {
            'SMTP_HOST': 'smtp.example.com',
            'SMTP_PORT': '587',
            'SMTP_FROM_EMAIL': 'noreply@example.com',
            'SMTP_USE_TLS': 'true',
            'SMTP_USE_SSL': 'false',
        }
        mock_getenv.side_effect = lambda key, default='': env_vars.get(key, default)

        # Execute
        result = await get_smtp_settings(current_user=current_user)

        # Assert
        assert result.is_configured is False


@pytest.mark.asyncio
async def test_get_smtp_settings_with_ssl():
    """Test getting SMTP settings with SSL enabled"""
    current_user = {'id': 'user-123', 'roles': []}

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        env_vars = {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '465',
            'SMTP_FROM_EMAIL': 'noreply@example.com',
            'SMTP_USE_TLS': 'false',
            'SMTP_USE_SSL': 'true',
            'SMTP_USERNAME': 'user@example.com',
            'SMTP_PASSWORD': 'secret',
        }
        mock_getenv.side_effect = lambda key, default='': env_vars.get(key, default)

        # Execute
        result = await get_smtp_settings(current_user=current_user)

        # Assert
        assert result.port == 465
        assert result.use_ssl is True
        assert result.use_tls is False


@pytest.mark.asyncio
async def test_get_smtp_settings_defaults():
    """Test getting SMTP settings with default values"""
    current_user = {'id': 'user-123', 'roles': []}

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        # Mock to return empty env vars, relying on defaults
        env_vars = {
            'SMTP_HOST': '',
            'SMTP_PORT': '587',
            'SMTP_FROM_EMAIL': '',
            'SMTP_REPLY_TO_EMAIL': None,
            'SMTP_USE_TLS': 'true',
            'SMTP_USE_SSL': 'false',
            'SMTP_USERNAME': None,
            'SMTP_PASSWORD': None,
        }
        mock_getenv.side_effect = lambda key, default='': env_vars.get(key, default)

        # Execute
        result = await get_smtp_settings(current_user=current_user)

        # Assert - should use defaults
        assert result.host == ''
        assert result.port == 587
        assert result.from_email == ''
        assert result.reply_to_email is None
        assert result.is_configured is False


@pytest.mark.asyncio
async def test_get_smtp_settings_no_reply_to():
    """Test getting SMTP settings without reply-to email"""
    current_user = {'id': 'user-123', 'roles': []}

    with patch('src.routes.settings.os.getenv') as mock_getenv:

        def getenv_side_effect(key, default=''):
            env_vars = {
                'SMTP_HOST': 'smtp.example.com',
                'SMTP_PORT': '587',
                'SMTP_FROM_EMAIL': 'noreply@example.com',
                'SMTP_USE_TLS': 'true',
                'SMTP_USE_SSL': 'false',
                'SMTP_USERNAME': 'user@example.com',
                'SMTP_PASSWORD': 'secret',
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect

        # Execute
        result = await get_smtp_settings(current_user=current_user)

        # Assert
        assert result.reply_to_email == ''


# ==============================================================================
# GET /sms - Get SMS settings
# ==============================================================================


@pytest.mark.asyncio
async def test_get_sms_settings_success():
    """Test getting SMS settings successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock user
    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        env_vars = {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
        }
        mock_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)

        # Execute
        result = await get_sms_settings(session=session, current_user=current_user)

        # Assert
        assert result.phone_number == '+1234567890'
        assert result.sms_notifications_enabled is True
        assert result.twilio_configured is True


@pytest.mark.asyncio
async def test_get_sms_settings_twilio_not_configured():
    """Test getting SMS settings when Twilio is not configured"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = False

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        # No Twilio credentials
        mock_getenv.return_value = None

        # Execute
        result = await get_sms_settings(session=session, current_user=current_user)

        # Assert
        assert result.twilio_configured is False


@pytest.mark.asyncio
async def test_get_sms_settings_user_not_found():
    """Test getting SMS settings when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'nonexistent', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    with pytest.raises(HTTPException) as exc_info:
        await get_sms_settings(session=session, current_user=current_user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_get_sms_settings_database_error():
    """Test getting SMS settings with database error"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock database error
    session.execute.side_effect = SQLAlchemyError('Database connection failed')

    with pytest.raises(HTTPException) as exc_info:
        await get_sms_settings(session=session, current_user=current_user)

    assert exc_info.value.status_code == 500
    assert 'Database error' in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_sms_settings_no_phone_number():
    """Test getting SMS settings when user has no phone number"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.phone_number = None
    user.sms_notifications_enabled = False

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        mock_getenv.return_value = 'test_value'

        # Execute
        result = await get_sms_settings(session=session, current_user=current_user)

        # Assert
        assert result.phone_number is None
        assert result.sms_notifications_enabled is False


# ==============================================================================
# PUT /sms - Update SMS settings
# ==============================================================================


@pytest.mark.asyncio
async def test_update_sms_settings_success():
    """Test updating SMS settings successfully"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.id = 'user-123'
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = False

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    settings = SMSSettingsUpdate(
        phone_number='+9876543210', sms_notifications_enabled=True
    )

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        env_vars = {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
        }
        mock_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)

        # Execute
        result = await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

        # Assert
        assert user.phone_number == '+9876543210'
        assert user.sms_notifications_enabled is True
        assert result.phone_number == '+9876543210'
        assert result.sms_notifications_enabled is True
        session.commit.assert_called_once()
        session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_sms_settings_enable_only():
    """Test updating SMS settings to enable notifications without changing phone"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = False

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Update only the enabled flag, not phone number
    settings = SMSSettingsUpdate(phone_number=None, sms_notifications_enabled=True)

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        mock_getenv.return_value = 'test'

        # Execute
        _result = await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

        # Assert - phone number should not change
        assert user.phone_number == '+1234567890'
        assert user.sms_notifications_enabled is True


@pytest.mark.asyncio
async def test_update_sms_settings_disable_notifications():
    """Test disabling SMS notifications"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    settings = SMSSettingsUpdate(phone_number=None, sms_notifications_enabled=False)

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        mock_getenv.return_value = None

        # Execute
        result = await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

        # Assert
        assert result.sms_notifications_enabled is False
        assert result.twilio_configured is False


@pytest.mark.asyncio
async def test_update_sms_settings_user_not_found():
    """Test updating SMS settings when user doesn't exist"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'nonexistent', 'roles': []}

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    settings = SMSSettingsUpdate(
        phone_number='+1234567890', sms_notifications_enabled=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == 'User not found'


@pytest.mark.asyncio
async def test_update_sms_settings_database_error():
    """Test updating SMS settings with database error"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    # Mock database error during commit
    user = MagicMock(spec=User)
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result
    session.commit.side_effect = SQLAlchemyError('Commit failed')

    settings = SMSSettingsUpdate(
        phone_number='+1234567890', sms_notifications_enabled=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

    assert exc_info.value.status_code == 500
    assert 'Database error' in exc_info.value.detail
    session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_sms_settings_clear_phone_number():
    """Test clearing phone number while keeping notifications enabled"""
    session = AsyncMock(spec=AsyncSession)
    current_user = {'id': 'user-123', 'roles': []}

    user = MagicMock(spec=User)
    user.phone_number = '+1234567890'
    user.sms_notifications_enabled = True

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    session.execute.return_value = user_result

    # Set phone_number to empty string to clear it
    settings = SMSSettingsUpdate(phone_number='', sms_notifications_enabled=True)

    with patch('src.routes.settings.os.getenv') as mock_getenv:
        mock_getenv.return_value = 'test'

        # Execute
        result = await update_sms_settings(
            settings=settings, session=session, current_user=current_user
        )

        # Assert - phone number should be updated to empty string
        assert user.phone_number == ''
        assert result.sms_notifications_enabled is True

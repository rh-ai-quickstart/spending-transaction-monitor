"""Tests for notification services"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.base.exceptions import TwilioRestException

from db.models import AlertNotification, NotificationMethod, NotificationStatus
from src.services.notifications.notification_service import NotificationService
from src.services.notifications.sms import send_sms_notification
from src.services.notifications.smtp import send_smtp_notification

# ==============================================================================
# SMS Service Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_send_sms_notification_success():
    """Test sending SMS notification successfully"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user with phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = '+1234567890'
    session.execute.return_value = user_result

    # Create notification
    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test Alert'
    notification.message = 'This is a test alert message'

    # Mock Twilio client
    with patch('src.services.notifications.sms.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = 'SM1234567890'
        mock_message.status = 'sent'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client

        # Mock settings
        with patch('src.services.notifications.sms.settings') as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = 'test_account_sid'
            mock_settings.TWILIO_AUTH_TOKEN = 'test_auth_token'
            mock_settings.TWILIO_PHONE_NUMBER = '+1987654321'

            # Execute
            result = await send_sms_notification(notification, session)

            # Assert
            assert result == notification
            assert notification.status == NotificationStatus.SENT
            assert notification.sent_at is not None
            mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_send_sms_notification_no_phone_number():
    """Test sending SMS when user has no phone number"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user without phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'

    with pytest.raises(HTTPException) as exc_info:
        await send_sms_notification(notification, session)

    assert exc_info.value.status_code == 404
    assert 'phone number not found' in exc_info.value.detail


@pytest.mark.asyncio
async def test_send_sms_notification_missing_twilio_credentials():
    """Test sending SMS without Twilio credentials"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user with phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = '+1234567890'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'

    with patch('src.services.notifications.sms.settings') as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = None
        mock_settings.TWILIO_AUTH_TOKEN = None

        with pytest.raises(HTTPException) as exc_info:
            await send_sms_notification(notification, session)

        assert exc_info.value.status_code == 500
        assert 'not configured' in exc_info.value.detail


@pytest.mark.asyncio
async def test_send_sms_notification_missing_phone_number_config():
    """Test sending SMS without configured Twilio phone number"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user with phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = '+1234567890'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'

    with patch('src.services.notifications.sms.settings') as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = 'test_sid'
        mock_settings.TWILIO_AUTH_TOKEN = 'test_token'
        mock_settings.TWILIO_PHONE_NUMBER = None

        with pytest.raises(HTTPException) as exc_info:
            await send_sms_notification(notification, session)

        assert exc_info.value.status_code == 500
        assert 'phone number not configured' in exc_info.value.detail


@pytest.mark.asyncio
async def test_send_sms_notification_twilio_api_error():
    """Test handling Twilio API errors"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user with phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = '+1234567890'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test'
    notification.message = 'Test message'

    with patch('src.services.notifications.sms.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=400, uri='test', msg='Invalid phone number', code=21211
        )
        mock_client_class.return_value = mock_client

        with patch('src.services.notifications.sms.settings') as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = 'test_sid'
            mock_settings.TWILIO_AUTH_TOKEN = 'test_token'
            mock_settings.TWILIO_PHONE_NUMBER = '+1987654321'

            with pytest.raises(HTTPException) as exc_info:
                await send_sms_notification(notification, session)

            assert exc_info.value.status_code == 500
            assert 'Failed to send SMS' in exc_info.value.detail


@pytest.mark.asyncio
async def test_send_sms_notification_message_truncation():
    """Test SMS message truncation for long messages"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user with phone number
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = '+1234567890'
    session.execute.return_value = user_result

    # Create notification with very long message
    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test Alert'
    notification.message = 'A' * 2000  # Very long message

    with patch('src.services.notifications.sms.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = 'SM123'
        mock_message.status = 'sent'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client

        with patch('src.services.notifications.sms.settings') as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = 'test_sid'
            mock_settings.TWILIO_AUTH_TOKEN = 'test_token'
            mock_settings.TWILIO_PHONE_NUMBER = '+1987654321'

            # Execute
            await send_sms_notification(notification, session)

            # Assert message was truncated
            call_args = mock_client.messages.create.call_args
            assert len(call_args.kwargs['body']) <= 1500


# ==============================================================================
# SMTP Service Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_send_smtp_notification_success():
    """Test sending email notification successfully"""
    session = AsyncMock(spec=AsyncSession)

    # Mock user email
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = 'user@test.com'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test Alert'
    notification.message = 'This is a test alert message'

    with patch('src.services.notifications.smtp.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        with patch('src.services.notifications.smtp.settings') as mock_settings:
            mock_settings.SMTP_HOST = 'smtp.test.com'
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USE_SSL = False
            mock_settings.SMTP_USE_TLS = True
            mock_settings.SMTP_USERNAME = 'test@test.com'
            mock_settings.SMTP_PASSWORD = 'password'
            mock_settings.SMTP_FROM_EMAIL = 'noreply@test.com'
            mock_settings.SMTP_REPLY_TO_EMAIL = None

            # Execute
            result = await send_smtp_notification(notification, session)

            # Assert
            assert result == notification
            assert notification.status == NotificationStatus.SENT
            assert notification.sent_at is not None
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()


@pytest.mark.asyncio
async def test_send_smtp_notification_with_ssl():
    """Test sending email using SSL"""
    session = AsyncMock(spec=AsyncSession)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = 'user@test.com'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test'
    notification.message = 'Test'

    with patch('src.services.notifications.smtp.smtplib.SMTP_SSL') as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        with patch('src.services.notifications.smtp.settings') as mock_settings:
            mock_settings.SMTP_HOST = 'smtp.test.com'
            mock_settings.SMTP_PORT = 465
            mock_settings.SMTP_USE_SSL = True
            mock_settings.SMTP_USE_TLS = False
            mock_settings.SMTP_USERNAME = 'test@test.com'
            mock_settings.SMTP_PASSWORD = 'password'
            mock_settings.SMTP_FROM_EMAIL = 'noreply@test.com'
            mock_settings.SMTP_REPLY_TO_EMAIL = 'reply@test.com'

            # Execute
            await send_smtp_notification(notification, session)

            # Assert
            mock_smtp_ssl.assert_called_once_with('smtp.test.com', 465)
            mock_server.starttls.assert_not_called()


@pytest.mark.asyncio
async def test_send_smtp_notification_no_email():
    """Test sending email when user has no email"""
    session = AsyncMock(spec=AsyncSession)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'

    with pytest.raises(HTTPException) as exc_info:
        await send_smtp_notification(notification, session)

    # The SMTP service catches HTTPException and re-raises as 500
    assert exc_info.value.status_code == 500
    assert 'Failed to send notifications' in exc_info.value.detail


@pytest.mark.asyncio
async def test_send_smtp_notification_smtp_error():
    """Test handling SMTP errors"""
    session = AsyncMock(spec=AsyncSession)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = 'user@test.com'
    session.execute.return_value = user_result

    notification = MagicMock(spec=AlertNotification)
    notification.user_id = 'user-123'
    notification.title = 'Test'
    notification.message = 'Test'

    with patch('src.services.notifications.smtp.smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = Exception('SMTP connection failed')

        with patch('src.services.notifications.smtp.settings') as mock_settings:
            mock_settings.SMTP_HOST = 'smtp.test.com'
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USE_SSL = False
            mock_settings.SMTP_USE_TLS = True

            with pytest.raises(HTTPException) as exc_info:
                await send_smtp_notification(notification, session)

            assert exc_info.value.status_code == 500
            assert 'Failed to send notifications' in exc_info.value.detail


# ==============================================================================
# NotificationService Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_notification_service_notify_email_success():
    """Test NotificationService sending email notification"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notification = MagicMock(spec=AlertNotification)
    notification.id = 'notif-123'
    notification.user_id = 'user-123'
    notification.alert_rule_id = 'rule-123'
    notification.notification_method = NotificationMethod.EMAIL
    notification.title = 'Test Alert'
    notification.message = 'Test message'
    notification.status = NotificationStatus.PENDING

    # Mock the email strategy
    with patch.object(
        service.strategies[NotificationMethod.EMAIL], 'send_notification'
    ) as mock_send:
        result_notification = MagicMock(spec=AlertNotification)
        result_notification.status = NotificationStatus.SENT
        result_notification.sent_at = datetime.now(UTC)
        result_notification.delivered_at = None
        mock_send.return_value = result_notification

        # Execute
        _result = await service.notify(notification, session)

        # Assert
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None
        mock_send.assert_called_once_with(notification, session)


@pytest.mark.asyncio
async def test_notification_service_notify_sms_success():
    """Test NotificationService sending SMS notification"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notification = MagicMock(spec=AlertNotification)
    notification.id = 'notif-123'
    notification.user_id = 'user-123'
    notification.alert_rule_id = 'rule-123'
    notification.notification_method = NotificationMethod.SMS
    notification.title = 'Test Alert'
    notification.message = 'Test message'
    notification.status = NotificationStatus.PENDING

    # Mock the SMS strategy
    with patch.object(
        service.strategies[NotificationMethod.SMS], 'send_notification'
    ) as mock_send:
        result_notification = MagicMock(spec=AlertNotification)
        result_notification.status = NotificationStatus.SENT
        result_notification.sent_at = datetime.now(UTC)
        result_notification.delivered_at = None
        mock_send.return_value = result_notification

        # Execute
        _result = await service.notify(notification, session)

        # Assert
        assert notification.status == NotificationStatus.SENT
        mock_send.assert_called_once_with(notification, session)


@pytest.mark.asyncio
async def test_notification_service_notify_failure():
    """Test NotificationService handling notification failures"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notification = MagicMock(spec=AlertNotification)
    notification.notification_method = NotificationMethod.EMAIL
    notification.alert_rule_id = 'rule-123'

    # Mock strategy to raise exception
    with patch.object(
        service.strategies[NotificationMethod.EMAIL], 'send_notification'
    ) as mock_send:
        mock_send.side_effect = Exception('Network error')

        # Execute
        _result = await service.notify(notification, session)

        # Assert
        assert notification.status == NotificationStatus.FAILED
        assert notification.updated_at is not None


@pytest.mark.asyncio
async def test_notification_service_notify_batch():
    """Test sending multiple notifications in batch"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    # Create multiple notifications
    notif1 = MagicMock(spec=AlertNotification)
    notif1.id = 'notif-1'
    notif1.notification_method = NotificationMethod.EMAIL
    notif1.alert_rule_id = 'rule-1'

    notif2 = MagicMock(spec=AlertNotification)
    notif2.id = 'notif-2'
    notif2.notification_method = NotificationMethod.SMS
    notif2.alert_rule_id = 'rule-2'

    notifications = [notif1, notif2]

    # Mock successful sending
    with patch.object(service, 'notify') as mock_notify:
        mock_notify.side_effect = [notif1, notif2]

        # Execute
        results = await service.notify_batch(notifications, session)

        # Assert
        assert len(results) == 2
        assert mock_notify.call_count == 2


@pytest.mark.asyncio
async def test_notification_service_notify_batch_with_failures():
    """Test batch notifications with some failures"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notif1 = MagicMock(spec=AlertNotification)
    notif1.id = 'notif-1'
    notif1.notification_method = NotificationMethod.EMAIL

    notif2 = MagicMock(spec=AlertNotification)
    notif2.id = 'notif-2'
    notif2.notification_method = NotificationMethod.SMS

    notifications = [notif1, notif2]

    # Mock first success, second failure
    with patch.object(service, 'notify') as mock_notify:
        mock_notify.side_effect = [notif1, Exception('Failed')]

        # Execute
        results = await service.notify_batch(notifications, session)

        # Assert
        assert len(results) == 2
        assert results[0] == notif1
        assert results[1].status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_notification_service_get_user_notifications():
    """Test getting user notifications"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    # Mock notifications
    notif1 = MagicMock(spec=AlertNotification)
    notif1.id = 'notif-1'
    notif1.user_id = 'user-123'

    notif2 = MagicMock(spec=AlertNotification)
    notif2.id = 'notif-2'
    notif2.user_id = 'user-123'

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif1, notif2]
    session.execute.return_value = mock_result

    # Execute
    results = await service.get_user_notifications(
        user_id='user-123', session=session, limit=50, offset=0
    )

    # Assert
    assert len(results) == 2
    assert results[0].id == 'notif-1'
    assert results[1].id == 'notif-2'
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_notification_service_get_user_notifications_with_status_filter():
    """Test getting user notifications filtered by status"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notif1 = MagicMock(spec=AlertNotification)
    notif1.status = NotificationStatus.SENT

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif1]
    session.execute.return_value = mock_result

    # Execute
    results = await service.get_user_notifications(
        user_id='user-123',
        session=session,
        limit=50,
        offset=0,
        status=NotificationStatus.SENT,
    )

    # Assert
    assert len(results) == 1
    assert results[0].status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_notification_service_mark_as_read():
    """Test marking notification as read"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notification = MagicMock(spec=AlertNotification)
    notification.id = 'notif-123'
    notification.status = NotificationStatus.SENT

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = notification
    session.execute.return_value = mock_result

    # Execute
    result = await service.mark_notification_as_read('notif-123', session)

    # Assert
    assert result == notification
    assert notification.status == NotificationStatus.READ
    assert notification.read_at is not None
    assert notification.updated_at is not None


@pytest.mark.asyncio
async def test_notification_service_mark_as_read_not_found():
    """Test marking non-existent notification as read"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    # Execute
    result = await service.mark_notification_as_read('nonexistent', session)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_notification_service_unsupported_method():
    """Test notification with unsupported method uses noop strategy"""
    session = AsyncMock(spec=AsyncSession)
    service = NotificationService()

    notification = MagicMock(spec=AlertNotification)
    notification.notification_method = NotificationMethod.PUSH
    notification.alert_rule_id = 'rule-123'

    # Mock noop strategy
    with patch.object(
        service.strategies[NotificationMethod.PUSH], 'send_notification'
    ) as mock_send:
        result_notification = MagicMock(spec=AlertNotification)
        result_notification.status = NotificationStatus.SENT
        result_notification.sent_at = datetime.now(UTC)
        result_notification.delivered_at = None
        mock_send.return_value = result_notification

        # Execute
        _result = await service.notify(notification, session)

        # Assert - noop strategy should be called
        mock_send.assert_called_once_with(notification, session)

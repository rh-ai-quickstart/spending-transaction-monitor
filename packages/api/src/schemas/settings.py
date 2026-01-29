from pydantic import BaseModel, Field


class SMTPConfigResponse(BaseModel):
    host: str
    port: int
    from_email: str
    reply_to_email: str | None = None
    use_tls: bool
    use_ssl: bool
    is_configured: bool  # True if username/password exist


class SMSSettingsUpdate(BaseModel):
    phone_number: str | None = Field(
        None, description="User's phone number for SMS notifications"
    )
    sms_notifications_enabled: bool = Field(
        True, description='Whether SMS notifications are enabled'
    )


class SMSSettingsResponse(BaseModel):
    phone_number: str | None
    sms_notifications_enabled: bool
    twilio_configured: bool  # True if Twilio credentials exist

"""
Tests for authentication bypass functionality
"""

import os
from typing import Literal
from unittest.mock import patch

from pydantic_settings import BaseSettings, SettingsConfigDict
import pytest

from src.auth.middleware import get_current_user, require_authentication


class IsolatedSettings(BaseSettings):
    """Test-only Settings class that doesn't load from env file"""

    model_config = SettingsConfigDict(
        extra='ignore',
    )

    # Environment settings
    ENVIRONMENT: Literal['development', 'production', 'staging', 'test'] = 'development'

    # Authentication settings
    BYPASS_AUTH: bool = False

    # Basic settings
    APP_NAME: str = 'spending-monitor'
    DEBUG: bool = False

    # CORS settings
    ALLOWED_HOSTS: list[str] = ['http://localhost:5173']

    # Database settings
    DATABASE_URL: str = (
        'postgresql+asyncpg://user:password@localhost:5432/spending-monitor'
    )

    # LLM settings
    LLM_PROVIDER: str = 'openai'
    NODE_ENV: str = 'development'
    BASE_URL: str = ''
    API_KEY: str = ''
    MODEL: str = 'gpt-3.5-turbo'

    # Keycloak settings
    KEYCLOAK_URL: str = 'http://localhost:8080'
    KEYCLOAK_REALM: str = 'spending-monitor'
    KEYCLOAK_CLIENT_ID: str = 'spending-monitor'

    def model_post_init(self, __context):
        """Set derived values based on environment"""
        # Auto-enable auth bypass in development if not explicitly set
        if (
            self.ENVIRONMENT == 'development'
            and not hasattr(self, '_bypass_auth_explicitly_set')
            and 'BYPASS_AUTH' not in os.environ
        ):
            self.BYPASS_AUTH = True

        # Set DEBUG based on environment if not explicitly set
        if not hasattr(self, '_debug_explicitly_set') and 'DEBUG' not in os.environ:
            self.DEBUG = self.ENVIRONMENT == 'development'


class TestAuthBypass:
    """Test authentication bypass functionality"""

    @pytest.mark.asyncio
    async def test_require_authentication_with_bypass_enabled(self):
        """Test that require_authentication returns dev user when bypass is enabled"""
        # Mock settings with bypass enabled
        with patch('src.auth.middleware.settings') as mock_settings:
            mock_settings.BYPASS_AUTH = True

            user = await require_authentication(credentials=None)

            assert user is not None
            assert user['id'] == 'u-001'
            assert user['email'] == 'monica.cohen@example.com'
            assert user['username'] == 'monica.cohen'
            assert user['roles'] == ['user', 'admin']
            assert user['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_current_user_with_bypass_enabled(self):
        """Test that get_current_user returns dev user when bypass is enabled"""
        with patch('src.auth.middleware.settings') as mock_settings:
            mock_settings.BYPASS_AUTH = True

            user = await get_current_user(credentials=None)

            assert user is not None
            assert user['id'] == 'u-001'
            assert user['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_current_user_without_bypass(self):
        """Test that get_current_user returns None when bypass is disabled and no credentials"""
        with patch('src.auth.middleware.settings') as mock_settings:
            mock_settings.BYPASS_AUTH = False

            user = await get_current_user(credentials=None)

            assert user is None

    def test_config_auto_enables_bypass_in_development(self):
        """Test that BYPASS_AUTH is auto-enabled in development mode"""
        # Test with development environment and no explicit BYPASS_AUTH
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=True):
            settings = IsolatedSettings()

            assert settings.ENVIRONMENT == 'development'
            assert settings.BYPASS_AUTH is True

    def test_config_respects_explicit_bypass_setting(self):
        """Test that explicit BYPASS_AUTH setting is respected"""
        # Test with development environment but explicit BYPASS_AUTH=false
        with patch.dict(
            os.environ,
            {'ENVIRONMENT': 'development', 'BYPASS_AUTH': 'false'},
            clear=True,
        ):
            settings = IsolatedSettings()

            assert settings.ENVIRONMENT == 'development'
            assert settings.BYPASS_AUTH is False

    def test_config_production_mode_no_auto_bypass(self):
        """Test that production mode doesn't auto-enable bypass"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
            settings = IsolatedSettings()

            assert settings.ENVIRONMENT == 'production'
            assert settings.BYPASS_AUTH is False

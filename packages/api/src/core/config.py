"""
Application configuration
"""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file_path() -> str:
    """
    Determine which .env file to use.
    Priority:
    1. ../../../../.env (root directory) - preferred
    2. ../../.env (packages/api directory) - fallback
    """
    # Get the directory where this config file is located (packages/api/src/core/)
    current_dir = Path(__file__).parent

    # Check root directory first
    # packages/api/src/core/ -> packages/api/src/ -> packages/api/ -> packages/ -> root/
    root_env = current_dir.parent.parent.parent.parent / '.env'
    if root_env.exists():
        return str(root_env)

    # Fallback to packages/api/.env
    api_env = current_dir.parent.parent / '.env'
    if api_env.exists():
        return str(api_env)

    # Default to root directory path (even if it doesn't exist yet)
    return str(root_env)


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        extra='ignore',  # Allow extra environment variables without validation errors
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
    LLAMASTACK_BASE_URL: str = 'http://localhost:8321'
    LLAMASTACK_MODEL: str = 'meta-llama/Llama-3.2-3B-Instruct'

    # Keycloak settings
    KEYCLOAK_URL: str = 'http://localhost:8080'
    KEYCLOAK_REALM: str = 'spending-monitor'
    KEYCLOAK_CLIENT_ID: str = 'spending-monitor'

    # SMTP settings
    SMTP_HOST: str = 'localhost'
    SMTP_PORT: int = 8025
    SMTP_USERNAME: str = ''
    SMTP_PASSWORD: str = ''
    SMTP_FROM_EMAIL: str = 'noreply@localhost'
    SMTP_REPLY_TO_EMAIL: str = 'noreply@localhost'
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    def model_post_init(self, __context):
        """Set derived values based on environment"""
        # Auto-enable auth bypass in development ONLY if not explicitly set in environment
        if self.ENVIRONMENT == 'development' and 'BYPASS_AUTH' not in os.environ:
            self.BYPASS_AUTH = True

        # Set DEBUG based on environment if not explicitly set
        if not hasattr(self, '_debug_explicitly_set') and 'DEBUG' not in os.environ:
            self.DEBUG = self.ENVIRONMENT == 'development'


settings = Settings()

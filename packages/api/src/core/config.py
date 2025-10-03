"""
Application configuration
"""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Define env file priority order (first one found is used)
    model_config = SettingsConfigDict(
        env_file=[
            Path(__file__).resolve().parents[4]
            / '.env.development',  # root/.env.development
            Path(__file__).resolve().parents[4] / '.env',  # root/.env
            Path(__file__).resolve().parents[2] / '.env',  # packages/api/.env
        ],
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

    # Embedding settings (for category normalization)
    EMBEDDING_PROVIDER: str = 'ollama'  # ollama, openai, llamastack
    EMBEDDING_MODEL: str = 'all-minilm:l6-v2'  # or text-embedding-3-small for openai
    EMBEDDING_DIMENSIONS: int = 384  # 384 for ollama/all-minilm, 1536 for openai
    OLLAMA_BASE_URL: str = 'http://localhost:11434'

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


# Create a global settings instance
settings = Settings()

"""
Database configuration and utilities
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# Only create async engine if using async driver (asyncpg)
# For alembic (which uses sync psycopg2), skip async engine creation
engine = None
_SessionLocal = None

def get_engine():
    global engine
    if engine is None and '+asyncpg' in settings.DATABASE_URL:
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
    return engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        eng = get_engine()
        if eng:
            _SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=eng, class_=AsyncSession
            )
    return _SessionLocal

# Backwards compatibility - create SessionLocal on first access
class SessionLocalFactory:
    def __call__(self):
        session_local = get_session_local()
        if session_local is None:
            raise RuntimeError("Database not configured for async operations")
        return session_local()

SessionLocal = SessionLocalFactory()

Base = declarative_base()

logger = logging.getLogger(__name__)

# Capture service startup time
SERVICE_START_TIME = datetime.now(UTC)


class DatabaseService:
    """Database service for handling database operations"""

    def __init__(self, engine=None):
        self.engine = engine or globals()['engine']
        self.start_time = SERVICE_START_TIME

    async def health_check(self) -> dict[str, Any]:
        """
        Perform database health check

        Returns:
            Dict containing health status information
        """
        try:
            # Test basic connectivity
            async with self.engine.begin() as conn:
                result = await conn.execute(text('SELECT 1 as health_check'))
                result.scalar()

            # Test if we can create a session
            async with SessionLocal() as session:
                await session.execute(text('SELECT version()'))

            return {
                'name': 'Database',
                'status': 'healthy',
                'message': 'PostgreSQL connection successful',
                'version': 'PostgreSQL',
                'start_time': self.start_time.isoformat(),
            }
        except Exception as e:
            logger.error(f'Database health check failed: {e}')
            return {
                'name': 'Database',
                'status': 'down',
                'message': f'PostgreSQL connection failed: {str(e)[:100]}',
                'version': 'PostgreSQL',
                'start_time': self.start_time.isoformat(),
            }

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return SessionLocal()


# Global database service instance
db_service = DatabaseService()


async def get_db():
    """Dependency to get database session"""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_service() -> DatabaseService:
    """Dependency to get database service"""
    return db_service

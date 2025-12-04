"""User Service - Business logic for user operations"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


class UserService:
    """Service class for user business logic and data access"""

    async def get_user(self, user_id: str, session: AsyncSession) -> User | None:
        """Get a user by ID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str, session: AsyncSession) -> User | None:
        """Get a user by email address."""
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_all_users(
        self, session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> list[User]:
        """Get all users with pagination."""
        query = (
            select(User)
            .where(User.is_active)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_active_users(self, session: AsyncSession) -> list[User]:
        """Get all active users."""
        result = await session.execute(select(User).where(User.is_active))
        return list(result.scalars().all())

    async def create_user(
        self, user_data: dict[str, Any], session: AsyncSession
    ) -> User:
        """Create a new user."""
        user = User(**user_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def update_user(
        self, user_id: str, user_data: dict[str, Any], session: AsyncSession
    ) -> User | None:
        """Update an existing user."""
        user = await self.get_user(user_id, session)
        if not user:
            return None

        # Update user fields
        for field, value in user_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(user)
        return user

    async def deactivate_user(self, user_id: str, session: AsyncSession) -> bool:
        """Deactivate a user (soft delete)."""
        user = await self.get_user(user_id, session)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.now(UTC)
        await session.commit()
        return True

    async def activate_user(self, user_id: str, session: AsyncSession) -> bool:
        """Activate a user."""
        user = await self.get_user(user_id, session)
        if not user:
            return False

        user.is_active = True
        user.updated_at = datetime.now(UTC)
        await session.commit()
        return True

    async def get_user_summary(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Get a summary of user information for use in alerts and notifications."""
        user = await self.get_user(user_id, session)
        if not user:
            return None

        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': f'{user.first_name} {user.last_name}',
            'phone_number': user.phone_number,
            'address': {
                'street': user.address_street,
                'city': user.address_city,
                'state': user.address_state,
                'zipcode': user.address_zipcode,
                'country': user.address_country,
            }
            if any([user.address_street, user.address_city, user.address_state])
            else None,
            'location_consent_given': user.location_consent_given,
            'credit_limit': float(user.credit_limit) if user.credit_limit else None,
            'credit_balance': float(user.credit_balance)
            if user.credit_balance
            else None,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }

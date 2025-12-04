"""Transaction Service - Business logic for transaction operations"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction


class TransactionService:
    """Service class for transaction business logic and data access"""

    async def get_latest_transaction(
        self, user_id: str, session: AsyncSession
    ) -> Transaction | None:
        """Get the latest transaction for a user."""
        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_user_transactions(
        self, user_id: str, session: AsyncSession, limit: int = 50, offset: int = 0
    ) -> list[Transaction]:
        """Get transactions for a user with pagination."""
        query = select(Transaction).where(Transaction.user_id == user_id)
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_transactions_with_filters(
        self,
        session: AsyncSession,
        user_id: str | None = None,
        credit_card_id: str | None = None,
        merchant_category: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get transactions with various filters."""
        query = select(Transaction)

        if user_id:
            query = query.where(Transaction.user_id == user_id)

        if credit_card_id:
            query = query.where(Transaction.credit_card_num == credit_card_id)

        if merchant_category:
            query = query.where(Transaction.merchant_category == merchant_category)

        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)

        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_transaction_by_id(
        self, transaction_id: str, session: AsyncSession
    ) -> Transaction | None:
        """Get a specific transaction by ID."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def user_has_transactions(self, user_id: str, session: AsyncSession) -> bool:
        """Check if a user has any transactions."""
        result = await session.execute(
            select(Transaction).where(Transaction.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def get_dummy_transaction(self, user_id: str) -> dict[str, Any]:
        """Get a dummy transaction for a user (for testing/fallback purposes)."""
        return {
            'user_id': user_id,
            'transaction_date': datetime.now().isoformat(),
            'credit_card_num': '1234567890',
            'amount': 100.00,
            'currency': 'USD',
            'description': 'Dummy transaction',
            'merchant_name': 'Dummy merchant',
            'merchant_category': 'Dummy category',
            'merchant_city': 'Dummy city',
            'merchant_state': 'Dummy state',
            'merchant_country': 'Dummy country',
            'merchant_zipcode': 'Dummy zipcode',
            'merchant_latitude': 10.00,
            'merchant_longitude': 10.00,
            'trans_num': 'Dummy trans_num',
            'authorization_code': 'Dummy authorization_code',
            'status': 'Dummy status',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

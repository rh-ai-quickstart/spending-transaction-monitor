"""Verify user data by printing joined info"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import SessionLocal
from db.models import User


async def verify() -> None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.creditCards),
                selectinload(User.transactions),
                selectinload(User.alertRules),
            )
            .where(User.email == 'john.doe@example.com')
        )
        user = result.scalar_one_or_none()
        if not user:
            print('User not found')
            return

        print('USER PROFILE:')
        print(f'   Name: {user.first_name} {user.last_name}')
        print(f'   Email: {user.email}')
        print(f'   Phone: {user.phone_number}')
        print(f'   Active: {user.is_active}\n')

        print('ADDRESS:')
        print(f'   Street: {user.address_street}')
        print(
            f'   City: {user.address_city}, {user.address_state} {user.address_zipcode}'
        )
        print(f'   Country: {user.address_country}\n')

        print('FINANCIAL INFO:')
        print(f'   Credit Limit: {user.credit_limit}')
        print(f'   Current Balance: {user.credit_balance}\n')

        print('RELATED DATA:')
        print(f'   Credit Cards: {len(user.creditCards)}')
        print(f'   Transactions: {len(user.transactions)}')
        print(f'   Alert Rules: {len(user.alertRules)}')


if __name__ == '__main__':
    asyncio.run(verify())

"""Seed database with sample data"""

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from db.database import SessionLocal
from db.models import (
    AlertRule,
    AlertType,
    CreditCard,
    NotificationMethod,
    Transaction,
    User,
)


async def seed() -> None:
    async with SessionLocal() as session:  # type: AsyncSession
        # Check if already seeded
        existing = await session.execute(
            select(User).where(User.email == 'john.doe@example.com')
        )
        if existing.scalar_one_or_none():
            print('Database already seeded; skipping.')
            return

        user_id = str(uuid.uuid4())
        card_id = str(uuid.uuid4())

        user = User(
            id=user_id,
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe',
            phone_number='+1-555-0123',
            address_street='123 Main Street, Apt 4B',
            address_city='San Francisco',
            address_state='CA',
            address_zipcode='94102',
            address_country='US',
            credit_limit=Decimal('15000.00'),
            credit_balance=Decimal('2347.85'),
            location_consent_given=True,
            last_app_location_latitude=37.7749,
            last_app_location_longitude=-122.4194,
            last_app_location_timestamp=datetime.fromisoformat(
                '2024-01-17T18:30:00+00:00'
            ),
            last_app_location_accuracy=5.0,
            last_transaction_latitude=37.7849,
            last_transaction_longitude=-122.4094,
            last_transaction_timestamp=datetime.fromisoformat(
                '2024-01-17T19:20:00+00:00'
            ),
            last_transaction_city='San Francisco',
            last_transaction_state='CA',
            last_transaction_country='US',
        )
        session.add(user)

        card = CreditCard(
            id=card_id,
            user_id=user_id,
            card_number='1234',
            card_type='Visa',
            bank_name='Example Bank',
            card_holder_name='John Doe',
            expiry_month=12,
            expiry_year=2027,
        )
        session.add(card)

        txs = [
            Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credit_card_num=card_id,
                amount=Decimal('89.99'),
                description='Grocery shopping',
                merchant_name='Whole Foods Market',
                merchant_category='Grocery',
                transaction_date=datetime.fromisoformat('2024-01-15T10:30:00+00:00'),
                merchant_city='San Francisco',
                merchant_state='CA',
                merchant_country='US',
                status=None,  # default
            ),
            Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credit_card_num=card_id,
                amount=Decimal('1299.99'),
                description='Laptop purchase',
                merchant_name='Apple Store',
                merchant_category='Electronics',
                transaction_date=datetime.fromisoformat('2024-01-16T14:45:00+00:00'),
                merchant_city='San Francisco',
                merchant_state='CA',
                merchant_country='US',
            ),
            Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credit_card_num=card_id,
                amount=Decimal('45.50'),
                description='Dinner',
                merchant_name='Restaurant ABC',
                merchant_category='Dining',
                transaction_date=datetime.fromisoformat('2024-01-17T19:20:00+00:00'),
                merchant_city='San Francisco',
                merchant_state='CA',
                merchant_country='US',
            ),
        ]
        session.add_all(txs)

        rules = [
            AlertRule(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name='High Amount Alert',
                description='Alert for transactions over $1000',
                alert_type=AlertType.AMOUNT_THRESHOLD,
                amount_threshold=Decimal('1000.00'),
                notification_methods=[NotificationMethod.EMAIL, NotificationMethod.SMS],
            ),
            AlertRule(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name='Electronics Purchase Alert',
                description='Alert for all electronics purchases',
                alert_type=AlertType.MERCHANT_CATEGORY,
                merchant_category='Electronics',
                notification_methods=[NotificationMethod.EMAIL],
            ),
            AlertRule(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name='AI Smart Alert',
                description='Smart pattern-based alerts using AI',
                alert_type=AlertType.PATTERN_BASED,
                natural_language_query='Alert me when I spend more than usual on dining in a week',
                notification_methods=[NotificationMethod.PUSH],
            ),
        ]
        session.add_all(rules)

        await session.commit()
        print('Seeded sample user, card, transactions, and rules.')


if __name__ == '__main__':
    asyncio.run(seed())

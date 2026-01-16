#!/usr/bin/env python3
"""
Script to test email notifications by creating a new user and transactions
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import sys

sys.path.append("packages/db/src")
sys.path.append("packages/api/src")

from db.database import SessionLocal
from db.models import (
    User,
    CreditCard,
    Transaction,
    AlertRule,
    NotificationMethod,
    AlertType,
)


async def create_test_user_and_transactions():
    """Create Yash Oza user with transactions that will trigger alerts"""

    async with SessionLocal() as session:
        try:
            # Create user Yash Oza
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                email="yoyashoza@gmail.com",
                first_name="Yash",
                last_name="Oza",
                phone_number="+1-555-0199",
                is_active=True,
                address_street="456 Tech Street",
                address_city="San Francisco",
                address_state="CA",
                address_zipcode="94105",
                address_country="US",
                credit_limit=Decimal("20000.00"),
                credit_balance=Decimal("1500.50"),
                location_consent_given=True,
                last_app_location_latitude=37.7849,
                last_app_location_longitude=-122.4094,
                last_app_location_timestamp=datetime.utcnow(),
                last_app_location_accuracy=10.0,
            )

            session.add(user)
            await session.flush()  # Get the user ID

            # Create credit card
            card_id = str(uuid.uuid4())
            card = CreditCard(
                id=card_id,
                user_id=user_id,
                card_number="5678",
                card_type="Mastercard",
                bank_name="Tech Bank",
                card_holder_name="Yash Oza",
                expiry_month=8,
                expiry_year=2028,
            )

            session.add(card)
            await session.flush()

            # Create transactions that will trigger alerts
            current_time = datetime.utcnow()

            transactions = [
                # High amount transaction - should trigger $500+ alert
                Transaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    credit_card_num=card_id,
                    amount=Decimal("899.99"),
                    currency="USD",
                    description="New iPhone 15 Pro",
                    merchant_name="Apple Store",
                    merchant_category="Electronics",
                    transaction_date=current_time - timedelta(minutes=5),
                    merchant_city="San Francisco",
                    merchant_state="CA",
                    merchant_country="US",
                ),
                # Another high amount transaction
                Transaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    credit_card_num=card_id,
                    amount=Decimal("1299.99"),
                    currency="USD",
                    description="MacBook Pro",
                    merchant_name="Apple Store",
                    merchant_category="Electronics",
                    transaction_date=current_time - timedelta(minutes=2),
                    merchant_city="San Francisco",
                    merchant_state="CA",
                    merchant_country="US",
                ),
                # Recent dining transaction
                Transaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    credit_card_num=card_id,
                    amount=Decimal("85.50"),
                    currency="USD",
                    description="Dinner with friends",
                    merchant_name="Fine Dining Restaurant",
                    merchant_category="Dining",
                    transaction_date=current_time - timedelta(minutes=1),
                    merchant_city="San Francisco",
                    merchant_state="CA",
                    merchant_country="US",
                ),
            ]

            # Create an alert rule for Yash that will trigger on $500+ transactions
            alert_rule = AlertRule(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name="High Spending Alert",
                description="Alert when spending more than $500 in one transaction",
                is_active=True,
                alert_type=AlertType.AMOUNT_THRESHOLD,
                amount_threshold=Decimal("500.00"),
                natural_language_query="Alert me when I spend more than $500 in one transaction",
                notification_methods=[NotificationMethod.EMAIL],
            )

            session.add(alert_rule)

            for transaction in transactions:
                session.add(transaction)

            await session.commit()

            print(f"✅ Created user: {user.first_name} {user.last_name} ({user.email})")
            print(f"✅ Created {len(transactions)} transactions")
            print(f"✅ Created alert rule: {alert_rule.name}")
            print("\nTransactions created:")
            for txn in transactions:
                print(
                    f"  - ${txn.amount} at {txn.merchant_name} ({txn.transaction_date})"
                )

            return user_id, alert_rule.id

        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(create_test_user_and_transactions())

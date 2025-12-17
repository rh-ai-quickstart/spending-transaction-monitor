#!/usr/bin/env python3
"""
Load Sample Alert Rules into Database
--------------------------------------

This script loads sample alert rules from CSV into the database
so the ML model has real data to work with for collaborative filtering.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys
import uuid

import pandas as pd

# Add the API package to path
sys.path.insert(0, str(Path(__file__).parent))

from db.database import SessionLocal
from db.models import AlertRule


async def load_sample_alerts():
    """Load sample alert rules from CSV into database"""

    print('=' * 60)
    print('Loading Sample Alert Rules into Database')
    print('=' * 60)

    # Load CSV
    data_dir = Path(__file__).parent.parent.parent / 'data'
    csv_path = data_dir / 'sample_user_alerts.csv'

    if not csv_path.exists():
        print(f'❌ CSV file not found: {csv_path}')
        return

    alerts_df = pd.read_csv(csv_path)
    print(f'✅ Loaded {len(alerts_df)} alert preferences from CSV')

    # Map alert types to natural language queries
    alert_type_mapping = {
        'alert_high_spender': {
            'name': 'High Spending Alert',
            'description': 'Monitor when total spending exceeds a threshold',
            'natural_language_query': 'Notify me when my total spending exceeds $2500',
            'alert_type': 'spending_threshold',
        },
        'alert_large_transaction': {
            'name': 'Large Transaction Alert',
            'description': 'Monitor unusually large purchases',
            'natural_language_query': 'Notify me when a single transaction exceeds $1000',
            'alert_type': 'fraud_protection',
        },
        'alert_near_credit_limit': {
            'name': 'Credit Limit Alert',
            'description': 'Get warned when approaching credit limit',
            'natural_language_query': 'Notify me when my credit utilization exceeds 70%',
            'alert_type': 'spending_threshold',
        },
        'alert_high_tx_volume': {
            'name': 'Frequent Transaction Alert',
            'description': 'Get notified when you have many transactions',
            'natural_language_query': 'Notify me when I have more than 10 transactions in a day',
            'alert_type': 'fraud_protection',
        },
        'alert_new_merchant': {
            'name': 'New Merchant Alert',
            'description': 'Track purchases from new merchants',
            'natural_language_query': 'Notify me when I make a purchase from a new merchant',
            'alert_type': 'fraud_protection',
        },
        'alert_high_merchant_diversity': {
            'name': 'Merchant Diversity Alert',
            'description': 'Track when you visit multiple different merchants',
            'natural_language_query': 'Notify me when I visit more than 5 different merchants in a day',
            'alert_type': 'merchant_monitoring',
        },
        'alert_location_based': {
            'name': 'Location-Based Alert',
            'description': 'Detect transactions in unusual locations',
            'natural_language_query': 'Notify me of transactions in unusual locations',
            'alert_type': 'location_based',
        },
        'alert_subscription_monitoring': {
            'name': 'Subscription Monitoring',
            'description': 'Track recurring subscription charges',
            'natural_language_query': 'Notify me of recurring subscription charges',
            'alert_type': 'subscription_monitoring',
        },
    }

    async with SessionLocal() as session:
        # Clear existing sample alerts (optional - only alerts without notifications)
        from sqlalchemy import select

        print('\n🗑️  Checking for existing alert rules...')
        existing_count = (await session.execute(select(AlertRule))).scalar()

        if existing_count:
            print(
                f'⚠️  Found {len(list(existing_count)) if hasattr(existing_count, "__iter__") else "some"} existing rules'
            )
            print('   Keeping existing rules and adding new ones...')

        # Create alert rules from CSV
        created_count = 0
        skipped_count = 0

        for _, row in alerts_df.iterrows():
            user_id = row['user_id']
            alert_type_key = row['alert_type']
            enabled = row['enabled']

            if not enabled:
                continue

            mapping = alert_type_mapping.get(alert_type_key)
            if not mapping:
                print(f'⚠️  Unknown alert type: {alert_type_key}')
                continue

            # Check if this user already has this alert type
            result = await session.execute(
                select(AlertRule).where(
                    AlertRule.user_id == user_id, AlertRule.name == mapping['name']
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                skipped_count += 1
                continue

            # Create new alert rule
            rule = AlertRule(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=mapping['name'],
                description=mapping['description'],
                is_active=True,
                alert_type=mapping['alert_type'],
                natural_language_query=mapping['natural_language_query'],
                notification_methods=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            session.add(rule)
            created_count += 1

        await session.commit()

        print(f'\n✅ Created {created_count} new alert rules')
        print(f'⏭️  Skipped {skipped_count} existing rules')

        # Verify
        total_rules = (await session.execute(select(AlertRule))).scalars().all()
        print(f'📊 Total alert rules in database: {len(total_rules)}')

    print('\n' + '=' * 60)
    print('✅ Sample Alert Rules Loaded Successfully!')
    print('=' * 60)
    print('\nNext step: Clear cache and regenerate recommendations')
    print('  podman exec postgres psql -U user -d spending-monitor \\')
    print('    -c "DELETE FROM cached_recommendations;"')


if __name__ == '__main__':
    asyncio.run(load_sample_alerts())

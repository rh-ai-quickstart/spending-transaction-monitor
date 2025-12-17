"""
ML Model Startup Initialization
--------------------------------

This module initializes the ML recommendation system on application startup:
1. Loads sample alert rules into the database (if not already present)
2. Trains the ML model with existing alert data
"""

from datetime import UTC, datetime
import logging
from pathlib import Path
import uuid

import pandas as pd
from sqlalchemy import select

from db.database import SessionLocal
from db.models import AlertRule

logger = logging.getLogger(__name__)


async def initialize_ml_system():
    """
    Initialize the ML recommendation system on startup.

    This function:
    1. Checks if sample alerts are loaded in the database
    2. If not, loads them from CSV
    3. Trains the ML model with the alert data
    """
    logger.info('🤖 Initializing ML recommendation system...')

    try:
        # Step 1: Load sample alerts if database is empty
        await load_sample_alerts_if_needed()

        # Step 2: Train or verify ML model
        await train_ml_model_if_needed()

        logger.info('✅ ML recommendation system initialized successfully')

    except Exception as e:
        logger.error(f'❌ Failed to initialize ML system: {e}', exc_info=True)
        logger.warning('⚠️  Continuing without ML initialization - will use defaults')


async def load_sample_alerts_if_needed():
    """Load sample alert rules from CSV if database has no alerts"""

    async with SessionLocal() as session:
        # Check if we have any alert rules
        result = await session.execute(select(AlertRule))
        existing_rules = result.scalars().all()

        if len(existing_rules) > 0:
            logger.info(
                f'📊 Found {len(existing_rules)} existing alert rules in database'
            )
            return

        logger.info('📂 No alert rules found - loading sample data...')

        # Load sample alerts from CSV
        data_dir = Path('/app/data')
        csv_path = data_dir / 'sample_user_alerts.csv'

        if not csv_path.exists():
            logger.warning(f'⚠️  Sample alerts CSV not found: {csv_path}')
            logger.warning('   Skipping sample data load')
            return

        alerts_df = pd.read_csv(csv_path)
        logger.info(f'✅ Loaded {len(alerts_df)} alert preferences from CSV')

        # Map alert types to natural language queries
        # Valid enum values: AMOUNT_THRESHOLD, MERCHANT_CATEGORY, MERCHANT_NAME, LOCATION_BASED, FREQUENCY_BASED, PATTERN_BASED, CUSTOM_QUERY
        alert_type_mapping = {
            'alert_high_spender': {
                'name': 'High Spending Alert',
                'description': 'Monitor when total spending exceeds a threshold',
                'natural_language_query': 'Notify me when my total spending exceeds $2500',
                'alert_type': 'AMOUNT_THRESHOLD',
            },
            'alert_large_transaction': {
                'name': 'Large Transaction Alert',
                'description': 'Monitor unusually large purchases',
                'natural_language_query': 'Notify me when a single transaction exceeds $1000',
                'alert_type': 'AMOUNT_THRESHOLD',
            },
            'alert_near_credit_limit': {
                'name': 'Credit Limit Alert',
                'description': 'Get warned when approaching credit limit',
                'natural_language_query': 'Notify me when my credit utilization exceeds 70%',
                'alert_type': 'PATTERN_BASED',
            },
            'alert_high_tx_volume': {
                'name': 'Frequent Transaction Alert',
                'description': 'Get notified when you have many transactions',
                'natural_language_query': 'Notify me when I have more than 10 transactions in a day',
                'alert_type': 'FREQUENCY_BASED',
            },
            'alert_new_merchant': {
                'name': 'New Merchant Alert',
                'description': 'Track purchases from new merchants',
                'natural_language_query': 'Notify me when I make a purchase from a new merchant',
                'alert_type': 'MERCHANT_NAME',
            },
            'alert_high_merchant_diversity': {
                'name': 'Merchant Diversity Alert',
                'description': 'Track when you visit multiple different merchants',
                'natural_language_query': 'Notify me when I visit more than 5 different merchants in a day',
                'alert_type': 'MERCHANT_CATEGORY',
            },
            'alert_location_based': {
                'name': 'Location-Based Alert',
                'description': 'Detect transactions in unusual locations',
                'natural_language_query': 'Notify me of transactions in unusual locations',
                'alert_type': 'LOCATION_BASED',
            },
            'alert_subscription_monitoring': {
                'name': 'Subscription Monitoring',
                'description': 'Track recurring subscription charges',
                'natural_language_query': 'Notify me of recurring subscription charges',
                'alert_type': 'PATTERN_BASED',
            },
        }

        # Create alert rules from CSV
        created_count = 0

        for _, row in alerts_df.iterrows():
            user_id = row['user_id']
            alert_type_key = row['alert_type']
            enabled = row['enabled']

            if not enabled:
                continue

            mapping = alert_type_mapping.get(alert_type_key)
            if not mapping:
                logger.warning(f'⚠️  Unknown alert type: {alert_type_key}')
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

        logger.info(f'✅ Created {created_count} sample alert rules in database')


async def train_ml_model_if_needed():
    """Train ML model if not already trained"""

    try:
        from src.ml.alert_recommender import AlertRecommenderModel
        from src.ml.alert_recommender.training import train_model

        # Check if model exists and is trained
        model = AlertRecommenderModel()

        if model.is_trained():
            logger.info('✅ ML model already trained and loaded')
            return

        logger.info('🤖 Training ML model with database data...')

        # Train model using database data
        async with SessionLocal() as session:
            trained_model = await train_model(
                session=session,
                model_path=model.model_path,
                n_neighbors=5,
                use_real_alerts=True,
            )

        logger.info(f'✅ ML model trained and saved to {trained_model.model_path}')

    except Exception as e:
        logger.error(f'❌ Failed to train ML model: {e}', exc_info=True)
        logger.warning('⚠️  Continuing without trained model - will use defaults')

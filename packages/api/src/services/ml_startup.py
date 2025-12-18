"""
ML Model Startup Initialization
--------------------------------

This module initializes the ML recommendation system on application startup:
1. Checks for existing alert rules in the database
2. Trains the ML model with existing alert data (or uses heuristic-based training)
"""

import logging

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
    """
    Skip loading sample alerts to avoid creating active alerts for users.

    The ML model will use heuristic-based training labels instead of pre-seeded alerts.
    As real users create real alerts, the model will learn from actual user preferences.
    """
    async with SessionLocal() as session:
        # Check if we have any alert rules
        result = await session.execute(select(AlertRule))
        existing_rules = result.scalars().all()

        if len(existing_rules) > 0:
            logger.info(
                f'📊 Found {len(existing_rules)} existing alert rules in database'
            )
        else:
            logger.info(
                '📊 No alert rules found - model will use heuristic-based training'
            )

        logger.info(
            '⏭️  Skipping sample alert creation (using heuristic training instead)'
        )


async def train_ml_model_if_needed():
    """Train ML model if not already trained"""

    try:
        from src.services.recommendations.ml import AlertRecommenderModel
        from src.services.recommendations.ml.training import train_model

        # Check if model exists and is trained
        model = AlertRecommenderModel()

        if model.is_trained():
            logger.info('✅ ML model already trained and loaded')
            return

        logger.info('🤖 Training ML model with database data...')

        # Check if we have real alert data
        async with SessionLocal() as session:
            result = await session.execute(select(AlertRule))
            existing_rules = result.scalars().all()
            has_real_alerts = len(existing_rules) > 0

            if has_real_alerts:
                logger.info(
                    f'📊 Found {len(existing_rules)} alert rules - using real alert data'
                )
            else:
                logger.info(
                    '📊 No alert rules found - using heuristic-based training labels'
                )

            # Train model using database data
            trained_model = await train_model(
                session=session,
                model_path=model.model_path,
                n_neighbors=5,
                use_real_alerts=has_real_alerts,
            )

        logger.info(f'✅ ML model trained and saved to {trained_model.model_path}')

    except Exception as e:
        logger.error(f'❌ Failed to train ML model: {e}', exc_info=True)
        logger.warning('⚠️  Continuing without trained model - will use defaults')

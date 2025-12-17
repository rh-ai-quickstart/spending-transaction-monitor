"""
Scheduled Retraining Module
---------------------------

Provides functionality for scheduled model retraining.
Can be run as a cron job or background task to periodically
retrain the model with new data.
"""

import asyncio
from datetime import datetime
import logging

from db.database import SessionLocal

from .training import retrain_model, should_retrain_model

logger = logging.getLogger(__name__)


async def run_scheduled_retraining(
    model_path: str | None = None, force: bool = False
) -> dict:
    """
    Run scheduled model retraining.

    Args:
        model_path: Path to the model file
        force: Force retraining even if model is fresh

    Returns:
        Dictionary with retraining results
    """
    logger.info('Starting scheduled model retraining check...')

    # Check if retraining is needed
    if not force and not should_retrain_model(model_path, days_threshold=7):
        logger.info('Model is still fresh, skipping retraining')
        return {
            'status': 'skipped',
            'reason': 'Model is still fresh (< 7 days old)',
            'timestamp': datetime.now().isoformat(),
        }

    logger.info('Model needs retraining, starting process...')

    # Create database session
    async with SessionLocal() as session:
        try:
            # Retrain the model
            model = await retrain_model(
                session=session, model_path=model_path, n_neighbors=5
            )

            logger.info('Model retraining completed successfully')

            return {
                'status': 'success',
                'message': 'Model retrained successfully',
                'timestamp': datetime.now().isoformat(),
                'model_path': model.model_path,
            }

        except Exception as e:
            logger.error(f'Error during scheduled retraining: {str(e)}', exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat(),
            }


def run_scheduled_retraining_sync(
    model_path: str | None = None, force: bool = False
) -> dict:
    """
    Synchronous wrapper for scheduled retraining.
    Useful for cron jobs.

    Args:
        model_path: Path to the model file
        force: Force retraining even if model is fresh

    Returns:
        Dictionary with retraining results
    """
    return asyncio.run(run_scheduled_retraining(model_path, force))


if __name__ == '__main__':
    # Can be run directly from command line
    import sys

    force = '--force' in sys.argv

    print('=' * 60)
    print('Alert Recommendation Model - Scheduled Retraining')
    print('=' * 60)

    result = run_scheduled_retraining_sync(force=force)

    print(f'\nStatus: {result["status"]}')
    print(f'Timestamp: {result["timestamp"]}')

    if result['status'] == 'success':
        print(f'✓ {result["message"]}')
        if 'model_path' in result:
            print(f'Model saved to: {result["model_path"]}')
    elif result['status'] == 'skipped':
        print(f'→ {result["reason"]}')
    else:
        print(f'✗ Error: {result["message"]}')

    sys.exit(0 if result['status'] in ['success', 'skipped'] else 1)

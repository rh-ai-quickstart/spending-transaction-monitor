"""Background Recommendation Service - Pre-generate and cache alert recommendations"""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any
import uuid

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal
from db.models import CachedRecommendation, User

from .alert_recommendation_service import AlertRecommendationService
from .recommendation_metrics import recommendation_metrics

logger = logging.getLogger(__name__)


class BackgroundRecommendationService:
    """Service for generating and caching alert recommendations in the background"""

    def __init__(self):
        self.recommendation_service = AlertRecommendationService()
        # Cache recommendations for 24 hours
        self.cache_duration_hours = 24

    def generate_recommendations_for_user_sync(self, user_id: str) -> dict[str, Any]:
        """Generate and cache recommendations for a specific user using synchronous operations"""

        # Start performance tracking
        metrics = recommendation_metrics.start_tracking(user_id)

        # Use synchronous database operations for background processing

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Convert async DATABASE_URL to sync URL for synchronous operations
        from core.config import settings
        from db.models import (
            User as SyncUser,
        )

        sync_database_url = settings.DATABASE_URL.replace(
            'postgresql+asyncpg://', 'postgresql://'
        )

        # Create synchronous engine and session
        sync_engine = create_engine(sync_database_url, echo=False)
        SyncSessionLocal = sessionmaker(bind=sync_engine)
        sync_session = SyncSessionLocal()

        try:
            # Check if user exists using sync operations
            user = sync_session.query(SyncUser).filter(SyncUser.id == user_id).first()
            if not user:
                logger.error(f'User {user_id} not found')
                recommendation_metrics.finish_tracking(
                    metrics, success=False, error_message='User not found'
                )
                return {'status': 'error', 'message': 'User not found'}

            # Generate recommendations using sync operations
            recommendations = self._generate_recommendations_sync(
                user_id, sync_session, user
            )

            if 'error' in recommendations:
                logger.error(
                    f'Failed to generate recommendations for user {user_id}: {recommendations["error"]}'
                )
                recommendation_metrics.finish_tracking(
                    metrics, success=False, error_message=recommendations['error']
                )
                return {'status': 'error', 'message': recommendations['error']}

            # Cache the recommendations
            self._cache_recommendations_sync(user_id, recommendations, sync_session)

            # Send WebSocket notification that recommendations are ready
            try:
                # Schedule the WebSocket notification in the main event loop
                # This will be handled by the main thread when it processes the job
                logger.info(
                    f'Generated personalized recommendations for user {user_id}'
                )
            except Exception as e:
                logger.warning(
                    f'Failed to prepare WebSocket notification for user {user_id}: {e}'
                )

            # Finish tracking with success metrics
            recommendation_metrics.finish_tracking(
                metrics,
                success=True,
                recommendation_type=recommendations.get(
                    'recommendation_type', 'unknown'
                ),
                recommendation_count=len(recommendations.get('recommendations', [])),
                thread_pool_used=True,
            )

            logger.info(
                f'Successfully generated and cached recommendations for user {user_id}'
            )
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendation_type': recommendations.get(
                    'recommendation_type', 'unknown'
                ),
                'recommendation_count': len(recommendations.get('recommendations', [])),
                'generated_at': recommendations.get('generated_at'),
            }

        except Exception as e:
            logger.error(
                f'Error generating recommendations for user {user_id}: {str(e)}',
                exc_info=True,
            )
            recommendation_metrics.finish_tracking(
                metrics, success=False, error_message=str(e)
            )
            return {
                'status': 'error',
                'message': f'Failed to generate recommendations: {str(e)}',
            }
        finally:
            sync_session.close()

    def _generate_recommendations_sync(
        self, user_id: str, sync_session, user
    ) -> dict[str, Any]:
        """Generate recommendations using synchronous operations"""
        try:
            # Run the recommendation service synchronously directly
            result = self._run_recommendation_service_sync(user_id, user.__dict__)
            return result

        except Exception as e:
            logger.error(f'Error in _generate_recommendations_sync: {str(e)}')
            return {'error': str(e)}

    def _run_recommendation_service_sync(
        self, user_id: str, user_dict: dict
    ) -> dict[str, Any]:
        """Run the recommendation service synchronously"""
        try:
            # Import the recommendation service functions
            # Get transaction data synchronously
            from sqlalchemy import create_engine, text

            from core.config import settings
            from services.agents.alert_recommender import (
                analyze_transaction_patterns,
                find_similar_users,
                recommend_alerts_for_existing_user,
                recommend_alerts_for_new_user,
            )

            sync_database_url = settings.DATABASE_URL.replace(
                'postgresql+asyncpg://', 'postgresql://'
            )
            sync_engine = create_engine(sync_database_url, echo=False)

            with sync_engine.connect() as conn:
                # Get transaction data
                result = conn.execute(
                    text("""
                    SELECT amount, merchant_category, merchant_name, created_at, 
                           merchant_city, merchant_state, merchant_country
                    FROM transactions 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT 1000
                """),
                    {'user_id': user_id},
                )

                transactions = [dict(row._mapping) for row in result]

                if not transactions:
                    # New user recommendations
                    return recommend_alerts_for_new_user(user_dict)
                else:
                    # Existing user recommendations
                    transaction_analysis = analyze_transaction_patterns(transactions)

                    # Get similar users data
                    similar_users_result = conn.execute(
                        text("""
                        SELECT id, first_name, last_name, address_city, address_state, 
                               address_country, credit_limit, created_at
                        FROM users 
                        WHERE id != :user_id AND is_active = true
                        LIMIT 100
                    """),
                        {'user_id': user_id},
                    )

                    similar_users_data = [
                        dict(row._mapping) for row in similar_users_result
                    ]
                    similar_users = find_similar_users(user_dict, similar_users_data)

                    return recommend_alerts_for_existing_user(
                        user_dict, transaction_analysis, similar_users
                    )

        except Exception as e:
            logger.error(f'Error in _run_recommendation_service_sync: {str(e)}')
            return {'error': str(e)}

    def _cache_recommendations_sync(
        self, user_id: str, recommendations: dict, sync_session
    ):
        """Cache recommendations using synchronous operations"""
        try:
            from datetime import UTC, datetime, timedelta
            import json

            from db.models import CachedRecommendation as SyncCachedRecommendation

            # Delete existing cached recommendations for this user
            sync_session.query(SyncCachedRecommendation).filter(
                SyncCachedRecommendation.user_id == user_id
            ).delete()

            # Create new cached recommendation
            expires_at = datetime.now(UTC) + timedelta(hours=self.cache_duration_hours)

            cached_rec = SyncCachedRecommendation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                recommendation_type=recommendations.get(
                    'recommendation_type', 'unknown'
                ),
                recommendations_json=json.dumps(recommendations),
                expires_at=expires_at,
            )

            sync_session.add(cached_rec)
            sync_session.commit()

            logger.info(f'Cached recommendations for user {user_id} until {expires_at}')

        except Exception as e:
            logger.error(f'Error caching recommendations for user {user_id}: {str(e)}')
            sync_session.rollback()
            raise e

    async def generate_recommendations_for_user(
        self, user_id: str, session: AsyncSession = None
    ) -> dict[str, Any]:
        """Generate and cache recommendations for a specific user"""

        # Start performance tracking
        logger.info(f'In generate_recommendations_for_user for user {user_id}')
        metrics = recommendation_metrics.start_tracking(user_id)

        owns_session = False
        if session is None:
            owns_session = True
            session_ctx = SessionLocal()
            session = await session_ctx.__aenter__()
            logger.info(f'Acquired session for user {user_id}')

        try:
            # Check if user exists
            logger.info(f'Checking if user {user_id} exists')
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                logger.error(f'User {user_id} not found')
                recommendation_metrics.finish_tracking(
                    metrics, success=False, error_message='User not found'
                )
                return {'status': 'error', 'message': 'User not found'}

            # Generate recommendations using existing service
            logger.info(f'Generating recommendations for user {user_id}')
            recommendations = await self.recommendation_service.get_recommendations(
                user_id, session
            )

            if 'error' in recommendations:
                recommendation_metrics.finish_tracking(
                    metrics, success=False, error_message=recommendations['error']
                )
                return {'status': 'error', 'message': recommendations['error']}

            # Cache the recommendations
            await self._cache_recommendations(user_id, recommendations, session)

            # Notify user via WebSocket that personalized recommendations are ready
            try:
                from routes.websocket import notify_recommendations_ready

                logger.info(f'Sending WebSocket notification for user {user_id}')
                await notify_recommendations_ready(user_id, recommendations)
            except Exception as e:
                logger.warning(
                    f'Failed to send WebSocket notification for user {user_id}: {e}'
                )

            # Finish tracking with success metrics
            recommendation_metrics.finish_tracking(
                metrics,
                success=True,
                recommendation_type=recommendations.get(
                    'recommendation_type', 'unknown'
                ),
                recommendation_count=len(recommendations.get('recommendations', [])),
                thread_pool_used=True,  # We're using thread pools now
            )

            logger.info(
                f'Successfully generated and cached recommendations for user {user_id}'
            )
            return {
                'status': 'success',
                'user_id': user_id,
                'recommendation_type': recommendations.get('recommendation_type'),
                'recommendation_count': len(recommendations.get('recommendations', [])),
                'generated_at': recommendations.get('generated_at'),
            }

        except Exception as e:
            logger.error(
                f'Error generating recommendations for user {user_id}: {str(e)}',
                exc_info=True,
            )
            recommendation_metrics.finish_tracking(
                metrics, success=False, error_message=str(e)
            )
            return {
                'status': 'error',
                'message': f'Failed to generate recommendations: {str(e)}',
            }
        finally:
            if owns_session:
                await session_ctx.__aexit__(None, None, None)

    def _process_user_batch_sync(
        self, users: list, max_concurrent: int
    ) -> list[dict[str, Any]]:
        """Process a batch of users with controlled concurrency using sync operations"""

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Create a semaphore to limit concurrent operations
        _ = asyncio.Semaphore(max_concurrent)

        def process_single_user_sync(user) -> dict[str, Any]:
            """Process a single user with semaphore control"""
            try:
                result = self.generate_recommendations_for_user_sync(user.id)
                return {'user_id': user.id, 'result': result}
            except Exception as e:
                logger.error(
                    f'Error generating recommendations for user {user.id}: {str(e)}'
                )
                return {
                    'user_id': user.id,
                    'result': {'status': 'error', 'message': str(e)},
                }

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all tasks
            futures = [
                executor.submit(process_single_user_sync, user) for user in users
            ]

            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f'Error in thread pool execution: {str(e)}')
                    results.append(
                        {
                            'user_id': 'unknown',
                            'result': {'status': 'error', 'message': str(e)},
                        }
                    )

        return results

    async def get_cached_recommendations(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Get cached recommendations for a user if they exist and are not expired"""

        try:
            # Look for non-expired cached recommendations
            result = await session.execute(
                select(CachedRecommendation)
                .where(
                    and_(
                        CachedRecommendation.user_id == user_id,
                        CachedRecommendation.expires_at > datetime.now(UTC),
                    )
                )
                .order_by(CachedRecommendation.generated_at.desc())
                .limit(1)
            )

            cached = result.scalar_one_or_none()
            if not cached:
                return None

            # Parse and return the cached recommendations
            recommendations_data = json.loads(cached.recommendations_json)

            return {
                'user_id': user_id,
                'recommendation_type': cached.recommendation_type,
                'recommendations': recommendations_data.get('recommendations', []),
                'generated_at': cached.generated_at.isoformat(),
                'cached': True,
            }

        except Exception as e:
            logger.error(
                f'Error retrieving cached recommendations for user {user_id}: {str(e)}'
            )
            return None

    def get_cached_recommendations_sync(self, user_id: str) -> dict[str, Any] | None:
        """Get cached recommendations synchronously for WebSocket notifications"""
        try:
            import json

            from sqlalchemy import create_engine, text

            from core.config import settings

            # Convert async DATABASE_URL to sync URL for synchronous operations
            sync_database_url = settings.DATABASE_URL.replace(
                'postgresql+asyncpg://', 'postgresql://'
            )
            sync_engine = create_engine(sync_database_url, echo=False)

            with sync_engine.connect() as conn:
                result = conn.execute(
                    text("""
                    SELECT user_id, recommendation_type, recommendations_json, generated_at
                    FROM cached_recommendations 
                    WHERE user_id = :user_id 
                    AND expires_at > NOW()
                    ORDER BY generated_at DESC 
                    LIMIT 1
                """),
                    {'user_id': user_id},
                )

                row = result.fetchone()
                if not row:
                    return None

                # Parse and return the cached recommendations
                recommendations_data = json.loads(row[2])  # recommendations_json

                return {
                    'user_id': row[0],  # user_id
                    'recommendation_type': row[1],  # recommendation_type
                    'recommendations': recommendations_data.get('recommendations', []),
                    'generated_at': row[3].isoformat(),  # generated_at
                    'cached': True,
                }

        except Exception as e:
            logger.error(
                f'Error retrieving cached recommendations for user {user_id}: {str(e)}'
            )
            return None

    async def _cache_recommendations(
        self, user_id: str, recommendations: dict[str, Any], session: AsyncSession
    ) -> None:
        """Store recommendations in cache"""

        try:
            # Remove any existing cached recommendations for this user
            await session.execute(
                delete(CachedRecommendation).where(
                    CachedRecommendation.user_id == user_id
                )
            )

            # Create new cached recommendation
            expires_at = datetime.now(UTC) + timedelta(hours=self.cache_duration_hours)

            cached_recommendation = CachedRecommendation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                recommendation_type=recommendations.get(
                    'recommendation_type', 'unknown'
                ),
                recommendations_json=json.dumps(
                    {'recommendations': recommendations.get('recommendations', [])}
                ),
                expires_at=expires_at,
            )

            session.add(cached_recommendation)
            await session.commit()

            logger.info(f'Cached recommendations for user {user_id} until {expires_at}')

        except Exception as e:
            logger.error(f'Error caching recommendations for user {user_id}: {str(e)}')
            await session.rollback()
            raise

    async def generate_recommendations_for_all_users(
        self, max_concurrent: int = 10, batch_size: int = 50
    ) -> dict[str, Any]:
        """Generate recommendations for all active users with parallel processing"""

        # Use synchronous database operations for background processing
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Convert async DATABASE_URL to sync URL for synchronous operations
        from core.config import settings
        from db.models import User as SyncUser

        sync_database_url = settings.DATABASE_URL.replace(
            'postgresql+asyncpg://', 'postgresql://'
        )

        # Create synchronous engine and session
        sync_engine = create_engine(sync_database_url, echo=False)
        SyncSessionLocal = sessionmaker(bind=sync_engine)
        sync_session = SyncSessionLocal()

        try:
            # Get all active users using sync operations
            users = sync_session.query(SyncUser).filter(SyncUser.is_active).all()

            total_users = len(users)
            if total_users == 0:
                return {
                    'status': 'completed',
                    'total_users': 0,
                    'success_count': 0,
                    'error_count': 0,
                    'results': [],
                    'generated_at': datetime.now(UTC).isoformat(),
                }

            logger.info(
                f'Starting parallel recommendation generation for {total_users} users '
                f'(max_concurrent: {max_concurrent}, batch_size: {batch_size})'
            )

            # Process users in batches to avoid overwhelming the system
            all_results = []
            success_count = 0
            error_count = 0

            for i in range(0, total_users, batch_size):
                batch_users = users[i : i + batch_size]
                batch_results = self._process_user_batch_sync(
                    batch_users, max_concurrent
                )

                all_results.extend(batch_results)

                # Count successes and errors
                for result in batch_results:
                    if result['result'].get('status') == 'success':
                        success_count += 1
                    else:
                        error_count += 1

                logger.info(
                    f'Processed batch {i // batch_size + 1}/{(total_users + batch_size - 1) // batch_size}: '
                    f'{len(batch_results)} users'
                )

            return {
                'status': 'completed',
                'total_users': total_users,
                'success_count': success_count,
                'error_count': error_count,
                'results': all_results,
                'generated_at': datetime.now(UTC).isoformat(),
                'processing_info': {
                    'max_concurrent': max_concurrent,
                    'batch_size': batch_size,
                    'total_batches': (total_users + batch_size - 1) // batch_size,
                },
            }

        except Exception as e:
            logger.error(
                f'Error in bulk recommendation generation: {str(e)}', exc_info=True
            )
            return {
                'status': 'error',
                'message': f'Bulk generation failed: {str(e)}',
            }
        finally:
            sync_session.close()

    async def _process_user_batch(
        self, users: list[User], max_concurrent: int
    ) -> list[dict[str, Any]]:
        """Process a batch of users with controlled concurrency"""

        # Create a semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_user(user: User) -> dict[str, Any]:
            """Process a single user with semaphore control"""
            async with semaphore:
                try:
                    result = await self.generate_recommendations_for_user(user.id)
                    return {'user_id': user.id, 'result': result}
                except Exception as e:
                    logger.error(
                        f'Error generating recommendations for user {user.id}: {str(e)}'
                    )
                    return {
                        'user_id': user.id,
                        'result': {'status': 'error', 'message': str(e)},
                    }

        # Create tasks for all users in the batch
        tasks = [process_single_user(user) for user in users]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that weren't caught in the task
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f'Unexpected error processing user {users[i].id}: {result}'
                )
                processed_results.append(
                    {
                        'user_id': users[i].id,
                        'result': {'status': 'error', 'message': str(result)},
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    async def clean_expired_recommendations(self) -> dict[str, Any]:
        """Remove expired cached recommendations"""

        session_ctx = SessionLocal()
        session = await session_ctx.__aenter__()

        try:
            # Delete expired recommendations
            result = await session.execute(
                delete(CachedRecommendation).where(
                    CachedRecommendation.expires_at <= datetime.now(UTC)
                )
            )

            deleted_count = result.rowcount
            await session.commit()

            logger.info(f'Cleaned up {deleted_count} expired cached recommendations')

            return {
                'status': 'success',
                'deleted_count': deleted_count,
                'cleaned_at': datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f'Error cleaning expired recommendations: {str(e)}')
            await session.rollback()
            return {
                'status': 'error',
                'message': f'Cleanup failed: {str(e)}',
            }
        finally:
            await session_ctx.__aexit__(None, None, None)

    def run_background_generation(self) -> None:
        """
        Run recommendation generation in background thread.
        This method can be called from FastAPI BackgroundTasks.
        """
        import threading

        def runner():
            try:
                result = asyncio.run(self.generate_recommendations_for_all_users())
                logger.info(f'Background recommendation generation completed: {result}')
            except Exception as e:
                logger.error(
                    f'Background recommendation generation failed: {e}', exc_info=True
                )

        threading.Thread(target=runner, daemon=True).start()

    def run_background_cleanup(self) -> None:
        """
        Run expired recommendations cleanup in background thread.
        This method can be called from FastAPI BackgroundTasks.
        """
        import threading

        def runner():
            try:
                result = asyncio.run(self.clean_expired_recommendations())
                logger.info(f'Background recommendation cleanup completed: {result}')
            except Exception as e:
                logger.error(
                    f'Background recommendation cleanup failed: {e}', exc_info=True
                )

        threading.Thread(target=runner, daemon=True).start()


# Global instance
background_recommendation_service = BackgroundRecommendationService()

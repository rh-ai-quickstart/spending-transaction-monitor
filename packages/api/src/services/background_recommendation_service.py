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

logger = logging.getLogger(__name__)


class BackgroundRecommendationService:
    """Service for generating and caching alert recommendations in the background"""

    def __init__(self):
        self.recommendation_service = AlertRecommendationService()
        # Cache recommendations for 24 hours
        self.cache_duration_hours = 24

    async def generate_recommendations_for_user(
        self, user_id: str, session: AsyncSession = None
    ) -> dict[str, Any]:
        """Generate and cache recommendations for a specific user"""

        owns_session = False
        if session is None:
            owns_session = True
            session_ctx = SessionLocal()
            session = await session_ctx.__aenter__()

        try:
            # Check if user exists
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                logger.error(f'User {user_id} not found')
                return {'status': 'error', 'message': 'User not found'}

            # Generate recommendations using existing service
            recommendations = await self.recommendation_service.get_recommendations(
                user_id, session
            )

            if 'error' in recommendations:
                logger.error(
                    f'Failed to generate recommendations for user {user_id}: {recommendations["error"]}'
                )
                return {'status': 'error', 'message': recommendations['error']}

            # Cache the recommendations
            await self._cache_recommendations(user_id, recommendations, session)

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
            return {
                'status': 'error',
                'message': f'Failed to generate recommendations: {str(e)}',
            }
        finally:
            if owns_session:
                await session_ctx.__aexit__(None, None, None)

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

    async def generate_recommendations_for_all_users(self) -> dict[str, Any]:
        """Generate recommendations for all active users"""

        session_ctx = SessionLocal()
        session = await session_ctx.__aenter__()

        try:
            # Get all active users
            result = await session.execute(select(User).where(User.is_active))
            users = result.scalars().all()

            total_users = len(users)
            success_count = 0
            error_count = 0
            results = []

            logger.info(
                f'Starting bulk recommendation generation for {total_users} users'
            )

            for user in users:
                try:
                    result = await self.generate_recommendations_for_user(
                        user.id, session
                    )
                    results.append({'user_id': user.id, 'result': result})

                    if result.get('status') == 'success':
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    logger.error(
                        f'Error generating recommendations for user {user.id}: {str(e)}'
                    )
                    error_count += 1
                    results.append(
                        {
                            'user_id': user.id,
                            'result': {'status': 'error', 'message': str(e)},
                        }
                    )

            return {
                'status': 'completed',
                'total_users': total_users,
                'success_count': success_count,
                'error_count': error_count,
                'results': results,
                'generated_at': datetime.now(UTC).isoformat(),
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
            await session_ctx.__aexit__(None, None, None)

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

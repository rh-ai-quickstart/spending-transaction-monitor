"""Recommendation Scheduler - Pre-generate recommendations for active users"""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal
from db.models import CachedRecommendation, User

from .background_recommendation_service import background_recommendation_service

logger = logging.getLogger(__name__)


class RecommendationScheduler:
    """Scheduler for pre-generating recommendations for active users"""

    def __init__(self):
        self.is_running = False
        self.task: asyncio.Task | None = None
        self.interval_hours = 6
        self.active_user_days = 7

    async def start(self):
        """Start the recommendation scheduler"""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._scheduler_loop())
            logger.info('Recommendation scheduler started')

    async def stop(self):
        """Stop the recommendation scheduler"""
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    logger.info('Recommendation scheduler cancelled')
            logger.info('Recommendation scheduler stopped')

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                await self._run_scheduled_generation()
                await asyncio.sleep(self.interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in recommendation scheduler: {e}', exc_info=True)
                await asyncio.sleep(3600)

    async def _run_scheduled_generation(self):
        """Run scheduled recommendation generation for active users (non-blocking)"""
        session_ctx = SessionLocal()
        session = await session_ctx.__aenter__()

        try:
            active_users = await self._get_users_needing_recommendations(session)
            if not active_users:
                logger.info('No users need recommendation updates')
                return

            logger.info(
                f'Starting scheduled recommendation generation for {len(active_users)} users'
            )

            success_count, error_count = 0, 0
            loop = asyncio.get_running_loop()

            for user in active_users:
                user_id = user.id
                try:
                    # Run sync recommendation generation in thread pool
                    result = await loop.run_in_executor(
                        None,  # use default ThreadPoolExecutor
                        background_recommendation_service.generate_recommendations_for_user_sync,
                        user_id,
                    )
                    if result.get('status') == 'success':
                        success_count += 1
                    else:
                        error_count += 1
                        logger.warning(
                            f'Failed to generate recommendations for user {user_id}: {result.get("message")}'
                        )
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f'Error generating recommendations for user {user_id}: {e}'
                    )

            logger.info(
                f'Scheduled recommendation generation completed: {success_count} success, {error_count} errors'
            )

        except Exception as e:
            logger.error(
                f'Error in scheduled recommendation generation: {e}', exc_info=True
            )
        finally:
            await session_ctx.__aexit__(None, None, None)

    async def _get_users_needing_recommendations(
        self, session: AsyncSession
    ) -> list[User]:
        """Get users who need fresh recommendations"""
        active_cutoff = datetime.now(UTC) - timedelta(days=self.active_user_days)
        stale_cutoff = datetime.now(UTC) - timedelta(hours=12)

        active_users_result = await session.execute(
            select(User).where(
                and_(
                    User.is_active,
                    User.updated_at > active_cutoff,
                )
            )
        )
        active_users = active_users_result.scalars().all()
        if not active_users:
            return []

        users_needing_recommendations = []
        for user in active_users:
            user_id = user.id
            cached_result = await session.execute(
                select(CachedRecommendation)
                .where(
                    and_(
                        CachedRecommendation.user_id == user_id,
                        CachedRecommendation.generated_at > stale_cutoff,
                    )
                )
                .order_by(CachedRecommendation.generated_at.desc())
                .limit(1)
            )
            cached = cached_result.scalar_one_or_none()
            if not cached:
                users_needing_recommendations.append(user)

        return users_needing_recommendations

    async def generate_for_user_now(self, user_id: str) -> dict[str, Any]:
        """Generate recommendations for a specific user immediately"""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                background_recommendation_service.generate_recommendations_for_user_sync,
                user_id,
            )
            return result
        except Exception as e:
            logger.error(f'Error generating recommendations for user {user_id}: {e}')
            return {'status': 'error', 'message': str(e)}

    async def get_scheduler_status(self) -> dict[str, Any]:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'interval_hours': self.interval_hours,
            'active_user_days': self.active_user_days,
            'next_run_in_hours': self.interval_hours if self.is_running else None,
        }


# Global scheduler instance
recommendation_scheduler = RecommendationScheduler()

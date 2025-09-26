"""Scheduler for periodic recommendation generation"""

import asyncio
from datetime import UTC, datetime, time
import logging

logger = logging.getLogger(__name__)


class RecommendationScheduler:
    """Schedules periodic recommendation generation and cleanup tasks"""

    def __init__(self):
        self._is_running = False
        self._scheduler_task: asyncio.Task | None = None

        # Schedule recommendations generation daily at 2 AM
        self.generation_time = time(2, 0)  # 2:00 AM

        # Schedule cleanup weekly on Sunday at 3 AM
        self.cleanup_time = time(3, 0)  # 3:00 AM
        self.cleanup_weekday = 6  # Sunday

    async def start(self):
        """Start the scheduler"""
        if not self._is_running:
            self._is_running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info('Recommendation scheduler started')

    async def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self._is_running = False
            if self._scheduler_task:
                self._scheduler_task.cancel()
                import contextlib

                with contextlib.suppress(asyncio.CancelledError):
                    await self._scheduler_task
            logger.info('Recommendation scheduler stopped')

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        from .recommendation_job_queue import recommendation_job_queue

        while self._is_running:
            try:
                now = datetime.now(UTC)

                # Check if it's time for daily recommendation generation
                if await self._should_run_generation(now):
                    logger.info('Scheduling daily recommendation generation')
                    try:
                        job_id = await recommendation_job_queue.enqueue_all_users_job()
                        logger.info(
                            f'Enqueued daily recommendation generation job: {job_id}'
                        )
                    except Exception as e:
                        logger.error(
                            f'Failed to enqueue daily recommendation generation: {e}'
                        )

                # Check if it's time for weekly cleanup
                if await self._should_run_cleanup(now):
                    logger.info('Scheduling weekly recommendation cleanup')
                    try:
                        job_id = await recommendation_job_queue.enqueue_cleanup_job()
                        logger.info(f'Enqueued weekly cleanup job: {job_id}')
                    except Exception as e:
                        logger.error(f'Failed to enqueue weekly cleanup: {e}')

                # Sleep for 1 hour before next check
                await asyncio.sleep(3600)  # 1 hour

            except Exception as e:
                logger.error(f'Error in recommendation scheduler: {e}')
                await asyncio.sleep(300)  # 5 minutes on error

    async def _should_run_generation(self, now: datetime) -> bool:
        """Check if it's time to run daily recommendation generation"""

        # Convert to local time for scheduling
        local_time = now.astimezone()

        # Check if current time is within 1 hour of scheduled generation time
        scheduled_today = local_time.replace(
            hour=self.generation_time.hour,
            minute=self.generation_time.minute,
            second=0,
            microsecond=0,
        )

        # Check if we're within the execution window (±30 minutes)
        time_diff = abs((local_time - scheduled_today).total_seconds())

        return time_diff <= 1800  # 30 minutes window

    async def _should_run_cleanup(self, now: datetime) -> bool:
        """Check if it's time to run weekly cleanup"""

        # Convert to local time for scheduling
        local_time = now.astimezone()

        # Check if today is the cleanup day (Sunday)
        if local_time.weekday() != self.cleanup_weekday:
            return False

        # Check if current time is within 1 hour of scheduled cleanup time
        scheduled_today = local_time.replace(
            hour=self.cleanup_time.hour,
            minute=self.cleanup_time.minute,
            second=0,
            microsecond=0,
        )

        # Check if we're within the execution window (±30 minutes)
        time_diff = abs((local_time - scheduled_today).total_seconds())

        return time_diff <= 1800  # 30 minutes window

    async def trigger_immediate_generation(self) -> str:
        """Trigger immediate recommendation generation for all users"""
        from .recommendation_job_queue import recommendation_job_queue

        logger.info('Triggering immediate recommendation generation')
        job_id = await recommendation_job_queue.enqueue_all_users_job()
        logger.info(f'Enqueued immediate recommendation generation job: {job_id}')
        return job_id

    async def trigger_immediate_cleanup(self) -> str:
        """Trigger immediate cleanup of expired recommendations"""
        from .recommendation_job_queue import recommendation_job_queue

        logger.info('Triggering immediate recommendation cleanup')
        job_id = await recommendation_job_queue.enqueue_cleanup_job()
        logger.info(f'Enqueued immediate cleanup job: {job_id}')
        return job_id


# Global scheduler instance
recommendation_scheduler = RecommendationScheduler()

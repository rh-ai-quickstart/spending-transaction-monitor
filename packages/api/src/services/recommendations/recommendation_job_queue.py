"""Recommendation Job Queue for Background Processing"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import logging
import threading
from typing import Any
import uuid

logger = logging.getLogger(__name__)


class RecommendationJobType(Enum):
    SINGLE_USER = 'single_user'
    ALL_USERS = 'all_users'
    CLEANUP_EXPIRED = 'cleanup_expired'


class JobStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class RecommendationJob:
    job_id: str
    job_type: RecommendationJobType
    user_id: str | None = None
    status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None


class RecommendationJobQueue:
    """Job queue for recommendation processing"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: dict[str, RecommendationJob] = {}
        self._is_running = False
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix='rec-worker'
        )
        self._worker_thread: threading.Thread | None = None

    async def start(self):
        if not self._is_running:
            self._is_running = True
            self._worker_thread = threading.Thread(
                target=self._run_worker_in_thread,
                name='recommendation-job-worker',
                daemon=True,
            )
            self._worker_thread.start()
            logger.info('Recommendation job queue worker started')

    async def stop(self):
        if self._is_running:
            self._is_running = False
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
            self._thread_pool.shutdown(wait=True)
            logger.info('Recommendation job queue worker stopped')

    async def enqueue_single_user_job(self, user_id: str) -> str:
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.SINGLE_USER,
            user_id=user_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._jobs[job_id] = job
        await self._queue.put(job)
        return job_id

    async def enqueue_all_users_job(self) -> str:
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.ALL_USERS,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._jobs[job_id] = job
        await self._queue.put(job)
        return job_id

    async def enqueue_cleanup_job(self) -> str:
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.CLEANUP_EXPIRED,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._jobs[job_id] = job
        await self._queue.put(job)
        return job_id

    def get_job_status(self, job_id: str) -> RecommendationJob | None:
        return self._jobs.get(job_id)

    def _run_worker_in_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._worker())
        finally:
            loop.close()

    async def _worker(self):
        from .background_recommendation_service import background_recommendation_service

        loop = asyncio.get_running_loop()

        while self._is_running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                job.status = JobStatus.PROCESSING
                self._jobs[job.job_id] = job

                try:
                    if job.job_type == RecommendationJobType.SINGLE_USER:
                        result = await loop.run_in_executor(
                            self._thread_pool,
                            background_recommendation_service.generate_recommendations_for_user_sync,
                            job.user_id,
                        )
                    elif job.job_type == RecommendationJobType.ALL_USERS:
                        result = await background_recommendation_service.generate_recommendations_for_all_users()
                    elif job.job_type == RecommendationJobType.CLEANUP_EXPIRED:
                        result = await background_recommendation_service.clean_expired_recommendations()
                    else:
                        raise ValueError(f'Unknown job type: {job.job_type}')

                    job.status = JobStatus.COMPLETED
                    job.result = result

                    # Send WebSocket notification for single user jobs
                    if (
                        job.job_type == RecommendationJobType.SINGLE_USER
                        and result.get('status') == 'success'
                        and job.user_id
                    ):
                        try:
                            from routes.websocket import (
                                notify_recommendations_ready,
                            )
                            from services.recommendations.background_recommendation_service import (
                                background_recommendation_service,
                            )

                            # Get cached recommendations synchronously
                            cached_recommendations = background_recommendation_service.get_cached_recommendations_sync(
                                job.user_id
                            )
                            if cached_recommendations:
                                # Schedule the notification in the main event loop
                                asyncio.run_coroutine_threadsafe(
                                    notify_recommendations_ready(
                                        job.user_id, cached_recommendations
                                    ),
                                    asyncio.get_event_loop(),
                                )
                                logger.info(
                                    f'Sent WebSocket notification for user {job.user_id}'
                                )
                        except Exception as e:
                            logger.warning(
                                f'Failed to send WebSocket notification for user {job.user_id}: {e}'
                            )

                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    logger.error(f'Job {job.job_id} failed: {e}')

                self._jobs[job.job_id] = job
                self._queue.task_done()

            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f'Error in recommendation job worker: {e}')
                await asyncio.sleep(1)


# Global instance
recommendation_job_queue = RecommendationJobQueue()

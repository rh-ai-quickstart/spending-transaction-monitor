"""Recommendation Job Queue for Background Processing"""

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import logging
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
    """Represents a background recommendation generation job"""

    job_id: str
    job_type: RecommendationJobType
    user_id: str | None = None  # For single user jobs
    status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None


class RecommendationJobQueue:
    """Job queue for recommendation processing"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: dict[str, RecommendationJob] = {}
        self._worker_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self):
        """Start the background worker"""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info('Recommendation job queue worker started')

    async def stop(self):
        """Stop the background worker"""
        if self._is_running:
            self._is_running = False
            if self._worker_task:
                self._worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._worker_task
            logger.info('Recommendation job queue worker stopped')

    async def enqueue_single_user_job(self, user_id: str) -> str:
        """Enqueue a job to generate recommendations for a single user"""
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.SINGLE_USER,
            user_id=user_id,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._jobs[job_id] = job
        await self._queue.put(job)

        logger.info(
            f'Enqueued single user recommendation job {job_id} for user {user_id}'
        )
        return job_id

    async def enqueue_all_users_job(self) -> str:
        """Enqueue a job to generate recommendations for all users"""
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.ALL_USERS,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._jobs[job_id] = job
        await self._queue.put(job)

        logger.info(f'Enqueued all users recommendation job {job_id}')
        return job_id

    async def enqueue_cleanup_job(self) -> str:
        """Enqueue a job to cleanup expired recommendations"""
        job_id = str(uuid.uuid4())
        job = RecommendationJob(
            job_id=job_id,
            job_type=RecommendationJobType.CLEANUP_EXPIRED,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._jobs[job_id] = job
        await self._queue.put(job)

        logger.info(f'Enqueued cleanup job {job_id}')
        return job_id

    def get_job_status(self, job_id: str) -> RecommendationJob | None:
        """Get the status of a job"""
        return self._jobs.get(job_id)

    async def _worker(self):
        """Background worker that processes recommendation jobs"""
        from .background_recommendation_service import background_recommendation_service

        while self._is_running:
            try:
                # Wait for a job with timeout
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Update job status
                job.status = JobStatus.PROCESSING
                self._jobs[job.job_id] = job

                logger.info(
                    f'Processing recommendation job {job.job_id} of type {job.job_type.value}'
                )

                try:
                    # Process the job based on type
                    if job.job_type == RecommendationJobType.SINGLE_USER:
                        result = await background_recommendation_service.generate_recommendations_for_user(
                            job.user_id
                        )
                    elif job.job_type == RecommendationJobType.ALL_USERS:
                        result = await background_recommendation_service.generate_recommendations_for_all_users()
                    elif job.job_type == RecommendationJobType.CLEANUP_EXPIRED:
                        result = await background_recommendation_service.clean_expired_recommendations()
                    else:
                        raise ValueError(f'Unknown job type: {job.job_type}')

                    # Update job with result
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    self._jobs[job.job_id] = job

                    logger.info(
                        f'Completed recommendation job {job.job_id}: {result.get("status")}'
                    )

                except Exception as e:
                    # Update job with error
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    self._jobs[job.job_id] = job

                    logger.error(f'Failed recommendation job {job.job_id}: {str(e)}')

                # Mark task as done
                self._queue.task_done()

            except TimeoutError:
                # No job available, continue
                continue
            except Exception as e:
                logger.error(f'Error in recommendation job worker: {str(e)}')
                await asyncio.sleep(1)  # Brief pause before retrying


# Global job queue instance
recommendation_job_queue = RecommendationJobQueue()

"""Alert Job Queue for Background Processing"""

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class AlertJob:
    """Represents a background alert processing job"""

    job_id: str
    user_id: str
    transaction_id: str
    alert_rule_ids: list[str] | None = None
    status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None


class AlertJobQueue:
    """Simple in-memory job queue for alert processing"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: dict[str, AlertJob] = {}
        self._worker_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self):
        """Start the background worker"""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info('Alert job queue worker started')

    async def stop(self):
        """Stop the background worker"""
        if self._is_running:
            self._is_running = False
            if self._worker_task:
                self._worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._worker_task
            logger.info('Alert job queue worker stopped')

    async def enqueue_job(
        self,
        user_id: str,
        transaction_id: str,
        alert_rule_ids: list[str] | None = None,
    ) -> str:
        """Enqueue a new alert processing job"""
        from datetime import datetime
        import uuid

        job_id = str(uuid.uuid4())
        job = AlertJob(
            job_id=job_id,
            user_id=user_id,
            transaction_id=transaction_id,
            alert_rule_ids=alert_rule_ids,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._jobs[job_id] = job
        await self._queue.put(job)

        logger.info(
            f'Enqueued alert job {job_id} for user {user_id}, transaction {transaction_id}'
        )
        return job_id

    def get_job_status(self, job_id: str) -> AlertJob | None:
        """Get the status of a job"""
        return self._jobs.get(job_id)

    async def _worker(self):
        """Background worker that processes jobs"""
        from .background_alert_service import background_alert_service

        while self._is_running:
            try:
                # Wait for a job with timeout
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Update job status
                job.status = JobStatus.PROCESSING
                self._jobs[job.job_id] = job

                logger.info(f'Processing alert job {job.job_id}')

                try:
                    # Process the job
                    result = await background_alert_service.process_alert_rules_async(
                        user_id=job.user_id,
                        transaction_id=job.transaction_id,
                        alert_rule_ids=job.alert_rule_ids,
                    )

                    # Update job with result
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    self._jobs[job.job_id] = job

                    logger.info(f'Completed alert job {job.job_id}: {result}')

                except Exception as e:
                    # Update job with error
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    self._jobs[job.job_id] = job

                    logger.error(f'Failed alert job {job.job_id}: {str(e)}')

                # Mark task as done
                self._queue.task_done()

            except TimeoutError:
                # No job available, continue
                continue
            except Exception as e:
                logger.error(f'Error in alert job worker: {str(e)}')
                await asyncio.sleep(1)  # Brief pause before retrying


# Global job queue instance
alert_job_queue = AlertJobQueue()

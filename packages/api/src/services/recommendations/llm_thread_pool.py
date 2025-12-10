"""Thread Pool for CPU-intensive LLM operations"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LLMThreadPool:
    """Thread pool for running CPU-intensive LLM operations in parallel"""

    def __init__(self, max_workers: int | None = None):
        from core.recommendation_config import recommendation_config

        self.max_workers = max_workers or recommendation_config.llm_thread_pool_workers
        self.executor: ThreadPoolExecutor | None = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the thread pool"""
        async with self._lock:
            if self.executor is None:
                self.executor = ThreadPoolExecutor(
                    max_workers=self.max_workers, thread_name_prefix='llm-worker'
                )
                logger.info(f'LLM thread pool started with {self.max_workers} workers')

    async def stop(self):
        """Stop the thread pool"""
        async with self._lock:
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
                logger.info('LLM thread pool stopped')

    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function in a thread pool"""
        if not self.executor:
            await self.start()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)

    async def run_multiple_in_threads(
        self, tasks: list[tuple[Callable, tuple, dict]]
    ) -> list[Any]:
        """Run multiple functions in parallel using the thread pool"""
        if not self.executor:
            await self.start()

        loop = asyncio.get_event_loop()

        # Create futures for all tasks
        futures = []
        for func, args, kwargs in tasks:
            future = loop.run_in_executor(self.executor, func, *args, **kwargs)
            futures.append(future)

        # Wait for all tasks to complete
        results = await asyncio.gather(*futures, return_exceptions=True)

        # Handle exceptions
        processed_results: list[dict[str, Any] | None] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f'Error in thread pool task {i}: {result}')
                processed_results.append(None)
            else:
                processed_results.append(result)  # type: ignore

        return processed_results


# Global thread pool instance
llm_thread_pool = LLMThreadPool()

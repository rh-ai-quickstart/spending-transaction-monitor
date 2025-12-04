"""Performance metrics for recommendation generation"""

from dataclasses import dataclass
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RecommendationMetrics:
    """Metrics for tracking recommendation generation performance"""

    user_id: str
    start_time: float
    end_time: float = 0
    duration_seconds: float = 0
    recommendation_type: str = 'unknown'
    recommendation_count: int = 0
    success: bool = False
    error_message: str = ''
    thread_pool_used: bool = False
    cache_hit: bool = False
    similar_users_count: int = 0
    transaction_count: int = 0

    def __post_init__(self):
        if self.end_time > 0:
            self.duration_seconds = self.end_time - self.start_time


class RecommendationMetricsCollector:
    """Collects and aggregates recommendation generation metrics"""

    def __init__(self):
        self.metrics: list[RecommendationMetrics] = []
        self._lock = None

    def start_tracking(self, user_id: str) -> RecommendationMetrics:
        """Start tracking metrics for a user"""
        return RecommendationMetrics(user_id=user_id, start_time=time.time())

    def finish_tracking(self, metrics: RecommendationMetrics, **kwargs):
        """Finish tracking and record metrics"""
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time

        # Update with any additional data
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        # Store the metrics
        if not self._lock:
            import asyncio

            self._lock = asyncio.Lock()

        # In a real implementation, you'd want to use proper locking
        self.metrics.append(metrics)

        # Log performance metrics
        logger.info(
            f'Recommendation generation for user {metrics.user_id}: '
            f'{metrics.duration_seconds:.2f}s, '
            f'type={metrics.recommendation_type}, '
            f'count={metrics.recommendation_count}, '
            f'success={metrics.success}, '
            f'thread_pool={metrics.thread_pool_used}, '
            f'cache_hit={metrics.cache_hit}'
        )

    def get_performance_summary(self, last_n_minutes: int = 60) -> dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = time.time() - (last_n_minutes * 60)

        recent_metrics = [m for m in self.metrics if m.start_time >= cutoff_time]

        if not recent_metrics:
            return {
                'total_requests': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'thread_pool_usage': 0,
                'cache_hit_rate': 0,
            }

        total_requests = len(recent_metrics)
        successful_requests = sum(1 for m in recent_metrics if m.success)
        avg_duration = sum(m.duration_seconds for m in recent_metrics) / total_requests
        thread_pool_usage = (
            sum(1 for m in recent_metrics if m.thread_pool_used) / total_requests
        )
        cache_hit_rate = sum(1 for m in recent_metrics if m.cache_hit) / total_requests

        return {
            'total_requests': total_requests,
            'success_rate': successful_requests / total_requests,
            'avg_duration': avg_duration,
            'thread_pool_usage': thread_pool_usage,
            'cache_hit_rate': cache_hit_rate,
            'recommendation_types': {
                m.recommendation_type: sum(
                    1
                    for x in recent_metrics
                    if x.recommendation_type == m.recommendation_type
                )
                for m in recent_metrics
            },
        }

    def get_user_metrics(self, user_id: str) -> list[RecommendationMetrics]:
        """Get metrics for a specific user"""
        return [m for m in self.metrics if m.user_id == user_id]

    def clear_old_metrics(self, hours: int = 24):
        """Clear metrics older than specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        self.metrics = [m for m in self.metrics if m.start_time >= cutoff_time]


# Global metrics collector
recommendation_metrics = RecommendationMetricsCollector()

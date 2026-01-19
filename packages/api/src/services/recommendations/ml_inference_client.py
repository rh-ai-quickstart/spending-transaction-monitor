"""
ML Inference Client for OpenShift AI

This client calls the deployed InferenceService on OpenShift AI
instead of loading the model locally in the API pod.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MLInferenceClient:
    """Client for calling ML inference service on OpenShift AI"""

    def __init__(
        self,
        endpoint_url: str | None = None,
        model_name: str = 'alert-recommender',
        timeout: int = 30,
    ):
        """
        Initialize the inference client.

        Args:
            endpoint_url: URL of the inference service (e.g., http://alert-recommender.spending-monitor.svc.cluster.local)
            model_name: Name of the model
            timeout: Request timeout in seconds
        """
        self.endpoint_url = endpoint_url or os.getenv(
            'ML_INFERENCE_ENDPOINT',
            'http://alert-recommender-predictor.spending-monitor.svc.cluster.local',
        )
        self.model_name = model_name
        self.timeout = timeout

        logger.info(f'ML Inference Client initialized: {self.endpoint_url}')

    async def get_recommendations(
        self,
        user_features: dict[str, float],
        user_id: str | None = None,
        k_neighbors: int = 5,
        threshold: float = 0.4,
    ) -> dict[str, Any]:
        """
        Get alert recommendations for a user.

        Args:
            user_features: Dictionary of user behavioral features
            user_id: User ID (optional, for logging)
            k_neighbors: Number of similar users to consider
            threshold: Minimum probability threshold for recommendations

        Returns:
            Dictionary with recommendations and metadata
        """
        try:
            # Prepare request in MLServer V2 format
            # Convert user_features dict to list of values in expected order
            feature_values = (
                list(user_features.values())
                if isinstance(user_features, dict)
                else user_features
            )

            request_data = {
                'inputs': [
                    {
                        'name': 'input-0',
                        'shape': [1, len(feature_values)],
                        'datatype': 'FP64',
                        'data': [feature_values],
                    }
                ],
                'parameters': {
                    'user_id': user_id,
                    'k_neighbors': k_neighbors,
                    'threshold': threshold,
                },
            }

            # Call MLServer V2 inference endpoint
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f'{self.endpoint_url}/v2/models/alert-recommender/infer'
                logger.debug(f'Calling MLServer V2 inference endpoint: {url}')

                response = await client.post(
                    url, json=request_data, headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()

            # Parse MLServer V2 response format
            result = response.json()

            # Extract recommendations from MLServer response
            # MLServer returns: {"outputs": [{"name": "output-0", "data": [...]}]}
            outputs = result.get('outputs', [])
            data = outputs[0].get('data', []) if outputs else []

            # The KNNRecommender.predict() returns a list per input
            # Since we send one input, extract the first (and only) element
            recommendations = (
                data[0] if data and isinstance(data, list) and len(data) > 0 else []
            )

            formatted_result = {
                'recommendations': recommendations,
                'user_id': user_id,
                'metadata': result.get('parameters', {}),
            }

            logger.info(
                f'Got {len(recommendations)} recommendations from MLServer '
                f'for user {user_id}'
            )

            return formatted_result

        except httpx.TimeoutException:
            logger.error(f'Timeout calling inference service: {self.endpoint_url}')
            raise RuntimeError('ML inference service timeout') from None
        except httpx.HTTPError as e:
            logger.error(f'HTTP error calling inference service: {e}')
            raise RuntimeError(f'ML inference service error: {e}') from e
        except Exception as e:
            logger.error(f'Error calling inference service: {e}', exc_info=True)
            raise

    async def health_check(self) -> bool:
        """
        Check if the inference service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # MLServer V2 API uses /v2/health/ready
                url = f'{self.endpoint_url}/v2/health/ready'
                response = await client.get(url)
                response.raise_for_status()

                # MLServer returns empty body for successful ready check (200 OK means healthy)
                is_healthy = response.status_code == 200

                if is_healthy:
                    logger.debug('Inference service is healthy')
                else:
                    logger.warning(
                        f'Inference service unhealthy: status={response.status_code}'
                    )

                return is_healthy

        except Exception as e:
            logger.error(f'Health check failed: {e}')
            return False

    async def get_model_metadata(self) -> dict[str, Any]:
        """
        Get model metadata from the inference service.

        Returns:
            Dictionary with model metadata
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f'{self.endpoint_url}/v1/models/{self.model_name}'
                response = await client.get(url)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f'Error getting model metadata: {e}')
            raise


# Singleton instance
_client: MLInferenceClient | None = None


def get_inference_client() -> MLInferenceClient:
    """
    Get or create the inference client singleton.

    Returns:
        MLInferenceClient instance
    """
    global _client

    if _client is None:
        _client = MLInferenceClient()

    return _client

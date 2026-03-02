"""Tests for ML Inference Client"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.recommendations.ml_inference_client import MLInferenceClient


class TestMLInferenceClient:
    """Test suite for ML Inference Client"""

    @pytest.fixture
    def client(self):
        """Create an MLInferenceClient instance for testing"""
        return MLInferenceClient(
            endpoint_url='http://test-inference-service',
            model_name='test-model',
            timeout=10,
        )

    @pytest.fixture
    def sample_user_features(self):
        """Sample user features for testing"""
        return {
            'avg_transaction_amount': 150.0,
            'transaction_count': 25,
            'unique_merchants': 12,
            'avg_daily_spending': 50.0,
            'max_transaction_amount': 500.0,
        }

    def test_client_initialization_default(self):
        """Test client initialization with default values"""
        with patch.dict('os.environ', {}, clear=True):
            client = MLInferenceClient()
            assert (
                client.endpoint_url
                == 'http://alert-recommender-predictor.spending-monitor.svc.cluster.local'
            )
            assert client.model_name == 'alert-recommender'
            assert client.timeout == 30

    def test_client_initialization_custom(self):
        """Test client initialization with custom values"""
        client = MLInferenceClient(
            endpoint_url='http://custom-endpoint',
            model_name='custom-model',
            timeout=60,
        )
        assert client.endpoint_url == 'http://custom-endpoint'
        assert client.model_name == 'custom-model'
        assert client.timeout == 60

    def test_client_initialization_from_env(self):
        """Test client initialization from environment variable"""
        with patch.dict('os.environ', {'ML_INFERENCE_ENDPOINT': 'http://env-endpoint'}):
            client = MLInferenceClient()
            assert client.endpoint_url == 'http://env-endpoint'

    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, client, sample_user_features):
        """Test successful recommendation retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'outputs': [
                {
                    'name': 'output-0',
                    'datatype': 'FP64',
                    'data': [[0.8, 0.6, 0.3]],
                }
            ],
            'parameters': {'some': 'metadata'},
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.get_recommendations(
                user_features=sample_user_features, user_id='test-user', k_neighbors=5
            )

            assert 'recommendations' in result
            assert result['user_id'] == 'test-user'
            assert 'metadata' in result
            assert result['recommendations'] == [0.8, 0.6, 0.3]
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendations_with_list_features(self, client):
        """Test recommendations with list-based features"""
        feature_list = [150.0, 25.0, 12.0, 50.0, 500.0]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'outputs': [{'name': 'predictions', 'data': [[0.7, 0.5]]}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.get_recommendations(user_features=feature_list)

            assert 'recommendations' in result
            # Verify the request data structure
            call_args = mock_client.post.call_args
            request_data = call_args.kwargs['json']
            assert request_data['inputs'][0]['data'] == [feature_list]

    @pytest.mark.asyncio
    async def test_get_recommendations_http_error(self, client, sample_user_features):
        """Test handling of HTTP errors"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.HTTPError('Connection failed')
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match='ML inference service error'):
                await client.get_recommendations(user_features=sample_user_features)

    @pytest.mark.asyncio
    async def test_get_recommendations_timeout(self, client, sample_user_features):
        """Test handling of timeout errors"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException('Request timeout')
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match='ML inference service timeout'):
                await client.get_recommendations(user_features=sample_user_features)

    @pytest.mark.asyncio
    async def test_get_recommendations_invalid_response(
        self, client, sample_user_features
    ):
        """Test handling of invalid response format"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'invalid': 'format'}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.get_recommendations(
                user_features=sample_user_features
            )

            # Should handle gracefully and return some result
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_recommendations_empty_features(self, client):
        """Test recommendations with empty features"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'outputs': [{'data': [[]]}]}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Empty dict or list should be handled
            result = await client.get_recommendations(user_features={})

            # Client should make the request even with empty features
            assert mock_client.post.called
            assert 'recommendations' in result

    @pytest.mark.asyncio
    async def test_get_recommendations_with_threshold(
        self, client, sample_user_features
    ):
        """Test recommendation filtering by threshold"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'outputs': [{'name': 'predictions', 'data': [[0.8, 0.6, 0.3, 0.2, 0.1]]}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            _result = await client.get_recommendations(
                user_features=sample_user_features, threshold=0.5
            )

            # Verify threshold was passed in request
            call_args = mock_client.post.call_args
            request_data = call_args.kwargs['json']
            assert request_data['parameters']['threshold'] == 0.5

    @pytest.mark.asyncio
    async def test_get_recommendations_request_structure(
        self, client, sample_user_features
    ):
        """Test that request follows MLServer V2 format"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'outputs': [{'data': [[0.5]]}]}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            await client.get_recommendations(
                user_features=sample_user_features, k_neighbors=3, threshold=0.4
            )

            # Verify request structure
            call_args = mock_client.post.call_args
            assert call_args is not None

            # Check URL
            url = call_args.args[0] if call_args.args else call_args.kwargs.get('url')
            assert 'test-inference-service' in url

            # Check request data format (MLServer V2)
            request_data = call_args.kwargs['json']
            assert 'inputs' in request_data
            assert len(request_data['inputs']) == 1
            assert request_data['inputs'][0]['name'] == 'input-0'
            assert request_data['inputs'][0]['datatype'] == 'FP64'
            assert 'shape' in request_data['inputs'][0]
            assert 'data' in request_data['inputs'][0]

            # Check parameters
            assert 'parameters' in request_data
            assert request_data['parameters']['k_neighbors'] == 3
            assert request_data['parameters']['threshold'] == 0.4

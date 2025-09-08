"""
Integration Tests for Ingestion Service
Tests the full FastAPI application with TestClient
"""

import os

# Import from parent directory
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from main import app


class TestIngestionServiceIntegration:
    """Integration tests using FastAPI TestClient"""

    @patch('main.kafka_manager.get_producer')
    def test_create_transaction_success(self, mock_get_producer):
        """Test successful transaction creation through API"""
        mock_producer = mock_get_producer.return_value
        mock_producer.send.return_value.get.return_value = None

        with TestClient(app) as client:
            incoming_transaction = {
                'User': 1,
                'Card': 1,
                'Year': 2023,
                'Month': 1,
                'Day': 1,
                'Time': '12:00',
                'Amount': '$10.00',
                'Use Chip': 'Swipe Transaction',
                'Merchant Name': 123456789,
                'Merchant City': 'New York',
                'Merchant State': 'NY',
                'Zip': '10001',
                'MCC': 5411,
                'Errors?': '',
                'Is Fraud?': 'No',
            }
            response = client.post('/transactions/', json=incoming_transaction)

            assert response.status_code == 200

            expected_response = {
                'user': 1,
                'card': 1,
                'year': 2023,
                'month': 1,
                'day': 1,
                'time': '12:00:00',
                'amount': 10.0,
                'use_chip': 'Swipe Transaction',
                'merchant_id': 123456789,
                'merchant_city': 'New York',
                'merchant_state': 'NY',
                'zip': '10001',
                'mcc': 5411,
                'errors': '',
                'is_fraud': False,
            }
            assert response.json() == expected_response

            # Verify Kafka producer was called
            mock_producer.send.assert_called_once()
            call_args = mock_producer.send.call_args
            assert call_args[0][0] == 'transactions'  # topic
            payload = call_args[0][1]
            assert payload['user'] == 1
            assert payload['amount'] == 10.0

    @patch('main.kafka_manager.get_producer')
    def test_create_transaction_kafka_unavailable(self, mock_get_producer):
        """Test transaction creation when Kafka is unavailable"""
        mock_get_producer.return_value = None

        with TestClient(app) as client:
            incoming_transaction = {
                'User': 1,
                'Card': 1,
                'Year': 2023,
                'Month': 1,
                'Day': 1,
                'Time': '12:00',
                'Amount': '$10.00',
                'Use Chip': 'Swipe Transaction',
                'Merchant Name': 123456789,
                'Merchant City': 'New York',
                'Merchant State': 'NY',
                'Zip': '10001',
                'MCC': 5411,
                'Errors?': '',
                'Is Fraud?': 'No',
            }
            response = client.post('/transactions/', json=incoming_transaction)

            # Should still return 200 with graceful degradation
            assert response.status_code == 200
            response_data = response.json()
            assert 'user' in response_data
            assert response_data['user'] == 1

    def test_healthz(self):
        """Test the simple health check endpoint"""
        with TestClient(app) as client:
            response = client.get('/healthz')
            assert response.status_code == 200
            assert response.json() == {'status': 'ok'}

    @patch('main.kafka_manager.health_check')
    def test_health_kafka_healthy(self, mock_health_check):
        """Test comprehensive health check when Kafka is healthy"""
        mock_health_check.return_value = {
            'kafka_status': 'healthy',
            'last_connection_attempt': '2023-01-01T12:00:00Z',
            'connection_pool_active': True,
        }

        with TestClient(app) as client:
            response = client.get('/health')
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'ingestion-service'
            assert 'kafka' in data
            assert data['kafka']['kafka_status'] == 'healthy'
            assert 'environment' in data

    @patch('main.kafka_manager.health_check')
    def test_health_kafka_unhealthy(self, mock_health_check):
        """Test comprehensive health check when Kafka is unhealthy"""
        mock_health_check.return_value = {
            'kafka_status': 'unhealthy',
            'last_connection_attempt': '2023-01-01T12:00:00Z',
            'connection_pool_active': False,
            'error': 'Connection timeout',
        }

        with TestClient(app) as client:
            response = client.get('/health')
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'degraded'
            assert data['service'] == 'ingestion-service'
            assert data['kafka']['kafka_status'] == 'unhealthy'

    def test_invalid_transaction_data(self):
        """Test API with invalid transaction data"""
        with TestClient(app) as client:
            invalid_transaction = {
                'User': 'not-a-number',  # Invalid type
                'Card': 1,
                # Missing required fields
            }
            response = client.post('/transactions/', json=invalid_transaction)

            # Should return validation error
            assert response.status_code == 422

    def test_missing_endpoint(self):
        """Test accessing non-existent endpoint"""
        with TestClient(app) as client:
            response = client.get('/non-existent')
            assert response.status_code == 404

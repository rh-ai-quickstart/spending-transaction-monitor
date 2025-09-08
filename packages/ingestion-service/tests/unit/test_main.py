"""
Unit Tests for Ingestion Service
Tests individual components in isolation with mocking
"""

import datetime
import os

# Import from parent directory
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.main import kafka_manager


class TestKafkaConnectionManager:
    """Test the Kafka connection manager in isolation"""

    def setup_method(self):
        """Reset the kafka manager for each test"""
        kafka_manager.producer = None
        kafka_manager.last_connection_attempt = 0

    @patch('src.main.KafkaProducer')
    def test_get_producer_success(self, mock_kafka_producer):
        """Test successful producer creation"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer.return_value = mock_producer_instance

        producer = kafka_manager.get_producer()

        assert producer is mock_producer_instance
        assert kafka_manager.producer is mock_producer_instance
        mock_kafka_producer.assert_called_once()

    @patch('src.main.KafkaProducer')
    def test_get_producer_failure(self, mock_kafka_producer):
        """Test producer creation failure"""
        mock_kafka_producer.side_effect = Exception('Connection failed')

        producer = kafka_manager.get_producer()

        assert producer is None
        assert kafka_manager.producer is None

    @patch('src.main.KafkaProducer')
    def test_health_check_healthy(self, mock_kafka_producer):
        """Test health check when Kafka is healthy"""
        mock_producer_instance = MagicMock()
        mock_kafka_producer.return_value = mock_producer_instance

        # First get a producer
        kafka_manager.get_producer()

        health = kafka_manager.health_check()

        assert health['kafka_status'] == 'healthy'
        assert health['connection_pool_active'] is True

    @patch('src.main.KafkaProducer')
    def test_health_check_unhealthy(self, mock_kafka_producer):
        """Test health check when Kafka is unhealthy"""
        mock_kafka_producer.side_effect = Exception('Connection failed')

        # Try to get a producer (will fail)
        kafka_manager.get_producer()

        health = kafka_manager.health_check()

        assert health['kafka_status'] == 'unhealthy'
        assert health['connection_pool_active'] is False

    @patch('src.main.KafkaProducer')
    def test_send_message_no_producer(self, mock_kafka_producer):
        """Test sending message when no producer is available"""
        # Mock KafkaProducer to raise exception to simulate connection failure
        mock_kafka_producer.side_effect = Exception('Connection failed')
        kafka_manager.producer = None

        result = kafka_manager.send_message('test-topic', {'test': 'data'})

        assert result is False

    @patch('src.main.KafkaProducer')
    def test_send_message_success(self, mock_kafka_producer):
        """Test successful message sending"""
        mock_producer_instance = MagicMock()
        mock_future = MagicMock()
        mock_record_metadata = MagicMock()
        mock_record_metadata.topic = 'test-topic'
        mock_record_metadata.partition = 0
        mock_record_metadata.offset = 123
        mock_future.get.return_value = mock_record_metadata
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance

        # Get producer first
        kafka_manager.get_producer()

        result = kafka_manager.send_message('test-topic', {'test': 'data'})

        assert result is True
        mock_producer_instance.send.assert_called_once_with(
            'test-topic', {'test': 'data'}
        )

    @patch('src.main.KafkaProducer')
    def test_send_message_failure(self, mock_kafka_producer):
        """Test message sending failure"""
        mock_producer_instance = MagicMock()
        mock_producer_instance.send.side_effect = Exception('Send failed')
        mock_kafka_producer.return_value = mock_producer_instance

        # Get producer first
        kafka_manager.get_producer()

        result = kafka_manager.send_message('test-topic', {'test': 'data'})

        assert result is False
        # Producer should be reset after failure
        assert kafka_manager.producer is None


class TestTransactionTransformation:
    """Test transaction transformation logic"""

    def test_transform_transaction_success(self):
        """Test successful transaction transformation"""
        from src.common.models import IncomingTransaction
        from src.main import transform_transaction

        test_data = {
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

        incoming = IncomingTransaction(**test_data)
        result = transform_transaction(incoming)

        assert result.user == 1
        assert result.amount == 10.0
        assert result.is_fraud is False
        assert result.time == datetime.time(12, 0)

    def test_transform_transaction_fraud_yes(self):
        """Test transaction transformation with fraud=Yes"""
        from src.common.models import IncomingTransaction
        from src.main import transform_transaction

        test_data = {
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
            'Is Fraud?': 'Yes',
        }

        incoming = IncomingTransaction(**test_data)
        result = transform_transaction(incoming)

        assert result.is_fraud is True

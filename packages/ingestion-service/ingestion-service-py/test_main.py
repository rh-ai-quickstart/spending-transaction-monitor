from fastapi.testclient import TestClient
from main import app, kafka_manager
from unittest.mock import patch, MagicMock
import pytest
import datetime

class TestIngestionService:
    
    @patch('main.kafka_manager.get_producer')
    def test_create_transaction_success(self, mock_get_producer):
        # Mock the producer and its methods
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.topic = 'transactions'
        mock_metadata.partition = 0
        mock_metadata.offset = 123
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future
        mock_get_producer.return_value = mock_producer
        
        with TestClient(app) as client:
            incoming_transaction = {
                "User": 1,
                "Card": 1,
                "Year": 2023,
                "Month": 1,
                "Day": 1,
                "Time": "12:00",
                "Amount": "$10.00",
                "Use Chip": "Swipe Transaction",
                "Merchant Name": 123456789,
                "Merchant City": "New York",
                "Merchant State": "NY",
                "Zip": "10001",
                "MCC": 5411,
                "Errors?": "",
                "Is Fraud?": "No"
            }
            response = client.post(
                "/transactions/",
                json=incoming_transaction,
            )
            assert response.status_code == 200

            expected_response = {
                "user": 1,
                "card": 1,
                "year": 2023,
                "month": 1,
                "day": 1,
                "time": "12:00:00",
                "amount": 10.0,
                "use_chip": "Swipe Transaction",
                "merchant_id": 123456789,
                "merchant_city": "New York",
                "merchant_state": "NY",
                "zip": "10001",
                "mcc": 5411,
                "errors": "",
                "is_fraud": False
            }
            assert response.json() == expected_response
            
            # Verify Kafka message was sent
            mock_producer.send.assert_called_once()
            call_args = mock_producer.send.call_args
            assert call_args[0][0] == 'transactions'  # topic
            assert call_args[0][1]['user'] == 1  # message content
    
    @patch('main.kafka_manager.get_producer')
    def test_create_transaction_kafka_unavailable(self, mock_get_producer):
        # Mock Kafka connection failure
        from fastapi import HTTPException
        mock_get_producer.side_effect = HTTPException(status_code=503, detail="Unable to connect to Kafka")
        
        with TestClient(app) as client:
            incoming_transaction = {
                "User": 1,
                "Card": 1,
                "Year": 2023,
                "Month": 1,
                "Day": 1,
                "Time": "12:00",
                "Amount": "$10.00",
                "Use Chip": "Swipe Transaction",
                "Merchant Name": 123456789,
                "Merchant City": "New York",
                "Merchant State": "NY",
                "Zip": "10001",
                "MCC": 5411,
                "Errors?": "",
                "Is Fraud?": "No"
            }
            response = client.post(
                "/transactions/",
                json=incoming_transaction,
            )
            assert response.status_code == 503
            assert "Unable to connect to Kafka" in response.json()["detail"]
    
    def test_healthz(self):
        with TestClient(app) as client:
            response = client.get("/healthz")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    
    @patch('main.kafka_manager.health_check')
    def test_health_kafka_healthy(self, mock_health_check):
        mock_health_check.return_value = {
            "kafka_status": "healthy",
            "kafka_host": "localhost:9092",
            "connection_state": "connected"
        }
        
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ingestion-service"
            assert data["kafka"]["kafka_status"] == "healthy"
            assert "timestamp" in data
            assert "environment" in data
    
    @patch('main.kafka_manager.health_check')
    def test_health_kafka_unhealthy(self, mock_health_check):
        mock_health_check.return_value = {
            "kafka_status": "unhealthy",
            "kafka_host": "localhost:9092",
            "connection_state": "failed",
            "error": "Connection refused"
        }
        
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["kafka"]["kafka_status"] == "unhealthy"
            assert data["kafka"]["error"] == "Connection refused"

class TestKafkaConnectionManager:
    
    def setup_method(self):
        # Reset the kafka manager for each test
        kafka_manager.producer = None
        kafka_manager.last_connection_attempt = 0
    
    @patch('main.KafkaProducer')
    def test_get_producer_success(self, mock_kafka_producer):
        mock_producer = MagicMock()
        mock_producer.bootstrap_connected.return_value = True
        mock_kafka_producer.return_value = mock_producer
        
        producer = kafka_manager.get_producer()
        assert producer == mock_producer
        mock_kafka_producer.assert_called_once()
    
    @patch('main.KafkaProducer')
    def test_get_producer_failure(self, mock_kafka_producer):
        from kafka.errors import NoBrokersAvailable
        mock_kafka_producer.side_effect = NoBrokersAvailable()
        
        with pytest.raises(Exception):
            kafka_manager.get_producer()
    
    @patch('main.KafkaProducer')
    def test_health_check_healthy(self, mock_kafka_producer):
        mock_producer = MagicMock()
        mock_producer.bootstrap_connected.return_value = True
        mock_kafka_producer.return_value = mock_producer
        
        health = kafka_manager.health_check()
        assert health["kafka_status"] == "healthy"
    
    @patch('main.KafkaProducer')
    def test_health_check_unhealthy(self, mock_kafka_producer):
        from kafka.errors import NoBrokersAvailable
        mock_kafka_producer.side_effect = NoBrokersAvailable("No brokers available")
        
        health = kafka_manager.health_check()
        assert health["kafka_status"] == "unhealthy"
        assert "No brokers available" in health["error"]

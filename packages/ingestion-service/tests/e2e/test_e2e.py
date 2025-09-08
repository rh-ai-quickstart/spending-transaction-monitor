#!/usr/bin/env python3
"""
End-to-End Tests for Ingestion Service
Tests the complete flow from API request through Kafka to message consumption

This script can be run both:
1. With pytest: `python -m pytest tests/e2e/test_e2e.py -v`
2. Standalone: `python tests/e2e/test_e2e.py`
"""

import json
import os
import sys
import time

import requests
from kafka import KafkaConsumer

# Try to import pytest, but don't fail if it's not available
try:
    import pytest

    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


def test_full_ingestion_flow():
    """Test the complete ingestion flow: API -> Kafka -> Consumer"""
    # Send a request to the ingestion service
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

    ingestion_service_host = os.environ.get('INGESTION_SERVICE_HOST', 'localhost')
    ingestion_service_port = os.environ.get('INGESTION_SERVICE_PORT', '8000')

    print(f'Sending transaction to {ingestion_service_host}:{ingestion_service_port}')
    print(f'Transaction: {incoming_transaction}')

    # Give services time to be ready
    time.sleep(5)

    # Send transaction to ingestion service
    response = requests.post(
        f'http://{ingestion_service_host}:{ingestion_service_port}/transactions/',
        json=incoming_transaction,
        timeout=30,
    )
    response.raise_for_status()

    print(f'API Response: {response.json()}')

    # Wait for message to be processed by Kafka
    print('Waiting for message to be processed by Kafka...')
    time.sleep(5)

    # Check if the message is in Kafka
    kafka_host = os.environ.get('KAFKA_HOST', 'localhost')
    kafka_port = os.environ.get('KAFKA_PORT', '9092')

    print(f'Connecting to Kafka at {kafka_host}:{kafka_port}')

    consumer = KafkaConsumer(
        'transactions',
        bootstrap_servers=f'{kafka_host}:{kafka_port}',
        auto_offset_reset='earliest',
        consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    )

    expected_transaction = {
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

    print('Checking for messages in Kafka...')

    for message in consumer:
        print(f'Received message: {message.value}')
        if message.value == expected_transaction:
            print('✅ Successfully received expected message from Kafka')
            return

    raise Exception('❌ Failed to receive expected message from Kafka')


def test_service_health_endpoints():
    """Test that all health endpoints are working"""
    ingestion_service_host = os.environ.get('INGESTION_SERVICE_HOST', 'localhost')
    ingestion_service_port = os.environ.get('INGESTION_SERVICE_PORT', '8000')
    base_url = f'http://{ingestion_service_host}:{ingestion_service_port}'

    # Test basic health endpoint
    response = requests.get(f'{base_url}/healthz', timeout=10)
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    print('✅ Basic health endpoint working')

    # Test comprehensive health endpoint
    response = requests.get(f'{base_url}/health', timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert 'service' in data
    assert 'kafka' in data
    assert data['service'] == 'ingestion-service'
    print(f'✅ Comprehensive health endpoint working - Status: {data["status"]}')


def main():
    """Main function for standalone execution"""
    service_host = os.environ.get('INGESTION_SERVICE_HOST', 'localhost')
    service_port = os.environ.get('INGESTION_SERVICE_PORT', '8000')
    base_url = f'http://{service_host}:{service_port}'

    kafka_host = os.environ.get('KAFKA_HOST', 'localhost')
    kafka_port = os.environ.get('KAFKA_PORT', '9092')
    kafka_bootstrap_servers = f'{kafka_host}:{kafka_port}'

    print('🚀 Starting E2E Test')
    print(f'Service URL: {base_url}')
    print(f'Kafka: {kafka_bootstrap_servers}')

    try:
        test_service_health_endpoints()
        test_full_ingestion_flow()
        print('🎉 All E2E tests passed!')
    except Exception as e:
        print(f'❌ E2E tests failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

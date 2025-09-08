#!/usr/bin/env python3
"""
Simple test runner for the ingestion service
This script handles all the complexity of running tests reliably
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def run_unit_tests():
    """Run unit tests using pytest"""
    print('=' * 50)
    print('RUNNING UNIT TESTS')
    print('=' * 50)

    try:
        # Import and run tests directly
        import pytest

        exit_code = pytest.main(['-v', 'tests/unit/'])
        if exit_code == 0:
            print('✅ Unit tests PASSED')
            return True
        else:
            print('❌ Unit tests FAILED')
            return False
    except Exception as e:
        print(f'❌ Unit tests failed with error: {e}')
        return False


def run_integration_tests():
    """Run integration tests using FastAPI TestClient"""
    print('=' * 50)
    print('RUNNING INTEGRATION TESTS')
    print('=' * 50)

    try:
        from fastapi.testclient import TestClient

        from src.common.models import IncomingTransaction
        from src.main import app, kafka_manager, transform_transaction

        print('✅ Service modules imported successfully')

        # Test Kafka manager
        print(
            f'✅ Kafka manager initialized - Host: {kafka_manager.kafka_host}:{kafka_manager.kafka_port}'
        )

        # Test transaction transformation - use the correct field names/aliases
        test_incoming_data = {
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
        test_incoming = IncomingTransaction(**test_incoming_data)

        transformed = transform_transaction(test_incoming)
        print(f'✅ Transaction transformation works - Amount: {transformed.amount}')

        # Test FastAPI endpoints
        with TestClient(app) as client:
            # Test healthz endpoint
            response = client.get('/healthz')
            assert response.status_code == 200
            assert response.json() == {'status': 'ok'}
            print(
                f'✅ Basic health endpoint: {response.status_code} - {response.json()}'
            )

            # Test health endpoint
            response = client.get('/health')
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert 'service' in data
            assert data['service'] == 'ingestion-service'
            print(f'✅ Comprehensive health endpoint: {response.status_code}')
            print(f'   Service status: {data.get("status")}')
            print(f'   Kafka status: {data.get("kafka", {}).get("kafka_status")}')

            # Test transaction endpoint
            transaction_data = {
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
            response = client.post('/transactions/', json=transaction_data)
            assert response.status_code == 200
            result = response.json()
            assert result['user'] == 1
            assert result['amount'] == 10.0
            print(f'✅ Transaction endpoint: {response.status_code}')
            print(
                f'   Processed user: {result.get("user")}, amount: ${result.get("amount")}'
            )

        print('✅ Integration tests PASSED')
        return True

    except Exception as e:
        print(f'❌ Integration tests failed with error: {e}')
        import traceback

        traceback.print_exc()
        return False


def run_service_validation():
    """Validate that the service can start and respond"""
    print('=' * 50)
    print('RUNNING SERVICE VALIDATION')
    print('=' * 50)

    try:
        # Test that we can import everything without errors
        from src.main import KafkaConnectionManager, app

        print('✅ All imports successful')

        # Test that we can create the app
        assert app is not None
        print('✅ FastAPI app created successfully')

        # Test Kafka manager creation
        test_manager = KafkaConnectionManager()
        assert test_manager.kafka_host is not None
        assert test_manager.kafka_port is not None
        print('✅ KafkaConnectionManager created successfully')

        # Test health check method
        health = test_manager.health_check()
        assert 'kafka_status' in health
        print(f'✅ Kafka health check method works - Status: {health["kafka_status"]}')

        print('✅ Service validation PASSED')
        return True

    except Exception as e:
        print(f'❌ Service validation failed with error: {e}')
        import traceback

        traceback.print_exc()
        return False


def run_e2e_tests():
    """Run E2E tests using pytest"""
    print('=' * 50)
    print('RUNNING E2E TESTS')
    print('=' * 50)

    try:
        # Import and run E2E tests
        import pytest

        exit_code = pytest.main(['-v', 'tests/e2e/', '-s'])  # -s to show print output
        if exit_code == 0:
            print('✅ E2E tests PASSED')
            return True
        else:
            print('❌ E2E tests FAILED')
            return False
    except Exception as e:
        print(f'❌ E2E tests failed with error: {e}')
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print('🚀 INGESTION SERVICE TEST RUNNER')
    print('=' * 50)

    # Change to the correct directory
    os.chdir(current_dir)
    print(f'Working directory: {os.getcwd()}')

    results = []

    # Run service validation first
    results.append(('Service Validation', run_service_validation()))

    # Run unit tests
    results.append(('Unit Tests', run_unit_tests()))

    # Run integration tests
    results.append(('Integration Tests', run_integration_tests()))

    # Print summary
    print('\n' + '=' * 50)
    print('TEST SUMMARY')
    print('=' * 50)

    all_passed = True
    for test_name, passed in results:
        status = '✅ PASSED' if passed else '❌ FAILED'
        print(f'{test_name}: {status}')
        if not passed:
            all_passed = False

    print('=' * 50)
    if all_passed:
        print('🎉 ALL TESTS PASSED! Service is ready for CI.')
        sys.exit(0)
    else:
        print('💥 SOME TESTS FAILED! Please fix issues before proceeding.')
        sys.exit(1)


if __name__ == '__main__':
    main()

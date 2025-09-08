import json
import os
import time

import requests
from kafka import KafkaConsumer


def main():
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
    print(f'Sending transaction: {incoming_transaction}')
    time.sleep(5)
    response = requests.post(
        f'http://{ingestion_service_host}:{ingestion_service_port}/transactions/',
        json=incoming_transaction,
    )
    response.raise_for_status()
    print('Waiting for message to be processed by Kafka...')
    time.sleep(5)

    # Check if the message is in Kafka
    kafka_host = os.environ.get('KAFKA_HOST', 'localhost')
    kafka_port = os.environ.get('KAFKA_PORT', '9092')
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

    for message in consumer:
        print(f'Received message: {message.value}')
        if message.value == expected_transaction:
            print('Successfully received message from Kafka')
            return

    raise Exception('Failed to receive message from Kafka')


if __name__ == '__main__':
    main()

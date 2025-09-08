"""
Test endpoints for Kafka consumer functionality
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from kafka import KafkaProducer
from pydantic import BaseModel

from ..core.config import settings
from ..services.kafka_consumer import transaction_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class TestTransactionRequest(BaseModel):
    user_id: str
    credit_card_num: str


# Global producer instance
_kafka_producer: KafkaProducer | None = None


def get_kafka_producer() -> KafkaProducer:
    """Dependency to get or create a Kafka producer instance"""
    global _kafka_producer

    if _kafka_producer is None:
        try:
            _kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f'Failed to create Kafka producer: {str(e)}'
            ) from e

    return _kafka_producer


def cleanup_kafka_producer():
    """Cleanup function to close the Kafka producer"""
    global _kafka_producer

    if _kafka_producer is not None:
        try:
            _kafka_producer.close()
            _kafka_producer = None
        except Exception as e:
            # Log the error but don't raise it during shutdown
            logger.error(f'Error closing Kafka producer: {e}')


@router.post('/send-test-transaction')
async def send_test_transaction_endpoint(
    request: TestTransactionRequest,
    producer: KafkaProducer = Depends(get_kafka_producer),
):
    """Send a test transaction message to Kafka in ingestion service format"""
    try:
        # Create test transaction in ingestion service format
        test_transaction = {
            'user': int(request.user_id),
            'card': int(request.credit_card_num),
            'year': datetime.now().year,
            'month': datetime.now().month,
            'day': datetime.now().day,
            'time': datetime.now().strftime('%H:%M:%S'),
            'amount': 150.00,
            'use_chip': 'Chip Transaction',
            'merchant_id': '12345',
            'merchant_city': 'Test City',
            'merchant_state': 'CA',
            'zip': '12345',
            'mcc': 5411,  # Grocery stores
            'errors': None,
            'is_fraud': False,
        }

        # Send the message
        future = producer.send(settings.KAFKA_TRANSACTIONS_TOPIC, test_transaction)
        record_metadata = future.get(timeout=10)

        return {
            'message': 'Test transaction sent successfully',
            'transaction': test_transaction,
            'topic': record_metadata.topic,
            'partition': record_metadata.partition,
            'offset': record_metadata.offset,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to send test transaction: {str(e)}'
        ) from e


@router.get('/health')
async def kafka_health_check():
    """Check Kafka connectivity and consumer status"""
    kafka_connection_ok = False
    consumer_status = 'unknown'

    try:
        # Test Kafka connection by getting the producer
        get_kafka_producer()
        kafka_connection_ok = True
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Kafka connection failed: {str(e)}',
            'kafka_connection': 'failed',
            'consumer_status': 'unknown',
            'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'topic': settings.KAFKA_TRANSACTIONS_TOPIC,
        }

    # Check actual consumer status
    if transaction_consumer is None:
        consumer_status = 'not_initialized'
    elif not transaction_consumer.running:
        consumer_status = 'stopped'
    elif (
        transaction_consumer.thread is None
        or not transaction_consumer.thread.is_alive()
    ):
        consumer_status = 'thread_dead'
    elif transaction_consumer.consumer is None:
        consumer_status = 'consumer_not_created'
    else:
        consumer_status = 'running'

    # Determine overall health status
    if kafka_connection_ok and consumer_status == 'running':
        overall_status = 'healthy'
        message = 'Kafka connection and consumer are working properly'
    else:
        overall_status = 'unhealthy'
        message = f'Kafka connection: {"ok" if kafka_connection_ok else "failed"}, Consumer: {consumer_status}'

    return {
        'status': overall_status,
        'message': message,
        'kafka_connection': 'ok' if kafka_connection_ok else 'failed',
        'consumer_status': consumer_status,
        'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'topic': settings.KAFKA_TRANSACTIONS_TOPIC,
        'consumer_details': {
            'initialized': transaction_consumer is not None,
            'running': transaction_consumer.running if transaction_consumer else False,
            'thread_alive': transaction_consumer.thread.is_alive()
            if transaction_consumer and transaction_consumer.thread
            else False,
            'consumer_created': transaction_consumer.consumer is not None
            if transaction_consumer
            else False,
        },
    }

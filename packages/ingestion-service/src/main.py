"""
Ingestion Service with Kafka Connection Management
"""

import datetime
import json
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from kafka import KafkaProducer

from .common.models import IncomingTransaction, Transaction


class KafkaConnectionManager:
    """Manages Kafka connections with lazy loading, retry logic, and health monitoring"""

    def __init__(self):
        self.producer: KafkaProducer | None = None
        self.kafka_host = os.environ.get('KAFKA_HOST', 'localhost')
        self.kafka_port = os.environ.get('KAFKA_PORT', '9092')
        self.connection_timeout = int(os.environ.get('KAFKA_CONNECTION_TIMEOUT', '10'))
        self.retry_attempts = int(os.environ.get('KAFKA_RETRY_ATTEMPTS', '3'))
        self.retry_delay = int(os.environ.get('KAFKA_RETRY_DELAY', '2'))
        self.last_connection_attempt = 0
        self.connection_cooldown = 30  # seconds

    def get_producer(self) -> KafkaProducer | None:
        """Get Kafka producer with lazy connection and retry logic"""
        if self.producer is not None:
            return self.producer

        # Check cooldown period
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_cooldown:
            print(
                f'Kafka connection in cooldown period. Last attempt: {self.last_connection_attempt}'
            )
            return None

        # Attempt connection with retries
        for attempt in range(self.retry_attempts):
            try:
                print(
                    f'Attempting Kafka connection (attempt {attempt + 1}/{self.retry_attempts})'
                )
                self.producer = KafkaProducer(
                    bootstrap_servers=f'{self.kafka_host}:{self.kafka_port}',
                    value_serializer=lambda v: json.dumps(v, default=str).encode(
                        'utf-8'
                    ),
                    request_timeout_ms=self.connection_timeout * 1000,
                    retries=0,  # We handle retries at the connection level
                )
                print(
                    f'Successfully connected to Kafka at {self.kafka_host}:{self.kafka_port}'
                )
                return self.producer

            except Exception as e:
                print(f'Kafka connection attempt {attempt + 1} failed: {e}')
                if attempt < self.retry_attempts - 1:
                    print(f'Retrying in {self.retry_delay} seconds...')
                    time.sleep(self.retry_delay)

        # All attempts failed
        self.last_connection_attempt = current_time
        print('All Kafka connection attempts failed. Entering cooldown period.')
        return None

    def send_message(self, topic: str, message: dict) -> bool:
        """Send message to Kafka topic with error handling"""
        producer = self.get_producer()
        if producer is None:
            print('Cannot send message: Kafka producer unavailable')
            return False

        try:
            future = producer.send(topic, message)
            record_metadata = future.get(timeout=10)
            print(
                f"Successfully sent message to topic '{record_metadata.topic}' at partition {record_metadata.partition} with offset {record_metadata.offset}"
            )
            return True
        except Exception as e:
            print(f'Failed to send message to Kafka: {e}')
            # Reset producer on send failure
            self.close()
            return False

    def health_check(self) -> dict:
        """Check Kafka connection health by attempting to connect"""
        current_time = time.time()

        # If we're in cooldown period, return cached status
        if current_time <= (self.last_connection_attempt + self.connection_cooldown):
            producer_exists = self.producer is not None
            return {
                'kafka_status': 'healthy' if producer_exists else 'unhealthy',
                'connection_pool_active': producer_exists,
                'last_connection_attempt': datetime.datetime.fromtimestamp(
                    self.last_connection_attempt
                ).isoformat()
                if self.last_connection_attempt > 0
                else None,
                'next_retry_available': False,
                'in_cooldown': True,
            }

        # Try to establish connection for health check
        try:
            # Create a temporary producer just for health checking
            test_producer = KafkaProducer(
                bootstrap_servers=f'{self.kafka_host}:{self.kafka_port}',
                request_timeout_ms=5000,  # Short timeout for health check
                api_version=(0, 10, 1),
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            )

            # Just creating the producer and closing it verifies connectivity
            # The constructor will fail if Kafka is not reachable
            test_producer.close()

            # If we get here, Kafka is reachable
            return {
                'kafka_status': 'healthy',
                'connection_pool_active': self.producer is not None,
                'last_health_check': datetime.datetime.now(datetime.UTC).isoformat(),
                'kafka_reachable': True,
            }

        except Exception as e:
            print(f'Kafka health check failed: {e}')
            return {
                'kafka_status': 'unhealthy',
                'connection_pool_active': False,
                'last_connection_attempt': datetime.datetime.fromtimestamp(
                    self.last_connection_attempt
                ).isoformat()
                if self.last_connection_attempt > 0
                else None,
                'next_retry_available': current_time
                > (self.last_connection_attempt + self.connection_cooldown),
                'kafka_reachable': False,
                'last_error': str(e),
            }

    def close(self):
        """Close Kafka producer connection"""
        if self.producer is not None:
            try:
                self.producer.close()
            except Exception as e:
                print(f'Error closing Kafka producer: {e}')
            finally:
                self.producer = None


# Global Kafka connection manager
kafka_manager = KafkaConnectionManager()


def transform_transaction(incoming_transaction: IncomingTransaction) -> Transaction:
    """Transform incoming transaction to internal format"""
    amount = float(incoming_transaction.Amount.replace('$', ''))
    is_fraud = incoming_transaction.is_fraud == 'Yes'

    # split time string into hours and minutes
    time_parts = incoming_transaction.Time.split(':')
    hour, minute = int(time_parts[0]), int(time_parts[1])

    return Transaction(
        user=incoming_transaction.User,
        card=incoming_transaction.Card,
        year=incoming_transaction.Year,
        month=incoming_transaction.Month,
        day=incoming_transaction.Day,
        time=datetime.time(hour, minute),
        amount=amount,
        use_chip=incoming_transaction.use_chip,
        merchant_id=incoming_transaction.merchant_name,
        merchant_city=incoming_transaction.merchant_city,
        merchant_state=incoming_transaction.merchant_state,
        zip=incoming_transaction.zip,
        mcc=incoming_transaction.mcc,
        errors=incoming_transaction.errors,
        is_fraud=is_fraud,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # No longer need to initialize Kafka connection at startup
    print('Ingestion service starting up...')
    yield
    print('Ingestion service shutting down...')
    kafka_manager.close()


app = FastAPI(lifespan=lifespan)


@app.post('/transactions/')
async def create_transaction(incoming_transaction: IncomingTransaction):
    """Create and process a transaction"""
    transaction = transform_transaction(incoming_transaction)
    print(f'Received transaction: {transaction.model_dump()}')

    # Attempt to send to Kafka (graceful degradation if unavailable)
    kafka_sent = kafka_manager.send_message('transactions', transaction.model_dump())

    if not kafka_sent:
        print('Warning: Transaction processed but not sent to Kafka (service degraded)')

    return transaction


@app.get('/healthz')
async def healthz():
    """Simple health check endpoint"""
    return {'status': 'ok'}


@app.get('/health')
async def health():
    """Comprehensive health check including Kafka status"""
    kafka_health = kafka_manager.health_check()
    overall_status = (
        'healthy' if kafka_health['kafka_status'] == 'healthy' else 'degraded'
    )

    return {
        'status': overall_status,
        'service': 'ingestion-service',
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
        'kafka': kafka_health,
        'environment': {
            'kafka_host': kafka_manager.kafka_host,
            'kafka_port': kafka_manager.kafka_port,
            'connection_timeout': kafka_manager.connection_timeout,
            'retry_attempts': kafka_manager.retry_attempts,
            'retry_delay': kafka_manager.retry_delay,
        },
    }

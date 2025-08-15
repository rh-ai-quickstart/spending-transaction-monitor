from fastapi import FastAPI, HTTPException
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
import json
import os
from contextlib import asynccontextmanager
import sys
import logging
from typing import Optional
import time

from common.models import Transaction, IncomingTransaction
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaConnectionManager:
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.kafka_host = os.environ.get("KAFKA_HOST", "localhost")
        self.kafka_port = os.environ.get("KAFKA_PORT", "9092")
        self.connection_timeout = int(os.environ.get("KAFKA_CONNECTION_TIMEOUT", "10"))
        self.retry_attempts = int(os.environ.get("KAFKA_RETRY_ATTEMPTS", "3"))
        self.retry_delay = int(os.environ.get("KAFKA_RETRY_DELAY", "2"))
        self.last_connection_attempt = 0
        self.connection_cooldown = 30  # seconds
        
    def _create_producer(self) -> KafkaProducer:
        """Create a new Kafka producer with retry logic"""
        bootstrap_servers = f"{self.kafka_host}:{self.kafka_port}"
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Attempting to connect to Kafka at {bootstrap_servers} (attempt {attempt + 1}/{self.retry_attempts})")
                producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    request_timeout_ms=self.connection_timeout * 1000,
                    retries=1,
                    max_block_ms=5000,
                    api_version=(0, 10, 1)
                )
                # Test the connection
                producer.bootstrap_connected()
                logger.info("Successfully connected to Kafka")
                return producer
            except (KafkaError, NoBrokersAvailable, Exception) as e:
                logger.warning(f"Failed to connect to Kafka (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to Kafka after {self.retry_attempts} attempts")
                    raise
    
    def get_producer(self) -> KafkaProducer:
        """Get or create Kafka producer with lazy initialization"""
        current_time = time.time()
        
        # If we have a producer and it's healthy, return it
        if self.producer is not None:
            try:
                # Quick health check - this will raise an exception if connection is dead
                self.producer.bootstrap_connected()
                return self.producer
            except Exception as e:
                logger.warning(f"Existing Kafka connection is unhealthy: {e}")
                self.producer = None
        
        # Apply connection cooldown to avoid hammering Kafka when it's down
        if current_time - self.last_connection_attempt < self.connection_cooldown:
            raise HTTPException(
                status_code=503, 
                detail=f"Kafka connection failed recently. Please try again in {int(self.connection_cooldown - (current_time - self.last_connection_attempt))} seconds."
            )
        
        self.last_connection_attempt = current_time
        
        try:
            self.producer = self._create_producer()
            return self.producer
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"Unable to connect to Kafka: {str(e)}"
            )
    
    def send_message(self, topic: str, message: dict) -> bool:
        """Send message to Kafka with error handling"""
        try:
            producer = self.get_producer()
            future = producer.send(topic, message)
            record_metadata = future.get(timeout=10)
            logger.info(f"Successfully sent message to topic '{record_metadata.topic}' at partition {record_metadata.partition} with offset {record_metadata.offset}")
            return True
        except HTTPException:
            # Re-raise HTTP exceptions (connection issues)
            raise
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send message to Kafka: {str(e)}"
            )
    
    def health_check(self) -> dict:
        """Check Kafka connection health"""
        try:
            if self.producer is None:
                # Try to connect without storing the producer
                test_producer = self._create_producer()
                test_producer.close()
                return {
                    "kafka_status": "healthy",
                    "kafka_host": f"{self.kafka_host}:{self.kafka_port}",
                    "connection_state": "not_connected"
                }
            else:
                self.producer.bootstrap_connected()
                return {
                    "kafka_status": "healthy",
                    "kafka_host": f"{self.kafka_host}:{self.kafka_port}",
                    "connection_state": "connected"
                }
        except Exception as e:
            return {
                "kafka_status": "unhealthy",
                "kafka_host": f"{self.kafka_host}:{self.kafka_port}",
                "connection_state": "failed",
                "error": str(e)
            }
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            try:
                self.producer.close()
                logger.info("Kafka producer connection closed")
            except Exception as e:
                logger.warning(f"Error closing Kafka producer: {e}")
            finally:
                self.producer = None

kafka_manager = KafkaConnectionManager()

def transform_transaction(incoming_transaction: IncomingTransaction) -> Transaction:
    amount = float(incoming_transaction.Amount.replace("$", ""))
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
        is_fraud=is_fraud
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # No longer connecting to Kafka on startup - using lazy initialization
    logger.info("Starting ingestion service with lazy Kafka connection")
    yield
    # Clean up Kafka connection on shutdown
    kafka_manager.close()

app = FastAPI(lifespan=lifespan)


@app.post("/transactions/")
async def create_transaction(incoming_transaction: IncomingTransaction):
    transaction = transform_transaction(incoming_transaction)
    logger.info(f"Received transaction: {transaction.dict()}")
    
    # Send to Kafka with improved error handling
    kafka_manager.send_message('transactions', transaction.dict())
    
    return transaction

@app.get("/healthz")
async def healthz():
    """Basic health check - service is running"""
    return {"status": "ok"}

@app.get("/health")
async def health():
    """Comprehensive health check including Kafka status"""
    kafka_health = kafka_manager.health_check()
    
    overall_status = "healthy" if kafka_health["kafka_status"] == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "service": "ingestion-service",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kafka": kafka_health,
        "environment": {
            "kafka_host": kafka_manager.kafka_host,
            "kafka_port": kafka_manager.kafka_port,
            "connection_timeout": kafka_manager.connection_timeout,
            "retry_attempts": kafka_manager.retry_attempts,
            "retry_delay": kafka_manager.retry_delay
        }
    }

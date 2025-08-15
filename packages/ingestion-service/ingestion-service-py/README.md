# Python Ingestion Service

This service is a Python-based implementation of the transaction ingestion service with robust Kafka connection management. It uses FastAPI to create a REST API and `kafka-python` to produce messages to a Kafka topic with lazy initialization and graceful degradation.

The service uses a common data model defined in the `common` directory. See the main `README.md` for more details on the data model.

## New Features (Kafka Connection Improvements)

- **🚀 Lazy Kafka Connection** - Service starts without requiring Kafka to be available
- **🏥 Health Monitoring** - Comprehensive health checks including Kafka status  
- **🔄 Automatic Retry** - Configurable retry logic with exponential backoff
- **⚠️ Graceful Degradation** - Proper HTTP error responses when Kafka is unavailable
- **🛡️ Connection Cooldown** - Prevents hammering unavailable Kafka instances
- **⚙️ Configurable Timeouts** - Environment variables for all connection parameters

## API Endpoints

- `POST /transactions/` - Submit a new transaction (returns 503 if Kafka unavailable)
- `GET /healthz` - Basic health check (service status only)  
- `GET /health` - Comprehensive health check (includes Kafka status and configuration)

## Environment Variables

Configure Kafka connection behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_HOST` | `localhost` | Kafka broker hostname |
| `KAFKA_PORT` | `9092` | Kafka broker port |
| `KAFKA_CONNECTION_TIMEOUT` | `10` | Connection timeout in seconds |
| `KAFKA_RETRY_ATTEMPTS` | `3` | Number of connection retry attempts |
| `KAFKA_RETRY_DELAY` | `2` | Delay between retry attempts in seconds |

## Running the service

To run the service locally, you will need to have Python installed.

1. Install the dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The service will start immediately even if Kafka is not available!

## Running the tests

To run the comprehensive test suite:

```bash
python -m pytest test_main.py -v
```

## Demo

Run the demo script to see the Kafka improvements in action:

```bash
python demo_kafka_improvements.py
```

This demonstrates lazy connection, health monitoring, and graceful degradation features.

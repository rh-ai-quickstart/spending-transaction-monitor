# Alert Recommender Pipeline

A Kubeflow pipeline for training and deploying KNN-based collaborative filtering models for alert recommendations.

## Overview

This pipeline converts the existing Jupyter notebooks into a production-ready Kubeflow pipeline that:

1. **Prepares Data** - Loads user and transaction data from PostgreSQL database or MinIO
2. **Trains Model** - Trains a KNN collaborative filtering model
3. **Saves Model** - Saves the model to MinIO and creates MLServer-compatible artifacts
4. **Registers Model** (optional) - Registers the model with OpenDataHub Model Registry
5. **Deploys Model** - Deploys the model as a KServe InferenceService

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kubeflow Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │ Prepare     │──▶│ Train       │──▶│ Save        │          │
│  │ Data        │   │ Model       │   │ Model       │          │
│  └─────────────┘   └─────────────┘   └──────┬──────┘          │
│                                              │                  │
│                                    ┌─────────┴─────────┐       │
│                                    ▼                   ▼       │
│                           ┌─────────────┐     ┌─────────────┐  │
│                           │ Register    │     │ Deploy      │  │
│                           │ Model       │────▶│ Model       │  │
│                           │ (optional)  │     │             │  │
│                           └──────┬──────┘     └──────┬──────┘  │
│                                  │                   │         │
│                                  ▼                   │         │
│                           ┌─────────────┐            │         │
│                           │   Model     │◀───────────┘         │
│                           │  Registry   │ (when deployFromRegistry=true)
│                           └─────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
# Pipeline Python code (ml-pipeline/alert-recommender-pipeline/)
alert-recommender-pipeline/
├── src/
│   ├── requirements.txt
│   └── alert_recommender_pipeline/
│       ├── __init__.py
│       ├── main.py              # FastAPI service
│       ├── models.py            # Pydantic models
│       ├── k8s.py               # Kubernetes utilities
│       └── pipelines/
│           ├── __init__.py      # Pipeline management
│           ├── pipelines.py     # Pipeline definitions
│           └── tasks.py         # Pipeline tasks
├── Containerfile
├── build.yaml
├── pyproject.toml
└── README.md

# Helm chart (deploy/helm/alert-recommender-pipeline/)
deploy/helm/alert-recommender-pipeline/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── dspa.yaml               # Data Science Pipelines Application
    ├── service.yaml
    ├── serviceaccount.yaml
    ├── rbac.yaml
    ├── secret.yaml
    ├── pipeline-job.yaml
    ├── serving-runtime.yaml
    └── minio.yaml
```

## Prerequisites

- OpenShift cluster with:
  - OpenShift AI (Data Science Pipelines)
  - KServe or OpenDataHub Model Serving
- MinIO or S3-compatible storage
- (Optional) OpenDataHub Model Registry

## Installation

### Using Helm

```bash
# Install with default values (includes DSPA setup)
helm install alert-recommender ../../deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --create-namespace

# Install with custom values
helm install alert-recommender ../../deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --set minio.endpoint="http://my-minio:9000" \
  --set minio.accessKey="myaccesskey" \
  --set minio.secretKey="mysecretkey" \
  --set modelRegistry.enabled=true

# Install without DSPA (if already exists)
helm install alert-recommender ../../deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --set dspa.deploy=false
```

### Data Science Pipelines

The chart now automatically deploys a `DataSciencePipelinesApplication` (DSPA) which is required for Kubeflow Pipelines. This includes:
- MariaDB for pipeline metadata
- MinIO for pipeline artifacts
- Pipeline API server, persistence agent, and scheduler

To use an existing DSPA, set `dspa.deploy=false` and configure `dsPipelines.url`.

### Configuration

Key configuration options in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pipeline.name` | Model name | `alert-recommender` |
| `pipeline.version` | Model version | `1.0.0` |
| `pipeline.nNeighbors` | KNN neighbors | `5` |
| `pipeline.deployModel` | Deploy after training | `true` |
| `pipeline.registerModel` | Register with Model Registry | `false` |
| `pipeline.deployFromRegistry` | Deploy model from registry instead of pipeline artifact | `false` |
| `pipeline.modelVersionToDeploy` | Specific version to deploy from registry (empty = latest) | `""` |
| `minio.endpoint` | MinIO endpoint URL | `http://minio-service:9000` |
| `minio.deploy` | Deploy MinIO | `false` |
| `modelRegistry.enabled` | Enable Model Registry | `false` |
| `modelRegistry.url` | Model Registry URL | `http://model-registry:8080` |

### Data Source Priority

The pipeline automatically tries data sources in the following order:

1. **PostgreSQL Database** (preferred) - Uses the `spending-monitor-secret` from the main application
2. **MinIO** - Falls back to S3-compatible storage if database is unavailable
3. **Local Files** - Last resort fallback to bundled sample data

No additional configuration is needed - the pipeline automatically reads database credentials from `spending-monitor-secret` when deployed in the same namespace as the spending-monitor application.

When loading from the database:
- Only active users are included
- Only approved/settled transactions are included
- Alert rules are loaded for real training labels (if available)

### Multiple Pipelines

You can define multiple pipeline configurations:

```yaml
pipelines:
  default-training:
    enabled: true
    name: "alert-recommender"
    version: "1.0.0"
    nNeighbors: 5
    deployModel: true

  high-precision:
    enabled: true
    name: "alert-recommender-hp"
    version: "1.0.0"
    nNeighbors: 10
    threshold: 0.6
    deployModel: true
```

## API Endpoints

The pipeline service exposes the following REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/train` | POST | Create and run a training pipeline |
| `/status` | GET | Get pipeline run status |
| `/delete` | DELETE | Delete a pipeline |
| `/cleanup` | POST | Clean up deployment resources |
| `/models` | GET | List deployed InferenceServices |

### Example: Create Training Pipeline

```bash
curl -X POST http://alert-recommender-pipeline/train \
  -H "Content-Type: application/json" \
  -d '{
    "name": "alert-recommender",
    "version": "1.0.0",
    "n_neighbors": 5,
    "deploy_model": true,
    "register_model": false
  }'
```

### Example: Check Pipeline Status

```bash
curl http://alert-recommender-pipeline/status?pipeline_name=alert-recommender-v1-0-0
```

## Model Serving

After deployment, the model is available as a KServe InferenceService:

```bash
# Get the inference endpoint
kubectl get inferenceservice alert-recommender -n spending-transaction-monitor

# Test the endpoint
curl -X POST http://<inference-url>/v2/models/alert-recommender/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "input",
      "shape": [1, 10],
      "datatype": "FP32",
      "data": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    }]
  }'
```

## Development

### Building the Container Image

```bash
# Build the image
podman build -t alert-recommender-pipeline:latest -f Containerfile .

# Push to registry
podman push alert-recommender-pipeline:latest quay.io/your-org/alert-recommender-pipeline:latest
```

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the FastAPI service locally
uvicorn alert_recommender_pipeline.main:app --reload --port 8000
```

### Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=alert_recommender_pipeline
```

## Pipeline Tasks

### 1. Prepare Data (`prepare_data`)
- Automatically tries data sources in priority order:
  1. **Database**: Queries PostgreSQL directly for users, transactions, and alert rules (preferred)
  2. **MinIO**: Downloads CSV files from S3-compatible storage
  3. **Local**: Falls back to local filesystem if other sources unavailable
- Uses `spending-monitor-secret` for database credentials (no extra config needed)
- Outputs: User and transaction CSV files, metadata JSON with data source used

### 2. Train Model (`train_model`)
- Performs feature engineering
- Generates alert labels (real or heuristic)
- Trains KNN model with configurable parameters
- Outputs: Trained model pickle file

### 3. Save Model (`save_model`)
- Creates KNNRecommender wrapper for MLServer
- Wraps in sklearn Pipeline
- Uploads to MinIO
- Outputs: Model artifacts in MinIO

### 4. Register Model (`register_model`) - Optional
- Registers model with OpenDataHub Model Registry
- Creates model version and artifact records

### 5. Deploy Model (`deploy_model`)
- Supports two deployment sources:
  - **Pipeline artifact** (default): Uses model saved in current pipeline run
  - **Model Registry**: Fetches model info from registry when `DEPLOY_FROM_REGISTRY=true`
- Creates storage-config secret
- Deploys ServingRuntime
- Deploys InferenceService
- Waits for service readiness

### 6. Cleanup (`cleanup_deployment`)
- Removes InferenceService
- Removes ServingRuntime
- Removes secrets and RBAC resources
- Optionally removes MinIO resources

## Model Registry Integration

When enabled, the pipeline registers models with the OpenDataHub Model Registry:

```yaml
modelRegistry:
  enabled: true
  url: "http://model-registry:8080"
```

This creates:
- **Registered Model**: Top-level model entry
- **Model Version**: Version-specific metadata
- **Model Artifact**: Storage location reference

### Deploy from Model Registry

You can deploy a model directly from the Model Registry instead of from the pipeline's saved artifact. This is useful for:
- Deploying a specific version of a model that was trained earlier
- Separating the training and deployment processes
- Rolling back to a previous model version

#### Configuration

Enable in `values.yaml`:

```yaml
pipeline:
  deployModel: true
  deployFromRegistry: true
  modelVersionToDeploy: ""  # Empty = latest version, or specify version like "25-01-29-143052"

modelRegistry:
  enabled: true
  url: "http://model-registry.rhoai-model-registries.svc.cluster.local:8080"
```

#### API Request

```bash
curl -X POST http://alert-recommender-pipeline/train \
  -H "Content-Type: application/json" \
  -d '{
    "name": "alert-recommender",
    "version": "1.0.0",
    "deploy_model": true,
    "deploy_from_registry": true,
    "model_version_to_deploy": "",
    "model_registry_url": "http://model-registry:8080"
  }'
```

#### How It Works

When `deploy_from_registry` is enabled, the deploy step:

1. Queries the Model Registry for the registered model by name
2. Fetches available model versions
3. Selects the requested version (or latest if not specified)
4. Extracts the storage URI from the model's custom properties
5. Configures the InferenceService to use that storage URI

This allows you to deploy any previously registered model version without re-running the training pipeline.

#### Example: Deploy-Only Pipeline Configuration

```yaml
pipelines:
  deploy-from-registry:
    enabled: true
    name: "alert-recommender"
    version: "1.0.0"
    deployModel: true
    deployFromRegistry: true
    modelVersionToDeploy: ""  # Deploy latest version
```

## Troubleshooting

### Pipeline Not Starting
1. Check Data Science Pipelines is running:
   ```bash
   kubectl get pods -l app=ds-pipeline -n openshift-ai
   ```
2. Check pipeline service logs:
   ```bash
   kubectl logs -l app=alert-recommender-pipeline
   ```

### Model Deployment Failing
1. Check InferenceService status:
   ```bash
   kubectl describe isvc alert-recommender
   ```
2. Check ServingRuntime:
   ```bash
   kubectl get servingruntimes
   ```
3. Verify MinIO connectivity and model artifacts

### Data Loading Issues

**For Database Data Source:**
1. Verify database connectivity:
   ```bash
   kubectl exec -it <pipeline-pod> -- psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -c "SELECT 1"
   ```
2. Check database credentials in secret
3. Ensure the database has users and transactions data
4. Check pipeline logs for connection errors

**For MinIO Data Source:**
1. Verify MinIO endpoint and credentials
2. Check bucket and data paths
3. Ensure data files exist in MinIO or local fallback

## License

Apache License 2.0

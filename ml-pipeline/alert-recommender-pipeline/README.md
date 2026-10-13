# Alert Recommender Pipeline

A Kubeflow pipeline for training and deploying KNN-based collaborative filtering models for alert recommendations.

## Overview

This pipeline converts the existing Jupyter notebooks into a production-ready Kubeflow pipeline that:

1. **Prepares Data** - Loads user and transaction data from PostgreSQL database or S4-backed S3 storage
2. **Trains Model** - Trains a KNN collaborative filtering model
3. **Saves Model** - Saves the model to the S4 `models` bucket and creates MLServer-compatible artifacts
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
    ├── pipeline-job.yaml
    ├── serving-runtime.yaml
    └── s4-bucket-bootstrap-job.yaml
```

## Prerequisites

- OpenShift cluster with:
  - OpenShift AI (Data Science Pipelines)
  - KServe or OpenDataHub Model Serving
- S4-backed S3 storage (installed by the chart dependency)
- (Optional) OpenDataHub Model Registry

## Installation

### Using Helm

```bash
# Install with default values (includes DSPA setup)
helm install alert-recommender deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --create-namespace

# Install with custom S4 storage values
helm install alert-recommender deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --set s3.bucketName="models" \
  --set aws-compatible-storage.storage.data.size="10Gi" \
  --set modelRegistry.enabled=true

# Install without DSPA (if already exists)
helm install alert-recommender deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --set dspa.deploy=false

# Reuse an existing standalone S4 release in the same namespace
helm install alert-recommender deploy/helm/alert-recommender-pipeline \
  --namespace spending-transaction-monitor \
  --set aws-compatible-storage.enabled=false
```

### Data Science Pipelines and S4

The chart now automatically deploys a `DataSciencePipelinesApplication` (DSPA) which is required for Kubeflow Pipelines. This includes:
- MariaDB for pipeline metadata
- S4-backed S3 storage for the `mlpipeline` artifact bucket and `models` bucket
- Pipeline API server, persistence agent, and scheduler

The [aws-compatible-storage (S4) chart](https://github.com/rh-ai-quickstart/ai-architecture-charts/tree/main/aws-compatible-storage) uses service `s4`, S3 API `http://s4:7480`, and a 10Gi data PVC. The chart enables the S4 UI Route and disables the S3 API Route. DSPA uses `s4.<namespace>.svc.cluster.local:7480` with the `s4-credentials` Secret. The parent chart creates both buckets with a regular boto3 Job, including when a standalone S4 release is reused. The default S4 credentials and UI password are demo values; override them for shared deployments.

When reusing S4 with another service name or port, set `s3.endpoint` and `s3.credentialsSecret`; the endpoint also supplies DSPA's host, port, and scheme. Set `s3.uiEndpoint` if the S4 UI health endpoint is on another host or port, and `s3.region` if it differs from `us-east-1`. The DSPA MariaDB name defaults to `mlpipeline`.

The standalone notebooks use the same S4 service. Configure `S3_ENDPOINT_URL`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` in the Workbench from the `s4-credentials` Secret before running notebooks 1 and 2. Notebook 3 reads that Secret and creates KServe's bucket-specific storage configuration and ServiceAccount. For a differently named S4 release, set `S4_SERVICE_NAME` and `S4_CREDENTIALS_SECRET` in notebook 3's environment.

Before running notebook 3, a namespace admin should apply `ml-pipeline/deployment/rbac.yaml`. Its RoleBinding targets a Workbench ServiceAccount named `alert-recommendation`; set the binding's subject to the actual Workbench ServiceAccount when that name differs. The Role grants the Secret and ServiceAccount access notebook 3 needs.

Helm does not copy existing MinIO objects. Copy any existing data in the `models` bucket to S4 before deploying models saved in the old store.

To use an existing DSPA, set `dspa.deploy=false` and configure `dsPipelines.url`.

### Configuration

Key configuration options in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pipelines.alert_recommender.name` | Model name | `alert-recommender` |
| `pipelines.alert_recommender.version` | Model version | `1.0.0` |
| `pipelines.alert_recommender.nNeighbors` | KNN neighbors | `5` |
| `pipelines.alert_recommender.deployModel` | Deploy after training | `true` |
| `pipelines.alert_recommender.registerModel` | Register with Model Registry | `true` |
| `pipelines.alert_recommender.deployFromRegistry` | Deploy model from registry instead of pipeline artifact | `false` |
| `pipelines.alert_recommender.modelVersionToDeploy` | Specific version to deploy from registry (empty = latest) | `""` |
| `s3.endpoint` | Optional S4 S3 API override; otherwise derived from S4 name and port | `http://s4:7480` (derived) |
| `s3.bucketName` | Model artifact and fallback data bucket | `models` |
| `dspa.objectStorage.bucket` | DSPA artifact bucket | `mlpipeline` |
| `modelRegistry.enabled` | Enable Model Registry | `true` |
| `modelRegistry.url` | Service CA verified Model Registry proxy | `https://model-registry.rhoai-model-registries.svc.cluster.local:8443` |

### Data Source Priority

The pipeline automatically tries data sources in the following order:

1. **PostgreSQL Database** (preferred) - Uses the `spending-monitor-secret` from the main application
2. **S4 S3 storage** - Falls back to the `models` bucket if the database is unavailable
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

For the `spending-monitor` Helm release, forward the pipeline Service in a separate terminal:

```bash
oc -n spending-transaction-monitor port-forward service/spending-monitor-alert-recommender-pipeline 8000:8080
```

```bash
curl -X POST http://localhost:8000/train \
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
curl 'http://localhost:8000/status?pipeline_name=alert-recommender-v1-0-0'
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
# From the repository root, build and publish the image selected by Make
make REGISTRY_URL=quay.io REPOSITORY=<your-quay-org> IMAGE_TAG=<tag> build-ml-pipeline
make REGISTRY_URL=quay.io REPOSITORY=<your-quay-org> IMAGE_TAG=<tag> push-ml-pipeline
```

Release CI also publishes `quay.io/rh-ai-quickstart/alert-recommender-pipeline:<release-tag>` and `:latest`. `make deploy-with-ml-dspa` passes the selected pipeline repository and tag to Helm; use `ML_PIPELINE_IMAGE_REPOSITORY` and `ML_PIPELINE_IMAGE_TAG` when they differ from the UI/API image location.

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
  2. **S4 S3 storage**: Downloads CSV files from the `models` bucket
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
- Uploads to the S4 `models` bucket
- Outputs: Model artifacts in S4

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
- Leaves Helm-managed S4 and stored model objects in place

## Model Registry Integration

When enabled, the pipeline registers models with the OpenDataHub Model Registry:

```yaml
modelRegistry:
  enabled: true
  url: "https://model-registry.rhoai-model-registries.svc.cluster.local:8443"
```

This creates:
- **Registered Model**: Top-level model entry
- **Model Version**: Version-specific metadata
- **Model Artifact**: Storage location reference

### Deploy from Model Registry

The training pipeline can use a model version from the Model Registry for its deploy step instead of the artifact saved by that run. This is useful for:
- Deploying a specific version of a model that was trained earlier
- Rolling back to a previous model version

#### Configuration

Enable in `values.yaml` for a pipeline that has a registered model version:

```yaml
pipelines:
  alert_recommender:
    deployModel: true
    deployFromRegistry: true
    modelVersionToDeploy: ""  # Empty = latest version

modelRegistry:
  enabled: true
  url: "https://model-registry.rhoai-model-registries.svc.cluster.local:8443"
```

The deploy task reads its mounted service account token and the OpenShift service CA bundle to authenticate to this proxy. The default `deployFromRegistry=false` uses the model artifact saved by the current run.

#### API Request

```bash
curl -X POST http://localhost:8000/train \
  -H "Content-Type: application/json" \
  -d '{
    "name": "alert-recommender",
    "version": "1.0.0",
    "deploy_model": true,
    "deploy_from_registry": true,
    "model_version_to_deploy": "",
    "model_registry_url": "https://model-registry.rhoai-model-registries.svc.cluster.local:8443"
  }'
```

#### How It Works

When `deploy_from_registry` is enabled, the deploy step:

1. Queries the Model Registry for the registered model by name
2. Fetches available model versions
3. Selects the requested version (or latest if not specified)
4. Extracts the storage URI from the model's custom properties
5. Configures the InferenceService to use that storage URI

The current pipeline still runs its prepare, train, and save steps; the deploy step can select an earlier registered version.

#### Example: Select a Registered Version After Training

```yaml
pipelines:
  alert_recommender:
    enabled: true
    name: "alert-recommender"
    version: "1.0.0"
    deployModel: true
    deployFromRegistry: true
    modelVersionToDeploy: ""  # Deploy latest version after this training run
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
3. Verify S4 readiness, credentials, bucket access, and model artifacts

### Data Loading Issues

**For Database Data Source:**
1. Verify database connectivity:
   ```bash
   kubectl exec -it <pipeline-pod> -- psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -c "SELECT 1"
   ```
2. Check database credentials in secret
3. Ensure the database has users and transactions data
4. Check pipeline logs for connection errors

**For S4 S3 Data Source:**
1. Verify the `s4` service endpoint and `s4-credentials` Secret
2. Check bucket and data paths
3. Ensure data files exist in the S4 `models` bucket or local fallback

## License

Apache License 2.0

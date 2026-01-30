"""Shared constants and configuration for pipeline tasks."""

import os

# Base image for all pipeline components
BASE_IMAGE = os.environ.get(
    "ALERT_RECOMMENDER_PIPELINE_IMAGE",
    "quay.io/rh-ai-quickstart/alert-recommender-pipeline:latest"
)

# These are the alert types that the model can recommend
ALERT_TYPES = [
    'alert_high_spender',
    'alert_high_tx_volume',
    'alert_high_merchant_diversity',
    'alert_near_credit_limit',
    'alert_large_transaction',
    'alert_new_merchant',
    'alert_location_based',
    'alert_subscription_monitoring'
]

# Features used for training the KNN model
FEATURE_COLUMNS = [
    'amount_mean',
    'amount_std',
    'amount_max',
    'amount_sum',
    'amount_count',
    'merchant_name_nunique',
    'merchant_category_nunique',
    'credit_limit',
    'credit_balance',
    'credit_utilization'
]

# Namespace defaults
DEFAULT_NAMESPACE = 'spending-transaction-monitor'

# Database defaults
DEFAULT_DB_HOST = 'spending-monitor-db'
DEFAULT_DB_PORT = '5432'
DEFAULT_DB_NAME = 'spending-monitor'
DEFAULT_DB_USER = 'user'

# MinIO defaults
DEFAULT_MINIO_ACCESS_KEY = 'minio'
DEFAULT_MINIO_SECRET_KEY = 'minio123'
DEFAULT_BUCKET_NAME = 'models'

def get_default_minio_endpoint(namespace: str = DEFAULT_NAMESPACE) -> str:
    """Get the default MinIO endpoint for a namespace."""
    return f'http://minio-service.{namespace}.svc.cluster.local:9000'

# Model defaults
DEFAULT_MODEL_NAME = 'alert-recommender'
DEFAULT_MODEL_VERSION = '1.0.0'
DEFAULT_N_NEIGHBORS = 5
DEFAULT_METRIC = 'cosine'
DEFAULT_THRESHOLD = 0.4

# Deployment defaults
DEFAULT_SERVING_RUNTIME = 'alert-recommender-runtime'
DEFAULT_SERVING_RUNTIME_IMAGE = 'docker.io/seldonio/mlserver:1.7.0-sklearn'

MODEL_REGISTRY_API_VERSION = 'v1alpha3'
MODEL_REGISTRY_API_BASE = f'/api/model_registry/{MODEL_REGISTRY_API_VERSION}'

KSERVE_GROUP = 'serving.kserve.io'
KSERVE_SERVING_RUNTIME_VERSION = 'v1alpha1'
KSERVE_INFERENCE_SERVICE_VERSION = 'v1beta1'

"""Pydantic models for Alert Recommender Pipeline configuration."""

from pydantic import BaseModel


class BasePipelineModel(BaseModel):
    """Base model for pipeline configurations."""
    name: str
    version: str
    source: str = "MINIO"  # Data source type (MINIO, S3, etc.)
    
    def pipeline_name(self) -> str:
        """Generate a Kubernetes-compliant pipeline name."""
        name = self.name.replace('_', '-').replace('.', '-').strip().lower()
        version = self.version.replace('_', '-').replace('.', '-').strip()
        return f"{name}-v{version}"


class PipelineConfig(BasePipelineModel):
    """Configuration for the alert recommender ML pipeline."""
    
    # Pipeline identification (inherited from BasePipelineModel)
    name: str = "alert-recommender"
    version: str = "1.0.0"
    source: str = "MINIO"
    
    # Data configuration
    data_version: str = "1"
    
    # Model hyperparameters
    n_neighbors: int = 5
    metric: str = "cosine"
    threshold: float = 0.4
    
    # MinIO/S3 configuration
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    bucket_name: str = "models"
    region: str = "us-east-1"
    
    # Deployment configuration
    namespace: str = "spending-transaction-monitor"
    serving_runtime: str = "mlserver-sklearn"
    
    # Model Registry configuration
    model_registry_enabled: bool = False
    model_registry_url: str = ""
    
    # Pipeline options
    deploy_model: bool = True
    cleanup_on_failure: bool = False
    create_serving_runtime: bool = True


class TrainModelConfig(BaseModel):
    """Configuration for model training task."""
    
    data_version: str = "1"
    n_neighbors: int = 5
    metric: str = "cosine"
    
    # Feature columns for training
    feature_columns: list[str] = [
        'amount_mean', 'amount_std', 'amount_max', 'amount_sum', 'amount_count',
        'merchant_name_nunique', 'merchant_category_nunique',
        'credit_limit', 'credit_balance', 'credit_utilization'
    ]
    
    # Alert types to predict
    alert_types: list[str] = [
        'alert_high_spender',
        'alert_high_tx_volume',
        'alert_high_merchant_diversity',
        'alert_near_credit_limit',
        'alert_large_transaction',
        'alert_new_merchant',
        'alert_location_based',
        'alert_subscription_monitoring'
    ]


class SaveModelConfig(BaseModel):
    """Configuration for model save task."""
    
    model_name: str = "alert-recommender"
    threshold: float = 0.4


class DeployModelConfig(BaseModel):
    """Configuration for model deployment task."""
    
    model_name: str = "alert-recommender"
    namespace: str = "spending-transaction-monitor"
    serving_runtime: str = "mlserver-sklearn"
    min_replicas: int = 1
    max_replicas: int = 3
    
    # Resource requests/limits
    cpu_request: str = "500m"
    memory_request: str = "512Mi"
    cpu_limit: str = "1"
    memory_limit: str = "1Gi"


class ModelRegistryConfig(BaseModel):
    """Configuration for model registry integration."""
    
    enabled: bool = False
    url: str = ""
    model_name: str = "alert-recommender"
    model_description: str = "KNN-based collaborative filtering model for alert recommendations"
    model_format: str = "sklearn"

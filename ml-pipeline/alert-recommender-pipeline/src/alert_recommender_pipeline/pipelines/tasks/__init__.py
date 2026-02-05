"""Kubeflow Pipeline tasks for Alert Recommender Pipeline."""

# Re-export all task functions for backward compatibility
from .data_tasks import prepare_data
from .training_tasks import train_model
from .storage_tasks import save_model
from .registry_tasks import register_model
from .deployment_tasks import deploy_model

# Also export constants for convenience
from .constants import (
    BASE_IMAGE,
    ALERT_TYPES,
    FEATURE_COLUMNS,
    DEFAULT_NAMESPACE,
    DEFAULT_MODEL_NAME,
    DEFAULT_N_NEIGHBORS,
    DEFAULT_METRIC,
    DEFAULT_THRESHOLD,
)

__all__ = [
    # Tasks
    'prepare_data',
    'train_model',
    'save_model',
    'register_model',
    'deploy_model',
    # Constants
    'BASE_IMAGE',
    'ALERT_TYPES',
    'FEATURE_COLUMNS',
    'DEFAULT_NAMESPACE',
    'DEFAULT_MODEL_NAME',
    'DEFAULT_N_NEIGHBORS',
    'DEFAULT_METRIC',
    'DEFAULT_THRESHOLD',
]

"""Kubeflow Pipeline definitions for Alert Recommender Pipeline.

This module defines the main pipeline that chains together the tasks:
1. prepare_data - Load and prepare training data
2. train_model - Train the KNN model
3. save_model - Save model to MinIO
4. register_model - Register with Model Registry (optional)
5. deploy_model - Deploy as InferenceService (optional)
"""

from kfp import dsl

from .tasks import (
    prepare_data as prepare_data_task_fn,
    train_model as train_model_task_fn,
    save_model as save_model_task_fn,
    register_model as register_model_task_fn,
    deploy_model as deploy_model_task_fn,
)


def alert_recommender_pipeline(
    pipeline_name: str,
    minio_endpoint: str,
    deploy_model: str = "true",
    register_model: str = "false",
    model_registry_url: str = ""
):
    """
    Create the alert recommender ML pipeline.
    
    Args:
        pipeline_name: Name of the pipeline (used for secrets)
        minio_endpoint: MinIO endpoint URL
        deploy_model: Whether to deploy the model ("true"/"false")
        register_model: Whether to register with Model Registry ("true"/"false")
        model_registry_url: URL of the Model Registry service
    
    Returns:
        A Kubeflow pipeline function
    """
    
    @dsl.pipeline(
        name="alert-recommender-training-pipeline",
        description="Train and deploy the alert recommendation KNN model"
    )
    def _pipeline():
        from kfp import kubernetes
        
        secret_key_to_env = {
            'NAME': 'MODEL_NAME',
            'VERSION': 'MODEL_VERSION',
            'DATA_VERSION': 'DATA_VERSION',
            'N_NEIGHBORS': 'N_NEIGHBORS',
            'METRIC': 'METRIC',
            'THRESHOLD': 'THRESHOLD',
            'POSTGRES_DB_HOST': 'POSTGRES_DB_HOST',
            'POSTGRES_DB_PORT': 'POSTGRES_DB_PORT',
            'POSTGRES_DB': 'POSTGRES_DB',
            'POSTGRES_USER': 'POSTGRES_USER',
            'POSTGRES_PASSWORD': 'POSTGRES_PASSWORD',
            'MINIO_ENDPOINT': 'MINIO_ENDPOINT',
            'MINIO_ACCESS_KEY': 'MINIO_ACCESS_KEY',
            'MINIO_SECRET_KEY': 'MINIO_SECRET_KEY',
            'BUCKET_NAME': 'BUCKET_NAME',
            'NAMESPACE': 'NAMESPACE',
            'MODEL_REGISTRY_ENABLED': 'MODEL_REGISTRY_ENABLED',
            'MODEL_REGISTRY_URL': 'MODEL_REGISTRY_URL',
            'DEPLOY_FROM_REGISTRY': 'DEPLOY_FROM_REGISTRY',
            'MODEL_VERSION_TO_DEPLOY': 'MODEL_VERSION_TO_DEPLOY',
            'DEPLOY_MODEL': 'DEPLOY_MODEL',
            'SERVING_RUNTIME': 'SERVING_RUNTIME',
            'CREATE_SERVING_RUNTIME': 'CREATE_SERVING_RUNTIME',
            'SERVING_RUNTIME_IMAGE': 'SERVING_RUNTIME_IMAGE',
        }
        
        pipeline_tasks = []
        
        prepare_data_task = prepare_data_task_fn()
        prepare_data_task.set_caching_options(False)
        pipeline_tasks.append(prepare_data_task)
        
        train_model_task = train_model_task_fn(
            input_data=prepare_data_task.outputs['output_data']
        )
        train_model_task.set_caching_options(False)
        pipeline_tasks.append(train_model_task)
        
        save_model_task = save_model_task_fn(
            input_model=train_model_task.outputs['output_model']
        )
        save_model_task.set_caching_options(False)
        pipeline_tasks.append(save_model_task)
        
        if register_model.lower() == "true":
            register_model_task = register_model_task_fn(
                input_artifact=save_model_task.outputs['output_artifact']
            )
            register_model_task.set_caching_options(False)
            pipeline_tasks.append(register_model_task)
        
        if deploy_model.lower() == "true":
            deploy_model_task = deploy_model_task_fn(
                input_artifact=save_model_task.outputs['output_artifact']
            )
            deploy_model_task.set_caching_options(False)
            
            if register_model.lower() == "true":
                deploy_model_task.after(register_model_task)
            
            pipeline_tasks.append(deploy_model_task)
        
        for task in pipeline_tasks:
            kubernetes.use_secret_as_env(
                task=task,
                secret_name=pipeline_name,
                secret_key_to_env=secret_key_to_env
            )
    
    return _pipeline


def training_only_pipeline(pipeline_name: str, minio_endpoint: str):
    """
    Create a training-only pipeline (no deployment).
    
    Args:
        pipeline_name: Name of the pipeline (used for secrets)
        minio_endpoint: MinIO endpoint URL
    
    Returns:
        A Kubeflow pipeline function
    """
    
    @dsl.pipeline(
        name="alert-recommender-training-only-pipeline",
        description="Train the alert recommendation KNN model without deployment"
    )
    def _pipeline():
        from kfp import kubernetes
        
        secret_key_to_env = {
            'NAME': 'MODEL_NAME',
            'VERSION': 'MODEL_VERSION',
            'DATA_VERSION': 'DATA_VERSION',
            'N_NEIGHBORS': 'N_NEIGHBORS',
            'METRIC': 'METRIC',
            'THRESHOLD': 'THRESHOLD',
            'POSTGRES_DB_HOST': 'POSTGRES_DB_HOST',
            'POSTGRES_DB_PORT': 'POSTGRES_DB_PORT',
            'POSTGRES_DB': 'POSTGRES_DB',
            'POSTGRES_USER': 'POSTGRES_USER',
            'POSTGRES_PASSWORD': 'POSTGRES_PASSWORD',
            'MINIO_ENDPOINT': 'MINIO_ENDPOINT',
            'MINIO_ACCESS_KEY': 'MINIO_ACCESS_KEY',
            'MINIO_SECRET_KEY': 'MINIO_SECRET_KEY',
            'BUCKET_NAME': 'BUCKET_NAME',
            'NAMESPACE': 'NAMESPACE',
        }
        
        prepare_data_task = prepare_data_task_fn()
        prepare_data_task.set_caching_options(False)
        
        train_model_task = train_model_task_fn(
            input_data=prepare_data_task.outputs['output_data']
        )
        train_model_task.set_caching_options(False)
        
        save_model_task = save_model_task_fn(
            input_model=train_model_task.outputs['output_model']
        )
        save_model_task.set_caching_options(False)
        
        for task in [prepare_data_task, train_model_task, save_model_task]:
            kubernetes.use_secret_as_env(
                task=task,
                secret_name=pipeline_name,
                secret_key_to_env=secret_key_to_env
            )
    
    return _pipeline

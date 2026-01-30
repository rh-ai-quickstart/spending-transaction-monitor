"""FastAPI service for Alert Recommender Pipeline management.

This service provides REST endpoints for:
- Creating and running ML training pipelines
- Checking pipeline status
- Deleting pipelines and cleaning up resources
"""

import asyncio
import logging
from typing import Optional

from fastapi import Body, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import k8s, pipelines

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Alert Recommender Pipeline Service",
    description="Manage ML training and deployment pipelines for alert recommendations",
    version="0.1.0"
)


class PipelineRequest(BaseModel):
    """Request body for creating a pipeline."""
    name: str = "alert-recommender"
    version: str = "1.0.0"
    data_version: str = "1"
    n_neighbors: int = 5
    metric: str = "cosine"
    threshold: float = 0.4
    postgres_db_host: str = ""
    postgres_db_port: str = "5432"
    postgres_db: str = "spending-monitor"
    postgres_user: str = ""
    postgres_password: str = ""
    minio_endpoint: str = ""
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    bucket_name: str = "models"
    namespace: str = "spending-transaction-monitor"
    serving_runtime: str = "alert-recommender-runtime"
    create_serving_runtime: bool = False
    serving_runtime_image: str = "docker.io/seldonio/mlserver:1.7.0-sklearn"
    deploy_model: bool = True
    register_model: bool = False
    model_registry_url: str = ""
    model_registry_enabled: bool = False
    deploy_from_registry: bool = False
    model_version_to_deploy: str = ""
    
    def pipeline_name(self) -> str:
        """Generate a Kubernetes-compliant pipeline name."""
        name = self.name.replace('_', '-').replace('.', '-').strip().lower()
        version = self.version.replace('_', '-').replace('.', '-').strip()
        return f"{name}-v{version}"


class CleanupRequest(BaseModel):
    """Request body for cleanup operation."""
    
    name: str = "alert-recommender"
    namespace: str = "spending-transaction-monitor"
    cleanup_minio: bool = False


@app.get("/ping")
def ping():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


@app.get("/health")
def health():
    """Detailed health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "service": "alert-recommender-pipeline",
        "version": "0.1.0"
    })


@app.post("/train")
async def train_pipeline(payload: PipelineRequest = Body(...)):
    """
    Create and run a training pipeline.
    
    This endpoint:
    1. Creates a Kubernetes secret with pipeline configuration
    2. Compiles the Kubeflow pipeline
    3. Uploads and runs the pipeline
    
    Returns the pipeline name and ID.
    """
    import os
    
    try:
        k8s_name = k8s.normalize_name(payload.pipeline_name())
        
        if not payload.postgres_db_host:
            payload.postgres_db_host = os.getenv('POSTGRES_DB_HOST', 'spending-monitor-db')
        if not payload.postgres_db_port:
            payload.postgres_db_port = os.getenv('POSTGRES_DB_PORT', '5432')
        if not payload.postgres_db:
            payload.postgres_db = os.getenv('POSTGRES_DB', 'spending-monitor')
        if not payload.postgres_user:
            payload.postgres_user = os.getenv('POSTGRES_USER', '')
        if not payload.postgres_password:
            payload.postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        
        logger.info(f"Database config: host={payload.postgres_db_host}, db={payload.postgres_db}, user={payload.postgres_user}, password_set={bool(payload.postgres_password)}")
        
        secret_name = await asyncio.to_thread(
            k8s.apply_config_as_secret,
            payload,
            replace=True
        )
        
        pipeline_id = await asyncio.to_thread(
            pipelines.add_pipeline,
            k8s_name,
            payload.deploy_model,
            payload.register_model
        )
        
        logger.info(f"Added pipeline {k8s_name}, {pipeline_id=}")
        
        return JSONResponse(
            content={
                "status": "ok",
                "pipeline_name": k8s_name,
                "pipeline_id": pipeline_id,
                "deploy_model": payload.deploy_model,
                "register_model": payload.register_model
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/status")
async def get_pipeline_status(pipeline_name: str):
    """
    Get the status of a pipeline.
    
    Args:
        pipeline_name: Name of the pipeline to check
    
    Returns the latest run state.
    """
    try:
        k8s_name = k8s.normalize_name(pipeline_name)
        state = await asyncio.to_thread(
            pipelines.get_latest_run_state,
            pipeline_name=k8s_name
        )
        logger.info(f"Returning state {state} for {pipeline_name=} {k8s_name=}")
        return JSONResponse(content={"state": state})
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.delete("/delete")
async def delete_pipeline(pipeline_name: str):
    """
    Delete a pipeline and its resources.
    
    Args:
        pipeline_name: Name of the pipeline to delete
    
    Returns deletion status.
    """
    try:
        k8s_name = k8s.normalize_name(pipeline_name)
        ret = await asyncio.to_thread(
            pipelines.delete_pipeline,
            pipeline_name=k8s_name
        )
        success = await asyncio.to_thread(
            k8s.delete_k8s_secret,
            secret_name=k8s_name
        )
        logger.info(f"Deleted pipeline {pipeline_name} {k8s_name=} {success=}")
        return JSONResponse(content={"deleted": True, "secret_deleted": success})
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post("/cleanup")
async def cleanup_deployment(payload: CleanupRequest = Body(...)):
    """
    Clean up deployment resources.
    
    This endpoint removes:
    - InferenceService
    - ServingRuntime
    - Secrets
    - RBAC resources
    - MinIO resources (optional)
    """
    try:
        from .models import PipelineConfig
        
        cleanup_config = PipelineConfig(
            name=payload.name,
            namespace=payload.namespace,
            cleanup_on_failure=payload.cleanup_minio
        )
        
        k8s_name = k8s.normalize_name(f"{payload.name}-cleanup")
        
        pipeline_id = await asyncio.to_thread(
            pipelines.add_cleanup_pipeline,
            k8s_name
        )
        
        logger.info(f"Started cleanup pipeline {k8s_name}, {pipeline_id=}")
        
        return JSONResponse(
            content={
                "status": "ok",
                "pipeline_name": k8s_name,
                "pipeline_id": pipeline_id
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/models")
async def list_models(namespace: Optional[str] = None):
    """
    List deployed InferenceServices.
    
    Args:
        namespace: Kubernetes namespace (optional)
    
    Returns list of deployed models.
    """
    try:
        from kubernetes import client, config
        
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        custom_api = client.CustomObjectsApi()
        
        ns = namespace or k8s.get_incluster_namespace("spending-transaction-monitor")
        
        result = custom_api.list_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=ns,
            plural="inferenceservices"
        )
        
        models = []
        for item in result.get('items', []):
            metadata = item.get('metadata', {})
            status = item.get('status', {})
            
            models.append({
                "name": metadata.get('name'),
                "namespace": metadata.get('namespace'),
                "url": status.get('url'),
                "ready": any(
                    c.get('type') == 'Ready' and c.get('status') == 'True'
                    for c in status.get('conditions', [])
                ),
                "annotations": metadata.get('annotations', {})
            })
        
        return JSONResponse(content={"models": models})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

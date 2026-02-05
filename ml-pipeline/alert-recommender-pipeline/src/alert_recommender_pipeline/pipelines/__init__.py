"""Pipeline management for Alert Recommender Pipeline."""

import logging
import os
import tempfile
import time

from kfp import Client, compiler

from . import pipelines

logger = logging.getLogger(__name__)


def add_pipeline(pipeline_name: str, deploy_model: bool = True, register_model: bool = False):
    """Add and run the alert recommender pipeline."""
    logger.info(f"Creating pipeline: {pipeline_name}, deploy={deploy_model}, register={register_model}")
    
    pipeline_params = {
        "pipeline_name": pipeline_name,
        "minio_endpoint": os.environ.get("MINIO_ENDPOINT", ""),
        "deploy_model": str(deploy_model).lower(),
        "register_model": str(register_model).lower(),
        "model_registry_url": os.environ.get("MODEL_REGISTRY_URL", ""),
    }
    
    with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp:
        compiler.Compiler().compile(
            pipeline_func=pipelines.alert_recommender_pipeline(**pipeline_params),
            package_path=tmp.name,
        )
        tmp.flush()
        
        # Connect to KFP
        client = Client(
            host=os.environ["DS_PIPELINE_URL"],
            verify_ssl=False
        )
        
        # Upload pipeline
        pipeline_id = client.get_pipeline_id(pipeline_name)
        
        experiments = client.list_experiments()
        experiment_id = experiments.experiments[0].experiment_id
        
        if pipeline_id is None:
            uploaded_pipeline = client.upload_pipeline(
                pipeline_package_path=tmp.name,
                pipeline_name=pipeline_name,
            )
            pipeline_id = uploaded_pipeline.pipeline_id
            versions = client.list_pipeline_versions(pipeline_id)
            version_id = [v.pipeline_version_id for v in versions.pipeline_versions if v.display_name == pipeline_name][0]
        else:
            version_name = f"{pipeline_name}-{time.strftime('%Y%m%d-%H%M%S')}"
            uploaded_pipeline = client.upload_pipeline_version(
                pipeline_package_path=tmp.name,
                pipeline_id=pipeline_id,
                pipeline_version_name=version_name,
            )
            version_id = uploaded_pipeline.pipeline_version_id
    
    run = client.run_pipeline(
        pipeline_id=pipeline_id,
        version_id=version_id,
        experiment_id=experiment_id,
        job_name=f"{pipeline_name}-run"
    )
    
    logger.info(f"Pipeline submitted! Run ID: {run.run_id}")
    return pipeline_id


def get_pipeline_runs(client: Client, pipeline_name: str):
    """Get all runs for a pipeline."""
    pipeline_id = client.get_pipeline_id(pipeline_name)
    logger.info(f"Found {pipeline_id=} for {pipeline_name=}")
    if pipeline_id is None:
        raise LookupError(f"Pipeline {pipeline_name} not found")
    
    pipeline_runs = []
    next_page_token = ""
    
    while True:
        response = client.list_runs(page_token=next_page_token)
        runs = response.runs or []
        filtered_runs = [
            run for run in runs
            if run.pipeline_version_reference and run.pipeline_version_reference.pipeline_id == pipeline_id
        ]
        pipeline_runs.extend(filtered_runs)
        if not response.next_page_token:
            break
        next_page_token = response.next_page_token
    
    logger.info(f"Collected runs: {[run.run_id for run in pipeline_runs]} for {pipeline_id=}")
    return pipeline_id, sorted(pipeline_runs, key=lambda r: r.created_at, reverse=True)


def get_latest_run_state(pipeline_name: str) -> str:
    """Get the state of the latest pipeline run."""
    logger.info(f"Pipeline status: {pipeline_name}")
    client = Client(
        host=os.environ["DS_PIPELINE_URL"],
        verify_ssl=False
    )
    
    _, runs = get_pipeline_runs(client=client, pipeline_name=pipeline_name)
    latest_run = runs[0] if runs else None
    return latest_run.state.lower() if latest_run else "unknown"


def delete_pipeline(pipeline_name: str):
    """Delete a pipeline and all its runs."""
    logger.info(f"Delete pipeline: {pipeline_name}")
    client = Client(
        host=os.environ["DS_PIPELINE_URL"],
        verify_ssl=False
    )
    
    pipeline_id, runs = get_pipeline_runs(client=client, pipeline_name=pipeline_name)
    for run in runs:
        logger.info(f"Deleting run {run.run_id}")
        client.delete_run(run.run_id)
    
    next_page_token = ""
    while True:
        response = client.list_pipeline_versions(
            pipeline_id=pipeline_id,
            page_token=next_page_token
        )
        
        for version in response.pipeline_versions or []:
            logger.info(f"Deleting pipeline version {version.pipeline_version_id}")
            client.delete_pipeline_version(
                pipeline_id=pipeline_id,
                pipeline_version_id=version.pipeline_version_id
            )
        
        if not response.next_page_token:
            break
        next_page_token = response.next_page_token
    
    return client.delete_pipeline(pipeline_id=pipeline_id)

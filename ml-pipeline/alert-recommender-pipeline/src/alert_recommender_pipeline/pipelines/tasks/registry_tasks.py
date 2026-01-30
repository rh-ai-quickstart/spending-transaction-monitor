"""Model registry task for Alert Recommender Pipeline."""

import os
from kfp import dsl
from kfp.dsl import Input, Artifact

from .constants import BASE_IMAGE


@dsl.component(base_image=BASE_IMAGE)
def register_model(input_artifact: Input[Artifact]):
    """
    Register the model with the Model Registry.
    
    This task:
    1. Connects to the Model Registry
    2. Creates or finds the registered model
    3. Creates a new model version
    4. Creates a model artifact with storage URI
    
    Inputs:
        input_artifact: Artifact from save_model containing vars.json
    """
    import os
    import json
    import requests
    
    # Configuration
    model_registry_url = os.getenv('MODEL_REGISTRY_URL', '')
    model_registry_enabled = os.getenv('MODEL_REGISTRY_ENABLED', 'false').lower() == 'true'
    
    if not model_registry_enabled or not model_registry_url:
        print("Model registry not enabled or URL not configured. Skipping registration.")
        return
    
    # Load deployment variables
    vars_path = os.path.join(input_artifact.path, 'vars.json')
    with open(vars_path, 'r') as f:
        vars_data = json.load(f)
    
    model_name = vars_data['model_name']
    model_version = vars_data['model_version']
    s3_bucket = vars_data['s3_bucket']
    s3_model_path = vars_data['s3_model_path']
    
    print(f"Registering model with Model Registry:")
    print(f"  URL: {model_registry_url}")
    print(f"  Model: {model_name}")
    print(f"  Version: {model_version}")
    
    # Model Registry API base path
    api_base = f"{model_registry_url}/api/model_registry/v1alpha3"
    
    try:
        # Step 1: Check if model exists
        print(f"Searching for existing registered model: {model_name}")
        response = requests.get(
            f"{api_base}/registered_model",
            params={"name": model_name}
        )
        
        registered_model_id = None
        if response.status_code == 200:
            registered_model = response.json()
            registered_model_id = registered_model.get('id')
            model_state = registered_model.get('state', 'UNKNOWN')
            if registered_model_id:
                print(f"Found existing model: {registered_model_id} (state: {model_state})")
                
                # If model is ARCHIVED, update it to LIVE
                if model_state == 'ARCHIVED':
                    print(f"Model is ARCHIVED, updating to LIVE state...")
                    patch_response = requests.patch(
                        f"{api_base}/registered_models/{registered_model_id}",
                        json={"state": "LIVE"},
                        headers={"Content-Type": "application/json"}
                    )
                    if patch_response.ok:
                        print(f"Successfully updated model state to LIVE")
                    else:
                        print(f"Warning: Failed to update model state: {patch_response.status_code}")
                        print(f"Response: {patch_response.text}")
            else:
                print(f"Warning: Model found but 'id' field is missing. Response: {registered_model}")
        elif response.status_code == 404:
            print(f"Model '{model_name}' not found, will create new")
        else:
            print(f"Unexpected response when searching for model: {response.status_code}")
            print(f"Response body: {response.text}")
        
        # Step 2: Create new model if not found
        if not registered_model_id:
            print(f"Creating new registered model: {model_name}")
            create_payload = {
                "name": model_name,
                "state": "LIVE",
                "description": "KNN-based collaborative filtering model for alert recommendations",
                "customProperties": {
                    "framework": {"metadataType": "MetadataStringValue", "string_value": "sklearn"},
                    "algorithm": {"metadataType": "MetadataStringValue", "string_value": "KNN"},
                    "task": {"metadataType": "MetadataStringValue", "string_value": "recommendation"}
                }
            }
            print(f"Create payload: {json.dumps(create_payload, indent=2)}")
            
            create_response = requests.post(
                f"{api_base}/registered_models",
                json=create_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not create_response.ok:
                print(f"Failed to create registered model: {create_response.status_code}")
                print(f"Response body: {create_response.text}")
                create_response.raise_for_status()
            
            registered_model_id = create_response.json().get('id')
            if not registered_model_id:
                print(f"Error: Created model but 'id' field is missing. Response: {create_response.json()}")
                return
            print(f"Created new model: {registered_model_id}")
        
        # Step 3: Get MinIO endpoint for storage info
        namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
        minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
        
        # Step 4: Check if model version already exists
        print(f"Checking for existing version: {model_version}")
        versions_response = requests.get(
            f"{api_base}/registered_models/{registered_model_id}/versions"
        )
        
        version_id = None
        if versions_response.ok:
            existing_versions = versions_response.json().get('items', [])
            for v in existing_versions:
                if v.get('name') == model_version:
                    version_id = v['id']
                    print(f"Found existing version '{model_version}': {version_id}")
                    break
        
        # Step 5: Create model version if not found
        if version_id is None:
            version_payload = {
                "name": model_version,
                "registeredModelId": registered_model_id,
                "customProperties": {
                    "storage_uri": {"metadataType": "MetadataStringValue", "string_value": f"s3://{s3_bucket}/{s3_model_path}"},
                    "model_format": {"metadataType": "MetadataStringValue", "string_value": "joblib"},
                    "minio_endpoint": {"metadataType": "MetadataStringValue", "string_value": minio_endpoint}
                }
            }
            print(f"Creating model version with payload: {json.dumps(version_payload, indent=2)}")
            
            version_response = requests.post(
                f"{api_base}/registered_models/{registered_model_id}/versions",
                json=version_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not version_response.ok:
                print(f"Version creation failed: {version_response.status_code}")
                print(f"Response body: {version_response.text}")
                version_response.raise_for_status()
            
            version_id = version_response.json().get('id')
            if not version_id:
                print(f"Error: Created version but 'id' field is missing. Response: {version_response.json()}")
                return
            print(f"Created model version: {version_id}")
        
        # Step 6: Check if artifact already exists
        artifact_name = f"{model_name}-{model_version}"
        print(f"Checking for existing artifact: {artifact_name}")
        
        artifacts_response = requests.get(
            f"{api_base}/model_versions/{version_id}/artifacts"
        )
        
        artifact_id = None
        if artifacts_response.ok:
            existing_artifacts = artifacts_response.json().get('items', [])
            for a in existing_artifacts:
                if a.get('name') == artifact_name:
                    artifact_id = a['id']
                    print(f"Found existing artifact '{artifact_name}': {artifact_id}")
                    break
        
        # Step 7: Create model artifact if not found
        if artifact_id is None:
            artifact_payload = {
                "name": artifact_name,
                "uri": f"s3://{s3_bucket}/{s3_model_path}model.joblib",
                "modelFormatName": "sklearn",
                "modelFormatVersion": "1.0",
                "artifactType": "model-artifact"
            }
            print(f"Creating model artifact with payload: {json.dumps(artifact_payload, indent=2)}")
            
            artifact_response = requests.post(
                f"{api_base}/model_versions/{version_id}/artifacts",
                json=artifact_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not artifact_response.ok:
                print(f"Artifact creation failed: {artifact_response.status_code}")
                print(f"Response body: {artifact_response.text}")
                artifact_response.raise_for_status()
            
            artifact_id = artifact_response.json().get('id')
            if not artifact_id:
                print(f"Warning: Created artifact but 'id' field is missing. Response: {artifact_response.json()}")
            else:
                print(f"Created model artifact: {artifact_id}")
        
        print("Model registration complete!")
        
    except Exception as e:
        print(f"Error registering model: {e}")
        # Don't fail the pipeline if registration fails
        print("Continuing without model registration...")

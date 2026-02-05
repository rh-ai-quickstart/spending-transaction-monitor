"""Kubernetes utilities for Alert Recommender Pipeline."""

import base64
import re
from typing import Optional

from kubernetes import client
from kubernetes import config as k8s_config

from .models import PipelineConfig


def normalize_name(name: str, max_length: int = 253) -> str:
    """Normalize a string to be Kubernetes-compliant."""
    name = name.lower()
    name = re.sub(r'[^a-z0-9-]', '-', name)
    name = re.sub(r'-+', '-', name)
    if len(name) > max_length:
        name = name[:max_length].rstrip('-')
    name = re.sub(r'^[^a-z0-9]+', '', name)
    name = re.sub(r'[^a-z0-9]+$', '', name)
    return name


def get_incluster_namespace(default: str = "default") -> str:
    """Get the namespace when running in-cluster."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except Exception:
        return default


def load_k8s_config():
    """Load Kubernetes configuration (in-cluster or kubeconfig)."""
    try:
        k8s_config.load_incluster_config()
    except Exception:
        k8s_config.load_kube_config()


def config_to_k8s_secret(pipeline_config, namespace: Optional[str] = None) -> client.V1Secret:
    """Convert PipelineConfig or PipelineRequest to a Kubernetes Secret."""
    namespace = namespace or get_incluster_namespace()
    
    config_data = pipeline_config.model_dump() if hasattr(pipeline_config, 'model_dump') else pipeline_config.dict()
    
    encoded_data = {
        k.upper(): base64.b64encode(str(v).encode()).decode()
        for k, v in config_data.items()
        if not isinstance(v, (list, dict, bool)) or isinstance(v, bool)
    }
    
    model_registry_enabled = getattr(pipeline_config, 'model_registry_enabled', 
                                     getattr(pipeline_config, 'register_model', False))
    deploy_model = getattr(pipeline_config, 'deploy_model', True)
    deploy_from_registry = getattr(pipeline_config, 'deploy_from_registry', False)
    create_serving_runtime = getattr(pipeline_config, 'create_serving_runtime', False)
    
    encoded_data['MODEL_REGISTRY_ENABLED'] = base64.b64encode(
        str(model_registry_enabled).lower().encode()
    ).decode()
    encoded_data['DEPLOY_MODEL'] = base64.b64encode(
        str(deploy_model).lower().encode()
    ).decode()
    encoded_data['DEPLOY_FROM_REGISTRY'] = base64.b64encode(
        str(deploy_from_registry).lower().encode()
    ).decode()
    encoded_data['CREATE_SERVING_RUNTIME'] = base64.b64encode(
        str(create_serving_runtime).lower().encode()
    ).decode()
    
    return client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=normalize_name(pipeline_config.pipeline_name()),
            namespace=namespace
        ),
        type="Opaque",
        data=encoded_data,
    )


def apply_config_as_secret(pipeline_config, namespace: Optional[str] = None, replace: bool = False) -> str:
    """Apply pipeline configuration as a Kubernetes Secret."""
    load_k8s_config()
    
    secret = config_to_k8s_secret(pipeline_config, namespace)
    
    api = client.CoreV1Api()
    try:
        api.create_namespaced_secret(
            namespace=secret.metadata.namespace,
            body=secret
        )
        return secret.metadata.name
    except client.exceptions.ApiException as e:
        if e.status == 409 and replace:
            api.replace_namespaced_secret(
                name=secret.metadata.name,
                namespace=secret.metadata.namespace,
                body=secret
            )
            return secret.metadata.name
        else:
            raise


def delete_k8s_secret(secret_name: str, namespace: Optional[str] = None) -> bool:
    """Delete a Kubernetes Secret."""
    load_k8s_config()
    
    namespace = namespace or get_incluster_namespace()
    
    api = client.CoreV1Api()
    try:
        api.delete_namespaced_secret(name=secret_name, namespace=namespace)
        return True
    except client.exceptions.ApiException:
        import traceback
        traceback.print_exc()
        return False


def create_service_account_with_secret(
    name: str,
    namespace: str,
    secret_name: str = "storage-config"
) -> str:
    """Create a ServiceAccount with a storage secret attached."""
    load_k8s_config()
    
    api = client.CoreV1Api()
    
    service_account = client.V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace
        ),
        secrets=[client.V1ObjectReference(name=secret_name)]
    )
    
    try:
        api.create_namespaced_service_account(namespace, service_account)
        return name
    except client.exceptions.ApiException as e:
        if e.status == 409:
            api.patch_namespaced_service_account(
                name=name,
                namespace=namespace,
                body=service_account
            )
            return name
        else:
            raise


def create_inference_service(
    name: str,
    namespace: str,
    bucket: str,
    model_path: str,
    serving_runtime: str = "mlserver-sklearn",
    service_account_name: str = None,
    min_replicas: int = 1,
    max_replicas: int = 3
) -> dict:
    """Create an InferenceService specification."""
    sa_name = service_account_name or f"{name}-sa"
    
    return {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "annotations": {
                "serving.kserve.io/deploymentMode": "RawDeployment"
            }
        },
        "spec": {
            "predictor": {
                "minReplicas": min_replicas,
                "maxReplicas": max_replicas,
                "serviceAccountName": sa_name,
                "model": {
                    "modelFormat": {
                        "name": "sklearn"
                    },
                    "runtime": serving_runtime,
                    "storageUri": f"s3://{bucket}/{model_path}"
                }
            }
        }
    }


def create_serving_runtime(
    namespace: str, 
    name: str = "alert-recommender-runtime",
    image: str = None
) -> dict:
    """Create a ServingRuntime specification for MLServer sklearn."""
    import os
    
    runtime_image = image or os.getenv(
        'SERVING_RUNTIME_IMAGE',
        'docker.io/seldonio/mlserver:1.7.0-sklearn'
    )
    
    return {
        "apiVersion": "serving.kserve.io/v1alpha1",
        "kind": "ServingRuntime",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "annotations": {
                "openshift.io/display-name": "MLServer SKLearn Runtime",
                "opendatahub.io/apiProtocol": "REST"
            }
        },
        "spec": {
            "supportedModelFormats": [
                {
                    "name": "sklearn",
                    "version": "1",
                    "autoSelect": True
                }
            ],
            "protocolVersions": ["v2"],
            "multiModel": False,
            "containers": [
                {
                    "name": "kserve-container",
                    "image": runtime_image,
                    "imagePullPolicy": "Always",
                    "env": [
                        {"name": "MLSERVER_MODEL_IMPLEMENTATION", "value": "mlserver_sklearn.SKLearnModel"},
                        {"name": "MLSERVER_HTTP_PORT", "value": "8080"},
                        {"name": "MLSERVER_GRPC_PORT", "value": "8081"},
                        {"name": "MLSERVER_MODEL_URI", "value": "/mnt/models"},
                        {"name": "MLSERVER_LOAD_MODELS_AT_STARTUP", "value": "true"}
                    ],
                    "ports": [
                        {"containerPort": 8080, "name": "http", "protocol": "TCP"},
                        {"containerPort": 8081, "name": "grpc", "protocol": "TCP"}
                    ],
                    "resources": {
                        "requests": {"cpu": "500m", "memory": "512Mi"},
                        "limits": {"cpu": "1", "memory": "1Gi"}
                    }
                }
            ]
        }
    }

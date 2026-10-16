"""Model deployment task for Alert Recommender Pipeline."""

from kfp import dsl
from kfp.dsl import Input, Artifact

from .constants import BASE_IMAGE


@dsl.component(base_image=BASE_IMAGE)
def deploy_model(input_artifact: Input[Artifact]):
    """
    Deploy the model as an InferenceService on OpenShift AI.
    
    This task can deploy from two sources:
    1. Pipeline artifact (default) - uses vars.json from save_model task
    2. Model Registry - fetches model info from the registry
    
    Set DEPLOY_FROM_REGISTRY=true to deploy the latest version from Model Registry.
    
    Inputs:
        input_artifact: Artifact from save_model containing vars.json
    """
    import os
    import json
    import time
    import requests
    from urllib.parse import urlparse
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    
    def load_config():
        """Load deployment configuration from environment variables."""
        namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
        return {
            'namespace': namespace,
            'deploy_enabled': os.getenv('DEPLOY_MODEL', 'true').lower() == 'true',
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'serving_runtime': os.getenv('SERVING_RUNTIME', 'alert-recommender-runtime'),
            'create_serving_runtime': os.getenv('CREATE_SERVING_RUNTIME', 'false').lower() == 'true',
            'runtime_image': os.getenv('SERVING_RUNTIME_IMAGE', 'docker.io/seldonio/mlserver:1.7.0-sklearn'),
            'deploy_from_registry': os.getenv('DEPLOY_FROM_REGISTRY', 'false').lower() == 'true',
            'model_registry_url': os.getenv('MODEL_REGISTRY_URL', ''),
            'model_registry_ca_bundle': os.getenv('MODEL_REGISTRY_CA_BUNDLE', ''),
            'model_registry_token_file': os.getenv(
                'MODEL_REGISTRY_TOKEN_FILE',
                '/var/run/secrets/kubernetes.io/serviceaccount/token',
            ),
            'model_name_override': os.getenv('MODEL_NAME', 'alert-recommender'),
            'model_version_override': os.getenv('MODEL_VERSION_TO_DEPLOY', ''),
            'default_s3_endpoint_url': os.getenv('S3_ENDPOINT_URL', f'http://s4.{namespace}.svc.cluster.local:7480'),
            's3_region': os.getenv('S3_REGION', 'us-east-1'),
        }
    
    def load_model_info_from_registry(cfg):
        """Fetch model deployment info from Model Registry."""
        api_base = f"{cfg['model_registry_url']}/api/model_registry/v1alpha3"
        model_name = cfg['model_name_override']
        version_override = cfg['model_version_override']
        
        print(f"Deploying from Model Registry:")
        print(f"  Registry URL: {cfg['model_registry_url']}")
        print(f"  Model Name: {model_name}")
        print(f"  Version: {version_override or 'latest'}")

        request_options = {'timeout': (5, 30)}
        if cfg['model_registry_ca_bundle']:
            request_options['verify'] = cfg['model_registry_ca_bundle']
        try:
            with open(cfg['model_registry_token_file'], 'r') as token_file:
                token = token_file.read().strip()
        except OSError as exc:
            raise RuntimeError('Model Registry service-account token is unavailable') from exc
        if not token:
            raise RuntimeError('Model Registry service-account token is empty')
        headers = {'Authorization': f'Bearer {token}'}
        
        # Get registered model
        print(f"Searching for registered model: {model_name}")
        response = requests.get(
            f"{api_base}/registered_model",
            params={"name": model_name},
            headers=headers,
            **request_options,
        )
        
        if response.status_code == 404:
            raise RuntimeError(f"Model '{model_name}' not found in registry")
        response.raise_for_status()
        
        registered_model = response.json()
        registered_model_id = registered_model.get('id')
        if not registered_model_id:
            raise RuntimeError(f"Model found but 'id' field is missing. Response: {registered_model}")
        print(f"Found registered model: {registered_model_id}")
        
        # Get model versions
        versions_response = requests.get(
            f"{api_base}/registered_models/{registered_model_id}/versions",
            headers=headers,
            **request_options,
        )
        if not versions_response.ok:
            print(f"Failed to get versions: {versions_response.status_code}")
            versions_response.raise_for_status()
        
        versions = versions_response.json().get('items', [])
        print(f"Found {len(versions)} versions")
        
        if not versions:
            raise RuntimeError(f"No versions found for model '{model_name}'")
        
        # Find requested version or use latest
        target_version = find_model_version(versions, version_override)
        model_version = target_version['name']
        version_id = target_version['id']
        print(f"Using version: {model_version} (id: {version_id})")
        
        # Extract storage info
        storage_uri, s3_endpoint_url = extract_storage_info(
            api_base, target_version, version_id, headers, request_options
        )
        
        if not storage_uri:
            raise RuntimeError("Could not find storage URI in model registry")
        
        # Parse storage URI (format: s3://bucket/path/)
        bucket, model_path = parse_s3_uri(storage_uri)
        
        # Use S4-backed S3 storage endpoint from registry or default
        if not s3_endpoint_url:
            s3_endpoint_url = cfg['default_s3_endpoint_url']
        
        print(f"Resolved deployment info from registry:")
        print(f"  Bucket: {bucket}, Path: {model_path}")
        print(f"  S4-backed S3 storage Endpoint: {s3_endpoint_url}")
        
        return {
            'model_name': model_name,
            'model_version': model_version,
            'bucket': bucket,
            'model_path': model_path,
            's3_endpoint_url': s3_endpoint_url,
        }
    
    def find_model_version(versions, version_override):
        """Find specific version or return latest."""
        if version_override:
            for v in versions:
                if v['name'] == version_override:
                    return v
            raise RuntimeError(f"Version '{version_override}' not found")
        # Return latest version
        return sorted(versions, key=lambda x: x.get('createTimeSinceEpoch', '0'), reverse=True)[0]
    
    def extract_storage_info(api_base, target_version, version_id, headers, request_options):
        """Extract storage URI and S4-backed S3 storage endpoint from version metadata."""
        custom_props = target_version.get('customProperties', {})
        storage_uri = custom_props.get('storage_uri', {}).get('string_value', '')
        s3_endpoint_url = custom_props.get('s3_endpoint_url', {}).get('string_value', '')
        
        if not storage_uri:
            # Try to get from model artifact
            artifacts_response = requests.get(
                f"{api_base}/model_versions/{version_id}/artifacts",
                headers=headers,
                **request_options,
            )
            if artifacts_response.ok:
                artifacts = artifacts_response.json().get('items', [])
                print(f"Found {len(artifacts)} artifacts")
                if artifacts:
                    storage_uri = artifacts[0].get('uri', '')
        
        return storage_uri, s3_endpoint_url
    
    def parse_s3_uri(storage_uri):
        """Parse S3 URI into bucket and path."""
        print(f"Storage URI: {storage_uri}")
        if not storage_uri.startswith('s3://'):
            raise RuntimeError(f"Unsupported storage URI format: {storage_uri}")
        uri_parts = storage_uri[5:].split('/', 1)
        bucket = uri_parts[0]
        model_path = uri_parts[1] if len(uri_parts) > 1 else ''
        return bucket, model_path
    
    def load_model_info_from_artifact(artifact_path, cfg):
        """Load model deployment info from pipeline artifact."""
        vars_path = os.path.join(artifact_path, 'vars.json')
        with open(vars_path, 'r') as f:
            vars_data = json.load(f)
        return {
            'model_name': vars_data['model_name'],
            'model_version': vars_data['model_version'],
            'bucket': vars_data['s3_bucket'],
            'model_path': vars_data['s3_model_path'],
            's3_endpoint_url': vars_data.get('s3_endpoint_url', cfg['default_s3_endpoint_url']),
        }
    
    def init_kubernetes_client():
        """Initialize Kubernetes API clients."""
        try:
            config.load_incluster_config()
            print("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            print("Loaded kubeconfig from local")
        return client.CoreV1Api(), client.CustomObjectsApi()
    
    def create_or_update_resource(create_fn, update_fn, resource_name):
        """Create a K8s resource, or update if it already exists."""
        try:
            create_fn()
            print(f"{resource_name} created")
        except ApiException as e:
            if e.status == 409:
                update_fn()
                print(f"{resource_name} updated")
            else:
                raise
    
    def create_storage_secret(core_v1, cfg, model_info):
        """Create the storage-config secret for S4-backed S3 storage access."""
        print("\nCreating storage-config secret...")
        
        parsed_endpoint = urlparse(model_info['s3_endpoint_url'])
        if parsed_endpoint.scheme not in ('http', 'https') or not parsed_endpoint.netloc:
            raise ValueError('S3 endpoint must be an absolute HTTP(S) URL')
        s3_host = parsed_endpoint.netloc
        use_https = '1' if parsed_endpoint.scheme == 'https' else '0'
        verify_ssl = use_https
        
        storage_config_json = json.dumps({
            "type": "s3",
            "access_key_id": cfg['aws_access_key_id'],
            "secret_access_key": cfg['aws_secret_access_key'],
            "endpoint_url": model_info['s3_endpoint_url'],
            "region": cfg['s3_region'],
            "verify_ssl": "true" if verify_ssl == '1' else "false"
        })
        
        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(
                name="storage-config",
                namespace=cfg['namespace'],
                annotations={
                    "serving.kserve.io/s3-endpoint": s3_host,
                    "serving.kserve.io/s3-usehttps": use_https,
                    "serving.kserve.io/s3-verifyssl": verify_ssl,
                    "serving.kserve.io/s3-region": cfg['s3_region']
                }
            ),
            type="Opaque",
            string_data={
                model_info['bucket']: storage_config_json,
                "AWS_ACCESS_KEY_ID": cfg['aws_access_key_id'],
                "AWS_SECRET_ACCESS_KEY": cfg['aws_secret_access_key'],
                "AWS_DEFAULT_REGION": cfg['s3_region'],
                "S3_ENDPOINT": model_info['s3_endpoint_url'],
                "S3_USE_HTTPS": use_https,
                "S3_VERIFY_SSL": verify_ssl
            }
        )
        
        create_or_update_resource(
            lambda: core_v1.create_namespaced_secret(cfg['namespace'], secret),
            lambda: core_v1.patch_namespaced_secret("storage-config", cfg['namespace'], secret),
            "Storage config secret"
        )
    
    def create_service_account(core_v1, cfg, model_name):
        """Create service account with storage secret reference."""
        sa_name = f"{model_name}-sa"
        print(f"\nCreating service account: {sa_name}...")
        
        sa = client.V1ServiceAccount(
            api_version="v1",
            kind="ServiceAccount",
            metadata=client.V1ObjectMeta(name=sa_name, namespace=cfg['namespace']),
            secrets=[client.V1ObjectReference(name="storage-config")]
        )
        
        create_or_update_resource(
            lambda: core_v1.create_namespaced_service_account(cfg['namespace'], sa),
            lambda: core_v1.patch_namespaced_service_account(sa_name, cfg['namespace'], sa),
            f"Service account {sa_name}"
        )
        return sa_name
    
    def build_serving_runtime_spec(cfg):
        """Build the ServingRuntime specification."""
        return {
            "apiVersion": "serving.kserve.io/v1alpha1",
            "kind": "ServingRuntime",
            "metadata": {
                "name": cfg['serving_runtime'],
                "namespace": cfg['namespace'],
                "annotations": {"openshift.io/display-name": "MLServer SKLearn Runtime"}
            },
            "spec": {
                "supportedModelFormats": [{"name": "sklearn", "version": "1", "autoSelect": True}],
                "protocolVersions": ["v2", "grpc-v2"],
                "multiModel": False,
                "grpcDataEndpoint": "port:8001",
                "grpcEndpoint": "port:8085",
                "containers": [{
                    "name": "kserve-container",
                    "image": cfg['runtime_image'],
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
                }]
            }
        }
    
    def create_serving_runtime(custom_api, cfg):
        """Create or update the ServingRuntime."""
        if not cfg['create_serving_runtime']:
            print(f"\nUsing existing ServingRuntime: {cfg['serving_runtime']}")
            return
        
        print(f"\nCreating ServingRuntime: {cfg['serving_runtime']}...")
        print(f"  Using image: {cfg['runtime_image']}")
        
        spec = build_serving_runtime_spec(cfg)
        
        create_or_update_resource(
            lambda: custom_api.create_namespaced_custom_object(
                group="serving.kserve.io", version="v1alpha1",
                namespace=cfg['namespace'], plural="servingruntimes", body=spec
            ),
            lambda: custom_api.patch_namespaced_custom_object(
                group="serving.kserve.io", version="v1alpha1",
                namespace=cfg['namespace'], plural="servingruntimes",
                name=cfg['serving_runtime'], body=spec
            ),
            f"ServingRuntime {cfg['serving_runtime']}"
        )
    
    def build_inference_service_spec(cfg, model_info, sa_name):
        """Build the InferenceService specification."""
        return {
            "apiVersion": "serving.kserve.io/v1beta1",
            "kind": "InferenceService",
            "metadata": {
                "name": model_info['model_name'],
                "namespace": cfg['namespace'],
                "annotations": {
                    "serving.kserve.io/deploymentMode": "RawDeployment",
                    "serving.kserve.io/storageSecretName": "storage-config",
                    "model-version": model_info['model_version']
                }
            },
            "spec": {
                "predictor": {
                    "minReplicas": 1,
                    "maxReplicas": 3,
                    "model": {
                        "modelFormat": {"name": "sklearn"},
                        "runtime": cfg['serving_runtime'],
                        "storageUri": f"s3://{model_info['bucket']}/{model_info['model_path']}",
                        "storage": {
                            "key": model_info['bucket'],
                            "parameters": {"endpoint": model_info['s3_endpoint_url'], "region": cfg['s3_region']}
                        }
                    },
                    "serviceAccountName": sa_name
                }
            }
        }
    
    def create_inference_service(custom_api, cfg, model_info, sa_name):
        """Create or update the InferenceService."""
        print("\nDeploying InferenceService...")
        
        spec = build_inference_service_spec(cfg, model_info, sa_name)
        model_name = model_info['model_name']
        
        create_or_update_resource(
            lambda: custom_api.create_namespaced_custom_object(
                group="serving.kserve.io", version="v1beta1",
                namespace=cfg['namespace'], plural="inferenceservices", body=spec
            ),
            lambda: custom_api.patch_namespaced_custom_object(
                group="serving.kserve.io", version="v1beta1",
                namespace=cfg['namespace'], plural="inferenceservices",
                name=model_name, body=spec
            ),
            "InferenceService"
        )
    
    def wait_for_inference_service(custom_api, cfg, model_name, timeout_seconds=300):
        """Wait for InferenceService to become ready."""
        print("\nWaiting for InferenceService to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                isvc = custom_api.get_namespaced_custom_object(
                    group="serving.kserve.io", version="v1beta1",
                    namespace=cfg['namespace'], plural="inferenceservices", name=model_name
                )
                
                status = isvc.get('status', {})
                for condition in status.get('conditions', []):
                    if condition['type'] == 'Ready' and condition['status'] == 'True':
                        url = status.get('url', 'N/A')
                        print(f"\nInferenceService is ready!")
                        print(f"Inference endpoint: {url}")
                        return True
                
                elapsed = int(time.time() - start_time)
                print(f"Waiting for InferenceService... ({elapsed}s)", end='\r')
                
            except ApiException:
                pass
            
            time.sleep(10)
        
        print(f"\nTimeout waiting for InferenceService to be ready")
        print(f"Check status: kubectl get isvc {model_name} -n {cfg['namespace']}")
        return False
    
    cfg = load_config()
    
    if not cfg['deploy_enabled']:
        print("Model deployment not enabled. Skipping.")
        return

    if not cfg['aws_access_key_id'] or not cfg['aws_secret_access_key']:
        raise RuntimeError('S4 credentials are missing from the pipeline task environment')
    
    if cfg['deploy_from_registry']:
        if not cfg['model_registry_url']:
            raise RuntimeError('Model Registry URL is required for deploy_from_registry')
        try:
            model_info = load_model_info_from_registry(cfg)
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch from Model Registry: {e}")
    else:
        model_info = load_model_info_from_artifact(input_artifact.path, cfg)
    
    print(f"\nDeployment configuration:")
    print(f"  Model: {model_info['model_name']}")
    print(f"  Version: {model_info['model_version']}")
    print(f"  Namespace: {cfg['namespace']}")
    print(f"  Bucket: {model_info['bucket']}")
    print(f"  Model Path: {model_info['model_path']}")
    print(f"  Serving Runtime: {cfg['serving_runtime']}")
    
    core_v1, custom_api = init_kubernetes_client()
    create_storage_secret(core_v1, cfg, model_info)
    sa_name = create_service_account(core_v1, cfg, model_info['model_name'])
    create_serving_runtime(custom_api, cfg)
    create_inference_service(custom_api, cfg, model_info, sa_name)
    if not wait_for_inference_service(custom_api, cfg, model_info['model_name']):
        raise RuntimeError(f"InferenceService {model_info['model_name']} did not become Ready")

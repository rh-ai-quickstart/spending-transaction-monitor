#!/bin/bash

# Deployment script for Alert Recommendation ML Model on OpenShift AI
# This script deploys an InferenceService using S4 installed by the Helm chart.

set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Default values
NAMESPACE="${NAMESPACE:-spending-transaction-monitor}"
BUCKET="${BUCKET:-models}"
MODEL_PATH="${MODEL_PATH:-alert-recommender/}"
MODEL_VERSION="${MODEL_VERSION:-1.0.0}"
S4_SERVICE_NAME="${S4_SERVICE_NAME:-s4}"
S4_CREDENTIALS_SECRET="${S4_CREDENTIALS_SECRET:-${S4_SERVICE_NAME}-credentials}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://${S4_SERVICE_NAME}.${NAMESPACE}.svc.cluster.local:7480}"
S3_REGION="${S3_REGION:-us-east-1}"

echo "====================================="
echo "ML Model Deployment Script"
echo "====================================="
echo "Namespace: $NAMESPACE"
echo "Bucket: $BUCKET"
echo "Model Path: $MODEL_PATH"
echo "Model Version: $MODEL_VERSION"
echo "====================================="

# Function to substitute variables in YAML templates without logging secret values.
substitute_vars() {
    local file=$1
    TEMPLATE_NAMESPACE="$NAMESPACE" \
    TEMPLATE_BUCKET="$BUCKET" \
    TEMPLATE_MODEL_PATH="$MODEL_PATH" \
    TEMPLATE_MODEL_VERSION="$MODEL_VERSION" \
    TEMPLATE_S3_ENDPOINT_URL="$S3_ENDPOINT_URL" \
    TEMPLATE_S3_REGION="$S3_REGION" \
    TEMPLATE_S4_CREDENTIALS_SECRET="$S4_CREDENTIALS_SECRET" \
    python3 - "$file" <<'PY'
import os
import sys
from pathlib import Path

content = Path(sys.argv[1]).read_text()
replacements = {
    "namespace": os.environ["TEMPLATE_NAMESPACE"],
    "bucket": os.environ["TEMPLATE_BUCKET"],
    "model_path": os.environ["TEMPLATE_MODEL_PATH"],
    "model_version": os.environ["TEMPLATE_MODEL_VERSION"],
    "s3_endpoint_url": os.environ["TEMPLATE_S3_ENDPOINT_URL"],
    "s3_region": os.environ["TEMPLATE_S3_REGION"],
    "s4_credentials_secret": os.environ["TEMPLATE_S4_CREDENTIALS_SECRET"],
}
for key, value in replacements.items():
    content = content.replace("{{ " + key + " }}", value)
print(content, end="")
PY
}

create_storage_config_secret() {
    NAMESPACE="$NAMESPACE" \
    BUCKET="$BUCKET" \
    S3_ENDPOINT_URL="$S3_ENDPOINT_URL" \
    S3_REGION="$S3_REGION" \
    AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    python3 - <<'PY' | oc apply -f -
import base64
import json
import os
from urllib.parse import urlparse

bucket = os.environ["BUCKET"]
access_key = os.environ["AWS_ACCESS_KEY_ID"]
secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
endpoint = os.environ["S3_ENDPOINT_URL"]
region = os.environ["S3_REGION"]
parsed_endpoint = urlparse(endpoint)
if parsed_endpoint.scheme not in ("http", "https") or not parsed_endpoint.netloc:
    raise ValueError("S3_ENDPOINT_URL must be an absolute HTTP(S) URL")
s3_host = parsed_endpoint.netloc
use_https = "1" if parsed_endpoint.scheme == "https" else "0"
verify_ssl = use_https
storage_config = {
    "type": "s3",
    "access_key_id": access_key,
    "secret_access_key": secret_key,
    "endpoint_url": endpoint,
    "default_bucket": bucket,
    "region": region,
    "verify_ssl": "true" if verify_ssl == "1" else "false",
}
data = {
    bucket: json.dumps(storage_config),
    "AWS_ACCESS_KEY_ID": access_key,
    "AWS_SECRET_ACCESS_KEY": secret_key,
    "AWS_DEFAULT_REGION": region,
    "S3_ENDPOINT": endpoint,
    "S3_USE_HTTPS": use_https,
    "S3_VERIFY_SSL": verify_ssl,
}
encoded = {
    key: base64.b64encode(value.encode()).decode()
    for key, value in data.items()
}
print(json.dumps({
    "apiVersion": "v1",
    "kind": "Secret",
    "metadata": {
        "name": "storage-config",
        "namespace": os.environ["NAMESPACE"],
        "annotations": {
            "serving.kserve.io/s3-endpoint": s3_host,
            "serving.kserve.io/s3-usehttps": use_https,
            "serving.kserve.io/s3-verifyssl": verify_ssl,
            "serving.kserve.io/s3-region": region,
        },
    },
    "type": "Opaque",
    "data": encoded,
}))
PY
}

# Step 1: Wait for S4 (nested or standalone Helm release)
echo ""
echo "Step 1: Waiting for S4..."
oc wait --for=condition=available --timeout=300s "deployment/$S4_SERVICE_NAME" -n "$NAMESPACE"
echo "✅ S4 is ready"

S4_CREDENTIALS_JSON="$(oc get secret "$S4_CREDENTIALS_SECRET" -n "$NAMESPACE" -o json)"
export S4_CREDENTIALS_JSON
AWS_ACCESS_KEY_ID="$(python3 -c 'import base64,json,os; print(base64.b64decode(json.loads(os.environ["S4_CREDENTIALS_JSON"])["data"]["AWS_ACCESS_KEY_ID"]).decode())')"
AWS_SECRET_ACCESS_KEY="$(python3 -c 'import base64,json,os; print(base64.b64decode(json.loads(os.environ["S4_CREDENTIALS_JSON"])["data"]["AWS_SECRET_ACCESS_KEY"]).decode())')"
unset S4_CREDENTIALS_JSON
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

# Step 2: Deploy storage-config secret
echo ""
echo "Step 2: Deploying storage-config secret..."
create_storage_config_secret
echo "✅ Storage config deployed"

# Step 3: Deploy model ServiceAccount with storage Secret
echo ""
echo "Step 3: Deploying model ServiceAccount..."
substitute_vars "$SCRIPT_DIR/service-account.yaml" | oc apply -f -
echo "✅ Model ServiceAccount deployed"

# Step 4: Deploy ServingRuntime
echo ""
echo "Step 4: Deploying ServingRuntime..."
substitute_vars "$SCRIPT_DIR/serving-runtime.yaml" | oc apply -f -
echo "✅ ServingRuntime deployed"

# Step 5: Deploy InferenceService
echo ""
echo "Step 5: Deploying InferenceService..."
substitute_vars "$SCRIPT_DIR/inference-service.yaml" | oc apply -f -
echo "✅ InferenceService deployed"

# Step 6: Wait for InferenceService to be ready
echo ""
echo "Step 6: Waiting for InferenceService to be ready..."
oc wait --for=condition=Ready --timeout=600s inferenceservice/alert-recommender -n "$NAMESPACE"

# Check status
echo ""
echo "Checking deployment status..."
oc get inferenceservice alert-recommender -n "$NAMESPACE"

echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "To check the status:"
echo "  oc get inferenceservice alert-recommender -n $NAMESPACE"
echo ""
echo "To test the service:"
echo "  oc run test-pod -n $NAMESPACE --image=registry.access.redhat.com/ubi8/ubi:latest --rm -i --restart=Never -- bash -c 'curl http://alert-recommender-predictor.$NAMESPACE.svc.cluster.local:8080/v2/models/alert-recommender'"
echo ""
echo "S4 UI:"
echo "  oc get route $S4_SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.host}'"
echo ""

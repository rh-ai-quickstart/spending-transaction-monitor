#!/bin/bash

# Deployment script for Alert Recommendation ML Model on OpenShift AI
# This script deploys MinIO and the InferenceService with dynamic variables

set -e

# Default values
NAMESPACE="${NAMESPACE:-spending-transaction-monitor}"
BUCKET="${BUCKET:-models}"
MODEL_PATH="${MODEL_PATH:-alert-recommender/}"
MODEL_VERSION="${MODEL_VERSION:-1.0.0}"

echo "====================================="
echo "ML Model Deployment Script"
echo "====================================="
echo "Namespace: $NAMESPACE"
echo "Bucket: $BUCKET"
echo "Model Path: $MODEL_PATH"
echo "Model Version: $MODEL_VERSION"
echo "====================================="

# Function to substitute variables in YAML files
substitute_vars() {
    local file=$1
    sed -e "s|{{ namespace }}|$NAMESPACE|g" \
        -e "s|{{ bucket }}|$BUCKET|g" \
        -e "s|{{ model_path }}|$MODEL_PATH|g" \
        -e "s|{{ model_version }}|$MODEL_VERSION|g" \
        "$file"
}

# Step 1: Deploy MinIO
echo ""
echo "Step 1: Deploying MinIO..."
substitute_vars minio.yaml | oc apply -f -
echo "✅ MinIO deployed"

# Step 2: Wait for MinIO to be ready
echo ""
echo "Step 2: Waiting for MinIO to be ready..."
oc wait --for=condition=available --timeout=300s deployment/minio -n $NAMESPACE
echo "✅ MinIO is ready"

# Step 3: Deploy storage-config secret
echo ""
echo "Step 3: Deploying storage-config secret..."
substitute_vars storage-config.yaml.template | oc apply -f -
echo "✅ Storage config deployed"

# Step 4: Deploy ServingRuntime
echo ""
echo "Step 4: Deploying ServingRuntime..."
substitute_vars serving-runtime.yaml | oc apply -f -
echo "✅ ServingRuntime deployed"

# Step 5: Deploy InferenceService
echo ""
echo "Step 5: Deploying InferenceService..."
substitute_vars inference-service.yaml | oc apply -f -
echo "✅ InferenceService deployed"

# Step 6: Wait for InferenceService to be ready
echo ""
echo "Step 6: Waiting for InferenceService to be ready..."
echo "This may take a few minutes..."
sleep 30

# Check status
echo ""
echo "Checking deployment status..."
oc get inferenceservice alert-recommender -n $NAMESPACE

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
echo "MinIO UI:"
echo "  oc get route minio-ui -n $NAMESPACE -o jsonpath='{.spec.host}'"
echo ""

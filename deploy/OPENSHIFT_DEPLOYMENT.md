# OpenShift Deployment Guide

This guide provides instructions for deploying the Spending Transaction Monitor application to OpenShift using Helm charts.

## Prerequisites

- OpenShift cluster access with project admin permissions
- Helm 3.x installed
- Docker images built and pushed to your container registry (quay.io/rh-ai-quickstart)
- OpenShift CLI (`oc`) configured and logged in

## Quick Start

1. **Create or switch to your OpenShift project:**
   ```bash
   oc new-project spending-monitor
   # or
   oc project spending-monitor
   ```

2. **Deploy the application with nginx reverse proxy (recommended):**
   ```bash
   helm install spending-monitor ./deploy/helm/spending-monitor \
     --set nginx.enabled=true \
     --namespace spending-monitor
   ```

3. **Get the application URL:**
   ```bash
   oc get routes -n spending-monitor
   # Access everything through the single nginx route:
   # UI: https://<nginx-route>
   # API: https://<nginx-route>/api/
   # Health: https://<nginx-route>/health
   ```

## Detailed Deployment Steps

### 1. Build and Push Docker Images

First, build and push the Docker images to your container registry:

```bash
# Build and tag images
make docker-build-all

# Push to registry (adjust registry URLs as needed)
docker push quay.io/rh-ai-quickstart/spending-monitor-api:1.0.14
docker push quay.io/rh-ai-quickstart/spending-monitor-ui:1.0.14
docker push quay.io/rh-ai-quickstart/spending-monitor-db:1.0.14
```

### 2. Configure Values

Update the `values.yaml` file if needed:

```yaml
global:
  imageRegistry: quay.io
  imageRepository: rh-ai-quickstart
  imageTag: 1.0.0
```

### 3. Deploy with Helm

#### Option 1: Deploy with Nginx Reverse Proxy (Recommended)

```bash
# Install with nginx enabled and auto-generated hostname
helm install spending-monitor ./deploy/helm/spending-monitor \
  --set nginx.enabled=true \
  --namespace spending-monitor \
  --create-namespace

# Install with nginx enabled and custom hostname
helm install spending-monitor ./deploy/helm/spending-monitor \
  --set nginx.enabled=true \
  --set routes.nginx.host=my-custom-domain.example.com \
  --namespace spending-monitor \
  --create-namespace

# Upgrade if already exists
helm upgrade spending-monitor ./deploy/helm/spending-monitor \
  --set nginx.enabled=true \
  --namespace spending-monitor
```

#### Option 2: Deploy without Nginx (Legacy)

```bash
# Install without nginx (creates separate UI and API routes)
helm install spending-monitor ./deploy/helm/spending-monitor \
  --set nginx.enabled=false \
  --namespace spending-monitor \
  --create-namespace
```

#### Option 3: Deploy with Model Registry

```bash
# Install with model registry enabled.
# This will create a new PostgreSQL DB in the rhoai-model-registries namespace, separate from the app's main database.
helm install spending-monitor ./deploy/helm/spending-monitor \
  --set pgvector.enabled=true \
  --set model-registry.enabled=true \
  --set model-registry.postgres.enabled=true \
  --set model-registry.createService=true \
  --namespace spending-monitor \
  --create-namespace
```

### 4. Verify Deployment

```bash
# Check pod status
oc get pods -n spending-monitor

# Check services
oc get svc -n spending-monitor

# Check routes
oc get routes -n spending-monitor

# Check logs
oc logs -f deployment/spending-monitor-api -n spending-monitor
```

## Architecture

The deployment consists of four main components:

### Nginx Reverse Proxy (When Enabled)
- **Service**: `spending-monitor-nginx:8080`
- **Replicas**: 2
- **Image**: `nginx:1.25-alpine`
- **Features**: Single entry point for UI and API traffic
- **Routing**:
  - `/api/*` → API service (with `/api` prefix strip)
  - `/health` → nginx health check
  - `/*` → UI service

### Database (PostgreSQL)
- **Service**: `spending-monitor-db:5432`
- **Storage**: Persistent volume (10Gi)
- **Image**: `quay.io/rh-ai-quickstart/spending-monitor-db:1.0.0`
- **Features**: Automatic migrations and seeding

### API (FastAPI)
- **Service**: `spending-monitor-api:8000`
- **Replicas**: 2
- **Health Check**: `/health`
- **Image**: `quay.io/rh-ai-quickstart/spending-monitor-api:1.0.0`
- **Database**: Connects to PostgreSQL with async driver

### UI (React)
- **Service**: `spending-monitor-ui:8080`
- **Replicas**: 2
- **Image**: `quay.io/rh-ai-quickstart/spending-monitor-ui:1.0.0`
- **Static Files**: Served with Node.js `serve` package

## Network Configuration

### Internal Service Communication
- **Database**: `spending-monitor-db:5432`
- **API**: `spending-monitor-api:8000`
- **UI**: `spending-monitor-ui:8080`
- **Nginx**: `spending-monitor-nginx:8080` (when enabled)

### External Access (OpenShift Routes)

#### With Nginx Enabled (Recommended)
- **Single Route**: All traffic goes through nginx reverse proxy
- **Auto-generated hostname**: `spending-monitor-nginx-route-<namespace>.apps.<cluster-domain>`
- **Custom hostname**: Configure `routes.nginx.host` in values.yaml

The nginx routing is configured so that:
- UI is served at the main route: `https://<nginx-route>/`
- API endpoints are accessible at: `https://<nginx-route>/api/*`
- Nginx health check at: `https://<nginx-route>/health`
- This eliminates CORS issues and provides a single entry point

#### Without Nginx (Legacy)
- **UI Route**: Main application interface
- **API Route**: API endpoints accessible at `/api` path on the UI domain
- Creates separate routes for UI and API with path-based routing

## Environment Variables

### API Configuration
The API deployment includes all necessary environment variables:

```yaml
env:
  DATABASE_URL: postgresql+asyncpg://user:password@spending-monitor-db:5432/spending-monitor
  ENVIRONMENT: production
  NODE_ENV: production
  DEBUG: "false"
  ALLOWED_HOSTS: '["*"]'
  APP_NAME: spending-monitor
  LLM_PROVIDER: openai
  BASE_URL: https://llama-3-3-70b-instruct-w8a8-llama-3-70b-quantized.apps.ai-dev04.kni.syseng.devcluster.openshift.com/v1
  API_KEY: [Your API Key]
  MODEL: llama-3-3-70b-instruct-w8a8
```

## Security

- **Service Account**: Custom service account created for the application
- **Security Context**: Non-root user, dropped capabilities, read-only root filesystem disabled for database requirements
- **TLS**: Enabled by default on routes with edge termination
- **Network Policies**: Uses ClusterIP services for internal communication

## Persistent Storage

The PostgreSQL database uses persistent storage:

```yaml
database:
  persistence:
    enabled: true
    size: 10Gi
    accessMode: ReadWriteOnce
```

## Health Checks

All components include health checks:

- **Nginx**: HTTP GET `/health` (port 8080) - nginx health check
- **API**: HTTP GET `/health` (port 8000) - application health
- **UI**: HTTP GET `/` (port 8080) - application availability
- **Database**: PostgreSQL `pg_isready` command

## Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   oc describe pod <pod-name> -n spending-monitor
   oc logs <pod-name> -n spending-monitor
   ```

2. **Database connection issues**:
   ```bash
   oc exec -it deployment/spending-monitor-api -n spending-monitor -- bash
   # Test database connection inside the pod
   ```

3. **Image pull errors**:
   - Verify image exists in registry
   - Check image pull secrets if using private registry

4. **Route access issues**:
   ```bash
   oc get routes -n spending-monitor
   # Check if routes are properly configured
   ```

### Logs

```bash
# API logs
oc logs -f deployment/spending-monitor-api -n spending-monitor

# UI logs
oc logs -f deployment/spending-monitor-ui -n spending-monitor

# Database logs
oc logs -f deployment/spending-monitor-db -n spending-monitor
```

## Scaling

To scale the application:

```bash
# Scale nginx
oc scale deployment spending-monitor-nginx --replicas=3 -n spending-monitor

# Scale API
oc scale deployment spending-monitor-api --replicas=3 -n spending-monitor

# Scale UI
oc scale deployment spending-monitor-ui --replicas=3 -n spending-monitor
```

Or update the `values.yaml` file and run:

```bash
helm upgrade spending-monitor ./deploy/helm/spending-monitor -n spending-monitor
```

## Uninstall

To remove the application:

```bash
helm uninstall spending-monitor -n spending-monitor
```

Note: This will not delete the persistent volume. To delete it manually:

```bash
oc delete pvc spending-monitor-db-pvc -n spending-monitor
```

## Monitoring

The application includes health endpoints for monitoring:

### With Nginx Enabled
- **Nginx Health**: `https://<nginx-route>/health`
- **API Health**: `https://<nginx-route>/api/health`
- **UI Health**: `https://<nginx-route>/`

### Without Nginx
- **API Health**: `https://<ui-route>/api/health`
- **UI Health**: `https://<ui-route>/`

These can be integrated with OpenShift monitoring or external monitoring solutions.

## Benefits of Nginx Reverse Proxy

1. **Single Entry Point**: All traffic goes through one route
2. **Simplified Routing**: No need for complex path-based OpenShift routes
3. **Better Performance**: Nginx handles static content and request routing efficiently
4. **Enhanced Security**: Centralized security headers and CORS handling
5. **Environment Agnostic**: Auto-generated hostnames work across different clusters
6. **Flexibility**: Easy to modify routing rules without changing OpenShift routes
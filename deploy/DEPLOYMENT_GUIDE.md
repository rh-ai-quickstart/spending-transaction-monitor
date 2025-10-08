# Deployment Guide - Spending Transaction Monitor

This guide provides comprehensive instructions for deploying the Spending Transaction Monitor to OpenShift using Helm charts.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Deployment Options](#deployment-options)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

## 🚀 Quick Start

The fastest way to deploy to OpenShift:

```bash
# 1. Configure your production environment variables
cp env.example .env.production
# Edit .env.production with your production settings

# 2. Login to OpenShift
oc login --token=<your-token> --server=<your-server>

# 3. Deploy everything (builds, pushes, deploys)
make full-deploy
```

That's it! The `make full-deploy` command will:
- Login to the container registry
- Create the OpenShift project
- Build all container images
- Push images to the registry
- Deploy using Helm with your environment variables

## 📦 Prerequisites

Before deploying, ensure you have:

### Required Tools
- **OpenShift CLI (`oc`)** - v4.10 or later
- **Helm** - v3.8 or later
- **Podman** - v4.0 or later (for building images)
- **Make** - For using Makefile commands

### Access Requirements
- OpenShift cluster with project admin permissions
- Container registry access (default: quay.io)
- Sufficient cluster resources (see [Resource Requirements](#resource-requirements))

### Configuration Files
- `.env.production` - Production environment variables (copy from `env.example`)
- `.env.development` - Development environment variables (for local testing)

## 🏗 Architecture

The deployment consists of the following components:

### Core Services

| Component | Port | Replicas | Purpose |
|-----------|------|----------|---------|
| **Database** | 5432 | 1 | PostgreSQL database with persistent storage |
| **API** | 8000 | 1+ | FastAPI backend service |
| **Ingestion** | 8001 | 1+ | Transaction ingestion service |
| **UI** | 8080 | 1+ | React frontend application |
| **Nginx** | 8080 | 1+ | Reverse proxy (optional but recommended) |

### Resource Requirements

**Development Environment:**
```yaml
Total CPU: ~600m
Total Memory: ~1.5Gi
Storage: 10Gi (database PVC)
```

**Production Environment (recommended):**
```yaml
Total CPU: ~2000m (2 cores)
Total Memory: ~4Gi
Storage: 50Gi (database PVC)
```

## 🎯 Deployment Options

### Option 1: Complete Deployment (Recommended)

Deploy everything with a single command:

```bash
make full-deploy
```

This performs the complete workflow:
1. Authenticates with OpenShift registry
2. Creates/switches to project
3. Builds all images
4. Pushes images to registry
5. Deploys with Helm

### Option 2: Step-by-Step Deployment

For more control, execute each step individually:

```bash
# 1. Login to OpenShift
oc login

# 2. Create project
make create-project NAMESPACE=my-app

# 3. Build images
make build-all

# 4. Push to registry
make push-all

# 5. Deploy with Helm
make deploy
```

### Option 3: Development Deployment

For testing with reduced resources:

```bash
make deploy-dev
```

This deployment:
- Disables persistent storage
- Sets replicas to 1 for all services
- Uses less memory/CPU

### Option 4: Using Pre-built Images

If images are already in the registry:

```bash
# Just deploy using existing images
make deploy IMAGE_TAG=v1.0.0
```

## 🔧 Environment Configuration

### Production Environment File

Create `.env.production` from the example:

```bash
cp env.example .env.production
```

### Required Variables

Edit `.env.production` and set these critical values:

```bash
# Database
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql+asyncpg://user:<password>@spending-monitor-db:5432/spending-monitor

# API Security
API_KEY=<your-api-key>
BYPASS_AUTH=false
ENVIRONMENT=production

# LLM Configuration
LLM_PROVIDER=openai
BASE_URL=https://api.openai.com/v1
MODEL=gpt-3.5-turbo

# SMTP for Notifications
SMTP_HOST=<smtp-server>
SMTP_PORT=587
SMTP_FROM_EMAIL=<from-email>
SMTP_USE_TLS=true

# Keycloak (if using authentication)
KEYCLOAK_URL=<keycloak-url>
KEYCLOAK_REALM=spending-monitor
KEYCLOAK_CLIENT_ID=spending-monitor

# CORS
CORS_ALLOWED_ORIGINS=https://your-route-url
ALLOWED_ORIGINS=https://your-route-url
```

### Environment-Specific Settings

**Development:**
```bash
ENVIRONMENT=development
DEBUG=true
BYPASS_AUTH=true  # Optional: disable auth for testing
```

**Production:**
```bash
ENVIRONMENT=production
DEBUG=false
BYPASS_AUTH=false
```

## 📊 Makefile Commands Reference

### Building Images

```bash
make build-all          # Build all images
make build-api          # Build API only
make build-ui           # Build UI only
make build-db           # Build DB migrations only
make build-ingestion    # Build ingestion service only
```

### Pushing Images

```bash
make push-all           # Push all images
make push-api           # Push API only
make push-ui            # Push UI only
make push-db            # Push DB only
make push-ingestion     # Push ingestion service only
```

### Deployment

```bash
make deploy             # Deploy with production settings
make deploy-dev         # Deploy with dev settings (reduced resources)
make deploy-all         # Build, push, and deploy
make full-deploy        # Complete pipeline: login + build + push + deploy
```

### Undeployment

```bash
make undeploy           # Remove deployment (keeps namespace)
make undeploy-all       # Remove deployment and namespace
```

### Development & Debugging

```bash
make port-forward-api   # Forward API to localhost:8000
make port-forward-ui    # Forward UI to localhost:8080
make port-forward-db    # Forward DB to localhost:5432
make status             # Show deployment status
make logs               # Show logs from all pods
make logs-api           # Follow API logs
make logs-ui            # Follow UI logs
make logs-db            # Follow DB logs
```

### Helm Operations

```bash
make helm-lint          # Validate Helm chart
make helm-template      # Render templates (dry-run)
make helm-debug         # Debug deployment
```

### Cleanup

```bash
make clean-images       # Remove local images
make clean-all          # Remove everything (deployment + images)
```

## 🔍 Accessing Your Deployment

After deployment, get the route URL:

```bash
oc get routes -n spending-transaction-monitor
```

### With Nginx Enabled (Default)

All traffic goes through a single route:

- **UI:** `https://<nginx-route>/`
- **API:** `https://<nginx-route>/api/`
- **Health Check:** `https://<nginx-route>/health`

### Without Nginx (Legacy)

Separate routes for UI and API:

- **UI:** `https://<ui-route>/`
- **API:** `https://<ui-route>/api/`

## 🐛 Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
oc get pods -n spending-transaction-monitor

# Describe pod for details
oc describe pod <pod-name> -n spending-transaction-monitor

# Check logs
oc logs <pod-name> -n spending-transaction-monitor
```

#### 2. Database Connection Issues

```bash
# Check database pod
oc get pod -l app.kubernetes.io/component=database -n spending-transaction-monitor

# Check database logs
make logs-db

# Verify DATABASE_URL in secrets
oc get secret spending-monitor-secret -o jsonpath='{.data.DATABASE_URL}' | base64 -d
```

#### 3. Image Pull Errors

```bash
# Verify images exist in registry
podman search quay.io/rh-ai-quickstart/spending-monitor

# Check image pull secrets
oc get secrets -n spending-transaction-monitor

# Re-login to registry
make login
```

#### 4. Migration Job Fails

```bash
# Check migration job
oc get job -n spending-transaction-monitor

# View migration logs
oc logs job/spending-monitor-migration -n spending-transaction-monitor

# Delete and retry
oc delete job spending-monitor-migration -n spending-transaction-monitor
make deploy
```

#### 5. Route Not Accessible

```bash
# Verify route exists
oc get route -n spending-transaction-monitor

# Check route details
oc describe route spending-monitor-nginx-route -n spending-transaction-monitor

# Test from within cluster
oc run test-pod --image=curlimages/curl -it --rm -- curl http://spending-monitor-api:8000/health
```

### Health Checks

Test service health:

```bash
# API health
curl https://<nginx-route>/api/health

# UI health
curl https://<nginx-route>/

# Nginx health
curl https://<nginx-route>/health
```

## 📈 Scaling

### Manual Scaling

Scale individual components:

```bash
# Scale API
oc scale deployment spending-monitor-api --replicas=3

# Scale UI
oc scale deployment spending-monitor-ui --replicas=3

# Scale Ingestion
oc scale deployment spending-monitor-ingestion --replicas=2
```

### Helm-based Scaling

Update `values.yaml` and redeploy:

```yaml
api:
  replicas: 3
ui:
  replicas: 3
ingestion:
  replicas: 2
```

Then:

```bash
make deploy
```

## 🔐 Security Best Practices

1. **Secrets Management**
   - Never commit `.env.production` to git
   - Use strong passwords for database
   - Rotate API keys regularly
   - Consider using External Secrets Operator for production

2. **Network Security**
   - Keep `BYPASS_AUTH=false` in production
   - Configure proper CORS origins
   - Use TLS for all routes (enabled by default)

3. **Resource Limits**
   - Set appropriate CPU/memory limits
   - Configure resource quotas for namespace
   - Monitor resource usage

4. **Database Security**
   - Use persistent volumes for production
   - Backup database regularly
   - Restrict database access to cluster-internal only

## 🚀 Advanced Topics

### Custom Registry

Deploy with a custom registry:

```bash
make deploy \
  REGISTRY_URL=my-registry.com \
  REPOSITORY=my-org \
  IMAGE_TAG=v1.0.0
```

### Custom Namespace

Deploy to a custom namespace:

```bash
make deploy NAMESPACE=my-custom-namespace
```

### Helm Values Override

Create a custom values file and deploy:

```bash
helm upgrade --install spending-monitor ./deploy/helm/spending-monitor \
  --namespace spending-transaction-monitor \
  -f my-custom-values.yaml
```

### External Database

To use an external database, update `values.yaml`:

```yaml
database:
  enabled: false  # Disable internal database

secrets:
  DATABASE_URL: "postgresql+asyncpg://user:password@external-db:5432/spending"
```

### Monitoring Integration

The application includes health endpoints compatible with Prometheus:

- API: `/health`
- UI: `/`
- Nginx: `/health`

## 📚 Additional Resources

- [OpenShift Deployment Guide](./OPENSHIFT_DEPLOYMENT.md) - Detailed OpenShift-specific instructions
- [Nginx Configuration](./deploy-nginx.md) - Nginx reverse proxy details
- [Main README](../README.md) - Project overview and architecture
- [Contributing Guide](../CONTRIBUTING.md) - Development guidelines

## 🆘 Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs: `make logs`
3. Check deployment status: `make status`
4. Verify environment variables in `.env.production`
5. Consult the [OpenShift documentation](https://docs.openshift.com/)

## 📝 Summary

Your deployment infrastructure is production-ready with:

✅ Complete Helm chart for all services
✅ Automated build and deployment pipeline
✅ Environment-based configuration
✅ Comprehensive Makefile with 40+ commands
✅ Health checks and monitoring
✅ Security best practices
✅ Detailed documentation

**Quick Deploy:** `make full-deploy`

That's it! You're ready to deploy to OpenShift.


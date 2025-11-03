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
# 1. Configure your environment variables
cp env.example .env.production

# 2. Login to OpenShift
oc login --token=<your-token> --server=<your-server>

# 3. Deploy with Keycloak authentication
make deploy MODE=keycloak NAMESPACE=my-app

# Or deploy without auth for development/testing
make deploy MODE=noauth NAMESPACE=my-test
```

**See [QUICKSTART.md](./QUICKSTART.md) for a one-page cheat sheet.**

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
- `.env.production` - OpenShift deployment environment variables (copy from `env.example`)
- `.env.development` - Local development environment variables

## 🏗 Architecture

The deployment consists of the following components:

### Core Services

| Component | Port | Replicas | Purpose |
|-----------|------|----------|---------|
| **Database** | 5432 | 1 | PostgreSQL database with persistent storage |
| **API** | 8000 | 1+ | FastAPI backend service |
| **UI** | 8080 | 1+ | React frontend application |
| **Nginx** | 8080 | 1+ | Reverse proxy (default, recommended) |
| **Keycloak** | 8080 | 1+ | Authentication service (when MODE=keycloak) |

### Resource Requirements

**Development/Testing (MODE=noauth):**
```yaml
Total CPU: ~600m
Total Memory: ~1.5Gi
Storage: Optional (ephemeral)
```

**Authenticated Deployment (MODE=keycloak, recommended):**
```yaml
Total CPU: ~2000m (2 cores)
Total Memory: ~4Gi
Storage: 50Gi (database PVC)
```

## 🎯 Deployment Modes

The application supports three deployment modes via the `MODE` parameter:

### MODE=keycloak (Authenticated Deployment)

**Use Case:** Staging, production, or any environment requiring authentication  
**Command:** `make deploy MODE=keycloak NAMESPACE=my-app`

**Features:**
- ✅ Keycloak SSO authentication required
- ✅ Multiple replicas for high availability (API: 2, UI: 2)
- ✅ Persistent database storage (50Gi)
- ✅ Automatic user synchronization from database to Keycloak
- ✅ Full resource allocation (2 CPU cores, 4Gi memory)
- ✅ Debug mode disabled

**Prerequisites:**
- ⚠️ **Keycloak Operator must be installed** (see [KEYCLOAK_OPERATOR.md](./KEYCLOAK_OPERATOR.md))
- Configure `.env.production` with Keycloak settings

**Example:**
```bash
make deploy MODE=keycloak NAMESPACE=staging
```

---

### MODE=noauth (Development/Testing)

**Use Case:** Development, testing, demos  
**Command:** `make deploy MODE=noauth NAMESPACE=dev-test`

**Features:**
- ✅ No authentication required (bypass enabled)
- ✅ Single replicas (reduced resources)
- ✅ No persistent storage (faster cleanup)
- ✅ Debug mode enabled
- ✅ All CORS origins allowed
- ⚠️ **Not suitable for sensitive data**

**Example:**
```bash
make deploy MODE=noauth NAMESPACE=dev-test
```

---

### MODE=dev (Minimal Resources)

**Use Case:** Resource-constrained environments, local testing  
**Command:** `make deploy MODE=dev NAMESPACE=test`

**Features:**
- Reduces all replicas to 1
- Disables persistent storage
- Uses minimal CPU/memory
- Can be combined with Keycloak auth if needed

**Example:**
```bash
make deploy MODE=dev NAMESPACE=test
```

---

### Deployment Methods

#### Using Pre-built Images

If images are already in a registry:

```bash
# Deploy with specific image tag
make deploy MODE=keycloak IMAGE_TAG=v1.0.0 NAMESPACE=my-app
```

---

### Comparison Matrix

| Feature | MODE=noauth | MODE=keycloak | MODE=dev |
|---------|-------------|---------------|----------|
| **Authentication** | ❌ Disabled | ✅ Keycloak SSO | Configurable |
| **API Replicas** | 1 | 2 | 1 |
| **UI Replicas** | 1 | 2 | 1 |
| **Database Persistence** | ❌ No | ✅ Yes (50Gi) | ❌ No |
| **Keycloak** | ❌ Disabled | ✅ Enabled | Optional |
| **Debug Mode** | ✅ Yes | ❌ No | ✅ Yes |
| **Memory (Total)** | ~1.5Gi | ~4Gi | ~1Gi |
| **CPU (Total)** | ~0.6 cores | ~2 cores | ~0.4 cores |
| **Use Case** | Dev/Test/Demo | Staging/Prod | Resource-limited |

## 🔧 Environment Configuration

### OpenShift Deployment Environment File

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
ENVIRONMENT=staging  # or 'production'

# LLM Configuration
LLM_PROVIDER=openai
BASE_URL=https://api.openai.com/v1
MODEL=gpt-3.5-turbo

# SMTP for Notifications
SMTP_HOST=<smtp-server>
SMTP_PORT=587
SMTP_FROM_EMAIL=<from-email>
SMTP_USE_TLS=true

# Keycloak (for MODE=keycloak)
KEYCLOAK_URL=<keycloak-url>
KEYCLOAK_REALM=spending-monitor
KEYCLOAK_CLIENT_ID=spending-monitor

# CORS
CORS_ALLOWED_ORIGINS=https://your-route-url
ALLOWED_ORIGINS=https://your-route-url
```

### Mode-Specific Settings

**MODE=noauth (Development/Testing):**
```bash
ENVIRONMENT=development
DEBUG=true
BYPASS_AUTH=true
```

**MODE=keycloak (Staging/Production):**
```bash
ENVIRONMENT=staging  # or 'production'
DEBUG=false
BYPASS_AUTH=false
```

**Note:** The `MODE` parameter in the Makefile automatically sets `BYPASS_AUTH` in the deployment, but you can also configure it via `.env.production` for fine-grained control.

## 📊 Makefile Commands Reference

### Core Deployment Commands

```bash
# Deploy with different modes
make deploy MODE=keycloak NAMESPACE=staging # With Keycloak auth
make deploy MODE=noauth NAMESPACE=dev       # Without auth (dev/test)
make deploy MODE=dev NAMESPACE=test         # Minimal resources

# Undeploy
make undeploy NAMESPACE=my-app              # Remove deployment
make undeploy-all NAMESPACE=my-app          # Remove deployment + namespace
```

### Building & Pushing Images

```bash
make build-all          # Build all images locally
make push-all           # Push all images to registry
make deploy-all         # Build, push, and deploy
```

### Local Development

```bash
make build-run-local                # Build & run with Keycloak
make build-run-local MODE=noauth    # Build & run without auth
make setup-keycloak                 # Setup Keycloak with DB users
make stop-local                     # Stop local services
make logs-local                     # View local logs
```

### Data Management

```bash
make seed-db                      # Seed database
make seed-keycloak-with-users     # Setup Keycloak + sync users
make setup-data                   # Migrate + seed all
```

### Utilities

```bash
make status           # Show deployment status
make helm-lint        # Validate Helm chart
make helm-template    # Render templates (dry-run)
make clean-all        # Clean up all resources
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
oc scale deployment spending-monitor-api --replicas=3 -n my-namespace

# Scale UI
oc scale deployment spending-monitor-ui --replicas=3 -n my-namespace

# Scale Nginx
oc scale deployment spending-monitor-nginx --replicas=3 -n my-namespace
```

### Helm-based Scaling

Update `values.yaml` and redeploy:

```yaml
api:
  replicas: 3
ui:
  replicas: 3
nginx:
  replicas: 3
```

Then:

```bash
make deploy MODE=keycloak NAMESPACE=my-namespace
```

## 🔐 Security Best Practices

1. **Secrets Management**
   - Never commit `.env.production` to git
   - Use strong passwords for database
   - Rotate API keys regularly
   - Consider using External Secrets Operator for sensitive environments

2. **Network Security**
   - Use `MODE=keycloak` for staging and production environments
   - Never use `BYPASS_AUTH=true` with real user data
   - Configure proper CORS origins (not `*`)
   - Use TLS for all routes (enabled by default in OpenShift)

3. **Resource Limits**
   - Set appropriate CPU/memory limits
   - Configure resource quotas for namespace
   - Monitor resource usage

4. **Database Security**
   - Enable persistent volumes for long-term deployments
   - Backup database regularly
   - Restrict database access to cluster-internal only

## 🚀 Advanced Topics

### Custom Registry

Deploy with a custom registry:

```bash
make deploy MODE=keycloak \
  REGISTRY_URL=my-registry.com \
  REPOSITORY=my-org \
  IMAGE_TAG=v1.0.0 \
  NAMESPACE=my-app
```

### Custom Namespace

Deploy to a custom namespace:

```bash
make deploy MODE=keycloak NAMESPACE=my-custom-namespace
```

### Helm Values Override

Create a custom values file and deploy:

```bash
helm upgrade --install spending-monitor ./deploy/helm/spending-monitor \
  --namespace my-namespace \
  --values ./deploy/helm/spending-monitor/values-keycloak.yaml \
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

- Nginx: `https://<route>/health`
- API: `https://<route>/api/health`
- UI: `https://<route>/`

## 📚 Additional Resources

- [Quickstart Guide](./QUICKSTART.md) - One-page cheat sheet
- [Keycloak Operator Setup](./KEYCLOAK_OPERATOR.md) - Keycloak installation guide
- [Helm Chart Documentation](./helm/DEPLOYMENT.md) - Helm-specific details
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

Your deployment infrastructure includes:

✅ Complete Helm chart for all services
✅ Three deployment modes (keycloak, noauth, dev)
✅ In-cluster builds (no registry access needed)
✅ Environment-based configuration
✅ Automated database migrations and seeding
✅ Keycloak SSO with automatic user sync
✅ Health checks and monitoring
✅ Security best practices

**Quick Deploy Commands:**
```bash
# Authenticated deployment (staging/production)
make deploy MODE=keycloak NAMESPACE=staging

# Development/testing without auth
make deploy MODE=noauth NAMESPACE=dev
```

**See [QUICKSTART.md](./QUICKSTART.md) for a one-page cheat sheet.**

That's it! You're ready to deploy to OpenShift.


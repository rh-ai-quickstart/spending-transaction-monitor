# Helm Chart Deployment

This directory contains the Helm chart for deploying the Spending Monitor application to Kubernetes/OpenShift.

## 📁 Directory Structure

```
spending-monitor/
├── Chart.yaml                  # Chart metadata
├── values.yaml                 # Default configuration
├── values-dev-noauth.yaml      # Dev mode (no auth)
├── values-keycloak.yaml        # Production (Keycloak auth)
├── templates/                  # Kubernetes manifests
│   ├── api-deployment.yaml
│   ├── ui-deployment.yaml
│   ├── database-deployment.yaml
│   ├── nginx-deployment.yaml
│   ├── keycloak-cr.yaml        # Keycloak instance
│   ├── keycloak-realm-cr.yaml # Keycloak realm
│   ├── keycloak-user-sync-job.yaml
│   ├── migration-job.yaml
│   ├── routes.yaml
│   └── ...
```

## 🚀 Quick Deployment

### Using Makefile (Recommended)

From the project root:

```bash
# Deploy with Keycloak authentication
make deploy MODE=keycloak NAMESPACE=production

# Deploy without authentication (dev/test)
make deploy MODE=noauth NAMESPACE=dev-test

# Deploy with reduced resources
make deploy MODE=dev NAMESPACE=test
```

### Direct Helm Usage

```bash
# Deploy with Keycloak authentication
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace production \
  --values ./spending-monitor/values-keycloak.yaml \
  --set global.imageRegistry=quay.io \
  --set global.imageRepository=rh-ai-quickstart \
  --set global.imageTag=latest

# Deploy without authentication
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace dev-test \
  --values ./spending-monitor/values-dev-noauth.yaml \
  --set global.imageRegistry=quay.io \
  --set global.imageRepository=rh-ai-quickstart \
  --set global.imageTag=latest
```

## 📊 Configuration Files

### values.yaml (Default)
Base configuration with placeholders. Not recommended for direct use - use one of the specific values files instead.

### values-keycloak.yaml (Production)
**Use Case:** Production deployments with authentication

**Features:**
- Keycloak SSO authentication
- Multiple replicas (HA)
- Persistent storage enabled
- Production resource allocations
- Automatic user synchronization

**Prerequisites:**
- Keycloak Operator must be installed
- See [../KEYCLOAK_OPERATOR.md](../KEYCLOAK_OPERATOR.md)

### values-dev-noauth.yaml (Development)
**Use Case:** Development and testing

**Features:**
- Authentication bypass (no login)
- Single replicas
- No persistent storage
- Debug mode enabled
- Reduced resources

## 🔧 Key Configuration Options

### Global Settings

```yaml
global:
  imageRegistry: quay.io
  imageRepository: rh-ai-quickstart
  imageTag: latest
```

### Authentication Mode

```yaml
secrets:
  BYPASS_AUTH: "true"   # No auth mode
  # or
  BYPASS_AUTH: "false"  # Keycloak mode
```

### Resource Allocation

```yaml
api:
  replicas: 2
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
```

### Database Persistence

```yaml
database:
  persistence:
    enabled: true
    size: 50Gi
    storageClass: ""  # Use cluster default
```

### Keycloak Configuration

```yaml
keycloak:
  enabled: true
  replicas: 1
  adminUser: admin
  adminPassword: admin  # Change for production!
```

## 🎯 Common Customizations

### Using OpenShift Internal Registry

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace my-namespace \
  --values ./spending-monitor/values-keycloak.yaml \
  --set global.imageRegistry=image-registry.openshift-image-registry.svc:5000 \
  --set global.imageRepository=my-namespace \
  --set global.imageTag=latest
```

### Custom Image Tags

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace production \
  --values ./spending-monitor/values-keycloak.yaml \
  --set global.imageTag=v1.0.0
```

### External Database

```yaml
database:
  enabled: false  # Disable internal database

secrets:
  DATABASE_URL: "postgresql+asyncpg://user:password@external-db:5432/spending"
```

### Custom Route Hostname

```yaml
routes:
  nginx:
    enabled: true
    host: spending-monitor.example.com
```

## 🔍 Verification

### Check Deployment Status

```bash
# Get all resources
oc get all -n my-namespace

# Check pods
oc get pods -n my-namespace

# Check routes
oc get route -n my-namespace
```

### Verify Keycloak

```bash
# Check Keycloak instance
oc get keycloak -n my-namespace

# Check Keycloak realm import
oc get keycloakrealmimport -n my-namespace

# Check user sync job
oc get job -n my-namespace | grep user-sync
```

### Test Application

```bash
# Get the route
ROUTE=$(oc get route spending-monitor-nginx-route -n my-namespace -o jsonpath='{.spec.host}')

# Test API health
curl https://$ROUTE/api/health

# Test UI
curl https://$ROUTE/
```

## 🔄 Upgrades

### Upgrade with New Images

```bash
# Update with new image tag
helm upgrade spending-monitor ./spending-monitor \
  --namespace my-namespace \
  --reuse-values \
  --set global.imageTag=v1.1.0
```

### Change Configuration

```bash
# Update with new configuration
helm upgrade spending-monitor ./spending-monitor \
  --namespace my-namespace \
  --values ./spending-monitor/values-keycloak.yaml \
  --set database.persistence.size=100Gi
```

## 🧹 Cleanup

```bash
# Uninstall release (keeps PVCs)
helm uninstall spending-monitor -n my-namespace

# Delete PVC if needed
oc delete pvc spending-monitor-db-pvc -n my-namespace

# Delete namespace
oc delete project my-namespace
```

## 📚 Additional Resources

- [Complete Deployment Guide](../DEPLOYMENT_GUIDE.md) - Full deployment instructions with all modes
- [Quickstart Guide](../QUICKSTART.md) - One-page cheat sheet
- [Keycloak Operator Setup](../KEYCLOAK_OPERATOR.md) - Keycloak installation

## 🎓 Helm Commands Reference

```bash
# Lint the chart
helm lint ./spending-monitor

# Render templates (dry-run)
helm template spending-monitor ./spending-monitor \
  --values ./spending-monitor/values-keycloak.yaml \
  --debug

# Show computed values
helm get values spending-monitor -n my-namespace

# Show deployment history
helm history spending-monitor -n my-namespace

# Rollback to previous version
helm rollback spending-monitor -n my-namespace
```

---

**For Makefile commands and automated deployment, see the [root README](../../README.md) and [DEPLOYMENT_GUIDE](../DEPLOYMENT_GUIDE.md).**

# Helm Chart Reference

This directory contains the Helm chart for the Spending Monitor application.

> **Note:** For standard deployment instructions, see the main [README.md](../../README.md#-openshift-deployment)

## 📁 Chart Structure

```
spending-monitor/
├── Chart.yaml                  # Chart metadata
├── values.yaml                 # Default configuration
├── values-dev-noauth.yaml      # Dev mode (no auth)
├── values-keycloak.yaml        # Authenticated deployment
└── templates/                  # Kubernetes manifests
```

## 🚀 Quick Reference

**Using Makefile (Recommended):**
```bash
make deploy MODE=keycloak NAMESPACE=my-app
```

**Direct Helm Commands:**
```bash
# Deploy with Keycloak authentication
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace my-app \
  --values ./spending-monitor/values-keycloak.yaml

# Deploy without authentication (dev/test)
helm upgrade --install spending-monitor ./spending-monitor \
  --namespace my-app \
  --values ./spending-monitor/values-dev-noauth.yaml
```

## 🔧 Values Files

### values-keycloak.yaml
For staging/production with authentication:
- Keycloak SSO enabled
- Multiple replicas (API: 2, UI: 2)
- Persistent storage (50Gi)
- Full resource allocation

### values-dev-noauth.yaml
For development/testing without auth:
- Authentication bypassed
- Single replicas
- Ephemeral storage
- Reduced resources

## ⚙️ Advanced Configuration

### Custom Image Registry

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --set global.imageRegistry=my-registry.com \
  --set global.imageRepository=my-org \
  --set global.imageTag=v1.0.0
```

### Custom Resources

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --set api.resources.requests.cpu=500m \
  --set api.resources.requests.memory=512Mi \
  --set api.replicas=3
```

### Custom Database

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --set database.persistence.size=100Gi \
  --set database.resources.requests.memory=2Gi
```

### Keycloak Configuration

```bash
helm upgrade --install spending-monitor ./spending-monitor \
  --values ./spending-monitor/values-keycloak.yaml \
  --set keycloak.realm=my-realm \
  --set keycloak.clientId=my-client
```

## 📊 Key Configuration Options

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Container registry | `quay.io` |
| `global.imageRepository` | Repository path | `rh-ai-quickstart` |
| `global.imageTag` | Image tag | `latest` |

### API Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.replicas` | Number of replicas | `2` (keycloak) / `1` (noauth) |
| `api.resources.requests.cpu` | CPU request | `500m` |
| `api.resources.requests.memory` | Memory request | `512Mi` |

### UI Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ui.replicas` | Number of replicas | `2` (keycloak) / `1` (noauth) |
| `ui.resources.requests.cpu` | CPU request | `200m` |
| `ui.resources.requests.memory` | Memory request | `256Mi` |

### Database Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `database.persistence.enabled` | Enable persistent storage | `true` (keycloak) / `false` (noauth) |
| `database.persistence.size` | PVC size | `50Gi` |
| `database.resources.requests.memory` | Memory request | `512Mi` |

## 🛠️ Helm Commands

```bash
# List installed releases
helm list -n my-app

# Get values for a release
helm get values spending-monitor -n my-app

# Check what would change
helm diff upgrade spending-monitor ./spending-monitor \
  --namespace my-app \
  --values ./spending-monitor/values-keycloak.yaml

# Rollback to previous version
helm rollback spending-monitor -n my-app

# Uninstall
helm uninstall spending-monitor -n my-app

# Lint chart
helm lint ./spending-monitor

# Template (dry-run)
helm template spending-monitor ./spending-monitor \
  --values ./spending-monitor/values-keycloak.yaml
```

## 📚 Additional Resources

- [Main README](../../README.md) - Complete deployment guide
- [Keycloak Operator Setup](../../docs/KEYCLOAK_OPERATOR.md) - Keycloak installation
- [values.yaml](./spending-monitor/values.yaml) - All configuration options

# Quickstart Guide

One-page cheat sheet for deploying the Spending Transaction Monitor.

## 🚀 Deploy Commands

**Authenticated Deployment (Staging/Production):**
```bash
make deploy MODE=keycloak NAMESPACE=staging
```

**Development/Testing (No Auth):**
```bash
make deploy MODE=noauth NAMESPACE=dev-test
```

## 📋 Prerequisites

```bash
# Required tools
oc version      # OpenShift CLI
helm version    # Helm 3.x
podman version  # Podman

# Required files
.env.production  # Copy from env.example
```

## 🔑 Essential Commands

| Command | Description |
|---------|-------------|
| `make deploy MODE=keycloak` | Deploy with Keycloak auth |
| `make deploy MODE=noauth` | Deploy without auth (dev/test) |
| `make deploy MODE=dev` | Deploy with reduced resources |
| `make undeploy` | Remove deployment |
| `make status` | Show deployment status |
| `make logs-local` | View local service logs |

## 🏗️ Build & Push

```bash
make build-all    # Build all images locally
make push-all     # Push all images to registry
make deploy-all   # Build, push, and deploy
```

## 🔍 Monitoring

```bash
# Check status
make status NAMESPACE=my-app

# View logs (local development)
make logs-local
```

## 🌐 Access Your App

```bash
# Get the route URL
oc get routes -n spending-transaction-monitor

# Expected output:
# NAME                           HOST/PORT
# spending-monitor-nginx-route   https://spending-monitor-nginx-route-...
```

**Access:**
- UI: `https://<nginx-route>/`
- API: `https://<nginx-route>/api/`
- Health: `https://<nginx-route>/health`

## ⚙️ Configuration

### Quick Setup

```bash
# 1. Copy example
cp env.example .env.production

# 2. Edit required values
# - POSTGRES_PASSWORD
# - API_KEY
# - LLM_PROVIDER & BASE_URL
# - SMTP settings
# - KEYCLOAK settings (if using auth)

# 3. Deploy
make deploy MODE=keycloak
```

### Environment Variables

**Must Change:**
- `POSTGRES_PASSWORD` - Strong database password
- `API_KEY` - Your LLM API key
- `BASE_URL` - LLM endpoint
- `SMTP_HOST` - Email server (for alerts)
- `KEYCLOAK_URL` - Keycloak server (for MODE=keycloak)

**Recommended Settings for MODE=keycloak:**
- `ENVIRONMENT=staging` or `production`
- `DEBUG=false`
- `BYPASS_AUTH=false`

## 🐛 Troubleshooting

```bash
# Check pod status
oc get pods -n spending-transaction-monitor

# Describe problematic pod
oc describe pod <pod-name> -n spending-transaction-monitor

# View pod logs
oc logs <pod-name> -n spending-transaction-monitor

# Check deployment status
make status

# Verify secrets
oc get secret spending-monitor-secret -o yaml
```

## 📦 Component Images

Built images (default registry: quay.io/rh-ai-quickstart):
- `spending-monitor-api:latest`
- `spending-monitor-ui:latest`
- `spending-monitor-db:latest`

## 🔄 Update Deployment

```bash
# Option 1: Rebuild and redeploy with registry
make build-all
make push-all
make deploy MODE=keycloak NAMESPACE=my-app

# Option 2: Or all at once
make deploy-all NAMESPACE=my-app
```

## 📊 Scaling

```bash
# Via oc
oc scale deployment spending-monitor-api --replicas=3 -n my-namespace

# Or update values.yaml and redeploy
make deploy MODE=keycloak NAMESPACE=my-namespace
```

## 🧹 Cleanup

```bash
make undeploy           # Remove deployment only
make undeploy-all       # Remove deployment + namespace
make clean-images       # Clean local images
```

## 📚 Full Documentation

For detailed information, see:
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete deployment instructions with all modes
- **[KEYCLOAK_OPERATOR.md](./KEYCLOAK_OPERATOR.md)** - Keycloak installation guide
- **[Main README](../README.md)** - Project overview

---

**Need Help?** Run `make help` for all available commands.


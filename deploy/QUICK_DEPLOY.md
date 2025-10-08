# Quick Deploy Reference Card

## 🚀 One-Command Deploy

```bash
make full-deploy
```

This single command:
1. ✅ Logs into OpenShift registry
2. ✅ Creates project
3. ✅ Builds all images
4. ✅ Pushes to registry
5. ✅ Deploys with Helm

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
| `make deploy` | Deploy to OpenShift (production) |
| `make deploy-dev` | Deploy with reduced resources |
| `make full-deploy` | Complete pipeline: build + push + deploy |
| `make undeploy` | Remove deployment |
| `make status` | Show deployment status |
| `make logs` | View all logs |

## 🏗️ Build & Push

```bash
make build-all    # Build all images
make push-all     # Push all images
make deploy       # Deploy using Helm
```

## 🔍 Monitoring

```bash
# Port forward services to localhost
make port-forward-api    # API → localhost:8000
make port-forward-ui     # UI → localhost:8080
make port-forward-db     # DB → localhost:5432

# View logs
make logs-api           # API logs
make logs-ui            # UI logs
make logs-db            # Database logs
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
make full-deploy
```

### Environment Variables

**Must Change:**
- `POSTGRES_PASSWORD` - Strong database password
- `API_KEY` - Your LLM API key
- `BASE_URL` - LLM endpoint
- `SMTP_HOST` - Email server

**Production Settings:**
- `ENVIRONMENT=production`
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

## 📦 Component Versions

Built images:
- `quay.io/rh-ai-quickstart/spending-monitor-api:latest`
- `quay.io/rh-ai-quickstart/spending-monitor-ui:latest`
- `quay.io/rh-ai-quickstart/spending-monitor-db:latest`
- `quay.io/rh-ai-quickstart/spending-monitor-ingestion:latest`

## 🔄 Update Deployment

```bash
# Rebuild and redeploy
make build-all
make push-all
make deploy

# Or all at once
make deploy-all
```

## 📊 Scaling

```bash
# Via kubectl/oc
oc scale deployment spending-monitor-api --replicas=3

# Or update values.yaml and redeploy
make deploy
```

## 🧹 Cleanup

```bash
make undeploy           # Remove deployment only
make undeploy-all       # Remove deployment + namespace
make clean-images       # Clean local images
```

## 📚 Full Documentation

For detailed information, see:
- [Complete Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [OpenShift Specific Guide](./OPENSHIFT_DEPLOYMENT.md)
- [Main README](../README.md)

---

**Need Help?** Run `make help` for all available commands.


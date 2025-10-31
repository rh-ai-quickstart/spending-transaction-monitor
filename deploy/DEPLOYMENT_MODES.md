# Deployment Modes Guide

The Spending Transaction Monitor supports two distinct deployment modes:

## 🔓 Mode 1: Development (Auth Bypass)

**Use Case:** Development, testing, demos  
**Authentication:** Disabled (no login required)  
**Command:** `make deploy-noauth`

### Features
- ✅ No authentication required
- ✅ Reduced resource requirements
- ✅ No persistent storage (faster cleanup)
- ✅ Debug mode enabled
- ✅ Ingestion service disabled by default
- ✅ All CORS origins allowed

### Quick Deploy

```bash
# Deploy to current namespace
make deploy-noauth

# Deploy to specific namespace
make deploy-noauth NAMESPACE=my-test-namespace

# Deploy with custom image tag
make deploy-noauth IMAGE_TAG=dev
```

### Configuration

Uses `values-dev-noauth.yaml` which sets:
```yaml
secrets:
  ENVIRONMENT: "development"
  DEBUG: "true"
  BYPASS_AUTH: "true"

api:
  replicas: 1
  
database:
  persistence:
    enabled: false

ingestion:
  enabled: false
```

### When to Use
- ✅ Local development testing
- ✅ Quick demos
- ✅ Integration testing
- ✅ UI/UX development
- ❌ NOT for production
- ❌ NOT for any sensitive data

---

## 🔐 Mode 2: Production (Keycloak Auth)

**Use Case:** Production, staging  
**Authentication:** Keycloak SSO  
**Command:** `make deploy-keycloak`

### Features
- ✅ Keycloak authentication required
- ✅ Production-grade resource allocations
- ✅ Persistent database storage
- ✅ All services enabled (including ingestion)
- ✅ Multiple replicas for high availability
- ✅ Debug mode disabled

### Prerequisites

1. **Keycloak Must Be Running**
   ```bash
   # Deploy Keycloak first, or use external Keycloak
   # Update KEYCLOAK_URL in .env.production
   ```

2. **Configure `.env.production`**
   ```bash
   cp env.example .env.production
   # Edit and set:
   # - POSTGRES_PASSWORD (strong password)
   # - API_KEY (real LLM API key)
   # - KEYCLOAK_URL (your Keycloak server)
   # - SMTP_HOST (email server for alerts)
   ```

### Quick Deploy

```bash
# Deploy to current namespace
make deploy-keycloak

# Deploy to specific namespace
make deploy-keycloak NAMESPACE=production

# Deploy with custom image tag
make deploy-keycloak IMAGE_TAG=v1.0.0
```

### Configuration

Uses `values-prod-keycloak.yaml` which sets:
```yaml
secrets:
  ENVIRONMENT: "production"
  DEBUG: "false"
  BYPASS_AUTH: "false"

api:
  replicas: 2

ui:
  replicas: 2
  
database:
  persistence:
    enabled: true
    size: 50Gi

ingestion:
  enabled: true
```

### When to Use
- ✅ Production deployments
- ✅ Staging environments
- ✅ Any deployment with real user data
- ✅ Compliance-required environments

---

## Comparison Matrix

| Feature | Dev (No Auth) | Prod (Keycloak) |
|---------|---------------|-----------------|
| **Authentication** | ❌ Disabled | ✅ Keycloak SSO |
| **API Replicas** | 1 | 2 |
| **UI Replicas** | 1 | 2 |
| **Database Persistence** | ❌ No | ✅ Yes (50Gi) |
| **Ingestion Service** | ❌ Disabled | ✅ Enabled |
| **Debug Mode** | ✅ Yes | ❌ No |
| **Memory (Total)** | ~1.5Gi | ~4Gi |
| **CPU (Total)** | ~0.6 cores | ~2 cores |
| **CORS** | All origins | Restricted |
| **Use Case** | Dev/Test | Production |

---

## Switching Between Modes

### From No-Auth to Keycloak

```bash
# 1. Ensure Keycloak is deployed and configured

# 2. Update deployment
make deploy-keycloak NAMESPACE=your-namespace

# The deployment will upgrade in-place
# Database data is preserved
```

### From Keycloak to No-Auth

```bash
# 1. Redeploy in no-auth mode
make deploy-noauth NAMESPACE=your-namespace

# Warning: This will disable persistence by default
# Export data first if needed
```

---

## Advanced: Custom Values Override

You can combine the values files with additional overrides:

### Example: Dev mode but with persistence

```bash
helm upgrade --install spending-monitor ./deploy/helm/spending-monitor \
  --namespace my-namespace \
  --values ./deploy/helm/spending-monitor/values-dev-noauth.yaml \
  --set database.persistence.enabled=true \
  --set database.persistence.size=10Gi
```

### Example: Prod mode with custom Keycloak URL

```bash
helm upgrade --install spending-monitor ./deploy/helm/spending-monitor \
  --namespace my-namespace \
  --values ./deploy/helm/spending-monitor/values-prod-keycloak.yaml \
  --set secrets.KEYCLOAK_URL="https://keycloak.example.com"
```

---

## Verification

### Check Authentication Status

```bash
# Get the route
ROUTE=$(oc get route spending-monitor-nginx-route -n your-namespace -o jsonpath='{.spec.host}')

# Test API health endpoint
curl https://$ROUTE/api/health

# Check if auth is required
curl https://$ROUTE/api/users
# No auth mode: Returns user list
# Keycloak mode: Returns 401 Unauthorized
```

### Check Deployment Mode

```bash
# Check the BYPASS_AUTH secret value
oc get secret spending-monitor-secret -n your-namespace -o jsonpath='{.data.BYPASS_AUTH}' | base64 -d
# Output: "true" = no-auth mode
# Output: "false" = keycloak mode
```

---

## Troubleshooting

### Auth Bypass Mode Issues

**Problem:** Still seeing login screen  
**Solution:** 
```bash
# Verify BYPASS_AUTH is set
oc get secret spending-monitor-secret -o yaml | grep BYPASS_AUTH

# If wrong, update:
make deploy-noauth NAMESPACE=your-namespace
```

### Keycloak Mode Issues

**Problem:** 401 errors even with valid token  
**Solution:**
```bash
# Check Keycloak URL is accessible from pods
oc get secret spending-monitor-secret -o jsonpath='{.data.KEYCLOAK_URL}' | base64 -d

# Test connectivity
oc run test --rm -it --image=curlimages/curl -- curl http://spending-monitor-keycloak:8080/health
```

**Problem:** Keycloak not deployed  
**Solution:**
```bash
# Option 1: Deploy Keycloak
# (Add Keycloak helm chart or deployment)

# Option 2: Use external Keycloak
# Update KEYCLOAK_URL in .env.production

# Option 3: Switch to no-auth for testing
make deploy-noauth
```

---

## Best Practices

### Development
1. Use `deploy-noauth` for rapid iteration
2. Test auth flow separately with `deploy-keycloak`
3. Keep persistence disabled for faster cleanup
4. Use unique namespaces per developer

### Production
1. Always use `deploy-keycloak`
2. Never use `BYPASS_AUTH=true` in production
3. Enable persistence with adequate storage
4. Configure proper CORS origins (not `*`)
5. Use strong passwords and real API keys
6. Set up monitoring and alerts
7. Regular backups of database PVC

---

## Quick Reference

```bash
# Development (no auth)
make deploy-noauth NAMESPACE=dev-test

# Production (with Keycloak)
make deploy-keycloak NAMESPACE=production

# Check status
oc get pods -n your-namespace
oc get route -n your-namespace

# View logs
make logs NAMESPACE=your-namespace

# Remove deployment
make undeploy NAMESPACE=your-namespace
```

---

## Summary

- **🔓 Use `make deploy-noauth`** for development and testing
- **🔐 Use `make deploy-keycloak`** for production deployments
- Both modes use the same Helm chart with different values files
- Easy to switch between modes
- Clear visual indicators (🔓/🔐) in deployment output

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)


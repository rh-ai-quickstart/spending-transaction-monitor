# Deployment Modes Guide

The Spending Transaction Monitor supports two distinct deployment modes:

## 🔓 Mode 1: Development (Auth Bypass)

**Use Case:** Development, testing, demos  
**Authentication:** Disabled (no login required)  
**Command:** `make deploy MODE=noauth`

### Features
- ✅ No authentication required
- ✅ Reduced resource requirements
- ✅ No persistent storage (faster cleanup)
- ✅ Debug mode enabled
- ✅ All CORS origins allowed

### Quick Deploy

```bash
# Deploy to current namespace
make deploy MODE=noauth

# Deploy to specific namespace
make deploy MODE=noauth NAMESPACE=my-test-namespace

# Deploy with custom image tag
make deploy MODE=noauth IMAGE_TAG=dev NAMESPACE=my-test
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
**Command:** `make deploy MODE=keycloak`

### Features
- ✅ Keycloak authentication required
- ✅ Production-grade resource allocations
- ✅ Persistent database storage
- ✅ Multiple replicas for high availability
- ✅ Debug mode disabled
- ✅ Automatic user synchronization from database to Keycloak

### Prerequisites

1. **⚠️ Keycloak Operator Must Be Installed (REQUIRED)**
   
   **The operator must be installed by a cluster admin BEFORE deploying.**
   
   ```bash
   # Option 1: Install via OpenShift Console (Recommended)
   # 1. Navigate to: Operators → OperatorHub
   # 2. Search for: "Red Hat Build of Keycloak" or "Keycloak Operator"
   # 3. Click Install
   
   # Option 2: CLI Installation
   # See: deploy/KEYCLOAK_OPERATOR.md for detailed instructions
   ```
   
   ✅ The Helm chart includes a **pre-flight check** that verifies the operator is installed.
   
   ❌ The deployment will **fail with clear error messages** if the operator is missing.
   
   Once the operator is installed, the Helm chart will deploy Keycloak automatically.
   **No manual Keycloak deployment needed!**

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
make deploy MODE=keycloak

# Deploy to specific namespace
make deploy MODE=keycloak NAMESPACE=production

# Deploy with custom image tag
make deploy MODE=keycloak IMAGE_TAG=v1.0.0 NAMESPACE=production
```

### Configuration

Uses `values-keycloak.yaml` which sets:
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

keycloak:
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
| **Keycloak** | ❌ Disabled | ✅ Enabled |
| **Debug Mode** | ✅ Yes | ❌ No |
| **Memory (Total)** | ~1.5Gi | ~4Gi |
| **CPU (Total)** | ~0.6 cores | ~2 cores |
| **CORS** | All origins | Restricted |
| **Use Case** | Dev/Test | Production |

---

## Switching Between Modes

### From No-Auth to Keycloak

```bash
# 1. Ensure Keycloak Operator is installed

# 2. Update deployment
make deploy MODE=keycloak NAMESPACE=your-namespace

# The deployment will upgrade in-place
# Database data is preserved
```

### From Keycloak to No-Auth

```bash
# 1. Redeploy in no-auth mode
make deploy MODE=noauth NAMESPACE=your-namespace

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
  --values ./deploy/helm/spending-monitor/values-keycloak.yaml \
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
make deploy MODE=noauth NAMESPACE=your-namespace
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
# Option 1: Ensure Keycloak Operator is installed
# Then redeploy with MODE=keycloak

# Option 2: Use external Keycloak
# Update KEYCLOAK_URL in .env.production

# Option 3: Switch to no-auth for testing
make deploy MODE=noauth NAMESPACE=your-namespace
```

---

## Best Practices

### Development
1. Use `make deploy MODE=noauth` for rapid iteration
2. Test auth flow separately with `make deploy MODE=keycloak`
3. Keep persistence disabled for faster cleanup
4. Use unique namespaces per developer
5. Use OpenShift in-cluster builds to avoid registry push

### Production
1. Always use `make deploy MODE=keycloak`
2. Never use `BYPASS_AUTH=true` in production
3. Enable persistence with adequate storage
4. Configure proper CORS origins (not `*`)
5. Use strong passwords and real API keys
6. Set up monitoring and alerts
7. Regular backups of database PVC
8. Ensure Keycloak Operator is installed before deployment

---

## Quick Reference

```bash
# Development (no auth)
make deploy MODE=noauth NAMESPACE=dev-test

# Production (with Keycloak)
make deploy MODE=keycloak NAMESPACE=production

# Dev mode (reduced resources)
make deploy MODE=dev NAMESPACE=test

# Check status
oc get pods -n your-namespace
oc get route -n your-namespace

# View logs
make status NAMESPACE=your-namespace

# Remove deployment
make undeploy NAMESPACE=your-namespace
```

---

## Summary

- **🔓 Use `make deploy MODE=noauth`** for development and testing
- **🔐 Use `make deploy MODE=keycloak`** for production deployments
- **⚙️ Use `make deploy MODE=dev`** for resource-constrained environments
- All modes use the same Helm chart with different values files
- Easy to switch between modes with a single command
- Keycloak mode includes automatic user synchronization

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)


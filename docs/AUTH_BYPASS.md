# Authentication Bypass Guide

This document explains how to enable/disable authentication bypass in development mode.

## 🔒 Default Behavior (Authentication Required)

By default, the application **requires authentication**:
- Backend: `BYPASS_AUTH=false` 
- Frontend: `VITE_BYPASS_AUTH=false`
- Users must authenticate via Keycloak

## 🚪 Enabling Auth Bypass (Development Mode)

To disable authentication for development/testing:

### Method 1: Environment Variable (Recommended)
```bash
# Set for current session
export BYPASS_AUTH=true

# Then start services
make build-run-local
```

### Method 2: .env.development File
```bash
# Edit .env.development file
echo "BYPASS_AUTH=true" >> .env.development

# Restart services to pick up changes
make stop-local
make build-run-local
```

## 🔄 How It Works

### Backend (API)
- **Environment Variable**: `BYPASS_AUTH`
- **Config Location**: `packages/api/src/core/config.py`
- **Default**: `false` (authentication required)
- **Auto-Enable**: In `development` environment only if `BYPASS_AUTH` not explicitly set

### Frontend (UI)  
- **Environment Variable**: `VITE_BYPASS_AUTH`
- **Config Location**: `packages/ui/src/config/auth.ts`
- **Default**: `false` (authentication required)
- **Auto-Propagation**: `VITE_BYPASS_AUTH` inherits from `BYPASS_AUTH` via podman-compose

## 🎛️ Environment Variable Propagation

The system automatically propagates `BYPASS_AUTH` to the frontend:

```yaml
# In podman-compose.yml
ui:
  environment:
    - VITE_BYPASS_AUTH=${VITE_BYPASS_AUTH:-${BYPASS_AUTH:-false}}
```

## ✅ Verification

Check if auth bypass is active:

### Backend API
```bash
curl http://localhost:8000/health
# Should return without authentication headers
```

### Frontend UI
```bash
# Check browser dev tools console for:
# "Auth bypass enabled" or "Authentication required"
```

### Environment Check
```bash
# Verify environment variables
echo "BYPASS_AUTH=$BYPASS_AUTH"
echo "VITE_BYPASS_AUTH=$VITE_BYPASS_AUTH"
```

## 🚨 Production Safety

- **Production**: Always `BYPASS_AUTH=false`
- **Security**: Never enable auth bypass in production
- **CI/CD**: Ensure production deployments don't inherit development bypass settings

## 🛠️ Troubleshooting

### Issue: Auth bypass not working
1. **Check environment**: `echo $BYPASS_AUTH`
2. **Restart services**: `make stop-local && make build-run-local`
3. **Clear browser cache**: Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
4. **Check logs**: `make logs-local`

### Issue: Auth required but bypass expected
1. **Verify spelling**: `BYPASS_AUTH=true` (not `true` variations)
2. **Check case sensitivity**: Must be exactly `true`
3. **Environment isolation**: Ensure no conflicting `.env` files

## 📋 Quick Reference

```bash
# Enable auth bypass
export BYPASS_AUTH=true && make build-run-local

# Disable auth bypass (require authentication)
export BYPASS_AUTH=false && make build-run-local

# Check current setting
echo "Auth bypass: ${BYPASS_AUTH:-false}"

# Setup Keycloak (for when auth is enabled)
make setup-keycloak
```

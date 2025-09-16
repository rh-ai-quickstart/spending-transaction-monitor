# Authentication Scripts

This directory contains scripts for authentication setup and development workflows.

## Scripts

### 🔑 `setup_keycloak.py`
**Purpose**: Automated Keycloak configuration for the spending monitor application

**What it does**:
- Sets up Keycloak realm, client, and user configurations
- Configures OAuth2/OIDC integration settings
- Creates test users and roles for development

**Usage**:
```bash
python scripts/auth/setup_keycloak.py
```

### 🛠️ `auth-dev.sh`
**Purpose**: Development authentication workflow script

**What it does**:
- Provides shortcuts for common auth development tasks
- Manages authentication bypass configurations
- Streamlines development authentication testing

**Usage**:
```bash
bash scripts/auth/auth-dev.sh
```

## Authentication Modes

### Development Mode (Default)
- **Auth Bypass**: Enabled by default via `BYPASS_AUTH=true`
- **Mock Users**: Automatic sign-in as development user
- **No Setup Required**: Start coding immediately without Keycloak setup

```bash
# Development mode is auto-enabled with:
pnpm dev:backend
pnpm dev
```

### Production Mode
- **Full Authentication**: Requires proper Keycloak configuration
- **Real OAuth2/OIDC**: Complete security flow
- **User Management**: Proper user registration and management

## Environment Variables

### Development
```bash
ENVIRONMENT=development
BYPASS_AUTH=true  # Auto-enabled in development
API_PORT=8002
```

### Production  
```bash
ENVIRONMENT=production
BYPASS_AUTH=false
KEYCLOAK_URL=https://your-keycloak.com
KEYCLOAK_REALM=spending-monitor
KEYCLOAK_CLIENT_ID=spending-monitor-api
```

## Integration Points

### API Authentication
- **Middleware**: `packages/api/src/auth/middleware.py`
- **JWT Validation**: Uses `python-jose` for token verification
- **User Context**: Provides authenticated user context to routes

### Frontend Authentication
- **Auth Provider**: `packages/ui/src/contexts/AuthContext.tsx`
- **Login Components**: Keycloak integration components
- **Route Protection**: Protected routes and authentication guards

## Quick Setup Guide

### For New Developers (Recommended)
```bash
# Clone and start - no auth setup needed
git clone <repo>
pnpm setup
pnpm dev  # 🔓 Auth automatically bypassed
```

### For Production Setup
1. **Install Keycloak**: Set up Keycloak server
2. **Run Setup Script**: `python scripts/auth/setup_keycloak.py`
3. **Configure Environment**: Set production environment variables
4. **Test Integration**: Verify OAuth2 flow works

## Troubleshooting

### Development Mode Not Working
- Check for yellow banner: "🔓 Development Mode - Auth Bypassed"
- Verify `ENVIRONMENT=development` is set
- Ensure `BYPASS_AUTH=true` is configured

### Keycloak Integration Issues
- Verify Keycloak server is running and accessible
- Check realm and client configuration
- Validate JWT token format and signing keys

### Permission Errors
- Ensure user has proper roles assigned
- Check route-level authentication requirements
- Verify middleware is properly configured

## Related Documentation

See `docs/auth/` for detailed authentication documentation:
- `DEVELOPMENT.md` - Development authentication guide
- `INTEGRATION.md` - Keycloak integration details
- `TESTING.md` - Authentication testing strategies

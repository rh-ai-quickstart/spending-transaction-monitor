# Authentication Service

OAuth2/OIDC authentication infrastructure using Keycloak for the Spending Monitor application.

## Components

- **Keycloak**: Identity provider and authorization server
- **JWT Middleware**: FastAPI middleware for token validation  
- **Setup Scripts**: Automated Keycloak configuration
- **Tests**: Comprehensive auth middleware test suite

## Quick Start

### Development Setup

#### 1. Start Services
```bash
./scripts/auth-dev.sh services-up
```

#### 2. Configure Realm (Development)
```bash
cd scripts
python3 setup_keycloak.py
```

#### 3. Access
- **Keycloak Admin Console**: http://localhost:8080
- **Admin Credentials**: admin / admin

### Production Setup

For production deployments, configure the following environment variables before running the setup script:

```bash
# Required for production
export ENVIRONMENT=production
export KEYCLOAK_URL=https://keycloak.your-domain.com
export KEYCLOAK_ADMIN=your-admin-username
export KEYCLOAK_ADMIN_PASSWORD=your-secure-admin-password
export KEYCLOAK_REDIRECT_URIS=https://app.your-domain.com/*,https://app.your-domain.com
export KEYCLOAK_WEB_ORIGINS=https://app.your-domain.com
export KEYCLOAK_DEFAULT_PASSWORD=your-secure-default-password

# Optional (have defaults)
export KEYCLOAK_REALM=spending-monitor
export KEYCLOAK_CLIENT_ID=spending-monitor

# Run setup
cd scripts
python3 setup_keycloak.py
```

**Important Security Notes for Production:**
- Never use default passwords in production
- Use HTTPS for all URLs (Keycloak, redirect URIs, web origins)
- Set strong admin credentials
- Configure proper CORS origins
- Consider using Keycloak's user federation instead of creating users with default passwords

## Configuration Options

The setup script supports the following environment variables for flexible configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_URL` | `http://localhost:8080` | Keycloak server URL |
| `KEYCLOAK_ADMIN` | `admin` | Keycloak admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | `admin` | Keycloak admin password |
| `KEYCLOAK_REALM` | `spending-monitor` | Realm name to create/configure |
| `KEYCLOAK_CLIENT_ID` | `spending-monitor` | Client ID for the application |
| `KEYCLOAK_REDIRECT_URIS` | `http://localhost:3000/*` | Comma-separated list of valid redirect URIs |
| `KEYCLOAK_WEB_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed web origins |
| `KEYCLOAK_DEFAULT_PASSWORD` | `password123` | Default password for created users |
| `ENVIRONMENT` | `development` | Environment mode (development/production) |

## Client Configuration

The setup script automatically creates:
- **Realm**: Value from `KEYCLOAK_REALM` (default: `spending-monitor`)
- **Client ID**: Value from `KEYCLOAK_CLIENT_ID` (default: `spending-monitor`)
- **Client Type**: Public (PKCE flow)
- **Valid Redirect URIs**: Value from `KEYCLOAK_REDIRECT_URIS`
- **Web Origins**: Value from `KEYCLOAK_WEB_ORIGINS`

## Test Users

Created automatically by setup script:
- **Username**: `testuser@example.com`
- **Password**: `password123`
- **Roles**: `user`

## Development

### Manual Setup

If automated setup fails:

1. Go to http://localhost:8080 → Administration Console
2. Login with admin/admin
3. Create realm: `spending-monitor`
4. Create client: `spending-monitor`
5. Configure client settings:
   - Client type: OpenID Connect
   - Client authentication: Off (public client)
   - Valid redirect URIs: `http://localhost:5173/*`
   - Web origins: `http://localhost:5173`

### Testing

Test the auth infrastructure:
```bash
cd ../api
uv run uvicorn src.main:app --reload

# Test endpoints
curl http://localhost:8000/health                           # ✅ Works (no auth)
curl -H "Authorization: Bearer <token>" http://localhost:8000/users/profile  # ⚠️  Will work when auth is enabled
```

## Integration

All authentication integration details are now included in this README above. The auth system provides complete JWT middleware, OIDC client setup, and database user mapping.

## Commands

```bash
./scripts/auth-dev.sh services-up    # Start DB + prepare for Keycloak
./scripts/auth-dev.sh services-down  # Stop services
./scripts/auth-dev.sh setup          # Setup Keycloak configuration
./scripts/auth-dev.sh status         # Check service status
./scripts/auth-dev.sh help           # Show all available commands
```

Or use the consolidated pnpm commands:
```bash
pnpm dev           # Start all services (API + UI + DB)
pnpm status        # Check all service health  
pnpm db:start      # Start just database
pnpm db:stop       # Stop database
```

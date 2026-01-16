# Keycloak Management Guide

This document describes the Keycloak management tools and Makefile commands available in this project.

## Quick Start

### Set Up Keycloak Realm
```bash
make seed-keycloak-with-users
```

This command:
- Uses `.env.production` for Keycloak configuration if present (recommended for OpenShift)
- Creates the `spending-monitor` realm
- Creates the `spending-monitor` client with proper redirect URIs
- Creates test users with known credentials
- Configures roles (user, admin)
- Verifies the OpenID configuration

### List Users and Credentials
```bash
make keycloak-users
```

This command displays:
- All users in the realm
- User status (enabled/disabled)
- Assigned roles
- Creation timestamp
- **Test credentials** (for users created by setup script)

## Available Scripts

### `packages/auth/scripts/setup-keycloak-realm.sh`
**Purpose**: Set up or update the Keycloak realm with proper configuration

**What it does**:
1. Loads environment variables from `.env.production`
2. Discovers OpenShift route URLs automatically
3. Configures redirect URIs for both production and development
4. Creates realm, client, roles, and test users
5. Verifies OpenID configuration endpoints

**Usage**:
```bash
./packages/auth/scripts/setup-keycloak-realm.sh
# Or via Makefile (recommended)
make seed-keycloak-with-users
```

**Requirements**:
- `uv` (Python package manager) - Install with `brew install uv`
- `.env.production` file with Keycloak configuration
- Keycloak must be running and accessible

**Environment Variables Used**:
- `KEYCLOAK_URL` - Keycloak server URL (e.g., `https://keycloak.example.com`)
- `KEYCLOAK_REALM` - Realm name (default: `spending-monitor`)
- `KEYCLOAK_CLIENT_ID` - Client ID (default: `spending-monitor`)
- `KEYCLOAK_ADMIN` - Admin username (default: `admin`)
- `KEYCLOAK_ADMIN_PASSWORD` - Admin password (required)
- `KEYCLOAK_REDIRECT_URIS` - Optional, auto-discovered from OpenShift routes
- `KEYCLOAK_WEB_ORIGINS` - Optional, auto-discovered from OpenShift routes

### `packages/auth/scripts/list-keycloak-users.sh`
**Purpose**: List all Keycloak users with their roles and test credentials

**What it does**:
1. Connects to Keycloak using admin credentials
2. Fetches all users from the specified realm
3. Displays user information including:
   - Username and email
   - Enabled/disabled status
   - Assigned roles
   - Creation timestamp
   - **Test credentials** (password) for known test users

**Usage**:
```bash
./packages/auth/scripts/list-keycloak-users.sh
# Or via Makefile
make keycloak-users
```

**Requirements**:
- `uv` (Python package manager)
- `.env.production` file with Keycloak configuration
- Keycloak must be running and accessible

**Output Example**:
```
👤 Username: testuser
   Email:    testuser@example.com
   Status:   ✅ Enabled
   Roles:    user
   Created:  2025-11-12 23:42:27
   🔑 TEST CREDENTIALS:
      Email:    testuser@example.com
      Password: password123
      (Standard test user)
```

## Test Users

The setup script creates the following test users:

| Username | Email | Password | Roles | Description |
|----------|-------|----------|-------|-------------|
| `testuser` | testuser@example.com | `password123` | user | Standard test user |
| `adminuser` | admin@example.com | `admin123` | user, admin | Admin test user |

**Note**: These are test credentials only. For production, you should:
1. Delete or disable these test users
2. Create production users via Keycloak Admin Console
3. Use proper password policies and 2FA

## Configuration

### Redirect URIs and Web Origins

The setup script automatically configures redirect URIs for both development and production:

**Development** (localhost):
- Redirect URI: `http://localhost:3000/*`
- Web Origin: `http://localhost:3000`

**Production** (OpenShift):
- Redirect URI: `https://<ui-route-hostname>/*`
- Web Origin: `https://<ui-route-hostname>`

The production URLs are automatically discovered from OpenShift routes.

### Hostname Configuration

The Keycloak hostname is automatically set from `KEYCLOAK_URL` in `.env.production`. This ensures that the OpenID configuration endpoints return the correct external URLs.

**Example**:
```bash
# In .env.production
KEYCLOAK_URL=https://keycloak.apps.example.com

# Results in OpenID configuration:
# issuer: https://keycloak.apps.example.com/realms/spending-monitor
# authorization_endpoint: https://keycloak.apps.example.com/realms/spending-monitor/protocol/openid-connect/auth
```

## Makefile Targets

### `make seed-keycloak-with-users`
Set up Keycloak realm, create test users, and sync database users.

### `make keycloak-users`
List all Keycloak users with test credentials.

**Equivalent to**:
```bash
./packages/auth/scripts/list-keycloak-users.sh
```

## Troubleshooting

### Issue: "uv not found"
**Solution**: Install uv using Homebrew:
```bash
brew install uv
```

### Issue: "Failed to get admin token"
**Causes**:
1. Keycloak is not running
2. `KEYCLOAK_ADMIN_PASSWORD` is incorrect
3. `KEYCLOAK_URL` is incorrect

**Solution**:
1. Check Keycloak pod status: `oc get pods -l app.kubernetes.io/name=keycloak`
2. Verify admin password in `.env.production`
3. Test Keycloak URL: `curl https://your-keycloak-url/health/ready`

### Issue: "Realm does not exist"
**Solution**: Run the setup script:
```bash
make seed-keycloak-with-users
```

### Issue: OpenID configuration shows localhost URLs
**Solution**: The hostname is now automatically set from `KEYCLOAK_URL`. Make sure:
1. `KEYCLOAK_URL` in `.env.production` contains the correct external URL
2. Redeploy: `make deploy`

**Verify the fix**:
```bash
source .env.production
curl -s "$KEYCLOAK_URL/realms/spending-monitor/.well-known/openid-configuration" | jq -r '.issuer'
```

## Adding Production Users

For production deployments:

### Option 1: Keycloak Admin Console (Recommended)
1. Access Keycloak Admin Console:
   ```bash
   source .env.production && echo "$KEYCLOAK_URL/admin"
   ```
2. Login as admin
3. Select `spending-monitor` realm
4. Go to **Users** > **Add user**
5. Set username, email, and other details
6. Go to **Credentials** tab and set password
7. Assign roles in **Role mappings** tab

### Option 2: Keycloak Admin API
Use the same Python script structure as `setup_keycloak.py` to programmatically create users.

### Option 3: Sync from Database
Use the sync script to import users from your database:
```bash
make seed-keycloak-with-users
```

## Security Best Practices

1. **Change Default Credentials**: Update `KEYCLOAK_ADMIN_PASSWORD` from default value
2. **Disable Test Users in Production**: Delete or disable `testuser` and `adminuser`
3. **Use Strong Passwords**: Enforce password policies in Keycloak
4. **Enable 2FA**: Configure multi-factor authentication
5. **Restrict Redirect URIs**: Only allow known application URLs
6. **Regular Audits**: Periodically review users and permissions
7. **Secure Secrets**: Never commit `.env.production` to version control

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/)
- [OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)

## Related Documentation

- `deploy/helm/keycloak/README.md` - Keycloak Helm chart documentation
- `packages/auth/README.md` - Authentication package documentation
- `env.example` - Environment variable reference


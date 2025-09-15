# Authentication Integration Guide

This guide explains how to integrate OAuth2/OIDC authentication into the spending-monitor application.

## Current State

The authentication infrastructure has been set up with the following components:

### Backend Components
- **JWT Middleware** (`packages/api/src/auth/middleware.py`)
- **Keycloak Setup** (`packages/auth/`)
- **Dependencies** (`python-jose`, `requests`)

### Test Endpoints
- `GET /health` - No authentication required (health check)
- `GET /users/profile` - Will require valid JWT token (user profile)
## Integration Steps

### 1. Backend Route Integration

To protect existing routes, update route files to use the auth middleware:

```python
# Before
from fastapi import APIRouter, Depends
from db import get_db

@router.get('/')
async def get_users(session: AsyncSession = Depends(get_db)):
    # route logic
```

```python
# After  
from fastapi import APIRouter, Depends
from db import get_db
from ..auth.middleware import require_authentication, get_current_user

@router.get('/')
async def get_users(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(require_authentication)  # Add this
):
    # route logic - can now access user['id'], user['username'], etc.
```

### 2. Adding Authentication to Endpoints (Future)

The auth middleware is available for when endpoints need protection:

- **Required Auth**: `Depends(require_authentication)` - Returns 401 if no valid token
- **Token Extraction**: `Depends(get_current_user)` - Returns `None` if no token, user dict if valid  
- **Role-based**: `Depends(require_role('admin'))` - Requires specific role

*Note: Currently endpoints are unprotected. Endpoint protection will be added in a future PR.*

### 3. Development Bypass ✅ IMPLEMENTED

**Backend Configuration** (`packages/api/src/core/config.py`):

```python
class Settings(BaseSettings):
    # Environment settings
    ENVIRONMENT: Literal['development', 'production', 'staging', 'test'] = 'development'
    
    # Authentication settings  
    BYPASS_AUTH: bool = False

    def __post_init__(self):
        """Auto-enable auth bypass in development if not explicitly set"""
        if (
            self.ENVIRONMENT == 'development'
            and not hasattr(self, '_bypass_auth_explicitly_set')
            and 'BYPASS_AUTH' not in os.environ
        ):
            self.BYPASS_AUTH = True
```

**Auth Middleware** (`packages/api/src/auth/middleware.py`):

```python
async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    """Extract user info from JWT token with development bypass (returns None if no token)"""
    
    # Development bypass - return mock user
    if settings.BYPASS_AUTH:
        logger.info("🔓 Authentication bypassed - development mode enabled")
        return {
            'id': 'dev-user-123',
            'email': 'developer@example.com',
            'username': 'developer',
            'roles': ['user', 'admin'],
            'is_dev_mode': True,
            'token_claims': {
                'sub': 'dev-user-123',
                'preferred_username': 'developer',
                'email': 'developer@example.com',
                'realm_access': {'roles': ['user', 'admin']}
            }
        }
    # ... existing production auth logic ...
```

**Usage**:
```bash
# Automatic bypass in development
ENVIRONMENT=development  # Auto-enables BYPASS_AUTH=true

# Explicit control
BYPASS_AUTH=true   # Force enable bypass
BYPASS_AUTH=false  # Force disable bypass
```

### 3.1. Enhanced Dev Mode - Dynamic User Selection ✅ IMPLEMENTED

**Header-Based User Selection**:

The development bypass now supports **dynamic user selection** via headers for better multi-user testing scenarios.

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db) if get_db else None,
    request: Request = None,
) -> dict | None:
    if settings.BYPASS_AUTH:
        # 🆕 NEW: Check for test user header (dynamic user selection)
        if request is not None:
            test_user_email = request.headers.get('X-Test-User-Email')
            if test_user_email:
                return await get_test_user(test_user_email, session)
        
        # Fallback to current behavior (first user or mock)
        return await get_dev_fallback_user(session)
```

**🆕 Enhanced Testing Capabilities**:

```bash
# Test as specific user (must exist in database)
curl -H "X-Test-User-Email: alice@example.com" http://localhost:8000/api/users/me

# Test as admin user  
curl -H "X-Test-User-Email: admin@company.com" http://localhost:8000/api/transactions

# Test user with specific transaction history
curl -H "X-Test-User-Email: user1@example.com" http://localhost:8000/api/users/me/transactions

# No header = current behavior (first user or mock)
curl http://localhost:8000/api/users/me
```

**Error Handling & Security**:

- ✅ **User not found**: Returns `400` error with clear message
- ✅ **Production safety**: Header completely ignored when `BYPASS_AUTH=false`
- ✅ **Clear logging**: Test user selection logged with `🧪 DEV MODE` prefix
- ✅ **Fail-secure**: Falls back to mock user if database unavailable

**Use Cases**:

- 🧪 **Multi-user testing**: Test different user roles and permissions
- 📊 **Transaction history**: Test with users having different transaction patterns
- 🔒 **Role testing**: Verify admin vs user access controls
- ⚡ **Quick switching**: No need to modify database or restart services

### 4. Frontend Integration ✅ IMPLEMENTED

**Auth Configuration** (`packages/ui/src/config/auth.ts`):

```typescript
export interface AuthConfig {
  bypassAuth: boolean;
  keycloakUrl: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  environment: 'development' | 'production' | 'staging' | 'test';
}

const environment = (import.meta.env.VITE_ENVIRONMENT || 'development') as AuthConfig['environment'];

export const authConfig: AuthConfig = {
  environment,
  bypassAuth:
    import.meta.env.VITE_BYPASS_AUTH === 'true' ||
    (environment === 'development' && import.meta.env.VITE_BYPASS_AUTH !== 'false'),
  // ... Keycloak config
};
```

**Auth Context** (`packages/ui/src/contexts/AuthContext.tsx`):

```tsx
// Custom AuthProvider that switches between dev and production modes
export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (authConfig.bypassAuth) {
    console.log('🔓 Running in development mode - authentication bypassed');
    return <DevAuthProvider>{children}</DevAuthProvider>;
  }
  return <ProductionAuthProvider>{children}</ProductionAuthProvider>;
}

// Development provider returns mock user immediately
function DevAuthProvider({ children }: { children: React.ReactNode }) {
  const [user] = useState<User>({
    id: 'dev-user-123',
    email: 'developer@example.com',
    username: 'developer',
    name: 'John Doe',
    roles: ['user', 'admin'],
    isDevMode: true,
  });
  // ... context implementation
}
```

**Usage**:
```bash
# Development Mode (Default) - Auto-bypass
VITE_ENVIRONMENT=development
VITE_BYPASS_AUTH=true

# Production Mode
VITE_ENVIRONMENT=production  
VITE_BYPASS_AUTH=false

# Force Production Auth in Development
VITE_ENVIRONMENT=development
VITE_BYPASS_AUTH=false  # Explicit override
```

**Visual Indicators**: 
- 🔓 Dev mode banner: "Development Mode - Auth Bypassed"
- Existing UserAvatar and DashboardHeader patterns maintained
## Setup Instructions

### 1. Start Keycloak
```bash
cd packages/auth
./scripts/auth-dev.sh services-up
```

### 2. Configure Keycloak Realm
```bash
cd packages/auth/scripts  
python3 setup_keycloak.py
```

### 3. Test Authentication
```bash
# Start API
cd packages/api
uv run uvicorn src.main:app --reload

# Test endpoints
curl http://localhost:8000/health                           # ✅ Works (no auth)
curl -H "Authorization: Bearer <token>" http://localhost:8000/users/profile  # ⚠️  Will work when auth is enabled
```

## Environment Variables

```bash
# API (.env)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=spending-monitor
KEYCLOAK_CLIENT_ID=spending-monitor

# Backend Development Mode
ENVIRONMENT=development        # Auto-enables auth bypass
BYPASS_AUTH=true              # Explicit control

# Frontend UI (.env)
VITE_ENVIRONMENT=development  # Auto-enables auth bypass
VITE_BYPASS_AUTH=true        # Explicit control
VITE_KEYCLOAK_URL=http://localhost:8080/realms/spending-monitor
VITE_KEYCLOAK_CLIENT_ID=spending-monitor
```

## Migration Strategy

1. **Phase 1**: Core infrastructure ✅ COMPLETED
   - JWT middleware and Keycloak setup 
   - Development bypass for backend and frontend
   - Test endpoints and documentation

2. **Phase 2**: Integrate auth into main routes (TODO)
   - Apply `Depends(require_authentication)` to protected routes
   - Add user context to business logic
   
3. **Phase 3**: Role-based permissions (TODO)  
   - Implement role checking decorators
   - Add admin-only endpoints
   
4. **Phase 4**: Production deployment (TODO)
   - Configure production Keycloak instance
   - HTTPS and security hardening

## Testing

Run the auth middleware tests:
```bash
cd packages/auth
python -m pytest tests/test_auth_middleware.py -v
```

## Security Considerations

- JWT tokens are validated against Keycloak's public keys
- Tokens are cached for performance (1-hour expiry)
- CORS is configured for the frontend domain
- HTTPS should be used in production
- Sensitive endpoints should require authentication

## Troubleshooting

### Common Issues

1. **Token validation fails**: Check Keycloak is running and realm is configured
2. **CORS errors**: Verify ALLOWED_HOSTS includes frontend URL
3. **Connection refused**: Ensure Keycloak is accessible at configured URL

### Debug Mode

Enable debug logging in the auth middleware:
```python
import logging
logging.getLogger('packages.api.src.middleware.auth').setLevel(logging.DEBUG)
```

## Next Steps

1. Implement development bypass mechanism
2. Integrate authentication into main API routes
3. Set up frontend OIDC provider
4. Add role-based access control
5. Configure for production deployment

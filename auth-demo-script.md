# 🔐 Authentication Demo Script

## Current Status ✅

**Services Running:**
- ✅ **Keycloak**: http://localhost:8080 (admin/admin)
- ✅ **API Server**: http://localhost:8000 
- ✅ **UI Development**: http://localhost:3000
- ✅ **Database**: PostgreSQL with sample data

**Authentication Setup:**
- ✅ **Keycloak Realm**: `spending-monitor` 
- ✅ **Test Users Created**:
  - `testuser@example.com` / `password123` (user role)
  - `admin@example.com` / `admin123` (admin role)
- ✅ **OIDC Client**: Configured for `http://localhost:3000/*`

## Demo Flow

### 1. 🔧 Development Mode (Current)

**Authentication is BYPASSED in development:**

```bash
# Test public endpoint
curl http://localhost:8000/health/
# → Returns: API + Database health status

# Test protected endpoint (works without auth in dev mode)  
curl http://localhost:8000/users/profile
# → Returns: {"id":"1c85902a...","email":"john.doe@example.com",...}

# Test other protected endpoints
curl http://localhost:8000/transactions/ | head -n 5
curl http://localhost:8000/alerts/rules | head -n 5
```

### 2. 🔒 Production Mode Demo

**To enable REAL authentication:**

1. **Set Environment Variables:**
   ```bash
   export BYPASS_AUTH=false
   export ENVIRONMENT=production
   
   # Or in UI:
   export VITE_BYPASS_AUTH=false
   export VITE_ENVIRONMENT=production
   ```

2. **Restart Services:**
   ```bash
   # Kill current servers
   pkill -f uvicorn
   pkill -f vite
   
   # Restart with production auth
   cd packages/api && BYPASS_AUTH=false uv run uvicorn src.main:app --reload &
   cd packages/ui && VITE_BYPASS_AUTH=false npm run dev:vite &
   ```

3. **Test Production Auth Flow:**
   ```bash
   # This will now require authentication
   curl http://localhost:8000/users/profile
   # → Returns: {"detail":"Authentication required"}
   
   # Get a token from Keycloak first
   curl -X POST http://localhost:8080/realms/spending-monitor/protocol/openid-connect/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "client_id=spending-monitor" \
        -d "grant_type=password" \
        -d "username=testuser@example.com" \
        -d "password=password123"
   
   # Use the token
   curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8000/users/profile
   ```

### 3. 🌐 Frontend Demo

**Access the UI at: http://localhost:3000**

**Development Mode:**
- Auth is bypassed
- Shows mock user data
- All features accessible

**Production Mode:**
- Redirects to login page
- Keycloak login flow
- Role-based access control

### 4. 🎯 Key Demonstration Points

**Backend Authentication:**
- ✅ JWT validation with Keycloak JWKS
- ✅ Role-based authorization (`user`, `admin`)
- ✅ Development bypass mode
- ✅ Proper error handling

**Frontend Authentication:**
- ✅ OIDC integration with `react-oidc-context`
- ✅ Automatic token refresh
- ✅ Protected routes
- ✅ Development mode bypass

**API Endpoints Protected:**
- ✅ `/users/profile` - Get current user
- ✅ `/users/{id}` - Get specific user (admin or self)
- ✅ `/transactions/` - List transactions (filtered by user)
- ✅ `/alerts/rules` - User's alert rules

## 📋 Test Scenarios

### Scenario 1: Happy Path Authentication
1. User visits app → redirected to Keycloak
2. Logs in with `testuser@example.com` / `password123`
3. Redirected back with valid JWT token
4. Can access protected resources
5. Token refreshes automatically

### Scenario 2: Role-Based Access
1. Regular user can only see their own data
2. Admin user can access all user data
3. Proper 403 errors for insufficient permissions

### Scenario 3: Development Workflow
1. Developer starts app → auth bypassed
2. Mock user data available immediately  
3. Full functionality for development/testing
4. Easy switch to production auth

## 🐛 Issues Fixed in This Demo

1. **Route Order Bug**: `/users/me` was being matched by `/{user_id}` → Fixed by using `/profile` and proper ordering
2. **Database Schema**: Alert rules column naming conflicts → Identified for future fix
3. **Environment Configuration**: Proper dev/prod auth toggles → Working

## 🚀 Next Steps for Recording

1. **Show Development Mode**: Quick demo of bypassed auth
2. **Enable Production Mode**: Show real Keycloak login
3. **Demonstrate Role Access**: Show user vs admin permissions
4. **Error Handling**: Show what happens without proper tokens

---

**Demo Branch**: `demo/auth-working-demo`  
**Recording Ready**: ✅ All core authentication functionality working

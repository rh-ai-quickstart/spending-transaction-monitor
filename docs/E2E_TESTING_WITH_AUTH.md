# E2E Testing with Authentication

Complete guide for running end-to-end alert rule tests with full Keycloak authentication.

## Quick Start (TL;DR)

```bash
# 1. Seed test data (automatically syncs users to Keycloak)
cd packages/db
pnpm seed:outside-home-city --force

# Expected output:
# ✅ All data committed to database
# 🔐 Syncing users to Keycloak
# ✅ User james.wilson synced to Keycloak
# 🎉 Keycloak sync completed: 1/1 users synced

# 2. Get auth token
TOKEN=$(curl -s -X POST http://localhost:8080/realms/spending-monitor/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=spending-monitor-app" \
  -d "grant_type=password" \
  -d "username=james.wilson@example.com" \
  -d "password=password123" \
  | jq -r '.access_token')

# 3. Call authenticated API
curl -X POST http://localhost:8000/api/alerts/rules/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"natural_language_query": "Alert me if a transaction happens outside my home city."}'
```

**That's it!** Your test users are now in both the database AND Keycloak.

---

## Overview

The e2e test infrastructure **automatically syncs seeded users to Keycloak**, enabling tests to run with full authentication. This ensures that the test environment mirrors production authentication flows.

## How It Works

### Automatic Keycloak Sync

When you seed test data using the `seed_alert_rules.py` script (or any pnpm seed command), the system now:

1. **Seeds the database** with users, transactions, and other test data
2. **Automatically syncs users to Keycloak** with proper credentials
3. **Reports sync status** so you know if auth is available

### Graceful Degradation

The Keycloak sync is designed to fail gracefully:

- ✅ If Keycloak is running → Users are synced, auth is available
- ⚠️ If Keycloak is not running → Warning is displayed, tests continue without auth
- ⚠️ If requests library is missing → Sync is skipped, tests continue

This means **tests never fail due to Keycloak unavailability** - they simply run without authentication if needed.

---

## Available Test Scenarios

### Location-Based Alerts

#### Outside Home City ✅ NEW
```bash
pnpm seed:outside-home-city --force
# User: james.wilson@example.com / password123
# Triggers when transaction occurs in a different city
```

#### Outside Home Country ✅ NEW
```bash
pnpm seed:outside-home-country --force
# User: sarah.martinez@example.com / password123
# Triggers when transaction occurs in a different country
```

#### Outside Home State ✅
```bash
pnpm seed:outside-home-state --force
# User: emily.clark@example.com / password123
# Triggers when transaction occurs in a different state
```

### All Available Scenarios (17/20 - 85% Coverage)

**Summary:**
- ✅ Implemented: 17 scenarios
- ❌ Not Implemented: 2 scenarios (first-time detection patterns)
- 🔄 Duplicate: 1 scenario

#### Transaction Frequency & Spending (4/4 - 100%) ✅
- `pnpm seed:last-hour` - More than 5 transactions in last hour
- `pnpm seed:dining` - More than $300 on dining
- `pnpm seed:spending-daily-300` - More than $300 in one day
- `pnpm seed:spending-weekly-500` - Exceed $500 in a week

#### Statistical Analysis (3/3 - 100%) ✅
- `pnpm seed:dining-30d-avg-40pct` - Dining expense exceeds 30-day average by 40%
- `pnpm seed:dining-avg-plus20` - Dining expense exceeds average by $20
- `pnpm seed:spending-electronics-3x` - Apple transaction exceeds typical electronics spend by 3x

#### Recurring Charges (3/3 - 100%) ✅
- `pnpm seed:pattern-recurring-20pct` - Recurring charge increases by 20%
- `pnpm seed:pattern-recurring-plus5` - Recurring charge increases by $5
- `pnpm seed:pattern-new-recurring` - New recurring charge detected

#### Location-Based (4/5 - 80%) 🟢
- `pnpm seed:location-far-from-known` - Transaction far from last known location
- `pnpm seed:outside-home-state` - Transaction outside home state
- `pnpm seed:outside-home-city` - Transaction outside home city ✨ NEW
- `pnpm seed:outside-home-country` - Transaction outside home country ✨ NEW
- ❌ First time transaction in city (not implemented)

#### Merchant Analysis (2/3 - 67%) 🟡
- `pnpm seed:charged-more-same-merchant` - Charged significantly more by same merchant
- `pnpm seed:more-than-20-same-merchant` - Charged $20 more by same merchant
- ❌ First time with merchant (not implemented)

#### Duplicate Charges (1/2 - 50%)
- `pnpm seed:merchant-same-day-dupes` - Charged more than once same day
- 🔄 Duplicate scenario exists in alert_rules.txt

Run `pnpm test:e2e:list` to see detailed test file names.

---

## Prerequisites

### 1. Keycloak Setup

Make sure Keycloak is running and configured:

```bash
# Check if Keycloak is running
curl http://localhost:8080/health

# If not running, start it
cd keycloak-setup-env
# Follow setup instructions in packages/auth/README.md
```

### 2. Environment Variables

Set these environment variables (or use defaults):

```bash
export KEYCLOAK_URL="http://localhost:8080"
export KEYCLOAK_ADMIN_USER="admin"
export KEYCLOAK_ADMIN_PASSWORD="admin"
export KEYCLOAK_REALM="spending-monitor"
export KEYCLOAK_DEFAULT_PASSWORD="password123"
```

**Default credentials** (if not set):
- Keycloak Admin: `admin/admin`
- Test Users: `password123`
- Realm: `spending-monitor`

---

## Running E2E Tests with Auth

### Option 1: Using pnpm Commands (Recommended)

All pnpm seed commands now automatically sync to Keycloak:

```bash
cd packages/db

# Seed and sync users for a specific test
pnpm seed:outside-home-city --force

# Expected output:
# ✅ All data committed to database
# 🔐 Syncing users to Keycloak
# ✅ Keycloak authentication successful
# ✅ User james.wilson synced to Keycloak
# 🎉 Keycloak sync completed: 1/1 users synced
```

### Option 2: Using the E2E Test Script

The test script automatically seeds data (which triggers Keycloak sync):

```bash
cd packages/db
pnpm test:e2e alert_outside_home_city_sample.json
```

This will:
1. Seed the database with test data
2. Sync users to Keycloak
3. Validate the alert rule via API
4. Create the alert rule
5. Trigger the alert

### Option 3: Manual Seeding

Use the Python script directly:

```bash
cd packages/db

# With Keycloak sync (default)
uv run python -m db.scripts.seed_alert_rules json/alert_outside_home_city_sample.json --force

# Skip Keycloak sync
uv run python -m db.scripts.seed_alert_rules json/alert_outside_home_city_sample.json --force --no-keycloak
```

---

## Testing with Authentication Enabled

### Step 1: Start All Services

```bash
# Terminal 1: Database
cd packages/db
pnpm dev

# Terminal 2: Keycloak
cd keycloak-setup-env
# Start Keycloak (see packages/auth/README.md)

# Terminal 3: API Server
cd packages/api
npm run dev  # Make sure AUTH_BYPASS=false or unset
```

### Step 2: Seed Test Data

```bash
cd packages/db
pnpm seed:outside-home-city --force
```

Output will show:
```
🎉 Seeding completed successfully!
============================================================
🔐 Syncing users to Keycloak
============================================================
🔑 Authenticating with Keycloak at http://localhost:8080...
✅ Keycloak authentication successful
  ✅ User james.wilson synced to Keycloak
============================================================
🎉 Keycloak sync completed: 1/1 users synced
🔗 Users can login with:
   • Username/Email: their email address
   • Password: password123
============================================================
```

### Step 3: Get Auth Token

```bash
# Login as the seeded user
curl -X POST http://localhost:8080/realms/spending-monitor/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=spending-monitor-app" \
  -d "grant_type=password" \
  -d "username=james.wilson@example.com" \
  -d "password=password123" \
  | jq -r '.access_token'
```

Save the token to a variable:
```bash
TOKEN=$(curl -X POST http://localhost:8080/realms/spending-monitor/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=spending-monitor-app" \
  -d "grant_type=password" \
  -d "username=james.wilson@example.com" \
  -d "password=password123" \
  | jq -r '.access_token')
```

### Step 4: Call API with Auth

```bash
# Validate alert rule (authenticated)
curl -X POST http://localhost:8000/api/alerts/rules/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"natural_language_query": "Alert me if a transaction happens outside my home city."}'

# Create alert rule (authenticated)
curl -X POST http://localhost:8000/api/alerts/rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "alert_rule": {...},
    "natural_language_query": "..."
  }'
```

---

## User Credentials by Test Scenario

After seeding each test scenario, you can login with these credentials:

| Test Scenario | Email | Username | Password |
|---------------|-------|----------|----------|
| Outside Home City | james.wilson@example.com | james.wilson | password123 |
| Outside Home Country | sarah.martinez@example.com | sarah.martinez | password123 |
| Outside Home State | emily.clark@example.com | emily.clark | password123 |
| Dining 30d Avg | (see JSON file) | (email prefix) | password123 |
| ... | (see JSON file) | (email prefix) | password123 |

**Note**: Username is always the part before `@` in the email address.

---

## Troubleshooting

### Keycloak Not Available

**Symptom**: You see:
```
⚠️  Keycloak not available or authentication failed (status 400)
   Tests will run without Keycloak authentication.
```

**Solution**: 
- Check if Keycloak is running: `curl http://localhost:8080/health`
- Start Keycloak if needed
- Verify `KEYCLOAK_URL` environment variable
- Re-run the seed command

### User Already Exists

**Symptom**: You see:
```
ℹ️  User james.wilson already exists in Keycloak
```

**Solution**: This is normal! The script detects existing users and skips them. No action needed.

### Authentication Required but No Token

**Symptom**: API returns 401 Unauthorized

**Solution**:
1. Ensure you seeded the data (which syncs users)
2. Get a fresh token using the curl command above
3. Make sure token is not expired (tokens expire after 5 minutes by default)
4. Verify the API is not in AUTH_BYPASS mode

### Wrong Credentials

**Symptom**: Token request fails with 401

**Solution**:
- Verify the user was seeded: Check Keycloak admin console
- Ensure you're using the correct email from the JSON file
- Default password is `password123` (unless `KEYCLOAK_DEFAULT_PASSWORD` is set)
- Make sure you're using the correct realm

---

## Advanced Usage

### Skip Keycloak Sync

If you want to seed data without Keycloak sync:

```bash
# Using pnpm (pass flag through)
pnpm seed:outside-home-city -- --no-keycloak --force

# Using Python directly
uv run python -m db.scripts.seed_alert_rules json/alert_outside_home_city_sample.json --force --no-keycloak
```

### Sync Existing Database Users

If you already have users in the database and want to sync them to Keycloak:

```bash
cd packages/auth
python scripts/sync_db_users_to_keycloak.py
```

This standalone script syncs **all** users from the database, not just newly seeded ones.

### Custom Keycloak Configuration

Override defaults with environment variables:

```bash
export KEYCLOAK_URL="http://keycloak.example.com:8080"
export KEYCLOAK_REALM="my-custom-realm"
export KEYCLOAK_DEFAULT_PASSWORD="MySecurePassword123"

# Then seed as normal
pnpm seed:outside-home-city --force
```

---

## CI/CD Considerations

### GitHub Actions / GitLab CI

Example workflow with Keycloak:

```yaml
name: E2E Tests with Auth

jobs:
  test:
    services:
      postgres:
        image: postgres:15
      keycloak:
        image: quay.io/keycloak/keycloak:latest
        env:
          KEYCLOAK_ADMIN: admin
          KEYCLOAK_ADMIN_PASSWORD: admin
        
    steps:
      - name: Seed test data
        run: |
          cd packages/db
          pnpm seed:outside-home-city --force
          # Keycloak sync happens automatically
      
      - name: Run E2E tests
        run: |
          cd packages/db
          pnpm test:e2e
```

### Kubernetes / OpenShift

For production-like environments, use the Helm charts with Keycloak enabled:

```bash
cd deploy/helm/spending-monitor
helm install my-release . --set keycloak.enabled=true
```

---

## Security Notes

### Test Passwords

⚠️ **WARNING**: Default test password is `password123` - this is intentionally weak and should **NEVER** be used in production.

### Production Considerations

For production deployments:

1. **Use strong passwords**: Set `KEYCLOAK_DEFAULT_PASSWORD` to a secure value
2. **Enable MFA**: Configure Keycloak to require 2FA
3. **Use HTTPS**: Always use TLS for Keycloak in production
4. **Rotate secrets**: Regularly update Keycloak admin credentials
5. **Limit access**: Restrict who can access the Keycloak admin console

---

## Integration with Test Framework

The e2e test script (`test_alert_rules.sh`) is aware of Keycloak sync:

```bash
# When you run the test script, it:
# 1. Seeds data (which syncs to Keycloak)
# 2. Validates the alert rule
# 3. Creates the alert rule
# 4. Triggers the alert

# The script can be extended to:
# - Obtain auth tokens automatically
# - Pass tokens to API calls
# - Verify auth-protected endpoints
```

Future enhancements could include:
- Auto-fetching auth tokens in test script
- Testing with expired tokens
- Testing with invalid tokens
- Testing role-based access control

---

## What Was Implemented

This guide reflects recent enhancements to the testing infrastructure:

### ✅ Location-Based Alerts (NEW)
- Added 2 new location-based alert scenarios
- Coverage increased from 40% → 80%
- Test files: `alert_outside_home_city_sample.json`, `alert_outside_home_country_sample.json`

### ✅ Keycloak Auto-Sync (NEW)
- Seeding now automatically syncs users to Keycloak
- No manual user creation needed
- All test users get `password123` as default password
- Graceful failure if Keycloak unavailable

### ✅ Overall Progress
- 17/20 alert scenarios now implemented (85% coverage)
- Full authentication testing enabled
- Better developer experience

### Remaining Work (2 scenarios)

Both unimplemented scenarios require historical query patterns:

1. **First Transaction in City** (Medium complexity)
   - Check if `merchant_city` exists in past transactions
   - Requires: `SELECT COUNT(*) FROM transactions WHERE merchant_city = ? AND transaction_date < ?`

2. **First Time with Merchant** (Medium complexity)
   - Check if `merchant_name` exists in past transactions
   - Requires: `SELECT COUNT(*) FROM transactions WHERE merchant_name = ? AND transaction_date < ?`

---

## Related Documentation

- [AUTH_BYPASS.md](AUTH_BYPASS.md) - How to bypass auth for development
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Overall development setup
- [packages/auth/README.md](../packages/auth/README.md) - Keycloak setup guide
- [packages/auth/TESTING.md](../packages/auth/TESTING.md) - Auth-specific testing
- [packages/api/tests/alert_rules.txt](../packages/api/tests/alert_rules.txt) - All 20 alert rule scenarios

---

*Last updated: 2025-10-14*


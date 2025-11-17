#!/bin/bash
set -e

echo "🚀 Starting database initialization process..."

# Wait for PostgreSQL to be ready with better error handling
echo "⏳ Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS: Checking PostgreSQL connection..."
    
    # Try pg_isready first
    if pg_isready -h ${POSTGRES_HOST:-postgres} -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-spending-monitor} -q; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo "❌ PostgreSQL not ready after $MAX_ATTEMPTS attempts"
        echo "Connection details:"
        echo "  Host: ${POSTGRES_HOST:-postgres}"
        echo "  User: ${POSTGRES_USER:-user}" 
        echo "  Database: ${POSTGRES_DB:-spending-monitor}"
        exit 1
    fi
    
    echo "   PostgreSQL not ready yet, waiting 5 seconds..."
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

# Change to the db package directory and run migrations
cd /app/packages/db

# Run Alembic migrations
echo "📊 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "❌ Database migrations failed"
    exit 1
fi

# Check if CSV data files exist and load them
USERS_CSV="/app/data/sample_users.csv"
TRANSACTIONS_CSV="/app/data/sample_transactions.csv"

if [ -f "$USERS_CSV" ] && [ -f "$TRANSACTIONS_CSV" ]; then
    echo "📋 Found CSV data files, loading sample data..."
    echo "   Users CSV: $USERS_CSV ($(wc -l < "$USERS_CSV") lines)"
    echo "   Transactions CSV: $TRANSACTIONS_CSV ($(wc -l < "$TRANSACTIONS_CSV") lines)"
    
    # Set PYTHONPATH to ensure imports work correctly
    export PYTHONPATH="/app/packages/db/src:/app/packages/api/src:$PYTHONPATH"
    
    # Load CSV data
    python3 -m db.scripts.load_csv_data
    
    if [ $? -eq 0 ]; then
        echo "✅ Sample data loaded successfully"
    else
        echo "❌ Sample data loading failed"
        echo "Check the logs above for details"
        exit 1
    fi
else
    echo "⚠️  CSV data files not found:"
    echo "   Expected users file: $USERS_CSV"
    echo "   Expected transactions file: $TRANSACTIONS_CSV"
    echo ""
    echo "Available files in /app/data/:"
    ls -la /app/data/ || echo "   /app/data/ directory not found"
    echo ""
    echo "Skipping sample data loading"
fi

# Sync users to Keycloak if auth is enabled
echo ""
echo "🔍 Checking if Keycloak user sync is needed..."
if [ "${BYPASS_AUTH:-true}" = "false" ] && [ -n "${KEYCLOAK_URL}" ]; then
    echo "✅ Authentication enabled - will sync users to Keycloak..."
    echo "   Keycloak URL: ${KEYCLOAK_URL}"
    echo "   Default password: ${KEYCLOAK_DEFAULT_PASSWORD:-password123}"
    
    # Run sync (with built-in timeouts to prevent blocking)
    echo "   Starting sync (non-blocking)..."
    # Use 'set +e' to ensure any Python errors don't fail the script
    set +e
    python3 << 'EOFPYTHON'
import os, re, requests, psycopg2, urllib3, sys
urllib3.disable_warnings()

try:
    # Use internal service URL from inside the cluster
    # External URL is for browser/API access, internal service is for pod-to-pod
    external_url = os.getenv("KEYCLOAK_URL", "").rstrip("/")
    
    # Check if we're running inside the cluster (has KUBERNETES_SERVICE_HOST)
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        # Use internal service (faster and more reliable)
        base_url = "http://spending-monitor-keycloak:8080"
        print(f"   Using internal service: {base_url}")
    else:
        # Use external URL (for local development)
        base_url = external_url
        print(f"   Using external URL: {base_url}")
    
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")
    realm = os.getenv("KEYCLOAK_REALM", "spending-monitor")
    
    # Quick health check first (fail fast if Keycloak isn't ready)
    print("   Checking Keycloak availability...")
    try:
        health_response = requests.get(f"{base_url}/health/ready", verify=False, timeout=10)
        if health_response.status_code not in [200, 404]:  # 404 is OK, might not have /health endpoint
            print(f"   ⚠️  Keycloak health check returned {health_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Keycloak not responding: {e}")
        print("   Keycloak may still be starting up. Skipping sync for now.")
        sys.exit(0)  # Exit gracefully
    
    # Get admin token
    print("   Getting admin token...")
    r = requests.post(
        f"{base_url}/realms/master/protocol/openid-connect/token",
        data={"username": "admin", "password": admin_password, "grant_type": "password", "client_id": "admin-cli"},
        verify=False,
        timeout=15
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    print("   ✅ Admin token obtained")
    
    # Connect to database
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    m = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
    if not m:
        print("   ❌ Could not parse DATABASE_URL")
        sys.exit(0)  # Don't fail the migration
    
    user, pwd, host, port, db = m.groups()
    conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=db)
    cur = conn.cursor()
    cur.execute("SELECT id, email, first_name, last_name FROM users")
    users = cur.fetchall()
    print(f"   📊 Found {len(users)} users in database")
    
    # Sync users
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    synced = 0
    default_password = os.getenv("KEYCLOAK_DEFAULT_PASSWORD", "password123")
    
    for uid, email, fname, lname in users:
        # Check if exists
        try:
            r = requests.get(f"{base_url}/admin/realms/{realm}/users?username={uid}", headers=headers, verify=False, timeout=10)
            if r.status_code == 200 and r.json():
                continue
        except requests.exceptions.RequestException:
            print(f"   ⚠️  Failed to check user {uid}, skipping...")
            continue
        
        # Create user
        data = {
            "username": uid,
            "email": email or f"{uid}@example.com",
            "firstName": fname or "",
            "lastName": lname or "",
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": default_password, "temporary": False}]
        }
        
        try:
            r = requests.post(f"{base_url}/admin/realms/{realm}/users", json=data, headers=headers, verify=False, timeout=10)
            if r.status_code == 201:
                synced += 1
                # Assign user role
                r2 = requests.get(f"{base_url}/admin/realms/{realm}/users?username={uid}", headers=headers, verify=False, timeout=10)
                if r2.status_code == 200 and r2.json():
                    user_id = r2.json()[0]["id"]
                    r3 = requests.get(f"{base_url}/admin/realms/{realm}/roles", headers=headers, verify=False, timeout=10)
                    if r3.status_code == 200:
                        for role in r3.json():
                            if role["name"] == "user":
                                requests.post(
                                    f"{base_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm",
                                    json=[role],
                                    headers=headers,
                                    verify=False,
                                    timeout=10
                                )
                                break
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Failed to create user {uid}: {e}")
            continue
    
    print(f"   ✅ Synced {synced} users to Keycloak")
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"   ⚠️  Keycloak sync failed: {e}")
    print("   Note: This is non-critical, migration will continue")
    sys.exit(0)  # Exit with 0 to not fail the migration
EOFPYTHON
    
    # Re-enable error checking
    set -e
    
    # Check exit code (but don't fail on non-zero)
    SYNC_EXIT_CODE=$?
    if [ $SYNC_EXIT_CODE -eq 0 ]; then
        echo "   ✅ Keycloak user sync completed"
    else
        echo "   ⚠️  Sync exited with code $SYNC_EXIT_CODE"
        echo "   Note: This is non-critical, migration continues"
        echo "   Run 'make keycloak-sync-users' later if needed"
    fi
else
    echo "ℹ️  Skipping Keycloak sync:"
    [ "${BYPASS_AUTH:-true}" != "false" ] && echo "   - BYPASS_AUTH=${BYPASS_AUTH:-true} (auth disabled)"
    [ -z "${KEYCLOAK_URL}" ] && echo "   - KEYCLOAK_URL not set"
fi

echo ""
echo "🎉 Database initialization completed!"

# Keep the container running if this is being used as a migration container
# The container will exit after completion, which is the desired behavior for init containers

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

# Setup Keycloak realm and sync users if auth is enabled
echo ""
echo "🔍 Checking if Keycloak setup is needed..."
if [ "${BYPASS_AUTH:-true}" = "false" ] && [ -n "${KEYCLOAK_URL}" ]; then
    echo "✅ Authentication enabled - will setup Keycloak realm and sync users..."
    echo "   Keycloak URL: ${KEYCLOAK_URL}"
    echo "   Realm: ${KEYCLOAK_REALM:-spending-monitor}"
    echo "   Default password: ${KEYCLOAK_DEFAULT_PASSWORD:-password123}"
    
    # Use 'set +e' to ensure any errors don't fail the script
    set +e
    
    # Setup realm and sync users using auth package CLI
    # The auth package is installed in the venv, so use venv's python
    echo ""
    cd /app/packages/auth/src
    /app/venv/bin/python3 -m keycloak.cli setup --sync-users
    
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

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
    
    # Use async DATABASE_URL (asyncpg driver) - this is the default and works with db.database
    # No need to override DATABASE_URL, just use the one from environment
    
    # Load CSV data using the venv python explicitly
    # First, verify asyncpg is importable
    echo "🔍 Verifying asyncpg installation..."
    if /app/venv/bin/python -c "import asyncpg; print(f'✅ asyncpg {asyncpg.__version__} is available')" 2>&1; then
        echo "✅ asyncpg is properly installed"
    else
        echo "⚠️  asyncpg import failed - CSV loading will fail"
    fi
    
    # Note: This may fail due to async/sync engine conflicts. Non-fatal.
    # Temporarily disable exit-on-error for this section
    set +e
    /app/venv/bin/python -m db.scripts.load_csv_data
    CSV_LOAD_EXIT_CODE=$?
    set -e
    
    if [ $CSV_LOAD_EXIT_CODE -eq 0 ]; then
        echo "✅ Sample data loaded successfully"
    else
        echo "⚠️  Sample data loading failed (non-fatal, exit code: $CSV_LOAD_EXIT_CODE)"
        echo "   This is expected if there's an async/sync driver conflict"
        echo "   Sample data can be added via API or direct SQL inserts"
        echo "   Continuing with deployment..."
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

echo "🎉 Database initialization completed!"

# Keep the container running if this is being used as a migration container
# The container will exit after completion, which is the desired behavior for init containers

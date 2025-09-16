# Location-Based Scripts

This directory contains scripts for testing and validating the location-based fraud detection system.

## Scripts

### 🧪 `test-location-fraud-detection.py`
**Purpose**: End-to-end testing of the location-based fraud detection system

**What it does**:
- Tests API health and connectivity
- Simulates user location capture via HTTP headers
- Creates location-based alert rules
- Creates test transactions with different geographic locations
- Verifies alert notifications are triggered for suspicious distances

**Usage**:
```bash
# From the project root
cd packages/api
uv run python ../../scripts/location/test-location-fraud-detection.py
```

**Test Scenarios**:
- **Nearby Transaction**: Brooklyn, NY (~13km from NYC user location) - should NOT trigger alert
- **Distant Transaction**: Los Angeles, CA (~3944km from NYC user location) - should trigger alert

### 🔍 `verify-database-functions.py`
**Purpose**: Direct database validation of location calculation functions

**What it does**:
- Tests the `haversine_distance_km()` PostgreSQL function directly
- Validates the `transaction_location_analysis` VIEW
- Checks user location data persistence
- Verifies distance calculations and risk level categorization

**Usage**:
```bash
# From the project root
cd packages/api
uv run python ../../scripts/location/verify-database-functions.py
```

**Database Components Tested**:
- Distance calculations (NYC to LA, NYC to Brooklyn)
- Transaction location analysis with risk levels
- User location data storage and consent management

## Prerequisites

1. **Running Backend**: Ensure the API server and database are running
   ```bash
   pnpm dev:backend
   ```

2. **Python Dependencies**: Scripts use the API package's `uv` environment which includes:
   - `requests` for HTTP API calls
   - `asyncio` for async database operations
   - `sqlalchemy` for database queries

## Expected Results

### Test Script Output
- ✅ API health check
- ✅ User location capture simulation
- ✅ Transaction creation (both nearby and distant)
- ⚠️ Alert rule creation (may need LLM configuration)
- ✅ Alert notification checking

### Database Verification Output
- ✅ Distance calculations with ~99.8% accuracy
- ✅ Risk level categorization (NORMAL, LOW_RISK, HIGH_RISK, VERY_HIGH_RISK)
- ✅ User location data persistence
- ✅ Real-time transaction location analysis

## Troubleshooting

### Import Errors
If you get Python import errors, ensure you're running from the correct directory:
```bash
cd packages/api
uv run python ../../scripts/location/script-name.py
```

### API Connection Issues
- Verify the API server is running on port 8002
- Check that the database is up and accessible
- Ensure development mode auth bypass is enabled

### Database Connection Issues
- Confirm PostgreSQL is running via `pnpm db:start`
- Verify database migrations are up to date: `pnpm db:upgrade`
- Check that test data is seeded: `pnpm db:seed`

## Integration with Documentation

Related documentation in `docs/location/`:
- `sequence-diagram.md` - System architecture and flow
- `test-results.md` - Detailed test results and analysis

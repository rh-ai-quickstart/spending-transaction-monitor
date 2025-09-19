# Location-Based Scripts

This directory contains development tools for the location-based fraud detection system.

## Scripts

### 📊 `monitor-location-data.py`
**Purpose**: Real-time monitoring of location data during development and testing

**What it does**:
- Monitors user location consent status in real-time
- Tracks GPS coordinate updates in the database
- Displays location accuracy and timestamps
- Provides development feedback during frontend testing

**Usage**:
```bash
# From the project root
cd packages/api
uv run python ../../scripts/location/monitor-location-data.py
```

**Workflow**:
1. Start the monitor script in one terminal
2. Start the frontend and backend services (`pnpm dev`)
3. Open browser to http://localhost:3000
4. Test location consent flow - monitor shows real-time updates

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

### Monitor Output
- ✅ Real-time location consent status updates
- ✅ GPS coordinate tracking (latitude, longitude)
- ✅ Location accuracy monitoring (±meters)
- ✅ Timestamp tracking for location updates
- ✅ Database persistence confirmation

### Development Feedback
- 🔄 `Consent: None | Location: No location` - Initial state
- ✅ `Consent: true | Location: 45.459, -73.423` - After user grants permission

## Troubleshooting

### Import Errors
If you get Python import errors, ensure you're running from the correct directory:
```bash
cd packages/api
uv run python ../../scripts/location/monitor-location-data.py
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

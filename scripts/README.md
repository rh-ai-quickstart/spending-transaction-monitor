# Scripts Directory

This directory contains ad-hoc scripts used for development, testing, and system validation.

## 📁 Directory Structure

### 🧭 `location/` — Location Monitoring
- `monitor-location-data.py`: real-time location data monitoring for development
- `README.md`: usage details

[📖 Location scripts documentation](location/README.md)

### 🧪 `category_normalization/` — Category Normalization Test Harness
- `test_category_normalization.py`: exercises the synonym + embedding-based category normalization pipeline

**Usage (example)**:

```bash
# Run from the repo root (recommended)
python scripts/category_normalization/test_category_normalization.py
```

**Notes**:
- Requires the database to be running and seeded with category synonym + embedding data (see `packages/api/CATEGORY_NORMALIZATION.md`).
- Embeddings are configured via the API config/env (see `packages/api/EMBEDDING_SERVICE.md`).

### ✉️ `notifications/` — Notification Test Harness
- `test_notifications.py`: creates a test user, transactions, and an alert rule to exercise notification flows

**Usage (example)**:

```bash
# Run from the repo root (recommended)
python scripts/notifications/test_notifications.py
```

### 🔧 `status-check.sh` — System Health
General system health and status checking script.

```bash
bash scripts/status-check.sh
```

## 📚 Related Documentation

- **Location system**: [`docs/location/README.md`](../docs/location/README.md)
- **Keycloak / auth**: [`docs/KEYCLOAK_MANAGEMENT.md`](../docs/KEYCLOAK_MANAGEMENT.md)
- **Developer guide**: [`docs/DEVELOPER_GUIDE.md`](../docs/DEVELOPER_GUIDE.md)
- **API docs**: `http://localhost:8002/docs` (when the server is running)

# Scripts Directory

This directory contains ad-hoc scripts used for development and system validation.

## 📁 Directory Structure

### 🧭 `location/` — Location Monitoring
- `monitor-location-data.py`: real-time location data monitoring for development
- `README.md`: usage details

[📖 Location scripts documentation](location/README.md)

### 🔧 `status-check.sh` — System Health
General system health and status checking script.

**Usage**:
```bash
bash scripts/status-check.sh
```

### 🔍 `check-dev-ports.sh` - Port Conflict Detection
Smart port checking script that detects conflicts and provides helpful resolution suggestions before starting development servers.

**Usage**:
```bash
./scripts/check-dev-ports.sh [command]
```

**Commands**:
- `check` - Check development server ports (default)
- `check-all` - Check all ports (including infrastructure)
- `info` - Show port assignments
- `help` - Show help message

**Ports checked**:
- **3000** - Frontend (Vite)
- **6006** - Storybook
- **8000** - API Server
- **5432** - PostgreSQL Database (infrastructure)
- **8080** - Keycloak (infrastructure)
- **3002** - SMTP UI (infrastructure)

**Features**:
- 🔍 Detects port conflicts before starting servers
- 📋 Shows detailed process information for occupied ports
- 💡 Provides specific suggestions to resolve conflicts
- 🎯 Smart process detection (recognizes uvicorn, vite, proxy processes)

**Makefile integration**:
```bash
make check-ports      # Check development ports
make check-all-ports  # Check all ports
make port-info        # Show port assignments
make dev              # Automatically runs port check
```

## 🚀 Quick Start

### For Development Environment Setup
```bash
# Check if development ports are available
make check-ports

# Start full development environment (includes automatic port checking)
make dev
```

### For Authentication Development
```bash
# Set up Keycloak (production)
python scripts/auth/setup_keycloak.py

# Development mode (auth bypass enabled)
pnpm dev:backend
```

### For Location System Development
```bash
# Start the backend and frontend systems
pnpm dev

# Monitor location data in real-time (in separate terminal)
cd packages/api
uv run python ../../scripts/location/monitor-location-data.py

# Open browser to http://localhost:3000 and test location consent flow
```

### For System Health Check
```bash
# Check overall system status
bash scripts/status-check.sh
```

## 🏗️ Development Workflow

### 1. Environment Setup
```bash
# Initial project setup
pnpm setup

# Check for port conflicts before starting
make check-ports

# Start development environment (includes automatic port checking)
make dev  # Full stack with infrastructure
# OR
pnpm dev  # Direct package dev commands
```

### 2. Feature Development
```bash
bash scripts/status-check.sh
```

### 3. Database Management
```bash
# Check database migrations
pnpm db:upgrade
pnpm db:verify

# Start/stop database services
pnpm db:start
pnpm db:stop
```

## 🎯 Script Categories

### Development Scripts
- **Port Checking**: Smart port conflict detection and resolution suggestions
- **Location Monitoring**: Real-time location data development monitoring
- **Auth Development**: Keycloak setup and development utilities
- **System Utilities**: Health checks and status monitoring

### Monitoring Scripts
- **Location System**: Real-time GPS coordinate and consent monitoring
- **System Health**: Database and API server status checking

## 📊 Expected Results

### Location System Monitoring
- ✅ Real-time GPS coordinate capture
- ✅ User location consent tracking
- ✅ Location accuracy monitoring
- ✅ Database location data persistence

### Authentication System
- ✅ Development auth bypass working
- ✅ JWT token validation
- ✅ User context management
- ✅ Route protection

### System Health
- ✅ API server responsive
- ✅ Database connectivity
- ✅ All services running
- ✅ Migration status current

## 🔧 Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure you're running from correct directory
cd packages/api
uv run python ../../scripts/location/monitor-location-data.py
```

**Permission Errors**:
```bash
# Make scripts executable
chmod +x scripts/auth/auth-dev.sh
chmod +x scripts/status-check.sh
```

**Database Connection Issues**:
```bash
# Restart database
pnpm db:stop && pnpm db:start
pnpm db:upgrade
```

### Getting Help

1. **Check Individual READMEs**: Each subdirectory has detailed documentation
2. **Review Logs**: Check terminal output for specific error messages  
3. **Verify Prerequisites**: Ensure all dependencies are installed
4. **Check Environment**: Verify environment variables are set correctly

## 📚 Related Documentation

- **Location system**: [`docs/location/README.md`](../docs/location/README.md)
- **Keycloak / auth**: [`docs/KEYCLOAK_MANAGEMENT.md`](../docs/KEYCLOAK_MANAGEMENT.md)
- **Developer guide**: [`docs/DEVELOPER_GUIDE.md`](../docs/DEVELOPER_GUIDE.md)
- **API docs**: `http://localhost:8002/docs` (when the server is running)

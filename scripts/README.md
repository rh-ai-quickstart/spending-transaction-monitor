# Scripts Directory

This directory contains organized scripts for testing, development, and system validation.

## 📁 Directory Structure

### 🔑 `auth/` - Authentication Scripts
Scripts for authentication setup, development workflows, and Keycloak integration.

**Scripts**:
- `setup_keycloak.py` - Automated Keycloak configuration
- `auth-dev.sh` - Development authentication utilities

**Use Cases**:
- Setting up OAuth2/OIDC authentication
- Managing development auth bypass
- Configuring production authentication

[📖 Detailed Documentation](auth/README.md)

### 📍 `location/` - Location-Based Scripts  
Scripts for testing and validating the location-based fraud detection system.

**Scripts**:
- `monitor-location-data.py` - Real-time location data monitoring for development

**Use Cases**:
- Monitoring location capture during development
- Real-time validation of location consent flow
- Debugging location-based fraud detection system

[📖 Detailed Documentation](location/README.md)

### 🔧 `status-check.sh` - System Health
General system health and status checking script.

**Usage**:
```bash
bash scripts/status-check.sh
```

## 🚀 Quick Start

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

# Start development environment
pnpm dev  # Full stack with auth bypass
# OR
pnpm dev:backend  # Backend only
```

### 2. Feature Development
```bash
# Test authentication features
cd scripts/auth && ./auth-dev.sh

# Monitor location features in development
cd packages/api
uv run python ../../scripts/location/monitor-location-data.py

# Check system health
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

- **Location System**: [docs/location/README.md](../docs/location/README.md)
- **Authentication**: [docs/auth/README.md](../docs/auth/README.md) 
- **Development Guide**: [docs/DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md)
- **API Documentation**: http://localhost:8002/docs (when server is running)

This organized script structure provides clear separation of concerns and comprehensive testing coverage for all major system components.

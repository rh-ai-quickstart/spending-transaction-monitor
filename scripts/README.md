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
- `test-location-fraud-detection.py` - End-to-end system testing
- `verify-database-functions.py` - Database function validation

**Use Cases**:
- Testing location capture and processing
- Validating distance calculations
- Verifying fraud detection algorithms

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

### For Location System Testing
```bash
# Start the backend system
pnpm dev:backend

# Run end-to-end location fraud detection test
cd packages/api
uv run python ../../scripts/location/test-location-fraud-detection.py

# Verify database location functions
uv run python ../../scripts/location/verify-database-functions.py
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

### 2. Feature Testing
```bash
# Test authentication features
cd scripts/auth && ./auth-dev.sh

# Test location features  
cd packages/api
uv run python ../../scripts/location/test-location-fraud-detection.py

# Check system health
bash scripts/status-check.sh
```

### 3. Database Validation
```bash
# Verify location database functions
cd packages/api
uv run python ../../scripts/location/verify-database-functions.py

# Check database migrations
pnpm db:upgrade
pnpm db:verify
```

## 🎯 Script Categories

### Testing Scripts
- **Location Testing**: Comprehensive fraud detection system validation
- **Authentication Testing**: Auth flow and security validation
- **Database Testing**: Function and schema verification

### Development Scripts
- **Auth Development**: Keycloak setup and development utilities
- **System Utilities**: Health checks and status monitoring

### Validation Scripts
- **End-to-End Testing**: Full system integration testing
- **Component Testing**: Individual feature validation
- **Performance Testing**: Database function benchmarks

## 📊 Expected Results

### Location System Tests
- ✅ 99.8% accurate distance calculations
- ✅ Real-time risk assessment
- ✅ Transaction location analysis
- ✅ User location persistence

### Authentication Tests
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
uv run python ../../scripts/location/script-name.py
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

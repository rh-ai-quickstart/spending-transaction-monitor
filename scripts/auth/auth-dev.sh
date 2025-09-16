#!/bin/bash

# 🔐 Authentication Development Helper Script
# Usage: ./scripts/auth-dev.sh <command>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${BLUE}🔐 $1${NC}"
    echo "======================================"
}

# Check if service is running
check_service() {
    local url=$1
    local name=$2
    if curl -sf "$url" >/dev/null 2>&1; then
        log_success "$name ($url)"
        return 0
    else
        log_error "$name ($url) - Not running"
        return 1
    fi
}

# Show help
show_help() {
    log_header "Authentication Development Commands"
    echo ""
    echo "Service Management:"
    echo "  setup           - Setup Keycloak with automated configuration"
    echo "  services-up     - Start all development services (DB + instructions for Keycloak)"
    echo "  services-down   - Stop all services"
    echo "  status          - Check status of all services"
    echo ""
    echo "Testing:"
    echo "  test            - Run all authentication tests"
    echo "  test-watch      - Run auth tests in watch mode"
    echo ""
    echo "Development:"
    echo "  dev-full        - Start full dev environment with auth setup"
    echo "  demo            - Show auth demo instructions"
    echo ""
    echo "Keycloak Management:"
    echo "  keycloak-logs   - Show Keycloak container logs (if containerized)"
    echo "  keycloak-stop   - Stop Keycloak container"
    echo ""
    echo "Examples:"
    echo "  ./scripts/auth-dev.sh setup"
    echo "  ./scripts/auth-dev.sh test"
    echo "  ./scripts/auth-dev.sh status"
    echo ""
}

# Setup Keycloak
setup_keycloak() {
    log_header "Setting up Keycloak configuration"
    log_info "Running automated setup script..."
    
    if python scripts/setup_keycloak.py; then
        log_success "Keycloak setup completed!"
        echo ""
        echo "📋 Created:"
        echo "   • Realm: spending-monitor"
        echo "   • Client: spending-monitor (OIDC, PKCE enabled)"
        echo "   • Test user: testuser@example.com / password123"
        echo "   • Roles: user, admin"
        echo ""
        echo "🌐 Access Keycloak at: http://localhost:8080"
    else
        log_error "Keycloak setup failed. Check that Keycloak is running on port 8080"
        exit 1
    fi
}

# Start services
services_up() {
    log_header "Starting development services"
    
    log_info "Starting PostgreSQL database..."
    pnpm db:start
    
    log_success "Database started"
    log_warning "Note: You need to start Keycloak separately"
    echo ""
    echo "To start Keycloak:"
    echo "  1. Using Docker: docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev"
    echo "  2. Or download and run Keycloak locally"
    echo "  3. Then run: ./scripts/auth-dev.sh setup"
}

# Stop services
services_down() {
    log_header "Stopping development services"
    
    log_info "Stopping database..."
    pnpm db:stop
    
    log_info "Attempting to stop Keycloak container..."
    if command -v podman >/dev/null 2>&1; then
        podman stop keycloak 2>/dev/null || log_warning "No Keycloak container found (podman)"
    elif command -v docker >/dev/null 2>&1; then
        docker stop keycloak 2>/dev/null || log_warning "No Keycloak container found (docker)"
    fi
    
    log_success "Services stopped"
}

# Check status
check_status() {
    log_header "Service Status"
    
    check_service "http://localhost:8000/health" "API (8000)"
    check_service "http://localhost:8080/health/ready" "Keycloak (8080)"
    check_service "http://localhost:3000" "UI (3000)"
    
    echo ""
    echo "OIDC Endpoints (if Keycloak is running):"
    echo "  • OIDC Config: http://localhost:8080/realms/spending-monitor/.well-known/openid-configuration"
    echo "  • JWKS: http://localhost:8080/realms/spending-monitor/protocol/openid-connect/certs"
}

# Run auth tests
run_tests() {
    log_header "Running authentication tests"
    cd packages/api
    uv run pytest tests/test_auth* -v
    cd ../..
}

# Run tests in watch mode
run_tests_watch() {
    log_header "Running auth tests in watch mode"
    cd packages/api
    log_info "Press Ctrl+C to stop watching..."
    uv run pytest tests/test_auth* -v --tb=short -f
    cd ../..
}

# Full development setup
dev_full() {
    log_header "Starting full development environment"
    
    services_up
    echo ""
    log_info "Waiting 5 seconds for services to start..."
    sleep 5
    
    log_info "Setting up Keycloak (this may fail if Keycloak isn't running yet)..."
    setup_keycloak || log_warning "Keycloak setup failed - you may need to set it up manually later"
    
    log_info "Starting development environment..."
    pnpm dev
}

# Show demo instructions
show_demo() {
    log_header "Authentication Demo Instructions"
    echo ""
    echo "🔐 Test Authentication Flow:"
    echo ""
    echo "1. Start services:"
    echo "   ./scripts/auth-dev.sh services-up"
    echo ""
    echo "2. Start Keycloak (in another terminal):"
    echo "   docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev"
    echo ""
    echo "3. Setup Keycloak:"
    echo "   ./scripts/auth-dev.sh setup"
    echo ""
    echo "4. Start development environment:"
    echo "   pnpm dev"
    echo ""
    echo "5. Test endpoints:"
    echo "   • Public: http://localhost:8000/health"
    echo "   • Protected: http://localhost:8000/users (requires auth)"
    echo "   • UI: http://localhost:3000"
    echo ""
    echo "📋 Test credentials:"
    echo "   • Email: testuser@example.com"
    echo "   • Password: password123"
}

# Keycloak logs
keycloak_logs() {
    log_info "Showing Keycloak logs..."
    if command -v podman >/dev/null 2>&1; then
        podman logs -f keycloak 2>/dev/null || log_warning "No Keycloak container found (podman)"
    elif command -v docker >/dev/null 2>&1; then
        docker logs -f keycloak 2>/dev/null || log_warning "No Keycloak container found (docker)"
    else
        log_error "Neither podman nor docker found"
    fi
}

# Keycloak stop
keycloak_stop() {
    log_info "Stopping Keycloak container..."
    if command -v podman >/dev/null 2>&1; then
        podman stop keycloak || log_warning "No Keycloak container found (podman)"
    elif command -v docker >/dev/null 2>&1; then
        docker stop keycloak || log_warning "No Keycloak container found (docker)"
    else
        log_error "Neither podman nor docker found"
    fi
}

# Main command handler
case "${1:-help}" in
    help|--help|-h)
        show_help
        ;;
    setup)
        setup_keycloak
        ;;
    services-up)
        services_up
        ;;
    services-down)
        services_down
        ;;
    status)
        check_status
        ;;
    test)
        run_tests
        ;;
    test-watch)
        run_tests_watch
        ;;
    dev-full)
        dev_full
        ;;
    demo)
        show_demo
        ;;
    keycloak-logs)
        keycloak_logs
        ;;
    keycloak-stop)
        keycloak_stop
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

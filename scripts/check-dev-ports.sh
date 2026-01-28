#!/bin/bash

# Port checking script for development environment
# Checks if required ports are available and shows helpful error messages

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Development ports to check (port|description format)
DEV_PORTS="3000|Frontend (Vite)|6006|Storybook|8000|API Server"

# Infrastructure ports (optional check)
INFRA_PORTS="5432|PostgreSQL Database|8080|Keycloak|3002|SMTP UI (smtp4dev)"

# Function to check what's using a port
check_port_usage() {
    local port=$1
    local service_name=$2

    # Check if port is in use
    if lsof -i :$port >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port ($service_name) is already in use${NC}"
        echo ""
        echo -e "${BLUE}Process details:${NC}"
        lsof -i :$port | while read line; do
            if [[ $line != COMMAND* ]]; then
                echo "   $line"
            else
                printf "   %-15s %-8s %-8s %-6s %-10s %s\n" "COMMAND" "PID" "USER" "FD" "TYPE" "NAME"
                echo "   $line"
            fi
        done
        echo ""

        # Get PID and suggest kill command
        local pid=$(lsof -t -i :$port | head -n1)
        if [[ -n $pid ]]; then
            local process_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            echo -e "${YELLOW}💡 To free this port, you can try:${NC}"
            echo "   kill $pid"
            echo "   # or if it's stubborn:"
            echo "   kill -9 $pid"
            echo ""

            # Special suggestions based on common processes
            case $process_name in
                *uvicorn*|*python*)
                    echo -e "${YELLOW}💡 This looks like a Python/FastAPI server. You might want to:${NC}"
                    echo "   - Check if another development server is already running"
                    echo "   - Stop it with Ctrl+C if it's running in a terminal"
                    echo "   - Use 'pkill -f uvicorn' to stop all uvicorn processes"
                    ;;
                *vite*|*node*)
                    echo -e "${YELLOW}💡 This looks like a Node.js/Vite server. You might want to:${NC}"
                    echo "   - Check if another development server is already running"
                    echo "   - Stop it with Ctrl+C if it's running in a terminal"
                    echo "   - Use 'pkill -f vite' to stop all Vite processes"
                    ;;
                *gvproxy*|*proxy*)
                    echo -e "${YELLOW}💡 This looks like a proxy process (possibly from Docker/Podman). You might want to:${NC}"
                    echo "   - Check if containers are running: podman ps"
                    echo "   - Stop containers if needed: podman stop <container_name>"
                    echo "   - Restart Podman Desktop if using it"
                    ;;
            esac
            echo ""
        fi
        return 1
    else
        echo -e "${GREEN}✅ Port $port ($service_name) is available${NC}"
        return 0
    fi
}

# Function to check all ports
check_all_ports() {
    local check_infra=$1
    local failed=0

    echo -e "${BLUE}🔍 Checking development server ports...${NC}"
    echo ""

    # Check development ports
    IFS='|' read -ra DEV_PORT_ARRAY <<< "$DEV_PORTS"
    for ((i=0; i<${#DEV_PORT_ARRAY[@]}; i+=2)); do
        local port="${DEV_PORT_ARRAY[i]}"
        local desc="${DEV_PORT_ARRAY[i+1]}"
        if ! check_port_usage "$port" "$desc"; then
            failed=1
        fi
    done

    # Optionally check infrastructure ports
    if [[ $check_infra == "true" ]]; then
        echo ""
        echo -e "${BLUE}🔍 Checking infrastructure ports...${NC}"
        echo ""
        IFS='|' read -ra INFRA_PORT_ARRAY <<< "$INFRA_PORTS"
        for ((i=0; i<${#INFRA_PORT_ARRAY[@]}; i+=2)); do
            local port="${INFRA_PORT_ARRAY[i]}"
            local desc="${INFRA_PORT_ARRAY[i+1]}"
            check_port_usage "$port" "$desc" || true  # Don't fail on infra ports
        done
    fi

    echo ""
    if [[ $failed -eq 1 ]]; then
        echo -e "${RED}❌ Some development ports are occupied. Please free them before starting development servers.${NC}"
        echo ""
        echo -e "${YELLOW}💡 Quick fix - try running:${NC}"
        echo "   make stop-dev    # Stop any running development servers"
        echo "   # Then run 'make dev' again"
        echo ""
        exit 1
    else
        echo -e "${GREEN}✅ All development ports are available!${NC}"
        return 0
    fi
}

# Function to show port information
show_port_info() {
    echo -e "${BLUE}📋 Development Environment Ports:${NC}"
    echo ""
    IFS='|' read -ra DEV_PORT_ARRAY <<< "$DEV_PORTS"
    for ((i=0; i<${#DEV_PORT_ARRAY[@]}; i+=2)); do
        local port="${DEV_PORT_ARRAY[i]}"
        local desc="${DEV_PORT_ARRAY[i+1]}"
        echo "   $port - $desc"
    done
    echo ""
    echo -e "${BLUE}📋 Infrastructure Ports:${NC}"
    echo ""
    IFS='|' read -ra INFRA_PORT_ARRAY <<< "$INFRA_PORTS"
    for ((i=0; i<${#INFRA_PORT_ARRAY[@]}; i+=2)); do
        local port="${INFRA_PORT_ARRAY[i]}"
        local desc="${INFRA_PORT_ARRAY[i+1]}"
        echo "   $port - $desc"
    done
    echo ""
}

# Main logic
case "${1:-check}" in
    "check")
        check_all_ports false
        ;;
    "check-all")
        check_all_ports true
        ;;
    "info")
        show_port_info
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  check      Check development server ports (default)"
        echo "  check-all  Check all ports (including infrastructure)"
        echo "  info       Show port information"
        echo "  help       Show this help message"
        echo ""
        exit 0
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information."
        exit 1
        ;;
esac
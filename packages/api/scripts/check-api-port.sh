#!/bin/bash

# Simple port checker for API development server
# Checks only the API port (8000) and gives specific error messages

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get API port from environment or default to 8000
API_PORT=${API_PORT:-8000}

echo -e "🔍 Checking API port $API_PORT..."

# Check if port is in use
if lsof -i :$API_PORT >/dev/null 2>&1; then
    echo -e "${RED}❌ Port $API_PORT is already in use!${NC}"
    echo ""
    echo -e "Process details:"
    lsof -i :$API_PORT | while read line; do
        if [[ $line != COMMAND* ]]; then
            echo "   $line"
        else
            printf "   %-15s %-8s %-8s %-6s %-10s %s\n" "COMMAND" "PID" "USER" "FD" "TYPE" "NAME"
            echo "   $line"
        fi
    done
    echo ""

    # Get PID and suggest kill command
    pid=$(lsof -t -i :$API_PORT | head -n1)
    if [[ -n $pid ]]; then
        process_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
        echo -e "${YELLOW}💡 To free port $API_PORT:${NC}"
        echo "   kill $pid"
        echo ""

        # Special suggestions
        case $process_name in
            *uvicorn*|*python*)
                echo -e "${YELLOW}💡 This looks like another API server. Try:${NC}"
                echo "   - Press Ctrl+C if it's running in a terminal"
                echo "   - Run: pkill -f uvicorn"
                echo "   - Run: make stop-dev"
                ;;
            *gvproxy*|*proxy*)
                echo -e "${YELLOW}💡 This looks like a proxy (Docker/Podman). Try:${NC}"
                echo "   - Check containers: podman ps"
                echo "   - Stop containers: make stop-local"
                ;;
        esac
    fi
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ Port $API_PORT is available${NC}"
    exit 0
fi
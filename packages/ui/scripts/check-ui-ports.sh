#!/bin/bash

# Port checker for UI development servers (Vite + Storybook)
# Checks ports 3000 (Vite) and 6006 (Storybook)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# UI ports
VITE_PORT=3000
STORYBOOK_PORT=6006

check_port() {
    local port=$1
    local service=$2

    echo -e "🔍 Checking $service port $port..."

    if lsof -i :$port >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port ($service) is already in use!${NC}"
        echo ""
        echo "Process details:"
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
        pid=$(lsof -t -i :$port | head -n1)
        if [[ -n $pid ]]; then
            echo -e "${YELLOW}💡 To free port $port:${NC}"
            echo "   kill $pid"
            echo ""
        fi
        return 1
    else
        echo -e "${GREEN}✅ Port $port ($service) is available${NC}"
        return 0
    fi
}

# Check both ports
echo "🔍 Checking UI development server ports..."
echo ""

failed=0

if ! check_port $VITE_PORT "Vite"; then
    failed=1
fi

echo ""

if ! check_port $STORYBOOK_PORT "Storybook"; then
    failed=1
fi

echo ""

if [[ $failed -eq 1 ]]; then
    echo -e "${RED}❌ Some UI ports are occupied. Please free them before starting development servers.${NC}"
    echo ""
    echo -e "${YELLOW}💡 Quick fixes:${NC}"
    echo "   make stop-dev           # Stop all dev servers"
    echo "   pkill -f vite           # Stop Vite servers"
    echo "   pkill -f storybook      # Stop Storybook servers"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ All UI ports are available!${NC}"
    exit 0
fi
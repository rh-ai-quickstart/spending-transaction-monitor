#!/bin/bash

# Test Alert Rules End-to-End Script
# This script tests the complete flow: seed data -> create alert rule -> trigger alert
#
# Usage:
#   ./test_alert_rules.sh                    # Test all alert rules
#   ./test_alert_rules.sh <filename>         # Test specific alert rule file
#   ./test_alert_rules.sh --list             # List available test files
#   ./test_alert_rules.sh --help             # Show help

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Configuration
API_BASE_URL="http://localhost:8000/api"
JSON_DIR="json"

# Auth Configuration
# You can provide AUTH_TOKEN directly, or we'll get one using admin credentials
AUTH_TOKEN="${AUTH_TOKEN:-}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

# Counter variables
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to get auth token from Keycloak using admin credentials
get_auth_token() {
    if [[ -n "$AUTH_TOKEN" ]]; then
        echo "$AUTH_TOKEN"
        return 0
    fi
    
    local token_url="${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    
    local response=$(curl -s -X POST "$token_url" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KEYCLOAK_ADMIN_USER}" \
        -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        -d "client_id=admin-cli")
    
    local access_token=""
    if command -v jq >/dev/null 2>&1; then
        access_token=$(echo "$response" | jq -r '.access_token // ""')
    else
        access_token=$(echo "$response" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")
    fi
    
    if [[ -z "$access_token" || "$access_token" == "null" ]]; then
        echo -e "${YELLOW}⚠️  Could not obtain auth token from Keycloak${NC}" >&2
        echo -e "${YELLOW}   Keycloak URL: $token_url${NC}" >&2
        echo -e "${YELLOW}   Admin user: $KEYCLOAK_ADMIN_USER${NC}" >&2
        echo -e "${YELLOW}   Response: $response${NC}" >&2
        echo -e "${YELLOW}   Continuing without authentication (BYPASS_AUTH should be enabled)${NC}" >&2
        echo ""
        return 1
    fi
    
    echo "$access_token"
    return 0
}

# Function to show usage
show_help() {
    echo -e "${BLUE}Alert Rules End-to-End Test Script${NC}"
    echo "============================================"
    echo "Usage:"
    echo "  $0                          # Test all alert rules"
    echo "  $0 <filename>               # Test specific alert rule file"
    echo "  $0 --list                   # List available test files"
    echo "  $0 --help                   # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 alert_rule_spending_daily_300_trigger.json"
    echo "  $0 spending_daily_300       # Partial filename match"
    echo ""
    echo "Environment Variables:"
    echo "  AUTH_TOKEN              Optional: Pre-obtained JWT token (bypasses Keycloak)"
    echo "  KEYCLOAK_URL            Keycloak server URL (default: http://localhost:8080)"
    echo "  KEYCLOAK_ADMIN_USER     Admin username (default: admin)"
    echo "  KEYCLOAK_ADMIN_PASSWORD Admin password (default: admin)"
    echo ""
}

# Function to list available test files
list_files() {
    echo -e "${BLUE}Available Alert Rule Test Files:${NC}"
    echo "============================================"
    local count=0
    local listed_files=()
    for json_file in "$JSON_DIR"/alert_rule_*.json "$JSON_DIR"/alert_*.json; do
        if [[ -f "$json_file" ]] && [[ "$(basename "$json_file")" != "alert_rules.txt" ]]; then
            local filename=$(basename "$json_file")
            # Skip if it's already counted (in case of overlap)
            if [[ ! " ${listed_files[@]} " =~ " ${filename} " ]]; then
                count=$((count + 1))
                echo -e "${YELLOW}${count}.${NC} $filename"
                listed_files+=("$filename")
            fi
        fi
    done
    echo ""
    echo -e "${GREEN}Total: $count test files available${NC}"
}

# Parse command line arguments
SPECIFIC_FILE=""
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --list|-l)
        list_files
        exit 0
        ;;
    "")
        # No arguments - test all files (default behavior)
        ;;
    *)
        # Specific file argument
        SPECIFIC_FILE="$1"
        ;;
esac

# Display header
if [[ -n "$SPECIFIC_FILE" ]]; then
    echo -e "${BLUE}🧪 Testing Specific Alert Rule: ${SPECIFIC_FILE}${NC}"
else
    echo -e "${BLUE}🧪 Starting Alert Rules End-to-End Tests (All Files)${NC}"
fi
echo "============================================"

# Check if API server is running
echo -e "${YELLOW}📡 Checking API server availability...${NC}"
if ! curl -s "http://localhost:8000/health/" > /dev/null; then
    echo -e "${RED}❌ API server is not running at http://localhost:8000${NC}"
    echo -e "${YELLOW}💡 Please start the API server first:${NC}"
    echo "   cd packages/api && npm run dev"
    exit 1
fi
echo -e "${GREEN}✅ API server is running${NC}"
echo ""

# Get authentication token
echo -e "${YELLOW}🔐 Getting authentication token...${NC}"
AUTH_TOKEN=$(get_auth_token)
AUTH_STATUS=$?
if [[ $AUTH_STATUS -eq 0 ]]; then
    echo -e "${GREEN}✅ Authentication token obtained${NC}"
    AUTH_HEADER="Authorization: Bearer $AUTH_TOKEN"
else
    echo -e "${YELLOW}⚠️  No authentication token - requests will be made without auth${NC}"
    AUTH_HEADER=""
fi
echo ""

# Function to extract alert_text from JSON file
extract_alert_text() {
    local file="$1"
    if [[ -f "$file" ]]; then
        # Try to extract alert_text using jq if available, otherwise use python
        if command -v jq >/dev/null 2>&1; then
            jq -r '.alert_text // empty' "$file" 2>/dev/null || echo ""
        else
            python3 -c "
import json, sys
try:
    with open('$file', 'r') as f:
        data = json.load(f)
        print(data.get('alert_text', ''))
except:
    pass
" 2>/dev/null || echo ""
        fi
    else
        echo ""
    fi
}

# Function to display test data preview with adjusted dates
display_test_data_preview() {
    local json_file="$1"
    
    if [[ ! -f "$json_file" ]]; then
        echo -e "${RED}❌ JSON file not found: $json_file${NC}"
        return
    fi
    
    echo -e "${BLUE}📊 Test Data Preview:${NC}"
    echo ""
    
    # Display User Data
    echo -e "${YELLOW}👤 USER DATA:${NC}"
    echo "┌─────────────────┬─────────────────────────────────────────────────────────┐"
    echo "│ Field           │ Value                                                   │"
    echo "├─────────────────┼─────────────────────────────────────────────────────────┤"
    
    if command -v jq >/dev/null 2>&1; then
        local user_id=$(jq -r '.user.id // "N/A"' "$json_file")
        local user_email=$(jq -r '.user.email // "N/A"' "$json_file")
        local user_name=$(jq -r '(.user.first_name // "") + " " + (.user.last_name // "")' "$json_file" | sed 's/^ *//;s/ *$//')
        local user_city=$(jq -r '.user.address_city // "N/A"' "$json_file")
        local user_state=$(jq -r '.user.address_state // "N/A"' "$json_file")
        
        printf "│ %-15s │ %-55s │\n" "ID" "$user_id"
        printf "│ %-15s │ %-55s │\n" "Email" "$user_email"
        printf "│ %-15s │ %-55s │\n" "Name" "$user_name"
        printf "│ %-15s │ %-55s │\n" "City" "$user_city"
        printf "│ %-15s │ %-55s │\n" "State" "$user_state"
    else
        printf "│ %-15s │ %-55s │\n" "Error" "jq not available for data preview"
    fi
    
    echo "└─────────────────┴─────────────────────────────────────────────────────────┘"
    echo ""
    
    # Display Transaction Data with adjusted dates
    echo -e "${YELLOW}💳 TRANSACTION DATA (Adjusted to Current Time):${NC}"
    echo "┌────┬─────────────────┬────────┬──────────────────────────┬─────────────────┬────────────┐"
    echo "│ #  │ Date            │ Amount │ Description              │ Merchant        │ Category   │"
    echo "├────┼─────────────────┼────────┼──────────────────────────┼─────────────────┼────────────┤"
    
    if command -v jq >/dev/null 2>&1; then
        # Get current time and latest transaction time
        local current_time=$(date +%s)
        local latest_txn_time=$(jq -r '.transactions | max_by(.transaction_date) | .transaction_date' "$json_file")
        
        # Convert latest transaction time to epoch
        local latest_epoch=0
        if [[ -n "$latest_txn_time" && "$latest_txn_time" != "null" ]]; then
            # Try to parse the date - handle different formats
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS date command
                latest_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$latest_txn_time" +%s 2>/dev/null || echo "$current_time")
            else
                # Linux date command
                latest_epoch=$(date -d "$latest_txn_time" +%s 2>/dev/null || echo "$current_time")
            fi
        else
            latest_epoch=$current_time
        fi
        
        local time_diff=$((current_time - latest_epoch))
        
        # Sort transactions by date and display with adjusted dates
        local counter=1
        jq -r '.transactions | sort_by(.transaction_date) | .[] | [.transaction_date, .amount, .description, .merchant_name, .merchant_category] | @tsv' "$json_file" | while IFS=$'\t' read -r orig_date amount desc merchant category; do
            # Convert original date to epoch
            local orig_epoch=0
            if [[ -n "$orig_date" && "$orig_date" != "null" ]]; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    # macOS date command
                    orig_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$orig_date" +%s 2>/dev/null || echo "$current_time")
                else
                    # Linux date command
                    orig_epoch=$(date -d "$orig_date" +%s 2>/dev/null || echo "$current_time")
                fi
            else
                orig_epoch=$current_time
            fi
            
            # Calculate adjusted date
            local new_timestamp=$((orig_epoch + time_diff))
            local adjusted_date=""
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS date command
                adjusted_date=$(date -r "$new_timestamp" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "Invalid Date")
            else
                # Linux date command
                adjusted_date=$(date -d "@$new_timestamp" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "Invalid Date")
            fi
            
            # Format and display
            local formatted_amount=$(printf "$%.2f" "$amount")
            local truncated_desc=$(printf "%.24s" "$desc")
            local truncated_merchant=$(printf "%.15s" "$merchant")
            local truncated_category=$(printf "%.10s" "$category")
            
            printf "│ %-2d │ %-15s │ %6s │ %-24s │ %-15s │ %-10s │\n" "$counter" "$adjusted_date" "$formatted_amount" "$truncated_desc" "$truncated_merchant" "$truncated_category"
            counter=$((counter + 1))
        done
    else
        printf "│ %-2s │ %-15s │ %-6s │ %-24s │ %-15s │ %-10s │\n" "??" "jq not available" "N/A" "Cannot preview data" "N/A" "N/A"
    fi
    
    echo "└────┴─────────────────┴────────┴──────────────────────────┴─────────────────┴────────────┘"
    echo ""
}

# Function to test a single alert rule file
test_alert_rule() {
    local json_file="$1"
    local filename=$(basename "$json_file")
    local seed_command=""
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}🔄 Testing: ${filename}${NC}"
    echo "----------------------------------------"
    
    # Map filename to seed command
    case "$filename" in
        "alert_rule_dining_30d_avg_40pct.json")
            seed_command="seed:dining-30d-avg-40pct" ;;
        "alert_rule_location_far_from_last_known_trigger.json")
            seed_command="seed:location-far-from-known" ;;
        "alert_rule_merchant_same_day_duplicates_trigger.json")
            seed_command="seed:merchant-same-day-dupes" ;;
        "alert_rule_pattern_new_recurring_detected_trigger.json")
            seed_command="seed:pattern-new-recurring" ;;
        "alert_rule_pattern_recurring_charge_20pct_trigger.json")
            seed_command="seed:pattern-recurring-20pct" ;;
        "alert_rule_pattern_recurring_charge_plus5_trigger.json")
            seed_command="seed:pattern-recurring-plus5" ;;
        "alert_rule_spending_daily_300_trigger.json")
            seed_command="seed:spending-daily-300" ;;
        "alert_rule_spending_dining_avg_plus20_trigger.json")
            seed_command="seed:dining-avg-plus20" ;;
        "alert_rule_spending_electronics_apple_3x_trigger.json")
            seed_command="seed:spending-electronics-3x" ;;
        "alert_rule_spending_weekly_500_trigger.json")
            seed_command="seed:spending-weekly-500" ;;
        "alert_rule_transaction_last_hour.json")
            seed_command="seed:last-hour" ;;
        "alert_rule_spending_amount_dining.json")
            seed_command="seed:dining" ;;
        "alert_charged_significantly_more_same_merchant.json")
            seed_command="seed:charged-more-same-merchant" ;;
        "alert_more_than_20_dollars_same_merchant.json")
            seed_command="seed:more-than-20-same-merchant" ;;
        "alert_outside_home_state_sample.json")
            seed_command="seed:outside-home-state" ;;
        "alert_over_500_transaction.json")
            seed_command="seed:over-500-transaction" ;;
        *)
            echo -e "${YELLOW}⚠️  No seed command mapped for ${filename}, skipping...${NC}"
            return ;;
    esac
    
    # Extract alert text from JSON file
    local alert_text=$(extract_alert_text "$json_file")
    
    if [[ -z "$alert_text" ]]; then
        echo -e "${YELLOW}⚠️  No alert_text found in ${filename}, skipping...${NC}"
        return
    fi
    
    echo -e "${YELLOW}📝 Alert Text: ${alert_text}${NC}"
    
    # Display test data preview with adjusted dates
    display_test_data_preview "$json_file"
    
    # Step 1: Seed the data
    echo -e "${YELLOW}🌱 Seeding data with: pnpm ${seed_command} --force${NC}"
    if pnpm "$seed_command" --force > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Data seeded successfully${NC}"
    else
        echo -e "${RED}❌ Failed to seed data${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo ""
        return
    fi
    
    # Step 2a: Validate alert rule via API
    echo -e "${YELLOW}🔍 Validating alert rule via API...${NC}"
    
    local validate_response
    if [[ -n "$AUTH_HEADER" ]]; then
        validate_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules/validate" \
            -H "Content-Type: application/json" \
            -H "$AUTH_HEADER" \
            -d "{\"natural_language_query\": \"$alert_text\"}")
    else
        validate_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules/validate" \
            -H "Content-Type: application/json" \
            -d "{\"natural_language_query\": \"$alert_text\"}")
    fi
    
    local validate_http_status=$(echo "$validate_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    local validate_response_body=$(echo "$validate_response" | sed -e 's/HTTPSTATUS:.*//g')
    
    if [[ "$validate_http_status" == "200" ]]; then
        echo -e "${GREEN}✅ Alert rule validation successful (HTTP 200)${NC}"
        
        # Extract validation status and details
        local validation_status=""
        local validation_message=""
        local alert_rule_json=""
        local sql_query=""
        
        if command -v jq >/dev/null 2>&1; then
            validation_status=$(echo "$validate_response_body" | jq -r '.status // ""')
            validation_message=$(echo "$validate_response_body" | jq -r '.message // ""')
            alert_rule_json=$(echo "$validate_response_body" | jq -c '.alert_rule // null')
            sql_query=$(echo "$validate_response_body" | jq -r '.sql_query // ""')
        else
            validation_status=$(echo "$validate_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', ''))
except:
    pass
")
            validation_message=$(echo "$validate_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('message', ''))
except:
    pass
")
            alert_rule_json=$(echo "$validate_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    alert_rule = data.get('alert_rule')
    if alert_rule:
        print(json.dumps(alert_rule))
    else:
        print('null')
except:
    print('null')
")
            sql_query=$(echo "$validate_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('sql_query', ''))
except:
    pass
")
        fi
        
        echo -e "${BLUE}📋 Validation Status: ${validation_status}${NC}"
        echo -e "${BLUE}📝 Validation Message: ${validation_message}${NC}"
        
        # Check if validation was successful (valid or warning)
        if [[ "$validation_status" == "valid" || "$validation_status" == "warning" ]]; then
            if [[ "$validation_status" == "warning" ]]; then
                echo -e "${YELLOW}⚠️  Warning detected but proceeding with rule creation${NC}"
            fi
            
            # Step 2b: Create alert rule using validation result
            echo -e "${YELLOW}🚨 Creating alert rule via API...${NC}"
            
            # Create payload using proper JSON construction to avoid escaping issues
            local create_payload
            if command -v jq >/dev/null 2>&1; then
                create_payload=$(jq -n \
                    --argjson alert_rule "$alert_rule_json" \
                    --arg sql_query "$sql_query" \
                    --arg natural_language_query "$alert_text" \
                    '{alert_rule: $alert_rule, sql_query: $sql_query, natural_language_query: $natural_language_query}')
            else
                # Use temporary file approach to avoid shell escaping issues
                echo "$validate_response_body" > /tmp/validation_result.json
                echo "$alert_text" > /tmp/alert_text.txt
                create_payload=$(python3 -c "
import json
with open('/tmp/validation_result.json', 'r') as f:
    validation_data = json.load(f)
with open('/tmp/alert_text.txt', 'r') as f:
    alert_text = f.read().strip()
payload = {
    'alert_rule': validation_data['alert_rule'],
    'sql_query': validation_data['sql_query'],
    'natural_language_query': alert_text
}
print(json.dumps(payload))
")
                rm -f /tmp/validation_result.json /tmp/alert_text.txt
            fi
            
            local create_response
            if [[ -n "$AUTH_HEADER" ]]; then
                create_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules" \
                    -H "Content-Type: application/json" \
                    -H "$AUTH_HEADER" \
                    -d "$create_payload")
            else
                create_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules" \
                    -H "Content-Type: application/json" \
                    -d "$create_payload")
            fi
            
            local http_status=$(echo "$create_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
            local response_body=$(echo "$create_response" | sed -e 's/HTTPSTATUS:.*//g')
            
                if [[ "$http_status" == "200" ]]; then
                    echo -e "${GREEN}✅ Alert rule created successfully (HTTP 200)${NC}"
                    
                    # Extract rule ID from response
                    local rule_id=""
                    if command -v jq >/dev/null 2>&1; then
                        rule_id=$(echo "$response_body" | jq -r '.id // empty')
                    else
                        rule_id=$(echo "$response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('id', ''))
except:
    pass
")
                    fi
                    
                    if [[ -z "$rule_id" ]]; then
                        echo -e "${RED}❌ Could not extract rule ID from response${NC}"
                        echo -e "${YELLOW}📄 Response: ${response_body}${NC}"
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                        echo ""
                        return
                    fi
                    
                    echo -e "${GREEN}🆔 Rule ID: ${rule_id}${NC}"
                    
                    # Step 3: Trigger the alert rule
                    echo -e "${YELLOW}🔔 Triggering alert rule...${NC}"
                    
                    local trigger_response
                    if [[ -n "$AUTH_HEADER" ]]; then
                        trigger_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules/${rule_id}/trigger" \
                            -H "Content-Type: application/json" \
                            -H "$AUTH_HEADER")
                    else
                        trigger_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST "${API_BASE_URL}/alerts/rules/${rule_id}/trigger" \
                            -H "Content-Type: application/json")
                    fi
                    
                    local trigger_http_status=$(echo "$trigger_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
                    local trigger_response_body=$(echo "$trigger_response" | sed -e 's/HTTPSTATUS:.*//g')
                    
                    if [[ "$trigger_http_status" == "200" ]]; then
                        echo -e "${GREEN}✅ Alert trigger API call successful (HTTP 200)${NC}"
                        
                        # Check if alert was actually triggered
                        local alert_triggered=""
                        local status=""
                        local alert_message=""
                        
                        if command -v jq >/dev/null 2>&1; then
                            alert_triggered=$(echo "$trigger_response_body" | jq -r '.rule_evaluation.alert_triggered // false')
                            status=$(echo "$trigger_response_body" | jq -r '.status // ""')
                            alert_message=$(echo "$trigger_response_body" | jq -r '.rule_evaluation.alert_message // ""')
                        else
                            alert_triggered=$(echo "$trigger_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('rule_evaluation', {}).get('alert_triggered', False))
except:
    print('false')
")
                            status=$(echo "$trigger_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', ''))
except:
    pass
")
                            alert_message=$(echo "$trigger_response_body" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('rule_evaluation', {}).get('alert_message', ''))
except:
    pass
")
                        fi
                        
                        if [[ "$alert_triggered" == "true" && "$status" == "triggered" ]]; then
                            echo -e "${GREEN}🎉 ALERT TRIGGERED SUCCESSFULLY!${NC}"
                            echo -e "${GREEN}📨 Alert Message: ${alert_message}${NC}"
                            PASSED_TESTS=$((PASSED_TESTS + 1))
                        else
                            echo -e "${RED}❌ Alert was not triggered${NC}"
                            echo -e "${YELLOW}🔍 Alert Triggered: ${alert_triggered}${NC}"
                            echo -e "${YELLOW}🔍 Status: ${status}${NC}"
                            echo -e "${YELLOW}📄 Full Response: ${trigger_response_body}${NC}"
                            FAILED_TESTS=$((FAILED_TESTS + 1))
                        fi
                    else
                        echo -e "${RED}❌ Failed to trigger alert (HTTP ${trigger_http_status})${NC}"
                        echo -e "${YELLOW}📄 Response: ${trigger_response_body}${NC}"
                        FAILED_TESTS=$((FAILED_TESTS + 1))
                    fi
                else
                    echo -e "${RED}❌ Failed to create alert rule (HTTP ${http_status})${NC}"
                    echo -e "${YELLOW}📄 Response: ${response_body}${NC}"
                    FAILED_TESTS=$((FAILED_TESTS + 1))
                fi
            else
                echo -e "${RED}❌ Validation failed - cannot create rule${NC}"
                echo -e "${YELLOW}📋 Validation Status: ${validation_status}${NC}"
                echo -e "${YELLOW}📝 Validation Message: ${validation_message}${NC}"
                FAILED_TESTS=$((FAILED_TESTS + 1))
            fi
        else
            echo -e "${RED}❌ Failed to validate alert rule (HTTP ${validate_http_status})${NC}"
            echo -e "${YELLOW}📄 Response: ${validate_response_body}${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    
    echo ""
}

# Function to find and test alert rule files
find_and_test_files() {
    local target_pattern="$1"
    local found_files=()
    
    # Find matching files - search both patterns
    local processed_files=()
    for json_file in "$JSON_DIR"/alert_rule_*.json "$JSON_DIR"/alert_*.json; do
        if [[ -f "$json_file" ]] && [[ "$(basename "$json_file")" != "alert_rules.txt" ]]; then
            local filename=$(basename "$json_file")
            
            # Skip if already processed (avoid duplicates)
            if [[ " ${processed_files[@]} " =~ " ${filename} " ]]; then
                continue
            fi
            processed_files+=("$filename")
            
            # If no specific file requested, add all files
            if [[ -z "$target_pattern" ]]; then
                found_files+=("$json_file")
            # If specific file requested, check for matches
            elif [[ "$filename" == "$target_pattern" ]] || [[ "$filename" == *"$target_pattern"* ]]; then
                found_files+=("$json_file")
            fi
        fi
    done
    
    # Check if we found any matching files
    if [[ ${#found_files[@]} -eq 0 ]]; then
        if [[ -n "$target_pattern" ]]; then
            echo -e "${RED}❌ No test files found matching: ${target_pattern}${NC}"
            echo ""
            echo -e "${YELLOW}Available files:${NC}"
            list_files
            exit 1
        else
            echo -e "${RED}❌ No alert rule test files found in ${JSON_DIR}${NC}"
            exit 1
        fi
    fi
    
    # Display what we're testing
    if [[ -n "$target_pattern" ]]; then
        echo -e "${BLUE}🔍 Found ${#found_files[@]} matching file(s) for pattern: ${target_pattern}${NC}"
    else
        echo -e "${BLUE}🔍 Found ${#found_files[@]} alert rule test file(s)${NC}"
    fi
    
    # Test each found file
    for json_file in "${found_files[@]}"; do
        test_alert_rule "$json_file"
        # Small delay between tests
        sleep 1
    done
}

# Main execution
find_and_test_files "$SPECIFIC_FILE"

# Final summary
echo "============================================"
echo -e "${BLUE}📊 TEST SUMMARY${NC}"
echo "============================================"
echo -e "${YELLOW}Total Tests: ${TOTAL_TESTS}${NC}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 Some tests failed!${NC}"
    if [[ $TOTAL_TESTS -eq 1 ]]; then
        echo -e "${YELLOW}💡 Tip: Check the API logs or run with verbose debugging for more details${NC}"
    else
        echo -e "${YELLOW}💡 Tip: Run individual failing tests for easier debugging${NC}"
        echo -e "${YELLOW}   Example: $0 <filename>${NC}"
    fi
    exit 1
fi

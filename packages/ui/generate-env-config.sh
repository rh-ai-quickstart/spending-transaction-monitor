#!/bin/sh
# Generate runtime environment configuration for the UI
# This allows us to change configuration without rebuilding the image
# NOTE: Uses both VITE_* prefixed and non-prefixed environment variables for compatibility

# Helper to get env var with VITE_ prefix fallback
get_env() {
  var_name=$1
  default=$2
  vite_var="VITE_$var_name"
  
  # Try VITE_ prefixed first, then non-prefixed, then default
  eval val=\${$vite_var:-\${$var_name:-$default}}
  echo "$val"
}

BYPASS_AUTH_VAL=$(get_env "BYPASS_AUTH" "false")
API_BASE_URL_VAL=$(get_env "API_BASE_URL" "/api")
ENVIRONMENT_VAL=$(get_env "ENVIRONMENT" "production")

# For Keycloak URL, construct the full URL with realm
KEYCLOAK_URL_VAL="${VITE_KEYCLOAK_URL:-${KEYCLOAK_URL:-http://localhost:8080}}"
KEYCLOAK_REALM_VAL="${VITE_KEYCLOAK_REALM:-${KEYCLOAK_REALM:-spending-monitor}}"
KEYCLOAK_CLIENT_ID_VAL="${VITE_KEYCLOAK_CLIENT_ID:-${KEYCLOAK_CLIENT_ID:-spending-monitor}}"

# Build the full Keycloak URL
FULL_KEYCLOAK_URL="${KEYCLOAK_URL_VAL}/realms/${KEYCLOAK_REALM_VAL}"

cat > /app/dist/env-config/env-config.js << EOF
// Runtime Environment Configuration
// This file is generated at container startup based on environment variables
window.ENV = {
  BYPASS_AUTH: ${BYPASS_AUTH_VAL},
  API_BASE_URL: '${API_BASE_URL_VAL}',
  ENVIRONMENT: '${ENVIRONMENT_VAL}',
  KEYCLOAK_URL: '${FULL_KEYCLOAK_URL}',
  KEYCLOAK_CLIENT_ID: '${KEYCLOAK_CLIENT_ID_VAL}',
  KEYCLOAK_REALM: '${KEYCLOAK_REALM_VAL}',
  DEV: true  // Force dev logging for debugging
};

console.log('🔧 Runtime config loaded:', window.ENV);
EOF

echo "✅ Generated env-config.js with:"
echo "   BYPASS_AUTH: ${BYPASS_AUTH_VAL}"
echo "   API_BASE_URL: ${API_BASE_URL_VAL}"
echo "   ENVIRONMENT: ${ENVIRONMENT_VAL}"
echo "   KEYCLOAK_URL: ${FULL_KEYCLOAK_URL}"
echo "   KEYCLOAK_CLIENT_ID: ${KEYCLOAK_CLIENT_ID_VAL}"
echo "   KEYCLOAK_REALM: ${KEYCLOAK_REALM_VAL}"


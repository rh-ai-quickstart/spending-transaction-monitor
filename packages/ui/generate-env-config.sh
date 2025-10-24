#!/bin/sh
# Generate runtime environment configuration for the UI
# This allows us to change configuration without rebuilding the image

cat > /app/dist/env-config/env-config.js << EOF
// Runtime Environment Configuration
// This file is generated at container startup based on environment variables
window.ENV = {
  BYPASS_AUTH: ${VITE_BYPASS_AUTH:-false},
  API_BASE_URL: '${VITE_API_BASE_URL:-/api}',
  ENVIRONMENT: '${VITE_ENVIRONMENT:-production}',
  KEYCLOAK_URL: '${VITE_KEYCLOAK_URL:-http://localhost:8080/realms/spending-monitor}',
  KEYCLOAK_CLIENT_ID: '${VITE_KEYCLOAK_CLIENT_ID:-spending-monitor}',
  DEV: true  // Force dev logging for debugging
};

console.log('🔧 Runtime config loaded:', window.ENV);
EOF

echo "✅ Generated env-config.js with:"
echo "   BYPASS_AUTH: ${VITE_BYPASS_AUTH:-false}"
echo "   API_BASE_URL: ${VITE_API_BASE_URL:-/api}"
echo "   ENVIRONMENT: ${VITE_ENVIRONMENT:-production}"


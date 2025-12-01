"""Keycloak API client for authentication and realm management."""

import os
import time

import requests


class KeycloakClient:
    """Base client for Keycloak API operations."""

    def __init__(self):
        # Determine Keycloak URL based on environment
        # If running inside Kubernetes, use internal service for better reliability
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            # Use internal service URL (pod-to-pod communication)
            self.base_url = os.getenv(
                'KEYCLOAK_INTERNAL_URL', 'http://spending-monitor-keycloak:8080'
            )
        else:
            # Use external URL (for local development or browser access)
            self.base_url = os.getenv('KEYCLOAK_URL', 'http://localhost:8080')

        self.admin_username = os.getenv('KEYCLOAK_ADMIN_USER', 'admin')
        self.admin_password = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')
        self.master_realm = 'master'
        self.app_realm = os.getenv('KEYCLOAK_REALM', 'spending-monitor')
        self.access_token: str | None = None

    def log(self, message: str, level: str = 'INFO'):
        """Print formatted log message."""
        timestamp = time.strftime('%H:%M:%S')
        print(f'[{timestamp}] {level}: {message}')

    def get_admin_token(self) -> bool:
        """Get admin access token from master realm."""
        try:
            url = f'{self.base_url}/realms/{self.master_realm}/protocol/openid-connect/token'
            data = {
                'username': self.admin_username,
                'password': self.admin_password,
                'grant_type': 'password',
                'client_id': 'admin-cli',
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']
            self.log('✅ Admin token obtained successfully')
            return True

        except Exception as e:
            self.log(f'❌ Failed to get admin token: {e}', 'ERROR')
            return False

    def get(self, path: str, **kwargs) -> requests.Response:
        """Make GET request to Keycloak API."""
        url = f'{self.base_url}{path}'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        return requests.get(url, headers=headers, timeout=10, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Make POST request to Keycloak API."""
        url = f'{self.base_url}{path}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        return requests.post(url, headers=headers, timeout=10, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        """Make PUT request to Keycloak API."""
        url = f'{self.base_url}{path}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        return requests.put(url, headers=headers, timeout=10, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """Make DELETE request to Keycloak API."""
        url = f'{self.base_url}{path}'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        return requests.delete(url, headers=headers, timeout=10, **kwargs)

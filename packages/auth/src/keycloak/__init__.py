"""
Keycloak management package.

Provides a consolidated interface for managing Keycloak realms, users, and authentication.
"""

from .client import KeycloakClient
from .realm import RealmManager
from .users import UserManager

__all__ = ['KeycloakClient', 'RealmManager', 'UserManager']

#!/usr/bin/env python3
"""
Keycloak Management CLI

Consolidated interface for all Keycloak operations.
"""

import argparse
import http.client
import os
import sys
import time
from urllib.parse import urlparse

from .realm import RealmManager
from .users import UserManager


def wait_for_keycloak(max_attempts: int = 60, interval: int = 2) -> int:
    """Wait for Keycloak to be ready.

    Args:
        max_attempts: Maximum number of connection attempts
        interval: Seconds to wait between attempts

    Returns:
        0 if Keycloak is ready, 1 otherwise
    """
    keycloak_url = os.getenv('KEYCLOAK_URL', 'http://localhost:8080')

    print(f'⏳ Waiting for Keycloak at {keycloak_url}...')

    # Parse URL
    parsed = urlparse(keycloak_url)
    host = parsed.hostname or 'localhost'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)

    for attempt in range(1, max_attempts + 1):
        try:
            # Make a simple HTTP connection without following redirects
            conn = http.client.HTTPConnection(host, port, timeout=2)
            conn.request('GET', '/')
            response = conn.getresponse()
            conn.close()

            # Accept any response (200, 302, etc.) - just need to know Keycloak is responding
            if response.status in (200, 302, 303, 307, 308):
                print('   ✅ Keycloak is ready!')
                return 0

        except Exception:
            pass

        if attempt < max_attempts:
            print(
                f'   Attempt {attempt}/{max_attempts}: Keycloak not ready, waiting {interval}s...'
            )
            time.sleep(interval)

    print(f'   ⚠️  Keycloak not ready after {max_attempts * interval} seconds')
    return 1


def setup_realm(sync_db_users: bool = False) -> int:
    """Set up Keycloak realm with configuration."""
    realm_mgr = RealmManager()

    # Setup realm
    if not realm_mgr.setup():
        return 1

    # Create test users
    user_mgr = UserManager()
    user_mgr.access_token = realm_mgr.access_token  # Reuse token

    if not user_mgr.create_test_users():
        realm_mgr.log('⚠️  Failed to create test users', 'WARNING')

    # Optionally sync database users
    if sync_db_users:
        realm_mgr.log('')
        realm_mgr.log('🔄 Syncing database users...')
        if not user_mgr.sync_from_database():
            realm_mgr.log('⚠️  Database user sync failed', 'WARNING')

    print()
    realm_mgr.log('=' * 50)
    realm_mgr.log('🎉 Keycloak setup completed successfully!')
    realm_mgr.log('=' * 50)
    print()
    realm_mgr.log('📋 Test Users Created:')
    realm_mgr.log('   • testuser@example.com / password123 (user role)')
    realm_mgr.log('   • admin@example.com / admin123 (admin role)')
    print()

    return 0


def list_users(include_test_users: bool = False) -> int:
    """List users in the realm.

    Args:
        include_test_users: If True, show test users (adminuser, testuser).
                           If False, only show database-synced users.
    """
    user_mgr = UserManager()

    if not user_mgr.get_admin_token():
        return 1

    return 0 if user_mgr.list_users(include_test_users=include_test_users) else 1


def sync_users() -> int:
    """Sync database users to Keycloak."""
    user_mgr = UserManager()

    if not user_mgr.get_admin_token():
        return 1

    return 0 if user_mgr.sync_from_database() else 1


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description='Keycloak Management CLI - Consolidated tool for all Keycloak operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Wait for Keycloak to be ready
  %(prog)s wait
  
  # Set up Keycloak realm
  %(prog)s setup

  # Set up realm and sync database users
  %(prog)s setup --sync-users

  # List all users with test credentials
  %(prog)s list-users

  # Sync database users to Keycloak
  %(prog)s sync-users

Environment Variables (from .env.production):
  KEYCLOAK_URL              Keycloak server URL
  KEYCLOAK_REALM            Realm name (default: spending-monitor)
  KEYCLOAK_CLIENT_ID        Client ID (default: spending-monitor)
  KEYCLOAK_ADMIN            Admin username (default: admin)
  KEYCLOAK_ADMIN_PASSWORD   Admin password (required)
  KEYCLOAK_REDIRECT_URIS    Comma-separated redirect URIs (optional)
  KEYCLOAK_WEB_ORIGINS      Comma-separated web origins (optional)
  DATABASE_URL              PostgreSQL connection (required for sync-users)
  KEYCLOAK_DEFAULT_PASSWORD Default password for synced users (default: password123)
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Setup realm command
    setup_parser = subparsers.add_parser('setup', help='Set up Keycloak realm')
    setup_parser.add_argument(
        '--sync-users',
        action='store_true',
        help='Also sync database users after realm setup',
    )

    # List users command
    list_parser = subparsers.add_parser('list-users', help='List database-synced users')
    list_parser.add_argument(
        '--include-test-users',
        action='store_true',
        help='Also show test users (adminuser, testuser)',
    )

    # Sync users command
    subparsers.add_parser('sync-users', help='Sync database users to Keycloak')

    # Wait command
    wait_parser = subparsers.add_parser('wait', help='Wait for Keycloak to be ready')
    wait_parser.add_argument(
        '--max-attempts',
        type=int,
        default=60,
        help='Maximum number of connection attempts (default: 60)',
    )
    wait_parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Seconds to wait between attempts (default: 2)',
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == 'setup':
        return setup_realm(sync_db_users=args.sync_users)
    elif args.command == 'list-users':
        return list_users(include_test_users=args.include_test_users)
    elif args.command == 'sync-users':
        return sync_users()
    elif args.command == 'wait':
        return wait_for_keycloak(
            max_attempts=args.max_attempts,
            interval=args.interval,
        )

    return 1


if __name__ == '__main__':
    sys.exit(main())

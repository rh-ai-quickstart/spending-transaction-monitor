"""Keycloak user management operations."""

import os
import re
from datetime import datetime
from typing import TypedDict

from .client import KeycloakClient


class UserData(TypedDict):
    """Type definition for user data dictionary."""

    username: str
    email: str
    firstName: str
    lastName: str
    password: str
    roles: list[str]


class UserManager(KeycloakClient):
    """Manages Keycloak user operations."""

    def __init__(self):
        super().__init__()
        self.default_password = os.getenv('KEYCLOAK_DEFAULT_PASSWORD', 'password123')
        self.test_credentials = {
            'testuser': {
                'email': 'testuser@example.com',
                'password': 'password123',
                'description': 'Standard test user',
            },
            'adminuser': {
                'email': 'admin@example.com',
                'password': 'admin123',
                'description': 'Admin test user',
            },
        }

    def create_test_users(self) -> bool:
        """Create test users with known credentials."""
        users: list[UserData] = [
            {
                'username': 'testuser',
                'email': 'testuser@example.com',
                'firstName': 'Test',
                'lastName': 'User',
                'password': 'password123',
                'roles': ['user'],
            },
            {
                'username': 'adminuser',
                'email': 'admin@example.com',
                'firstName': 'Admin',
                'lastName': 'User',
                'password': 'admin123',
                'roles': ['user', 'admin'],
            },
        ]

        for user_data in users:
            if not self.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['firstName'],
                last_name=user_data['lastName'],
                password=user_data['password'],
                roles=user_data['roles'],
            ):
                return False

        return True

    def create_user(
        self,
        username: str,
        email: str,
        first_name: str = '',
        last_name: str = '',
        password: str = '',
        roles: list[str] = None,
    ) -> bool:
        """Create a single user in Keycloak."""
        try:
            # Check if user exists
            response = self.get(
                f'/admin/realms/{self.app_realm}/users', params={'username': username}
            )

            if response.status_code == 200:
                existing_users = response.json()
                if existing_users:
                    self.log(f"ℹ️  User '{username}' already exists")
                    return True

            # Create user
            user_data = {
                'username': username,
                'email': email,
                'firstName': first_name,
                'lastName': last_name,
                'enabled': True,
                'emailVerified': True,
                'credentials': [
                    {
                        'type': 'password',
                        'value': password or self.default_password,
                        'temporary': False,
                    }
                ],
            }

            response = self.post(
                f'/admin/realms/{self.app_realm}/users', json=user_data
            )

            if response.status_code != 201:
                self.log(
                    f"❌ Failed to create user '{username}': {response.status_code}"
                )
                return False

            self.log(f"✅ User '{username}' created successfully")

            # Get user ID and assign roles
            if roles:
                response = self.get(
                    f'/admin/realms/{self.app_realm}/users',
                    params={'username': username},
                )

                if response.status_code == 200:
                    users = response.json()
                    if users:
                        user_id = users[0]['id']
                        return self.assign_roles(user_id, roles)

            return True

        except Exception as e:
            self.log(f"❌ Error creating user '{username}': {e}", 'ERROR')
            return False

    def assign_roles(self, user_id: str, roles: list[str]) -> bool:
        """Assign roles to a user."""
        try:
            # Get available roles
            response = self.get(f'/admin/realms/{self.app_realm}/roles')
            if response.status_code != 200:
                return False

            available_roles = response.json()
            roles_to_assign = []

            for role_name in roles:
                for role in available_roles:
                    if role['name'] == role_name:
                        roles_to_assign.append(role)
                        break

            if not roles_to_assign:
                return True

            # Assign roles
            response = self.post(
                f'/admin/realms/{self.app_realm}/users/{user_id}/role-mappings/realm',
                json=roles_to_assign,
            )

            if response.status_code == 204:
                self.log(f'✅ Roles {roles} assigned successfully')
                return True

            return False

        except Exception as e:
            self.log(f'❌ Error assigning roles: {e}', 'ERROR')
            return False

    def list_users(self, include_test_users: bool = False) -> bool:
        """List users in the realm.

        Args:
            include_test_users: If True, includes test users (adminuser, testuser).
                               If False (default), only shows database-synced users.
        """
        try:
            response = self.get(f'/admin/realms/{self.app_realm}/users')
            response.raise_for_status()

            users = response.json()

            if not users:
                self.log('❌ No users found in realm')
                return False

            # Filter out test users unless explicitly requested
            if not include_test_users:
                test_usernames = set(self.test_credentials.keys())
                users = [u for u in users if u.get('username') not in test_usernames]

                if not users:
                    self.log('❌ No database-synced users found in realm')
                    self.log(
                        'ℹ️  Run with --include-test-users to see adminuser and testuser'
                    )
                    return False

            user_type = 'user(s)' if include_test_users else 'database-synced user(s)'
            self.log(f'✅ Found {len(users)} {user_type} in realm "{self.app_realm}"')
            self.log('')
            self.log('=' * 100)

            for user in users:
                username = user.get('username', 'N/A')
                email = user.get('email', 'N/A')
                enabled = '✅ Enabled' if user.get('enabled', False) else '❌ Disabled'
                user_id = user.get('id')
                created = user.get('createdTimestamp')

                if created:
                    dt = datetime.fromtimestamp(created / 1000)
                    created_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_str = 'N/A'

                # Get user roles
                roles_response = self.get(
                    f'/admin/realms/{self.app_realm}/users/{user_id}/role-mappings/realm'
                )
                roles = []
                if roles_response.status_code == 200:
                    role_data = roles_response.json()
                    roles = [
                        role['name']
                        for role in role_data
                        if role['name']
                        not in [
                            'default-roles-spending-monitor',
                            'offline_access',
                            'uma_authorization',
                        ]
                    ]
                roles_str = ', '.join(roles) if roles else 'None'

                print(f'\n👤 Username: {username}')
                print(f'   Email:    {email}')
                print(f'   Status:   {enabled}')
                print(f'   Roles:    {roles_str}')
                print(f'   Created:  {created_str}')

                # Show test credentials if this is a known test user
                if username in self.test_credentials:
                    creds = self.test_credentials[username]
                    print('   🔑 TEST CREDENTIALS:')
                    print(f'      Email:    {creds["email"]}')
                    print(f'      Password: {creds["password"]}')
                    print(f'      ({creds["description"]})')
                else:
                    # For database users, show the default password
                    print(f'   🔑 PASSWORD: {self.default_password}')
                    print('      (Database users use default password)')

                print('-' * 100)

            print('\n📝 Notes:')
            print('   • Passwords are hashed in Keycloak and cannot be retrieved')
            if not include_test_users:
                print(
                    '   • Database users shown above use the default password: password123'
                )
                print('   • Test users (adminuser, testuser) are hidden by default')
                print(
                    '   • Run "make keycloak-users-all" to see all users including test users'
                )
            else:
                print('   • Test users: adminuser, testuser')
                print('   • Database users: synced from spending-monitor-db')
            print('')

            return True

        except Exception as e:
            self.log(f'❌ Failed to list users: {e}', 'ERROR')
            return False

    def sync_from_database(self) -> bool:
        """Sync users from PostgreSQL database to Keycloak."""
        try:
            import psycopg2

            # Parse DATABASE_URL
            database_url = os.getenv('DATABASE_URL', '')
            if not database_url or not database_url.startswith('postgresql'):
                self.log('❌ DATABASE_URL not set or invalid', 'ERROR')
                return False

            # Strip driver suffix (e.g., postgresql+asyncpg:// -> postgresql://)
            # This handles both postgresql:// and postgresql+asyncpg:// formats
            database_url = database_url.replace(
                'postgresql+asyncpg://', 'postgresql://'
            )
            database_url = database_url.replace(
                'postgresql+psycopg2://', 'postgresql://'
            )

            # Parse postgresql://user:password@host:port/database
            match = re.match(
                r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url
            )

            if not match:
                self.log('❌ Could not parse DATABASE_URL', 'ERROR')
                return False

            db_user, db_password, db_host, db_port, db_name = match.groups()

            self.log('🔄 Connecting to database...')
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                dbname=db_name,
            )

            cursor = conn.cursor()
            cursor.execute('SELECT id, email, first_name, last_name FROM users')
            db_users = cursor.fetchall()

            if not db_users:
                self.log('ℹ️  No users found in database')
                cursor.close()
                conn.close()
                return True

            self.log(f'📊 Found {len(db_users)} users in database')
            synced_count = 0

            for user_id, email, first_name, last_name in db_users:
                username = user_id  # Using 'id' column as username
                if self.create_user(
                    username=username,
                    email=email or f'{username}@example.com',
                    first_name=first_name or '',
                    last_name=last_name or '',
                    password=self.default_password,
                    roles=['user'],
                ):
                    synced_count += 1

            cursor.close()
            conn.close()

            self.log(f'✅ Synced {synced_count}/{len(db_users)} users to Keycloak')
            return True

        except ImportError:
            self.log(
                '❌ psycopg2 not installed. Run: pip install psycopg2-binary', 'ERROR'
            )
            return False
        except Exception as e:
            self.log(f'❌ Error syncing users from database: {e}', 'ERROR')
            return False

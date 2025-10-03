#!/usr/bin/env python3
"""
Set up Keycloak realm and populate it with users from the database
"""

import asyncio
import csv
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


class KeycloakSetupWithDatabaseUsers:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.admin_username = "admin"
        self.admin_password = "admin"
        self.master_realm = "master"
        self.app_realm = "spending-monitor"
        self.client_id = "spending-monitor"
        self.access_token: Optional[str] = None
        
        # Database connection
        database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql+asyncpg://user:password@localhost:5432/spending-monitor'
        )
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    def log(self, message: str, level: str = "INFO"):
        """Print formatted log message"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def get_admin_token(self) -> bool:
        """Get admin access token from master realm"""
        try:
            url = f"{self.base_url}/realms/{self.master_realm}/protocol/openid-connect/token"
            data = {
                "username": self.admin_username,
                "password": self.admin_password,
                "grant_type": "password",
                "client_id": "admin-cli",
            }

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.log("✅ Admin token obtained successfully")
            return True

        except Exception as e:
            self.log(f"❌ Failed to get admin token: {e}", "ERROR")
            return False

    def create_realm(self) -> bool:
        """Create a new realm for the spending-monitor application"""
        try:
            url = f"{self.base_url}/admin/realms"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            realm_data = {
                "realm": self.app_realm,
                "enabled": True,
                "displayName": "Spending Monitor",
                "displayNameHtml": '<div class="kc-logo-text"><span>Spending Monitor</span></div>',
                "attributes": {"frontendUrl": "http://localhost:5173"},
            }

            response = requests.post(url, json=realm_data, headers=headers, timeout=10)

            if response.status_code == 201:
                self.log(f"✅ Realm '{self.app_realm}' created successfully")
                return True
            elif response.status_code == 409:
                self.log(f"ℹ️  Realm '{self.app_realm}' already exists")
                return True
            else:
                self.log(f"❌ Failed to create realm: {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ Error creating realm: {e}", "ERROR")
            return False

    def create_client(self) -> bool:
        """Create or update the spending-monitor client in the realm"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Check if client already exists
            clients_url = f"{self.base_url}/admin/realms/{self.app_realm}/clients"
            response = requests.get(clients_url, headers=headers, timeout=10)

            if response.status_code != 200:
                self.log(f"❌ Failed to get clients: {response.status_code}")
                return False

            existing_client = None
            for client in response.json():
                if client.get("clientId") == self.client_id:
                    existing_client = client
                    break

            client_data = {
                "clientId": self.client_id,
                "name": "Spending Monitor Frontend",
                "description": "Frontend application for spending transaction monitoring",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "implicitFlowEnabled": False,
                "redirectUris": ["http://localhost:5173/*"],
                "webOrigins": ["http://localhost:5173"],
                "attributes": {"pkce.code.challenge.method": "S256"},
            }

            if existing_client:
                # Update existing client
                client_uuid = existing_client["id"]
                update_url = f"{self.base_url}/admin/realms/{self.app_realm}/clients/{client_uuid}"
                update_data = {**existing_client, **client_data}

                response = requests.put(update_url, json=update_data, headers=headers, timeout=10)

                if response.status_code == 204:
                    self.log("✅ Client 'spending-monitor' updated successfully")
                    return True
                else:
                    self.log(f"❌ Failed to update client: {response.status_code}")
                    return False
            else:
                # Create new client
                response = requests.post(clients_url, json=client_data, headers=headers, timeout=10)

                if response.status_code == 201:
                    self.log("✅ Client 'spending-monitor' created successfully")
                    return True
                else:
                    self.log(f"❌ Failed to create client: {response.status_code}")
                    return False

        except Exception as e:
            self.log(f"❌ Error creating/updating client: {e}", "ERROR")
            return False

    def create_roles(self) -> bool:
        """Create user and admin roles in the new realm"""
        try:
            roles = ["user", "admin"]
            headers = {"Authorization": f"Bearer {self.access_token}"}

            for role_name in roles:
                url = f"{self.base_url}/admin/realms/{self.app_realm}/roles"
                role_data = {
                    "name": role_name,
                    "description": f"{role_name.title()} role for spending-monitor",
                }

                response = requests.post(url, json=role_data, headers=headers, timeout=10)

                if response.status_code == 201:
                    self.log(f"✅ Role '{role_name}' created successfully")
                elif response.status_code == 409:
                    self.log(f"ℹ️  Role '{role_name}' already exists")
                else:
                    self.log(f"❌ Failed to create role '{role_name}': {response.status_code}")
                    return False

            return True

        except Exception as e:
            self.log(f"❌ Error creating roles: {e}", "ERROR")
            return False

    async def get_users_from_database(self) -> List[Dict[str, Any]]:
        """Fetch users from the database"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, email, keycloak_id, first_name, last_name, 
                               phone_number, is_active, address_city, address_state
                        FROM users 
                        WHERE is_active = true
                        ORDER BY created_at
                        LIMIT 50
                    """)
                )
                
                users = []
                for row in result.fetchall():
                    users.append({
                        'id': row[0],
                        'email': row[1], 
                        'keycloak_id': row[2],
                        'first_name': row[3],
                        'last_name': row[4],
                        'phone_number': row[5],
                        'is_active': row[6],
                        'address_city': row[7],
                        'address_state': row[8]
                    })
                
                self.log(f"📖 Found {len(users)} active users in database")
                return users
                
        except Exception as e:
            self.log(f"❌ Error fetching users from database: {e}", "ERROR")
            # Fallback to CSV file if database is not available
            return await self.get_users_from_csv()

    async def get_users_from_csv(self) -> List[Dict[str, Any]]:
        """Fallback: Read users from CSV file if database is not available"""
        try:
            csv_path = Path(__file__).parent.parent.parent.parent / "data" / "sample_users.csv"
            
            if not csv_path.exists():
                self.log(f"❌ CSV file not found: {csv_path}")
                return []
                
            users = []
            with open(csv_path, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get('is_active', '').lower() == 'true':
                        users.append({
                            'id': row['id'],
                            'email': row['email'],
                            'keycloak_id': row.get('keycloak_id'),
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'phone_number': row.get('phone_number'),
                            'is_active': True,
                            'address_city': row.get('address_city'),
                            'address_state': row.get('address_state')
                        })
            
            self.log(f"📖 Loaded {len(users)} users from CSV file")
            return users[:20]  # Limit to first 20 for demo
            
        except Exception as e:
            self.log(f"❌ Error reading CSV file: {e}", "ERROR")
            return []

    def create_database_user_in_keycloak(self, user_data: Dict[str, Any]) -> bool:
        """Create a user from database in Keycloak"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Use email as username for consistency
            username = user_data['email']
            email = user_data['email'] 
            first_name = user_data['first_name']
            last_name = user_data['last_name']
            keycloak_id = user_data.get('keycloak_id')
            
            # Check if user already exists
            users_url = f"{self.base_url}/admin/realms/{self.app_realm}/users"
            check_url = f"{users_url}?username={username}"
            response = requests.get(check_url, headers=headers, timeout=10)

            user_id = None
            if response.status_code == 200 and len(response.json()) > 0:
                existing_user = response.json()[0]
                user_id = existing_user["id"]
                self.log(f"ℹ️  User '{username}' already exists in Keycloak")
            else:
                # Create new user with database information
                user_payload = {
                    "username": username,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                    "emailVerified": True,
                    "credentials": [
                        {"type": "password", "value": "password123", "temporary": False}
                    ],
                }
                
                # Add keycloak_id as an attribute if available
                if keycloak_id:
                    user_payload["attributes"] = {
                        "db_user_id": [user_data['id']],
                        "original_keycloak_id": [keycloak_id]
                    }

                response = requests.post(users_url, json=user_payload, headers=headers, timeout=10)

                if response.status_code == 201:
                    user_id = response.headers.get("Location", "").split("/")[-1]
                    self.log(f"✅ User '{username}' created successfully")
                elif response.status_code == 409:
                    # User exists, try to get the user ID
                    response = requests.get(check_url, headers=headers, timeout=10)
                    if response.status_code == 200 and len(response.json()) > 0:
                        user_id = response.json()[0]["id"]
                        self.log(f"ℹ️  User '{username}' already exists")
                    else:
                        self.log(f"❌ Failed to get existing user ID for '{username}'")
                        return False
                else:
                    self.log(f"❌ Failed to create user '{username}': {response.status_code}")
                    if response.text:
                        self.log(f"   Error: {response.text[:200]}")
                    return False

            # Assign user role if we have a user ID
            if user_id:
                return self.assign_role_to_user(user_id, "user")

            return True

        except Exception as e:
            self.log(f"❌ Error creating user '{user_data.get('email', 'unknown')}': {e}", "ERROR")
            return False

    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Get role data
            role_url = f"{self.base_url}/admin/realms/{self.app_realm}/roles/{role_name}"
            role_response = requests.get(role_url, headers=headers, timeout=10)

            if role_response.status_code == 200:
                role_data = role_response.json()

                # Check if role is already assigned
                user_roles_url = f"{self.base_url}/admin/realms/{self.app_realm}/users/{user_id}/role-mappings/realm"
                user_roles_response = requests.get(user_roles_url, headers=headers, timeout=10)

                has_role = False
                if user_roles_response.status_code == 200:
                    user_roles = user_roles_response.json()
                    has_role = any(r["name"] == role_name for r in user_roles)

                if not has_role:
                    # Assign role to user
                    assign_response = requests.post(
                        user_roles_url,
                        json=[role_data],
                        headers=headers,
                        timeout=10,
                    )

                    if assign_response.status_code == 204:
                        return True
                    else:
                        self.log(f"⚠️  Failed to assign role '{role_name}' to user")
                        return False
                else:
                    return True
            else:
                self.log(f"⚠️  Could not find role '{role_name}'")
                return False

        except Exception as e:
            self.log(f"❌ Error assigning role '{role_name}': {e}", "ERROR")
            return False

    def create_admin_user(self) -> bool:
        """Create an admin test user"""
        admin_user = {
            'id': 'admin-001',
            'email': 'admin@example.com',
            'keycloak_id': None,
            'first_name': 'Admin',
            'last_name': 'User',
            'phone_number': '555-ADMIN',
            'is_active': True,
            'address_city': 'Admin City',
            'address_state': 'AC'
        }
        
        if self.create_database_user_in_keycloak(admin_user):
            # Get the user ID and assign admin role
            try:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                users_url = f"{self.base_url}/admin/realms/{self.app_realm}/users"
                check_url = f"{users_url}?username=admin@example.com"
                response = requests.get(check_url, headers=headers, timeout=10)
                
                if response.status_code == 200 and len(response.json()) > 0:
                    user_id = response.json()[0]["id"]
                    if self.assign_role_to_user(user_id, "admin"):
                        self.log("✅ Admin role assigned to admin@example.com")
                        return True
                        
            except Exception as e:
                self.log(f"❌ Error assigning admin role: {e}", "ERROR")
                
        return False

    def test_oidc_config(self) -> bool:
        """Test if OIDC configuration is accessible"""
        try:
            url = f"{self.base_url}/realms/{self.app_realm}/.well-known/openid-configuration"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                config = response.json()
                self.log("✅ OIDC configuration is accessible")
                self.log(f"   Issuer: {config.get('issuer', 'N/A')}")
                return True
            else:
                self.log(f"❌ OIDC configuration not accessible: {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ Error testing OIDC config: {e}", "ERROR")
            return False

    async def run_setup(self) -> bool:
        """Run the complete realm setup with database users"""
        self.log("🚀 Starting Keycloak setup with database users")
        self.log("=" * 60)

        # Step 1: Get admin token
        if not self.get_admin_token():
            return False

        # Step 2: Create realm
        if not self.create_realm():
            return False

        # Step 3: Create client
        if not self.create_client():
            return False

        # Step 4: Create roles
        if not self.create_roles():
            return False

        # Step 5: Get users from database
        users = await self.get_users_from_database()
        if not users:
            self.log("⚠️  No users found, skipping user creation")
            return False

        # Step 6: Create database users in Keycloak
        self.log(f"👥 Creating {len(users)} users in Keycloak...")
        success_count = 0
        
        for i, user in enumerate(users, 1):
            self.log(f"   [{i}/{len(users)}] Creating {user['email']}...")
            if self.create_database_user_in_keycloak(user):
                success_count += 1
            
            # Small delay to avoid overwhelming Keycloak
            if i % 5 == 0:
                time.sleep(1)

        self.log(f"✅ Successfully created/updated {success_count}/{len(users)} users")

        # Step 7: Create admin user
        if self.create_admin_user():
            self.log("✅ Admin user created successfully")

        # Step 8: Test OIDC configuration
        self.log("⏳ Waiting for Keycloak to process changes...")
        time.sleep(3)

        if not self.test_oidc_config():
            self.log("❌ OIDC configuration test failed")
            return False

        # Cleanup
        await self.engine.dispose()

        self.log("=" * 60)
        self.log("🎉 Keycloak setup completed successfully!")
        self.log("📋 Summary:")
        self.log(f"   • Realm: {self.app_realm}")
        self.log(f"   • Users created: {success_count}")
        self.log(f"   • Admin user: admin@example.com / password123")
        self.log(f"   • Test user: {users[0]['email'] if users else 'N/A'} / password123")
        self.log("🔗 Next steps:")
        self.log("   1. Set BYPASS_AUTH=false in your environment")
        self.log("   2. Test the UI: http://localhost:5173/")
        self.log("   3. Login with created users")

        return True


async def main():
    """Main entry point"""
    setup = KeycloakSetupWithDatabaseUsers()

    try:
        success = await setup.run_setup()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

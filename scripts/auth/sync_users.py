#!/usr/bin/env python3
"""
Sync users between Keycloak and the database
This script will:
1. Fetch all users from Keycloak
2. Check which users exist in the database
3. Create missing users in the database
4. Update existing users with Keycloak IDs
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
import uuid

# Add the packages to the path so we can import from them
packages_path = Path(__file__).resolve().parent.parent.parent / "packages"
api_path = packages_path / "api" / "src"
db_path = packages_path / "db" / "src"
sys.path.insert(0, str(api_path))
sys.path.insert(0, str(db_path))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import database and models
try:
    from db.database import SessionLocal
    from db.models import User
except ImportError as e:
    print(f"❌ Could not import database modules: {e}")
    print("Make sure you're running this from the API environment with: uv run python")
    sys.exit(1)


class KeycloakUserSync:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.admin_username = "admin"
        self.admin_password = "admin"
        self.master_realm = "master"
        self.app_realm = "spending-monitor"
        self.access_token: str | None = None

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

    def get_keycloak_users(self) -> List[Dict[str, Any]]:
        """Get all users from Keycloak realm"""
        try:
            url = f"{self.base_url}/admin/realms/{self.app_realm}/users"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            users = response.json()
            self.log(f"✅ Retrieved {len(users)} users from Keycloak")
            return users

        except Exception as e:
            self.log(f"❌ Failed to get Keycloak users: {e}", "ERROR")
            return []

    async def get_database_users(self, session: AsyncSession) -> List[User]:
        """Get all users from the database"""
        try:
            result = await session.execute(select(User))
            users = list(result.scalars().all())
            self.log(f"✅ Retrieved {len(users)} users from database")
            return users
        except Exception as e:
            self.log(f"❌ Failed to get database users: {e}", "ERROR")
            return []

    async def sync_user_to_database(
        self, keycloak_user: Dict[str, Any], session: AsyncSession
    ) -> bool:
        """Sync a single Keycloak user to the database"""
        try:
            keycloak_id = keycloak_user.get("id")
            email = keycloak_user.get("email")
            first_name = keycloak_user.get("firstName", "")
            last_name = keycloak_user.get("lastName", "")
            enabled = keycloak_user.get("enabled", True)

            if not keycloak_id or not email:
                self.log(
                    f"⚠️ Skipping user with missing ID or email: {keycloak_user}", "WARN"
                )
                return False

            # Check if user already exists by keycloak_id
            result = await session.execute(
                select(User).where(User.keycloak_id == keycloak_id)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                # Update existing user
                existing_user.email = email
                existing_user.first_name = first_name or existing_user.first_name
                existing_user.last_name = last_name or existing_user.last_name
                existing_user.is_active = enabled
                self.log(f"🔄 Updated existing user: {email}")
                return True

            # Check if user exists by email (for migration)
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                # Update existing user with Keycloak ID
                existing_user.keycloak_id = keycloak_id
                existing_user.first_name = first_name or existing_user.first_name
                existing_user.last_name = last_name or existing_user.last_name
                existing_user.is_active = enabled
                self.log(
                    f"🔗 Linked existing user to Keycloak: {email} -> {keycloak_id}"
                )
                return True

            # Create new user
            new_user = User(
                id=str(uuid.uuid4()),
                keycloak_id=keycloak_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=enabled,
            )
            session.add(new_user)
            self.log(f"➕ Created new user: {email}")
            return True

        except Exception as e:
            self.log(
                f"❌ Failed to sync user {keycloak_user.get('email', 'unknown')}: {e}",
                "ERROR",
            )
            return False

    async def sync_all_users(self) -> Dict[str, Any]:
        """Sync all users from Keycloak to database"""
        self.log("🚀 Starting Keycloak to Database user synchronization")

        # Get admin token
        if not self.get_admin_token():
            return {"status": "error", "message": "Failed to get admin token"}

        # Get Keycloak users
        keycloak_users = self.get_keycloak_users()
        if not keycloak_users:
            return {"status": "error", "message": "No users found in Keycloak"}

        # Get database session
        async with SessionLocal() as session:
            try:
                # Get existing database users
                db_users = await self.get_database_users(session)

                self.log(
                    f"📊 Found {len(keycloak_users)} Keycloak users and {len(db_users)} database users"
                )

                # Sync each Keycloak user to database
                success_count = 0
                error_count = 0

                for kc_user in keycloak_users:
                    if await self.sync_user_to_database(kc_user, session):
                        success_count += 1
                    else:
                        error_count += 1

                # Commit all changes
                await session.commit()

                self.log(
                    f"✅ Sync completed: {success_count} successful, {error_count} errors"
                )

                return {
                    "status": "success",
                    "keycloak_users": len(keycloak_users),
                    "database_users_before": len(db_users),
                    "successful_syncs": success_count,
                    "errors": error_count,
                }

            except Exception as e:
                await session.rollback()
                self.log(f"❌ Sync failed: {e}", "ERROR")
                return {"status": "error", "message": str(e)}

    async def list_users_comparison(self) -> Dict[str, Any]:
        """Compare users between Keycloak and database"""
        self.log("📋 Comparing users between Keycloak and database")

        # Get admin token
        if not self.get_admin_token():
            return {"status": "error", "message": "Failed to get admin token"}

        # Get Keycloak users
        keycloak_users = self.get_keycloak_users()

        # Get database users
        async with SessionLocal() as session:
            db_users = await self.get_database_users(session)

        # Create comparison
        kc_emails = {user.get("email") for user in keycloak_users if user.get("email")}
        db_emails = {user.email for user in db_users}

        only_in_keycloak = kc_emails - db_emails
        only_in_database = db_emails - kc_emails
        in_both = kc_emails & db_emails

        self.log("📊 User Comparison Results:")
        self.log(f"   👥 Total Keycloak users: {len(keycloak_users)}")
        self.log(f"   🗄️ Total database users: {len(db_users)}")
        self.log(f"   🤝 Users in both: {len(in_both)}")
        self.log(f"   🆕 Only in Keycloak: {len(only_in_keycloak)}")
        self.log(f"   🏠 Only in database: {len(only_in_database)}")

        if only_in_keycloak:
            self.log("Users only in Keycloak:")
            for email in only_in_keycloak:
                self.log(f"   - {email}")

        if only_in_database:
            self.log("Users only in database:")
            for email in only_in_database:
                self.log(f"   - {email}")

        return {
            "status": "success",
            "keycloak_total": len(keycloak_users),
            "database_total": len(db_users),
            "in_both": len(in_both),
            "only_in_keycloak": list(only_in_keycloak),
            "only_in_database": list(only_in_database),
        }


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync users between Keycloak and database"
    )
    parser.add_argument(
        "--action",
        choices=["sync", "compare"],
        default="compare",
        help="Action to perform (default: compare)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    sync_service = KeycloakUserSync()

    if args.action == "compare":
        result = await sync_service.list_users_comparison()
    else:  # sync
        if args.dry_run:
            sync_service.log("🔍 DRY RUN MODE - No changes will be made")
            result = await sync_service.list_users_comparison()
        else:
            result = await sync_service.sync_all_users()

    if result["status"] == "error":
        print(f"\n❌ Operation failed: {result['message']}")
        sys.exit(1)
    else:
        print(f"\n✅ Operation completed successfully")


if __name__ == "__main__":
    asyncio.run(main())

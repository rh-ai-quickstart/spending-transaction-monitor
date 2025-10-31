import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

# Add the parent directory to sys.path to make imports work when run as script
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import func, select, text

from db.database import SessionLocal
from db.models import AlertNotification, AlertRule, CreditCard, Transaction, User

# Optional: Import requests for Keycloak API calls
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print(
        "⚠️  'requests' library not available. Keycloak user creation will be skipped."
    )

# Keycloak configuration from environment
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL', 'http://localhost:8080')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'spending-monitor')
KEYCLOAK_ADMIN_USER = os.getenv('KEYCLOAK_ADMIN_USER', 'admin')
KEYCLOAK_ADMIN_PASSWORD = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')


def get_keycloak_admin_token() -> str | None:
    """Get admin access token from Keycloak"""
    if not REQUESTS_AVAILABLE:
        return None

    try:
        url = f'{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token'
        data = {
            'username': KEYCLOAK_ADMIN_USER,
            'password': KEYCLOAK_ADMIN_PASSWORD,
            'grant_type': 'password',
            'client_id': 'admin-cli',
        }

        response = requests.post(url, data=data, timeout=5)
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        print(f'⚠️  Could not get Keycloak admin token: {e}')
        return None


def create_keycloak_user(
    email: str, first_name: str, last_name: str, password: str = 'password'
) -> bool:
    """Create or update a user in Keycloak"""
    if not REQUESTS_AVAILABLE:
        return False

    token = get_keycloak_admin_token()
    if not token:
        return False

    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        # Check if user exists
        users_url = f'{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users'
        check_url = f'{users_url}?email={email}'
        response = requests.get(check_url, headers=headers, timeout=5)

        if response.status_code == 200 and len(response.json()) > 0:
            print(f"   ℹ️  Keycloak user '{email}' already exists")
            return True

        # Extract username from email
        username = email.split('@')[0]

        # Create new user
        user_data = {
            'username': username,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': True,
            'emailVerified': True,
            'credentials': [
                {'type': 'password', 'value': password, 'temporary': False}
            ],
        }

        response = requests.post(users_url, json=user_data, headers=headers, timeout=5)

        if response.status_code == 201:
            print(f"   ✅ Created Keycloak user '{email}' (password: {password})")

            # Assign 'user' role
            user_id = response.headers.get('Location', '').split('/')[-1]
            if user_id:
                role_url = f'{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles/user'
                role_response = requests.get(role_url, headers=headers, timeout=5)
                if role_response.status_code == 200:
                    role_data = role_response.json()
                    assign_url = f'{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm'
                    requests.post(
                        assign_url, json=[role_data], headers=headers, timeout=5
                    )
                    print(f"   ✅ Assigned 'user' role to '{email}'")

            return True
        elif response.status_code == 409:
            print(f"   ℹ️  Keycloak user '{email}' already exists")
            return True
        else:
            print(
                f"   ⚠️  Failed to create Keycloak user '{email}': {response.status_code}"
            )
            return False

    except Exception as e:
        print(f'   ⚠️  Error creating Keycloak user: {e}')
        return False

# Import Keycloak sync functionality (optional)
try:
    import importlib.util
    auth_script = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'auth', 'scripts', 'sync_db_users_to_keycloak.py')
    spec = importlib.util.spec_from_file_location("sync_db_users_to_keycloak", auth_script)
    if spec and spec.loader:
        sync_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync_module)
        DatabaseUserSyncer = sync_module.DatabaseUserSyncer
        KEYCLOAK_SYNCER_AVAILABLE = True
    else:
        raise ImportError("Could not load Keycloak sync module")
except (ImportError, FileNotFoundError, AttributeError):
    DatabaseUserSyncer = None  # type: ignore
    KEYCLOAK_SYNCER_AVAILABLE = False
    print('ℹ️  Keycloak sync unavailable (auth package not found), tests will run without authentication')


def get_user_confirmation() -> bool:
    """Get user confirmation to proceed with data deletion"""
    print('\n' + '=' * 60)
    print('⚠️  WARNING: DATABASE RESET IMMINENT')
    print('=' * 60)
    print('🗑️  This script will DELETE ALL existing data from:')
    print('   • Cached Recommendations')
    print('   • Users')
    print('   • Credit Cards')
    print('   • Transactions')
    print('   • Alert Rules')
    print('   • Alert Notifications')
    print('\n🔄 Then it will seed the database with new test data.')
    print('=' * 60)

    while True:
        response = input(
            "\n❓ Do you want to continue? (type 'YES' to confirm, 'no' to cancel): "
        ).strip()
        if response == 'YES':
            print('✅ Confirmed. Proceeding with database reset and seeding...')
            return True
        elif response.lower() in ['no', 'n']:
            print('❌ Cancelled. No changes made to database.')
            return False
        else:
            print("⚠️  Please type 'YES' to confirm or 'no' to cancel.")


async def reset_database(session) -> None:
    """Delete all data from database tables
    
    TODO: Implement non-destructive seeding mode
    - Add --append flag to skip database reset
    - Add --upsert flag to merge with existing data
    - Add conflict resolution for duplicate IDs
    - Preserve existing data while adding test data
    This would allow incremental test data additions without full resets.
    """
    print('\n🗑️  Clearing existing database data...')

    try:
        # Delete in correct order (respecting foreign key constraints)
        print('🔄 Deleting cached_recommendations...')
        await session.execute(text('DELETE FROM cached_recommendations'))

        print('📋 Deleting alert_notifications...')
        await session.execute(text('DELETE FROM alert_notifications'))

        print('⚠️  Deleting alert_rules...')
        await session.execute(text('DELETE FROM alert_rules'))

        print('💳 Deleting transactions...')
        await session.execute(text('DELETE FROM transactions'))

        print('🏦 Deleting credit_cards...')
        await session.execute(text('DELETE FROM credit_cards'))

        print('👤 Deleting users...')
        await session.execute(text('DELETE FROM users'))

        await session.commit()
        print('✅ Database cleared successfully!')

    except Exception as e:
        print(f'❌ Error during database reset: {e}')
        await session.rollback()
        raise


def normalize_json_structure(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Normalize JSON structure to handle both singular and plural formats"""
    normalized = {}

    # Handle users
    if 'users' in data:
        normalized['users'] = data['users']
    elif 'user' in data:
        normalized['users'] = [data['user']]
    else:
        normalized['users'] = []

    # Handle credit_cards
    if 'credit_cards' in data:
        normalized['credit_cards'] = data['credit_cards']
    elif 'credit_card' in data:
        normalized['credit_cards'] = [data['credit_card']]
    else:
        normalized['credit_cards'] = []

    # Handle transactions
    normalized['transactions'] = data.get('transactions', [])

    return normalized


def convert_timestamps(obj_data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Convert string timestamps to datetime objects"""
    obj_copy = obj_data.copy()
    for field in fields:
        if obj_copy.get(field) and isinstance(obj_copy[field], str):
            # Remove Z and parse ISO format
            timestamp_str = obj_copy[field].replace('Z', '+00:00')
            obj_copy[field] = datetime.fromisoformat(timestamp_str)
        # If it's already a datetime object, leave it as is
    return obj_copy


def sync_users_to_keycloak(users: list[dict[str, Any]], quiet: bool = False) -> bool:
    """
    Sync seeded users to Keycloak for authentication using the existing DatabaseUserSyncer
    
    Args:
        users: List of user dictionaries to sync
        quiet: If True, suppress output messages
        
    Returns:
        True if sync succeeded or was skipped gracefully, False on critical error
    """
    if not KEYCLOAK_SYNCER_AVAILABLE:
        if not quiet:
            print('\nℹ️  Keycloak sync skipped (auth package not available)')
            print('   Tests will run without authentication')
        return True
    
    if not users:
        if not quiet:
            print('\n⚠️  No users to sync to Keycloak')
        return True
    
    if not quiet:
        print('\n' + '=' * 60)
        print('🔐 Syncing users to Keycloak')
        print('=' * 60)
    
    try:
        # Use the existing DatabaseUserSyncer but pass in user data directly
        syncer = DatabaseUserSyncer()
        
        # Get admin token
        if not syncer.get_admin_token():
            if not quiet:
                print('⚠️  Keycloak not available, tests will run without authentication')
            return True
        
        # Sync each user
        success_count = 0
        for user_data in users:
            # Transform to the format expected by create_keycloak_user
            user_sync_data = {
                'id': user_data.get('id'),
                'email': user_data['email'],
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'username': user_data['email'].split('@')[0],
                'password': syncer.default_password
            }
            
            if syncer.create_keycloak_user(user_sync_data):
                success_count += 1
                if not quiet:
                    print(f'  ✅ User {user_sync_data["username"]} synced')
            else:
                if not quiet:
                    print(f'  ⚠️  Failed to sync user {user_sync_data["username"]}')
        
        if not quiet:
            print('=' * 60)
            print(f'🎉 Keycloak sync completed: {success_count}/{len(users)} users synced')
            print(f'🔗 Users can login with:')
            print(f'   • Username/Email: their email address')
            print(f'   • Password: {syncer.default_password}')
            print('=' * 60)
        
        return True
        
    except Exception as e:
        if not quiet:
            print(f'\n⚠️  Keycloak sync failed: {e}')
            print('   This is not critical - tests can run without Keycloak.')
        return True  # Not a critical error


async def seed_from_json(json_file_path: str, sync_keycloak: bool = True) -> None:
    """Seed database with data from JSON file
    
    Args:
        json_file_path: Path to JSON file with test data
        sync_keycloak: If True, sync users to Keycloak after seeding (default: True)
    """

    # Validate file exists
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f'JSON file not found: {json_file_path}')

    print(f'📂 Loading fixture from: {json_file_path}')
    with open(json_file_path) as f:
        fixture_data = json.load(f)

    # Normalize JSON structure
    fixture = normalize_json_structure(fixture_data)

    async with SessionLocal() as session:
        try:
            # Reset database first
            await reset_database(session)

            print(f'\n🔄 Starting seeding from {os.path.basename(json_file_path)}...')

            # --- Insert Users ---
            for user_data in fixture['users']:
                user_data_copy = convert_timestamps(
                    user_data,
                    [
                        'created_at',
                        'updated_at',
                        'last_app_location_timestamp',
                        'last_transaction_timestamp',
                    ],
                )

                user = User(**user_data_copy)
                await session.merge(user)
                print(f'👤 Seeded User: {user.first_name} {user.last_name}')

                # Also create user in Keycloak for authentication
                if REQUESTS_AVAILABLE and user.email:
                    print(f'🔐 Creating Keycloak user for: {user.email}')
                    create_keycloak_user(
                        email=user.email,
                        first_name=user.first_name or '',
                        last_name=user.last_name or '',
                        password='password',  # Default password for test users
                    )

            # --- Insert Credit Cards ---
            for card_data in fixture['credit_cards']:
                card_data_copy = convert_timestamps(
                    card_data, ['created_at', 'updated_at']
                )

                card = CreditCard(**card_data_copy)
                await session.merge(card)
                print(f'💳 Seeded Credit Card: ****{card.card_number[-4:]}')

            # --- Insert Transactions (with dynamic dates) ---
            if fixture['transactions']:
                now = datetime.now(UTC)  # Use timezone-aware datetime
                print(f'\n⏰ Current time: {now}')
                print(f'📊 Processing {len(fixture["transactions"])} transactions...')

                # Calculate time offset based on first transaction
                time_offset = None
                first_transaction = fixture['transactions'][0]

                # Parse the first transaction date to calculate offset
                if 'transaction_date' in first_transaction:
                    original_date_str = first_transaction['transaction_date']
                    print(f'🔍 First transaction date from JSON: {original_date_str}')

                    # Parse the original date
                    if isinstance(original_date_str, str):
                        # Handle ISO format with 'Z' timezone
                        date_str_clean = original_date_str.replace('Z', '+00:00')
                        try:
                            original_date = datetime.fromisoformat(date_str_clean)
                        except ValueError:
                            # Fallback parsing - assume UTC if no timezone
                            try:
                                original_date = datetime.fromisoformat(
                                    original_date_str
                                )
                                if original_date.tzinfo is None:
                                    original_date = original_date.replace(tzinfo=UTC)
                            except ValueError:
                                # Last resort - parse as naive and assume UTC
                                original_date = datetime.strptime(
                                    original_date_str, '%Y-%m-%dT%H:%M:%S'
                                )
                                original_date = original_date.replace(tzinfo=UTC)
                    else:
                        original_date = original_date_str
                        if original_date.tzinfo is None:
                            original_date = original_date.replace(tzinfo=UTC)

                    # Calculate the time difference to bring transactions to "now"
                    time_offset = now - original_date
                    print(
                        f'🔍 Time offset calculated: {time_offset} (bringing {original_date} to ~{now})'
                    )
                else:
                    print(
                        '⚠️ No transaction_date found in first transaction, using fallback logic'
                    )
                    time_offset = timedelta(0)

                for i, txn_data in enumerate(fixture['transactions']):
                    print(
                        f'\n🔍 Processing transaction {i}: {txn_data.get("trans_num", "Unknown")}'
                    )
                    txn_data_copy = txn_data.copy()

                    # Generate new UUID
                    txn_data_copy['id'] = str(uuid.uuid4())

                    # Apply intelligent date transformation
                    if 'transaction_date' in txn_data_copy and time_offset is not None:
                        original_txn_date_str = txn_data_copy['transaction_date']
                        print(f'🔍 Original transaction date: {original_txn_date_str}')

                        # Parse the original transaction date
                        if isinstance(original_txn_date_str, str):
                            date_str_clean = original_txn_date_str.replace(
                                'Z', '+00:00'
                            )
                            try:
                                original_txn_date = datetime.fromisoformat(
                                    date_str_clean
                                )
                            except ValueError:
                                # Fallback parsing - assume UTC if no timezone
                                try:
                                    original_txn_date = datetime.fromisoformat(
                                        original_txn_date_str
                                    )
                                    if original_txn_date.tzinfo is None:
                                        original_txn_date = original_txn_date.replace(
                                            tzinfo=UTC
                                        )
                                except ValueError:
                                    # Last resort - parse as naive and assume UTC
                                    original_txn_date = datetime.strptime(
                                        original_txn_date_str, '%Y-%m-%dT%H:%M:%S'
                                    )
                                    original_txn_date = original_txn_date.replace(
                                        tzinfo=UTC
                                    )
                        else:
                            original_txn_date = original_txn_date_str
                            if original_txn_date.tzinfo is None:
                                original_txn_date = original_txn_date.replace(
                                    tzinfo=UTC
                                )

                        # Apply the time offset to maintain relative timing
                        new_txn_date = original_txn_date + time_offset
                        txn_data_copy['transaction_date'] = new_txn_date

                        print(
                            f'🔍 Adjusted transaction date: {original_txn_date} + {time_offset} = {new_txn_date}'
                        )
                    else:
                        # Fallback to old logic if no transaction_date
                        minutes_offset = 5 * i
                        txn_data_copy['transaction_date'] = now - timedelta(
                            minutes=minutes_offset
                        )
                        print(
                            f'🔍 Fallback: transaction date set to: {txn_data_copy["transaction_date"]}'
                        )

                    # Set created_at and updated_at to match transaction_date
                    txn_data_copy['created_at'] = txn_data_copy['transaction_date']
                    txn_data_copy['updated_at'] = txn_data_copy['transaction_date']

                    # Convert any remaining string timestamps
                    txn_data_copy = convert_timestamps(
                        txn_data_copy, ['transaction_date', 'created_at', 'updated_at']
                    )

                    try:
                        txn = Transaction(**txn_data_copy)
                        await session.merge(txn)
                        print(
                            f'💰 Seeded Transaction: {txn.trans_num} - ${txn.amount} at {txn.merchant_name} ({txn.transaction_date})'
                        )
                    except Exception as e:
                        print(f'❌ Failed to create transaction: {e}')
                        print(f'❌ Transaction data: {txn_data_copy}')
                        raise

            # Commit all changes
            await session.commit()
            print('\n✅ All data committed to database')

            # Verify insertion
            user_count = await session.scalar(select(func.count(User.id)))
            card_count = await session.scalar(select(func.count(CreditCard.id)))
            txn_count = await session.scalar(select(func.count(Transaction.id)))
            alert_rule_count = await session.scalar(select(func.count(AlertRule.id)))
            alert_notif_count = await session.scalar(
                select(func.count(AlertNotification.id))
            )

            print('\n📈 Final counts:')
            print(f'   • Users: {user_count}')
            print(f'   • Credit Cards: {card_count}')
            print(f'   • Transactions: {txn_count}')
            print(f'   • Alert Rules: {alert_rule_count}')
            print(f'   • Alert Notifications: {alert_notif_count}')
            print('\n🎉 Seeding completed successfully!')
            
            # Sync users to Keycloak if enabled
            if sync_keycloak and fixture['users']:
                sync_users_to_keycloak(fixture['users'])

        except Exception as e:
            print(f'\n❌ Error during seeding: {e}')
            await session.rollback()
            raise


def main():
    """Main function to handle command line arguments and execute seeding"""
    parser = argparse.ArgumentParser(
        description='Seed database with test data from JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_alert_rules.py json/spending_amount_dining.json
  python seed_alert_rules.py json/transaction_last_hour.json
  
Available JSON files in json/ directory:
  • spending_amount_dining.json - Dining transactions test data
  • transaction_last_hour.json - Recent transactions test data
        """,
    )

    parser.add_argument(
        'json_file',
        help='Path to JSON file containing test data (relative to script directory or absolute path)',
    )

    parser.add_argument(
        '--force',
        '-f',
        action='store_true',
        help='Skip confirmation prompt and proceed directly',
    )
    
    parser.add_argument(
        '--no-keycloak',
        action='store_true',
        help='Skip Keycloak user synchronization',
    )

    args = parser.parse_args()

    # Resolve JSON file path
    if os.path.isabs(args.json_file):
        json_file_path = args.json_file
    else:
        script_dir = os.path.dirname(__file__)
        json_file_path = os.path.join(script_dir, args.json_file)

    # Get user confirmation unless forced
    if not args.force:
        if not get_user_confirmation():
            return
    else:
        print('🔧 Force mode enabled. Skipping confirmation...')

    # Execute seeding
    try:
        asyncio.run(seed_from_json(json_file_path, sync_keycloak=not args.no_keycloak))
    except KeyboardInterrupt:
        print('\n⚠️  Interrupted by user. Exiting...')
    except Exception as e:
        print(f'\n💥 Failed to complete seeding: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

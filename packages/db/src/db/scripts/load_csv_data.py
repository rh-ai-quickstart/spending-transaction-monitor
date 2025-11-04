#!/usr/bin/env python3
"""Load sample data from CSV files into the database (SYNC version for migrations)"""

import csv
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

from db.config import settings
from db.models import AlertNotification, AlertRule, CreditCard, Transaction, User


def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in ISO format and ensure it's timezone-aware"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # Fallback for different formats
        dt = datetime.fromisoformat(date_str)

    # If the datetime is naive (no timezone), assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt


def clear_existing_data(session) -> None:
    """Clear all existing data from tables to ensure fresh load"""
    print('🗑️  Clearing existing data from all tables...')

    try:
        # Delete in order to respect foreign key constraints
        # Child tables first, then parent tables

        # Clear cached recommendations (has foreign keys to users)
        print('   Clearing cached recommendations...')
        result = session.execute(text('DELETE FROM cached_recommendations'))
        cached_recommendations_count = result.rowcount
        print(f'   Deleted {cached_recommendations_count} cached recommendations')

        # Clear alert notifications (has foreign keys to alert rules)
        print('   Clearing alert notifications...')
        result = session.execute(delete(AlertNotification))
        alert_notification_count = result.rowcount
        print(f'   Deleted {alert_notification_count} alert notifications')

        # Clear alert rules (has foreign keys to users)
        print('   Clearing alert notifications...')
        result = session.execute(delete(AlertRule))
        alert_count = result.rowcount
        print(f'   Deleted {alert_count} alert rules')

        # Clear transactions (has foreign keys to users and credit cards)
        print('   Clearing transactions...')
        result = session.execute(delete(Transaction))
        transaction_count = result.rowcount
        print(f'   Deleted {transaction_count} transactions')

        # Clear credit cards (has foreign keys to users)
        print('   Clearing credit cards...')
        result = session.execute(delete(CreditCard))
        card_count = result.rowcount
        print(f'   Deleted {card_count} credit cards')

        # Clear users (parent table, no foreign keys from other tables at this point)
        print('   Clearing users...')
        result = session.execute(delete(User))
        user_count = result.rowcount
        print(f'   Deleted {user_count} users')

        session.commit()

        total_deleted = transaction_count + alert_count + card_count + user_count
        print(f'✅ Successfully cleared {total_deleted} total records from all tables')

    except Exception as e:
        print(f'❌ Error clearing existing data: {e}')
        session.rollback()
        raise


def load_users_from_csv(session, csv_file_path: str) -> dict[str, str]:
    """Load users from CSV and return mapping of user_id to user_id (for validation)"""
    print(f'📥 Loading users from {csv_file_path}...')
    user_id_mapping = {}

    try:
        with open(csv_file_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            users_to_add = []

            for row in reader:
                user = User(
                    id=row['id'],
                    email=row['email'],
                    keycloak_id=row.get('keycloak_id'),
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    phone_number=row.get('phone_number'),
                    created_at=parse_datetime(row['created_at'])
                    if row.get('created_at')
                    else datetime.now(UTC),
                    updated_at=parse_datetime(row['updated_at'])
                    if row.get('updated_at')
                    else datetime.now(UTC),
                    is_active=row.get('is_active', 'True') == 'True',
                    address_street=row.get('address_street'),
                    address_city=row.get('address_city'),
                    address_state=row.get('address_state'),
                    address_zipcode=row.get('address_zipcode'),
                    address_country=row.get('address_country', 'US'),
                )
                users_to_add.append(user)

            # Bulk insert users
            session.bulk_save_objects(users_to_add, return_defaults=True)
            session.commit()

            # Create mapping of user IDs (ID is already in CSV)
            for user in users_to_add:
                user_id_mapping[user.id] = user.id

            print(f'✅ Loaded {len(users_to_add)} users')
            return user_id_mapping

    except FileNotFoundError:
        print(f'❌ CSV file not found: {csv_file_path}')
        raise
    except Exception as e:
        print(f'❌ Error loading users: {e}')
        session.rollback()
        raise


def load_transactions_from_csv(
    session, csv_file_path: str, user_id_mapping: dict[str, str]
) -> None:
    """Load transactions from CSV"""
    print(f'📥 Loading transactions from {csv_file_path}...')

    try:
        with open(csv_file_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            batch_size = 1000
            transactions_to_add = []
            total_loaded = 0
            skipped = 0

            for i, row in enumerate(reader, 1):
                user_id = row.get('user_id')
                if not user_id or user_id not in user_id_mapping:
                    skipped += 1
                    continue

                try:
                    transaction = Transaction(
                        id=row['id'],
                        user_id=user_id,
                        credit_card_num=row.get('credit_card_num'),
                        amount=Decimal(str(row['amount'])),
                        currency=row.get('currency', 'USD'),
                        description=row.get('description', ''),
                        merchant_name=row.get('merchant_name', ''),
                        merchant_category=row.get('merchant_category', ''),
                        transaction_date=parse_datetime(row['transaction_date']),
                        transaction_type=row.get('transaction_type', 'PURCHASE'),
                        merchant_latitude=float(row['merchant_latitude'])
                        if row.get('merchant_latitude')
                        else None,
                        merchant_longitude=float(row['merchant_longitude'])
                        if row.get('merchant_longitude')
                        else None,
                        merchant_zipcode=row.get('merchant_zipcode'),
                        merchant_city=row.get('merchant_city'),
                        merchant_state=row.get('merchant_state'),
                        merchant_country=row.get('merchant_country', 'US'),
                        status=row.get('status', 'APPROVED'),
                        authorization_code=row.get('authorization_code'),
                        trans_num=row.get('trans_num'),
                        created_at=parse_datetime(row['created_at'])
                        if row.get('created_at')
                        else datetime.now(UTC),
                        updated_at=parse_datetime(row['updated_at'])
                        if row.get('updated_at')
                        else datetime.now(UTC),
                    )
                    transactions_to_add.append(transaction)

                    # Commit in batches
                    if len(transactions_to_add) >= batch_size:
                        session.bulk_save_objects(transactions_to_add)
                        session.commit()
                        total_loaded += len(transactions_to_add)
                        print(f'   Loaded {total_loaded} transactions...')
                        transactions_to_add = []

                except (ValueError, KeyError) as e:
                    print(f'   ⚠️  Skipping row {i} due to error: {e}')
                    skipped += 1
                    continue

            # Commit remaining transactions
            if transactions_to_add:
                session.bulk_save_objects(transactions_to_add)
                session.commit()
                total_loaded += len(transactions_to_add)

            print(f'✅ Loaded {total_loaded} transactions')
            if skipped > 0:
                print(f'   ⚠️  Skipped {skipped} transactions due to errors')

    except FileNotFoundError:
        print(f'❌ CSV file not found: {csv_file_path}')
        raise
    except Exception as e:
        print(f'❌ Error loading transactions: {e}')
        session.rollback()
        raise


def load_csv_data(
    users_csv_path: str = '/app/data/sample_users.csv',
    transactions_csv_path: str = '/app/data/sample_transactions.csv',
) -> None:
    """Main function to load data from CSV files using sync engine"""
    print('🚀 Starting CSV data loading process (SYNC mode)...')

    # Create sync engine from DATABASE_URL (replace asyncpg with psycopg2)
    database_url = settings.DATABASE_URL.replace('+asyncpg', '+psycopg2')
    print(
        f'📊 Using database: {database_url.split("@")[1] if "@" in database_url else "..."}'
    )

    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        try:
            # Clear all existing data first
            clear_existing_data(session)

            # Load users first and get ID mapping
            user_id_mapping = load_users_from_csv(session, users_csv_path)

            if not user_id_mapping:
                print('❌ No users loaded, skipping transactions')
                return

            # Load transactions using the user ID mapping
            load_transactions_from_csv(session, transactions_csv_path, user_id_mapping)

            print('✅ CSV data loading completed successfully!')

        except Exception as e:
            print(f'❌ Error during CSV data loading: {e}')
            session.rollback()
            raise


if __name__ == '__main__':
    load_csv_data()

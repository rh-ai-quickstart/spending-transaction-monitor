#!/usr/bin/env python3
"""Load sample data from CSV files into the database"""

import asyncio
import csv
import os
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, text

from db.database import SessionLocal
from db.models import AlertNotification, AlertRule, CreditCard, Transaction, User


async def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in ISO format and ensure it's timezone-aware"""
    try:
        # Handle both formats: with 'Z' and without timezone info
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # Fallback for different formats
        try:
            dt = datetime.fromisoformat(date_str)
        except ValueError:
            # Last resort: try parsing as basic datetime
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')

    # CRITICAL: Ensure the datetime is timezone-aware (assume UTC if naive)
    # This prevents "can't subtract offset-naive and offset-aware datetimes" errors
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt


async def clear_existing_data(session) -> None:
    """Clear all existing data from tables to ensure fresh load"""
    print('🗑️  Clearing existing data from all tables...')

    try:
        # Delete in order to respect foreign key constraints
        # Child tables first, then parent tables

        # Clear cached recommendations (has foreign keys to users)
        print('   Clearing cached recommendations...')
        result = await session.execute(text('DELETE FROM cached_recommendations'))
        cached_recommendations_count = result.rowcount
        print(f'   Deleted {cached_recommendations_count} cached recommendations')

        # Clear alert notifications (has foreign keys to alert rules)
        print('   Clearing alert notifications...')
        result = await session.execute(delete(AlertNotification))
        alert_notification_count = result.rowcount
        print(f'   Deleted {alert_notification_count} alert notifications')

        # Clear alert rules (has foreign keys to users)
        print('   Clearing alert rules...')
        result = await session.execute(delete(AlertRule))
        alert_count = result.rowcount
        print(f'   Deleted {alert_count} alert rules')

        # Clear transactions first (has foreign keys to users)
        print('   Clearing transactions...')
        result = await session.execute(delete(Transaction))
        transaction_count = result.rowcount
        print(f'   Deleted {transaction_count} transactions')

        # Clear credit cards (has foreign keys to users)
        print('   Clearing credit cards...')
        result = await session.execute(delete(CreditCard))
        card_count = result.rowcount
        print(f'   Deleted {card_count} credit cards')

        # Clear users last (parent table)
        print('   Clearing users...')
        result = await session.execute(delete(User))
        user_count = result.rowcount
        print(f'   Deleted {user_count} users')

        # Reset auto-increment sequences if using PostgreSQL
        try:
            # This will reset sequences for auto-increment columns
            await session.execute(
                text("SELECT setval(pg_get_serial_sequence('users', 'id'), 1, false);")
            )
            await session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('transactions', 'id'), 1, false);"
                )
            )
            await session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('alert_rules', 'id'), 1, false);"
                )
            )
            await session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('credit_cards', 'id'), 1, false);"
                )
            )
            print('   Reset auto-increment sequences')
        except Exception as seq_error:
            # Sequences may not exist or may have different names, which is okay
            print(
                f'   Note: Could not reset sequences (this is usually okay): {seq_error}'
            )

        await session.commit()

        total_deleted = transaction_count + alert_count + card_count + user_count
        print(f'✅ Successfully cleared {total_deleted} total records from all tables')

    except Exception as e:
        print(f'❌ Error clearing existing data: {e}')
        await session.rollback()
        raise


async def load_users_from_csv(session, csv_path: str) -> dict[str, str]:
    """Load users from CSV file and return mapping of old_id -> new_user_id"""
    print(f'Loading users from {csv_path}')

    if not os.path.exists(csv_path):
        print(f'❌ CSV file not found: {csv_path}')
        return {}

    user_id_mapping = {}

    try:
        # First pass: Read all users to find the latest created_at date for time adjustment
        users_data = []
        latest_user_date = None

        with open(csv_path, encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Parse user creation date for time adjustment
                if row.get('created_at'):
                    created_at = await parse_datetime(row['created_at'])
                    if latest_user_date is None or created_at > latest_user_date:
                        latest_user_date = created_at
                    users_data.append((row, created_at))
                else:
                    users_data.append((row, None))

        if not users_data:
            print('No users found in CSV file')
            return {}

        # Calculate time adjustment offset for users
        current_time = datetime.now(UTC)
        if latest_user_date:
            user_time_offset = current_time - latest_user_date
            print(f'👥 Latest user creation date in CSV: {latest_user_date}')
            print(f'👥 Adjusting user timestamps by: {user_time_offset}')
        else:
            user_time_offset = None
            print('⚠️  No user creation dates found, using current time')

        # Second pass: Insert users with adjusted timestamps
        users_added = 0

        for row, original_created_at in users_data:
            # Adjust created_at timestamp
            if original_created_at and user_time_offset:
                adjusted_created_at = original_created_at + user_time_offset
            elif original_created_at:
                adjusted_created_at = original_created_at
            else:
                adjusted_created_at = current_time

            # Adjust updated_at timestamp
            if row.get('updated_at'):
                original_updated_at = await parse_datetime(row['updated_at'])
                if user_time_offset:
                    adjusted_updated_at = original_updated_at + user_time_offset
                else:
                    adjusted_updated_at = original_updated_at
            else:
                adjusted_updated_at = current_time

            user = User(
                id=row['id'],  # Use the ID from CSV
                email=row['email'],
                keycloak_id=row.get('keycloak_id'),
                first_name=row['first_name'],
                last_name=row['last_name'],
                phone_number=row.get('phone_number'),
                address_street=row.get('address_street'),
                address_city=row.get('address_city'),
                address_state=row.get('address_state'),
                address_zipcode=row.get('address_zipcode'),
                address_country=row.get('address_country'),
                credit_limit=Decimal(row.get('credit_limit', '0'))
                if row.get('credit_limit')
                else None,
                credit_balance=Decimal(row.get('credit_balance', '0'))
                if row.get('credit_balance')
                else None,
                is_active=row.get('is_active', 'True').lower() == 'true',
                created_at=adjusted_created_at,
                updated_at=adjusted_updated_at,
            )

            session.add(user)
            user_id_mapping[row['id']] = row['id']
            users_added += 1

        await session.commit()
        print(
            f'✅ Successfully loaded {users_added} users from CSV with adjusted timestamps'
        )
        return user_id_mapping

    except Exception as e:
        print(f'❌ Error loading users from CSV: {e}')
        await session.rollback()
        return {}


async def load_transactions_from_csv(
    session, csv_path: str, user_id_mapping: dict[str, str]
) -> None:
    """Load transactions from CSV file with adjusted timestamps"""
    print(f'Loading transactions from {csv_path}')

    if not os.path.exists(csv_path):
        print(f'❌ CSV file not found: {csv_path}')
        return

    try:
        # First pass: Read all transactions to find the latest transaction_date
        print('🕐 Analyzing transaction dates to adjust timestamps...')
        transactions_data = []
        latest_transaction_date = None

        with open(csv_path, encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Map user_id from CSV to actual user_id
                user_id = user_id_mapping.get(row['user_id'])
                if not user_id:
                    print(
                        f'Warning: User ID {row["user_id"]} not found in user mapping, skipping transaction'
                    )
                    continue

                # Parse transaction date
                if row.get('transaction_date'):
                    transaction_date = await parse_datetime(row['transaction_date'])
                    if (
                        latest_transaction_date is None
                        or transaction_date > latest_transaction_date
                    ):
                        latest_transaction_date = transaction_date

                    # Store transaction data for processing
                    transactions_data.append((row, user_id, transaction_date))
                else:
                    # Handle transactions without dates
                    transactions_data.append((row, user_id, None))

        if not transactions_data:
            print('No transactions found in CSV file')
            return

        # Calculate time adjustment offset
        current_time = datetime.now(UTC)
        if latest_transaction_date:
            time_offset = current_time - latest_transaction_date
            print(f'📅 Latest transaction date in CSV: {latest_transaction_date}')
            print(f'📅 Current time: {current_time}')
            print(f'📅 Adjusting all transaction dates by: {time_offset}')
        else:
            time_offset = None
            print(
                '⚠️  No transaction dates found, using current time for all transactions'
            )

        # Second pass: Insert transactions with adjusted timestamps
        transactions_added = 0

        for row, user_id, original_date in transactions_data:
            # Adjust transaction date
            if original_date and time_offset:
                adjusted_transaction_date = original_date + time_offset
            elif original_date:
                adjusted_transaction_date = original_date
            else:
                adjusted_transaction_date = current_time

            # Adjust created_at and updated_at times as well
            if row.get('created_at'):
                original_created_at = await parse_datetime(row['created_at'])
                if time_offset:
                    adjusted_created_at = original_created_at + time_offset
                else:
                    adjusted_created_at = original_created_at
            else:
                adjusted_created_at = current_time

            if row.get('updated_at'):
                original_updated_at = await parse_datetime(row['updated_at'])
                if time_offset:
                    adjusted_updated_at = original_updated_at + time_offset
                else:
                    adjusted_updated_at = original_updated_at
            else:
                adjusted_updated_at = current_time

            transaction = Transaction(
                id=row['id'],
                user_id=user_id,
                credit_card_num=row.get('credit_card_num'),
                amount=Decimal(row['amount']) if row.get('amount') else Decimal('0'),
                currency=row.get('currency', 'USD'),
                description=row.get('description'),
                merchant_name=row.get('merchant_name'),
                merchant_category=row.get('merchant_category'),
                transaction_date=adjusted_transaction_date,
                transaction_type=row.get('transaction_type'),
                merchant_latitude=float(row['merchant_latitude'])
                if row.get('merchant_latitude')
                else None,
                merchant_longitude=float(row['merchant_longitude'])
                if row.get('merchant_longitude')
                else None,
                merchant_zipcode=row.get('merchant_zipcode'),
                merchant_city=row.get('merchant_city'),
                merchant_state=row.get('merchant_state'),
                merchant_country=row.get('merchant_country'),
                status=row.get('status'),
                authorization_code=row.get('authorization_code'),
                trans_num=row.get('trans_num'),
                created_at=adjusted_created_at,
                updated_at=adjusted_updated_at,
            )

            session.add(transaction)
            transactions_added += 1

        await session.commit()
        print(
            f'✅ Successfully loaded {transactions_added} transactions from CSV with adjusted timestamps'
        )

        # Show some example adjusted dates for verification
        if transactions_data and time_offset:
            print('📊 Timestamp Adjustment Summary:')
            print(f'   • Original latest transaction: {latest_transaction_date}')
            print(f'   • Adjusted to current time: {current_time}')
            print(f'   • Time shift applied: {time_offset}')
            print(
                f'   • All {len(transactions_data)} transactions shifted by the same amount'
            )

    except Exception as e:
        print(f'❌ Error loading transactions from CSV: {e}')
        await session.rollback()


async def load_csv_data(
    users_csv_path: str = '/app/data/sample_users.csv',
    transactions_csv_path: str = '/app/data/sample_transactions.csv',
) -> None:
    """Main function to load data from CSV files"""
    print('🚀 Starting CSV data loading process...')

    async with SessionLocal() as session:
        try:
            # Clear all existing data first
            await clear_existing_data(session)

            # Load users first and get ID mapping
            user_id_mapping = await load_users_from_csv(session, users_csv_path)

            if not user_id_mapping:
                print('❌ No users loaded, skipping transactions')
                return

            # Load transactions using the user ID mapping
            await load_transactions_from_csv(
                session, transactions_csv_path, user_id_mapping
            )

            print('✅ CSV data loading completed successfully!')

        except Exception as e:
            print(f'❌ Error during CSV data loading: {e}')
            await session.rollback()
            raise


if __name__ == '__main__':
    asyncio.run(load_csv_data())

#!/usr/bin/env python3
"""
Generate sample data files from credit_card_transactions.csv
Extracts top 50 users and creates sample_users.csv and sample_transactions.csv
matching the application schema.
"""

import csv
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
import random


def parse_date(date_str):
    """Parse date string from CSV"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%d")


def convert_to_2025(original_date):
    """Convert any date to 2025 while preserving month, day, and time"""
    return original_date.replace(year=2025)


def format_credit_card(cc_num):
    """Format credit card number to match schema format (####-####-####-####)"""
    cc_str = str(cc_num)
    cc_str = cc_str.zfill(16)
    return f"{cc_str[0:4]}-{cc_str[4:8]}-{cc_str[8:12]}-{cc_str[12:16]}"


def generate_user_id(index):
    """Generate user ID in format u-XXX"""
    return f"u-{str(index).zfill(3)}"


def main():
    input_file = "credit_card_transactions.csv"
    users_output = "data/sample_users.csv"
    transactions_output = "data/sample_transactions.csv"

    print(f"Reading {input_file}...")

    # Read all transactions and group by user
    user_transactions = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cc_num = row['cc_num']
            user_transactions[cc_num].append(row)

    # Get top 50 users by transaction count
    top_users = sorted(user_transactions.items(),
                      key=lambda x: len(x[1]),
                      reverse=True)[:50]

    print(f"Found {len(user_transactions)} unique users")
    print(f"Extracting top 50 users with most transactions...")

    # Generate users CSV
    user_data = []
    cc_num_to_user_id = {}

    for idx, (cc_num, transactions) in enumerate(top_users, start=1):
        user_id = generate_user_id(idx)
        cc_num_to_user_id[cc_num] = user_id

        # Get user info from first transaction
        first_trans = transactions[0]

        # Calculate credit balance from all transactions
        total_amount = sum(float(t['amt']) for t in transactions)

        # Random credit limit between 5000-15000
        credit_limit = random.choice([5000, 7000, 10000, 12000, 15000])

        user_data.append({
            'id': user_id,
            'email': f"{first_trans['first'].lower()}.{first_trans['last'].lower()}@example.com",
            'keycloak_id': str(uuid.uuid4()),
            'first_name': first_trans['first'],
            'last_name': first_trans['last'],
            'phone_number': f"555-{str(idx).zfill(5)}",
            'created_at': convert_to_2025(parse_date('2025-01-01 00:00:00')).isoformat(),
            'updated_at': convert_to_2025(datetime.now()).isoformat(),
            'is_active': 'True',
            'address_street': first_trans['street'],
            'address_city': first_trans['city'],
            'address_state': first_trans['state'],
            'address_zipcode': first_trans['zip'],
            'address_country': 'US',
            'credit_limit': credit_limit,
            'credit_balance': round(total_amount % credit_limit, 2)  # Keep balance under limit
        })

    # Write users CSV
    print(f"Writing {len(user_data)} users to {users_output}...")
    with open(users_output, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'email', 'keycloak_id', 'first_name', 'last_name',
                     'phone_number', 'created_at', 'updated_at', 'is_active',
                     'address_street', 'address_city', 'address_state',
                     'address_zipcode', 'address_country', 'credit_limit', 'credit_balance']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(user_data)

    # Generate transactions CSV
    transaction_data = []

    for cc_num, transactions in top_users:
        user_id = cc_num_to_user_id[cc_num]

        for trans in transactions:
            trans_date = parse_date(trans['trans_date_trans_time'])
            trans_date_2025 = convert_to_2025(trans_date)

            # Map category to more readable format
            category_map = {
                'gas_transport': 'Gas & Transport',
                'grocery_pos': 'Grocery',
                'grocery_net': 'Grocery',
                'misc_pos': 'Miscellaneous',
                'misc_net': 'Miscellaneous',
                'entertainment': 'Entertainment',
                'shopping_net': 'Shopping',
                'shopping_pos': 'Shopping',
                'food_dining': 'Food & Dining',
                'personal_care': 'Personal Care',
                'health_fitness': 'Health & Fitness',
                'travel': 'Travel',
                'home': 'Home'
            }

            merchant_category = category_map.get(trans['category'], trans['category'].title())

            # Determine transaction status (most should be approved)
            status = 'APPROVED' if int(trans.get('is_fraud', 0)) == 0 else random.choice(['APPROVED', 'DECLINED'])

            transaction_data.append({
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'credit_card_num': format_credit_card(cc_num),
                'amount': float(trans['amt']),
                'currency': 'USD',
                'description': f"Purchase at {trans['merchant'].replace('fraud_', '')}",
                'merchant_name': trans['merchant'].replace('fraud_', ''),
                'merchant_category': merchant_category,
                'transaction_date': trans_date_2025.isoformat(),
                'transaction_type': 'PURCHASE',
                'merchant_latitude': float(trans['merch_lat']) if trans['merch_lat'] else None,
                'merchant_longitude': float(trans['merch_long']) if trans['merch_long'] else None,
                'merchant_zipcode': trans.get('merch_zipcode', ''),
                'merchant_city': trans['city'],
                'merchant_state': trans['state'],
                'merchant_country': 'US',
                'status': status,
                'authorization_code': str(random.randint(100000, 999999)),
                'trans_num': trans['trans_num'],
                'created_at': trans_date_2025.isoformat(),
                'updated_at': trans_date_2025.isoformat()
            })

    # Write transactions CSV
    print(f"Writing {len(transaction_data)} transactions to {transactions_output}...")
    with open(transactions_output, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'user_id', 'credit_card_num', 'amount', 'currency',
                     'description', 'merchant_name', 'merchant_category',
                     'transaction_date', 'transaction_type', 'merchant_latitude',
                     'merchant_longitude', 'merchant_zipcode', 'merchant_city',
                     'merchant_state', 'merchant_country', 'status',
                     'authorization_code', 'trans_num', 'created_at', 'updated_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transaction_data)

    print("\nComplete!")
    print(f"Generated {len(user_data)} users")
    print(f"Generated {len(transaction_data)} transactions")
    print(f"\nOutput files:")
    print(f"  - {users_output}")
    print(f"  - {transactions_output}")


if __name__ == "__main__":
    main()

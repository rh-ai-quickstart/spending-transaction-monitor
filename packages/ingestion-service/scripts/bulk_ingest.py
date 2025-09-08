import csv
import os
import sys

import requests

# Add the `ingestion-service-py` directory to the path to allow imports from the `common` directory
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../ingestion-service-py'))
)
from common.models import Transaction


def bulk_ingest(file_path, url):
    with open(file_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clean up the amount field
            amount = float(row['Amount'].replace('$', ''))

            # Convert 'Yes'/'No' to boolean
            is_fraud = row['Is Fraud?'] == 'Yes'

            transaction = Transaction(
                user=int(row['User']),
                card=int(row['Card']),
                year=int(row['Year']),
                month=int(row['Month']),
                day=int(row['Day']),
                time=row['Time'],
                amount=amount,
                use_chip=row['Use Chip'],
                merchant_id=int(row['Merchant Name']),
                merchant_city=row['Merchant City'],
                merchant_state=row['Merchant State'],
                zip=row['Zip'],
                mcc=int(row['MCC']),
                errors=row['Errors?'],
                is_fraud=is_fraud,
            )

            response = requests.post(
                url,
                data=transaction.json(),
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()


if __name__ == '__main__':
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Go up one directory and then into the data directory
    file_path = os.path.join(script_dir, '..', 'data', 'transactions.csv')
    bulk_ingest(file_path, 'http://localhost:8000/transactions/')

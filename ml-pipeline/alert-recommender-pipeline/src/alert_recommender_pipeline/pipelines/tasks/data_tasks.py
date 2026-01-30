"""Data preparation task for Alert Recommender Pipeline."""

from kfp import dsl
from kfp.dsl import Output, Dataset

from .constants import BASE_IMAGE


@dsl.component(base_image=BASE_IMAGE)
def prepare_data(output_data: Output[Dataset]):
    """
    Prepare training data by loading from PostgreSQL database, MinIO, or local storage.
    
    This task automatically tries data sources in order:
    1. PostgreSQL database (using spending-monitor-db service)
    2. MinIO (S3-compatible storage)
    3. Local filesystem (fallback)
    
    The database is preferred as it contains live application data.
    
    Outputs:
        output_data: Dataset containing users.csv, transactions.csv, and metadata.json
    """
    import os
    import json
    import pandas as pd
    import boto3
    from botocore.client import Config
    
    data_version = os.getenv('DATA_VERSION', '1')
    
    print(f"Data preparation configuration:")
    print(f"  Data Version: {data_version}")
    
    os.makedirs(output_data.path, exist_ok=True)
    
    users_df = None
    transactions_df = None
    use_real_alerts = False
    data_source_used = None
    
    def load_from_database():
        """Load users and transactions from PostgreSQL database."""
        import psycopg2
        
        db_host = os.getenv('POSTGRES_DB_HOST', 'spending-monitor-db')
        db_port = os.getenv('POSTGRES_DB_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'spending-monitor')
        db_user = os.getenv('POSTGRES_USER', 'user')
        db_password = os.getenv('POSTGRES_PASSWORD', '')
        
        print(f"Attempting database connection:")
        print(f"  Host: {db_host}")
        print(f"  Port: {db_port}")
        print(f"  Database: {db_name}")
        
        if not db_password:
            raise RuntimeError("Database password not configured (POSTGRES_PASSWORD)")
        
        conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"
        
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        print("Connected to PostgreSQL database")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('users', 'transactions')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        if 'users' not in existing_tables:
            cursor.close()
            conn.close()
            raise RuntimeError("Table 'users' does not exist - database migrations may not have run yet")
        
        if 'transactions' not in existing_tables:
            cursor.close()
            conn.close()
            raise RuntimeError("Table 'transactions' does not exist - database migrations may not have run yet")
        
        users_query = """
            SELECT 
                id, email, first_name, last_name,
                credit_limit, credit_balance, is_active, created_at
            FROM public.users
            WHERE is_active = true
        """
        cursor.execute(users_query)
        columns = [desc[0] for desc in cursor.description]
        users_df = pd.DataFrame(cursor.fetchall(), columns=columns)
        print(f"Loaded {len(users_df)} users from database")
        
        if len(users_df) == 0:
            cursor.close()
            conn.close()
            raise RuntimeError("No users found in database")
        
        transactions_query = """
            SELECT 
                id, user_id, amount, currency, merchant_name, merchant_category,
                transaction_date, transaction_type, status,
                merchant_city, merchant_state, merchant_country
            FROM public.transactions
            WHERE status IN ('APPROVED', 'SETTLED')
            ORDER BY transaction_date DESC
        """
        cursor.execute(transactions_query)
        columns = [desc[0] for desc in cursor.description]
        transactions_df = pd.DataFrame(cursor.fetchall(), columns=columns)
        print(f"Loaded {len(transactions_df)} transactions from database")
        
        if len(transactions_df) == 0:
            cursor.close()
            conn.close()
            raise RuntimeError("No transactions found in database")
        
        use_real_alerts = False
        try:
            alerts_query = """
                SELECT user_id, alert_type, is_active, amount_threshold, merchant_category, merchant_name
                FROM public.alert_rules
                WHERE is_active = true
            """
            cursor.execute(alerts_query)
            columns = [desc[0] for desc in cursor.description]
            alerts_df = pd.DataFrame(cursor.fetchall(), columns=columns)
            print(f"Loaded {len(alerts_df)} alert rules from database")
            use_real_alerts = len(alerts_df) > 0
        except Exception as e:
            print(f"Could not load alert rules from database: {e}")
        
        cursor.close()
        conn.close()
        return users_df, transactions_df, use_real_alerts
    
    def load_from_minio():
        """Load users and transactions from MinIO S3-compatible storage. This is a backup data source in case the database is not available."""
        namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
        bucket_name = os.getenv('BUCKET_NAME', 'models')
        minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
        minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
        minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
        
        print(f"Attempting MinIO connection:")
        print(f"  Endpoint: {minio_endpoint}")
        print(f"  Bucket: {bucket_name}")
        
        s3_client = boto3.client(
            's3',
            endpoint_url=minio_endpoint,
            aws_access_key_id=minio_access_key,
            aws_secret_access_key=minio_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        data_key_prefix = f'data/v{data_version}'
        
        users_key = f'{data_key_prefix}/users.csv'
        users_local_path = os.path.join(output_data.path, 'users.csv')
        s3_client.download_file(bucket_name, users_key, users_local_path)
        users_df = pd.read_csv(users_local_path)
        print(f"Loaded {len(users_df)} users from MinIO")
        
        transactions_key = f'{data_key_prefix}/transactions.csv'
        transactions_local_path = os.path.join(output_data.path, 'transactions.csv')
        s3_client.download_file(bucket_name, transactions_key, transactions_local_path)
        transactions_df = pd.read_csv(transactions_local_path)
        print(f"Loaded {len(transactions_df)} transactions from MinIO")
        
        use_real_alerts = False
        try:
            alerts_key = f'{data_key_prefix}/user_alerts.csv'
            alerts_local_path = os.path.join(output_data.path, 'user_alerts.csv')
            s3_client.download_file(bucket_name, alerts_key, alerts_local_path)
            user_alerts_df = pd.read_csv(alerts_local_path)
            print(f"Loaded {len(user_alerts_df)} alert preferences from MinIO")
            use_real_alerts = True
        except Exception as e:
            print(f"No alert preferences found in MinIO: {e}")
        
        return users_df, transactions_df, use_real_alerts
    
    def load_from_local():
        """Load users and transactions from local filesystem."""
        users_path = '/app/data/users.csv'
        transactions_path = '/app/data/transactions.csv'
        
        print(f"Attempting local file load:")
        print(f"  Users path: {users_path}")
        print(f"  Transactions path: {transactions_path}")
        
        if not os.path.exists(users_path):
            raise RuntimeError(f"No users data found at {users_path}")
        if not os.path.exists(transactions_path):
            raise RuntimeError(f"No transactions data found at {transactions_path}")
        
        users_df = pd.read_csv(users_path)
        print(f"Loaded {len(users_df)} users from local storage")
        
        transactions_df = pd.read_csv(transactions_path)
        print(f"Loaded {len(transactions_df)} transactions from local storage")
        
        return users_df, transactions_df, False
    
    # Try data sources in order: Database -> MinIO -> Local
    try:
        print("\n=== Trying database as data source ===")
        users_df, transactions_df, use_real_alerts = load_from_database()
        data_source_used = 'database'
    except Exception as e:
        print(f"Database load failed: {e}")
        try:
            print("\n=== Falling back to MinIO ===")
            users_df, transactions_df, use_real_alerts = load_from_minio()
            data_source_used = 'minio'
        except Exception as e2:
            print(f"MinIO load failed: {e2}")
            print("\n=== Falling back to local storage ===")
            users_df, transactions_df, use_real_alerts = load_from_local()
            data_source_used = 'local'
    
    print(f"\n=== Data loaded from: {data_source_used} ===")
    
    users_local_path = os.path.join(output_data.path, 'users.csv')
    transactions_local_path = os.path.join(output_data.path, 'transactions.csv')
    
    users_df.to_csv(users_local_path, index=False)
    transactions_df.to_csv(transactions_local_path, index=False)
    
    metadata = {
        'data_source': data_source_used,
        'data_version': data_version,
        'n_users': len(users_df),
        'n_transactions': len(transactions_df),
        'use_real_alerts': use_real_alerts
    }
    
    with open(os.path.join(output_data.path, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Data preparation complete. Output: {output_data.path}")

"""Kubeflow Pipeline tasks for Alert Recommender Pipeline.

These tasks replicate the functionality from the Jupyter notebooks:
- 1_train_alert_model.ipynb -> train_model
- 2_save_model.ipynb -> save_model
- 3_deploy_model.ipynb -> deploy_model
- 4_cleanup_deployment.ipynb -> cleanup_deployment
"""

import os
from kfp import dsl
from kfp.dsl import Output, Input, Dataset, Model, Artifact

BASE_IMAGE = os.environ.get("ALERT_RECOMMENDER_PIPELINE_IMAGE", "quay.io/rh-ai-quickstart/alert-recommender-pipeline:latest")


@dsl.component(base_image=BASE_IMAGE)
def prepare_data(output_data: Output[Dataset]):
    """
    Prepare training data by loading from PostgreSQL database, MinIO, or local storage.
    
    This task automatically tries data sources in order:
    1. PostgreSQL database (using spending-monitor-db service)
    2. MinIO (S3-compatible storage)
    3. Local filesystem (fallback)
    
    The database is preferred as it contains live application data.
    """
    import os
    import json
    import pandas as pd
    import boto3
    from botocore.client import Config
    
    data_version = os.getenv('DATA_VERSION', '1')
    
    print(f"Data preparation configuration:")
    print(f"  Data Version: {data_version}")
    
    # Create output directory
    os.makedirs(output_data.path, exist_ok=True)
    
    users_df = None
    transactions_df = None
    use_real_alerts = False
    data_source_used = None
    
    # Helper function to load from database
    def load_from_database():
        """Load users and transactions from PostgreSQL database."""
        import psycopg2
        
        # Get database configuration from environment
        # These come from the spending-monitor-secret in the same namespace
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
        
        # Build connection string
        conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"
        
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        print("Connected to PostgreSQL database")
        
        # Check if tables exist before querying
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('users', 'transactions')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {existing_tables}")
        
        if 'users' not in existing_tables:
            cursor.close()
            conn.close()
            raise RuntimeError("Table 'users' does not exist - database migrations may not have run yet")
        
        if 'transactions' not in existing_tables:
            cursor.close()
            conn.close()
            raise RuntimeError("Table 'transactions' does not exist - database migrations may not have run yet")
        
        # Query users - select columns needed for ML pipeline
        # Use explicit public schema to avoid search_path issues
        users_query = """
            SELECT 
                id,
                email,
                first_name,
                last_name,
                credit_limit,
                credit_balance,
                is_active,
                created_at
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
        
        # Query transactions - select columns needed for ML pipeline
        transactions_query = """
            SELECT 
                id,
                user_id,
                amount,
                currency,
                merchant_name,
                merchant_category,
                transaction_date,
                transaction_type,
                status,
                merchant_city,
                merchant_state,
                merchant_country
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
        
        # Try to load alert rules for real labels
        use_real_alerts = False
        try:
            alerts_query = """
                SELECT 
                    user_id,
                    alert_type,
                    is_active,
                    amount_threshold,
                    merchant_category,
                    merchant_name
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
    
    # Helper function to load from MinIO
    def load_from_minio():
        """Load users and transactions from MinIO S3-compatible storage."""
        namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
        bucket_name = os.getenv('BUCKET_NAME', 'models')
        minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
        minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
        minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
        
        print(f"Attempting MinIO connection:")
        print(f"  Endpoint: {minio_endpoint}")
        print(f"  Bucket: {bucket_name}")
        
        # Initialize MinIO client
        s3_client = boto3.client(
            's3',
            endpoint_url=minio_endpoint,
            aws_access_key_id=minio_access_key,
            aws_secret_access_key=minio_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        
        data_key_prefix = f'data/v{data_version}'
        
        # Load users
        users_key = f'{data_key_prefix}/users.csv'
        users_local_path = os.path.join(output_data.path, 'users.csv')
        s3_client.download_file(bucket_name, users_key, users_local_path)
        users_df = pd.read_csv(users_local_path)
        print(f"Loaded {len(users_df)} users from MinIO")
        
        # Load transactions
        transactions_key = f'{data_key_prefix}/transactions.csv'
        transactions_local_path = os.path.join(output_data.path, 'transactions.csv')
        s3_client.download_file(bucket_name, transactions_key, transactions_local_path)
        transactions_df = pd.read_csv(transactions_local_path)
        print(f"Loaded {len(transactions_df)} transactions from MinIO")
        
        # Try to load alert preferences
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
    
    # Helper function to load from local files
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
    # Database is preferred as it has live application data
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
    
    # Save data to output directory
    users_local_path = os.path.join(output_data.path, 'users.csv')
    transactions_local_path = os.path.join(output_data.path, 'transactions.csv')
    
    users_df.to_csv(users_local_path, index=False)
    transactions_df.to_csv(transactions_local_path, index=False)
    
    # Save metadata
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


@dsl.component(base_image=BASE_IMAGE)
def train_model(input_data: Input[Dataset], output_model: Output[Model]):
    """
    Train the KNN-based collaborative filtering model.
    
    This task:
    1. Performs feature engineering on user and transaction data
    2. Generates alert labels (using real data or heuristics)
    3. Trains a KNN model for alert recommendations
    4. Saves the trained model and metadata
    """
    import os
    import json
    import pickle
    from datetime import datetime
    import pandas as pd
    import numpy as np
    from sklearn.neighbors import NearestNeighbors
    from sklearn.preprocessing import StandardScaler
    
    # Get configuration
    n_neighbors = int(os.getenv('N_NEIGHBORS', '5'))
    metric = os.getenv('METRIC', 'cosine')
    model_version = os.getenv('MODEL_VERSION', '1.0.0')
    data_version = os.getenv('DATA_VERSION', '1')
    
    print(f"Training configuration:")
    print(f"  N Neighbors: {n_neighbors}")
    print(f"  Metric: {metric}")
    print(f"  Model Version: {model_version}")
    
    # Load data
    users_df = pd.read_csv(os.path.join(input_data.path, 'users.csv'))
    transactions_df = pd.read_csv(os.path.join(input_data.path, 'transactions.csv'))
    
    with open(os.path.join(input_data.path, 'metadata.json'), 'r') as f:
        data_metadata = json.load(f)
    
    use_real_alerts = data_metadata.get('use_real_alerts', False)
    
    # Load alert preferences if available
    alerts_path = os.path.join(input_data.path, 'user_alerts.csv')
    user_alerts_df = None
    if os.path.exists(alerts_path):
        user_alerts_df = pd.read_csv(alerts_path)
    
    # Alert types
    ALERT_TYPES = [
        'alert_high_spender',
        'alert_high_tx_volume',
        'alert_high_merchant_diversity',
        'alert_near_credit_limit',
        'alert_large_transaction',
        'alert_new_merchant',
        'alert_location_based',
        'alert_subscription_monitoring'
    ]
    
    # Feature columns
    FEATURE_COLUMNS = [
        'amount_mean', 'amount_std', 'amount_max', 'amount_sum', 'amount_count',
        'merchant_name_nunique', 'merchant_category_nunique',
        'credit_limit', 'credit_balance', 'credit_utilization'
    ]
    
    # Feature engineering
    def build_user_features(users_df, transactions_df):
        """Build behavioral features from transaction history."""
        transactions_df['amount'] = pd.to_numeric(transactions_df['amount'], errors='coerce')
        
        tx_agg = transactions_df.groupby('user_id').agg({
            'amount': ['count', 'mean', 'std', 'max', 'sum'],
            'merchant_name': pd.Series.nunique,
            'merchant_category': pd.Series.nunique
        })
        
        tx_agg.columns = ['_'.join(col) if isinstance(col, tuple) else col for col in tx_agg.columns]
        tx_agg = tx_agg.reset_index()
        tx_agg.columns = ['user_id', 'amount_count', 'amount_mean', 'amount_std',
                          'amount_max', 'amount_sum', 'merchant_name_nunique',
                          'merchant_category_nunique']
        
        user_feats = tx_agg.merge(
            users_df[['id', 'credit_limit', 'credit_balance']],
            left_on='user_id',
            right_on='id',
            how='left'
        )
        
        if 'id' in user_feats.columns:
            user_feats = user_feats.drop(columns=['id'])
        
        user_feats['credit_limit'] = pd.to_numeric(user_feats['credit_limit'], errors='coerce').fillna(0)
        user_feats['credit_balance'] = pd.to_numeric(user_feats['credit_balance'], errors='coerce').fillna(0)
        user_feats['credit_utilization'] = np.where(
            user_feats['credit_limit'] > 0,
            user_feats['credit_balance'] / user_feats['credit_limit'],
            0
        )
        
        user_feats = user_feats.fillna(0)
        return user_feats
    
    def generate_heuristic_labels(df):
        """Generate alert labels based on behavioral heuristics."""
        df = df.copy()
        
        df['alert_high_spender'] = (df['amount_sum'] >= df['amount_sum'].quantile(0.75)).astype(int)
        df['alert_high_tx_volume'] = (df['amount_count'] >= df['amount_count'].quantile(0.75)).astype(int)
        df['alert_high_merchant_diversity'] = (df['merchant_name_nunique'] >= df['merchant_name_nunique'].quantile(0.75)).astype(int)
        df['alert_near_credit_limit'] = (df['credit_utilization'] >= 0.7).astype(int)
        df['alert_large_transaction'] = (df['amount_max'] >= df['amount_max'].quantile(0.75)).astype(int)
        df['alert_new_merchant'] = 0
        df['alert_location_based'] = 0
        df['alert_subscription_monitoring'] = 0
        
        return df
    
    # Build features
    user_features = build_user_features(users_df, transactions_df)
    print(f"Built features for {len(user_features)} users")
    
    # Generate labels
    if use_real_alerts and user_alerts_df is not None:
        pivot = user_alerts_df.pivot_table(
            index='user_id',
            columns='alert_type',
            values='enabled',
            fill_value=0,
            aggfunc='max'
        )
        pivot.columns = [f'alert_{col}' if not col.startswith('alert_') else col for col in pivot.columns]
        pivot = pivot.reset_index()
        
        user_features_with_labels = user_features.merge(pivot, on='user_id', how='left')
        for alert_type in ALERT_TYPES:
            if alert_type in user_features_with_labels.columns:
                user_features_with_labels[alert_type] = user_features_with_labels[alert_type].fillna(0).astype(int)
            else:
                user_features_with_labels[alert_type] = 0
        print("Using real alert labels from data")
    else:
        user_features_with_labels = generate_heuristic_labels(user_features)
        print("Generated heuristic-based alert labels")
    
    # Prepare training data
    X = user_features_with_labels[FEATURE_COLUMNS].values
    y = user_features_with_labels[ALERT_TYPES].values
    user_ids = user_features_with_labels['user_id'].values
    
    print(f"Training data shape: X={X.shape}, y={y.shape}")
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    print("Features normalized")
    
    # Train KNN model
    knn_model = NearestNeighbors(
        n_neighbors=min(n_neighbors, len(X_scaled)),
        metric=metric,
        algorithm='brute'
    )
    knn_model.fit(X_scaled)
    print(f"KNN model trained with {knn_model.n_neighbors} neighbors")
    
    # Save model artifacts
    os.makedirs(output_model.path, exist_ok=True)
    
    model_artifacts = {
        'knn_model': knn_model,
        'scaler': scaler,
        'feature_columns': FEATURE_COLUMNS,
        'alert_types': ALERT_TYPES,
        'user_ids': user_ids,
        'alert_labels': y,
        'training_features': X_scaled
    }
    
    model_path = os.path.join(output_model.path, 'model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_artifacts, f)
    
    print(f"Model saved to {model_path}")
    
    # Save metadata
    metadata = {
        'model_version': model_version,
        'data_version': data_version,
        'trained_at': datetime.now().isoformat(),
        'n_users': len(user_ids),
        'n_neighbors': n_neighbors,
        'metric': metric,
        'feature_columns': FEATURE_COLUMNS,
        'alert_types': ALERT_TYPES,
        'use_real_alerts': use_real_alerts,
        'model_size_bytes': os.path.getsize(model_path)
    }
    
    with open(os.path.join(output_model.path, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Model metadata saved")
    print(f"Training complete!")


@dsl.component(base_image=BASE_IMAGE)
def save_model(input_model: Input[Model], output_artifact: Output[Artifact]):
    """
    Save the trained model to MinIO and prepare for deployment.
    
    This task:
    1. Creates a KNNRecommender wrapper class
    2. Wraps the model in an sklearn Pipeline
    3. Uploads artifacts to MinIO
    4. Creates model-settings.json for MLServer
    """
    import os
    import json
    import pickle
    import joblib
    from datetime import datetime
    import numpy as np
    import boto3
    from botocore.client import Config
    
    # Get configuration
    namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
    bucket_name = os.getenv('BUCKET_NAME', 'models')
    minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
    threshold = float(os.getenv('THRESHOLD', '0.4'))
    
    # Generate model version with timestamp
    model_version = datetime.now().strftime("%y-%m-%d-%H%M%S")
    model_name = os.getenv('MODEL_NAME', 'alert-recommender')
    
    print(f"Model: {model_name}")
    print(f"Version: {model_version}")
    
    # Initialize MinIO client
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    
    # Create bucket if it doesn't exist
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Created bucket: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e) or 'BucketAlreadyExists' in str(e):
            print(f"Bucket already exists: {bucket_name}")
        else:
            print(f"Note: {e}")
    
    # Load model artifacts
    model_path = os.path.join(input_model.path, 'model.pkl')
    with open(model_path, 'rb') as f:
        model_artifacts = pickle.load(f)
    
    print(f"Model artifacts loaded: {list(model_artifacts.keys())}")
    
    # Create output directory
    os.makedirs(output_artifact.path, exist_ok=True)
    
    # Save model components separately using joblib (Python version independent)
    # This avoids cloudpickle's code serialization which causes Python version incompatibility
    import joblib
    
    model_components = {
        'scaler': model_artifacts['scaler'],
        'knn_model': model_artifacts['knn_model'],
        'alert_labels': model_artifacts['alert_labels'],
        'alert_types': model_artifacts['alert_types'],
        'threshold': threshold
    }
    
    pipeline_path = os.path.join(output_artifact.path, 'model.joblib')
    joblib.dump(model_components, pipeline_path, protocol=4)  # protocol 4 is compatible with Python 3.4+
    
    print(f"Model components saved: {os.path.getsize(pipeline_path) / 1024:.2f} KB")
    
    # Create custom MLServer model implementation
    # This handles loading our model components and providing predictions
    model_impl_code = '''"""Custom MLServer model for Alert Recommender."""
import joblib
import numpy as np
from mlserver import MLModel
from mlserver.codecs import NumpyCodec
from mlserver.types import InferenceRequest, InferenceResponse, ResponseOutput

class AlertRecommenderModel(MLModel):
    """Custom MLServer model that loads our model components."""
    
    async def load(self) -> bool:
        """Load the model components from the joblib file."""
        model_uri = self.settings.parameters.uri
        self._components = joblib.load(model_uri)
        
        self._scaler = self._components['scaler']
        self._knn_model = self._components['knn_model']
        self._alert_labels = self._components['alert_labels']
        self._alert_types = self._components['alert_types']
        self._threshold = self._components['threshold']
        
        self.ready = True
        return self.ready
    
    async def predict(self, payload: InferenceRequest) -> InferenceResponse:
        """Make predictions using the loaded model."""
        # Decode input
        input_data = None
        for inp in payload.inputs:
            input_data = NumpyCodec.decode_input(inp)
            break
        
        if input_data is None:
            raise ValueError("No input data provided")
        
        # Scale the input
        X_scaled = self._scaler.transform(input_data)
        
        # Get nearest neighbors
        k_neighbors = min(5, len(self._alert_labels))
        distances, indices = self._knn_model.kneighbors(X_scaled, n_neighbors=k_neighbors)
        
        # Generate recommendations
        all_recommendations = []
        for idx_list in indices:
            similar_labels = self._alert_labels[idx_list]
            probabilities = similar_labels.mean(axis=0)
            
            recommendations = []
            for i, alert_type in enumerate(self._alert_types):
                if probabilities[i] >= self._threshold:
                    recommendations.append({
                        "alert_type": alert_type,
                        "probability": float(probabilities[i]),
                        "confidence": "high" if probabilities[i] >= 0.7 else "medium"
                    })
            
            all_recommendations.append(recommendations)
        
        # Encode output
        output_data = np.array(all_recommendations, dtype=object)
        
        return InferenceResponse(
            model_name=self.name,
            outputs=[
                ResponseOutput(
                    name="predictions",
                    shape=list(output_data.shape),
                    datatype="BYTES",
                    data=[str(r) for r in all_recommendations]
                )
            ]
        )
'''
    
    impl_path = os.path.join(output_artifact.path, 'model.py')
    with open(impl_path, 'w') as f:
        f.write(model_impl_code)
    
    # Upload to MinIO
    s3_model_path = f'{model_name}/'
    
    # Upload model components
    model_key = f'{s3_model_path}model.joblib'
    print(f"Uploading model to s3://{bucket_name}/{model_key}")
    s3_client.upload_file(pipeline_path, bucket_name, model_key)
    
    # Upload custom implementation
    impl_key = f'{s3_model_path}model.py'
    print(f"Uploading implementation to s3://{bucket_name}/{impl_key}")
    s3_client.upload_file(impl_path, bucket_name, impl_key)
    
    # Create and upload model-settings.json
    # Use our custom implementation instead of sklearn
    model_settings = {
        "name": model_name,
        "implementation": "model.AlertRecommenderModel",
        "parameters": {
            "uri": "/mnt/models/model.joblib"
        }
    }
    
    settings_key = f'{s3_model_path}model-settings.json'
    s3_client.put_object(
        Bucket=bucket_name,
        Key=settings_key,
        Body=json.dumps(model_settings, indent=2)
    )
    print(f"Uploaded model-settings.json")
    
    # Save deployment variables
    vars_data = {
        'model_version': model_version,
        'model_name': model_name,
        's3_bucket': bucket_name,
        's3_model_path': s3_model_path,
        'minio_endpoint': minio_endpoint
    }
    
    with open(os.path.join(output_artifact.path, 'vars.json'), 'w') as f:
        json.dump(vars_data, f, indent=2)
    
    print(f"Model save complete!")
    print(f"Model uploaded to: s3://{bucket_name}/{s3_model_path}")
    
    # Note: Model registration is handled by the dedicated register_model task
    # which runs as a separate pipeline step when MODEL_REGISTRY_ENABLED=true


@dsl.component(base_image=BASE_IMAGE)
def register_model(input_artifact: Input[Artifact]):
    """
    Register the model with the Model Registry.
    
    This task:
    1. Connects to the Model Registry
    2. Registers the model with metadata
    3. Creates a new model version
    """
    import os
    import json
    import requests
    
    # Get configuration
    model_registry_url = os.getenv('MODEL_REGISTRY_URL', '')
    model_registry_enabled = os.getenv('MODEL_REGISTRY_ENABLED', 'false').lower() == 'true'
    
    if not model_registry_enabled or not model_registry_url:
        print("Model registry not enabled or URL not configured. Skipping registration.")
        return
    
    # Load deployment variables
    vars_path = os.path.join(input_artifact.path, 'vars.json')
    with open(vars_path, 'r') as f:
        vars_data = json.load(f)
    
    model_name = vars_data['model_name']
    model_version = vars_data['model_version']
    s3_bucket = vars_data['s3_bucket']
    s3_model_path = vars_data['s3_model_path']
    
    print(f"Registering model with Model Registry:")
    print(f"  URL: {model_registry_url}")
    print(f"  Model: {model_name}")
    print(f"  Version: {model_version}")
    
    # Create or get registered model
    try:
        # Check if model exists using the singular search endpoint
        # API: GET /api/model_registry/v1alpha3/registered_model?name=<name>
        # Returns: 200 with single object if found, 404 if not found
        print(f"Searching for existing registered model: {model_name}")
        response = requests.get(
            f"{model_registry_url}/api/model_registry/v1alpha3/registered_model",
            params={"name": model_name}
        )
        
        registered_model_id = None
        if response.status_code == 200:
            # Found existing model - response is a single object, not a list
            registered_model = response.json()
            registered_model_id = registered_model.get('id')
            model_state = registered_model.get('state', 'UNKNOWN')
            if registered_model_id:
                print(f"Found existing model: {registered_model_id} (state: {model_state})")
                
                # If model is ARCHIVED, update it to LIVE so it shows in the UI
                if model_state == 'ARCHIVED':
                    print(f"Model is ARCHIVED, updating to LIVE state...")
                    patch_response = requests.patch(
                        f"{model_registry_url}/api/model_registry/v1alpha3/registered_models/{registered_model_id}",
                        json={"state": "LIVE"},
                        headers={"Content-Type": "application/json"}
                    )
                    if patch_response.ok:
                        print(f"Successfully updated model state to LIVE")
                    else:
                        print(f"Warning: Failed to update model state: {patch_response.status_code}")
                        print(f"Response: {patch_response.text}")
            else:
                print(f"Warning: Model found but 'id' field is missing. Response: {registered_model}")
        elif response.status_code == 404:
            # Model not found, will create new
            print(f"Model '{model_name}' not found, will create new")
        else:
            print(f"Unexpected response when searching for model: {response.status_code}")
            print(f"Response body: {response.text}")
        
        # Create new model if not found
        if not registered_model_id:
            print(f"Creating new registered model: {model_name}")
            create_payload = {
                "name": model_name,
                "state": "LIVE",  # Explicitly set to LIVE so it shows in UI
                "description": "KNN-based collaborative filtering model for alert recommendations",
                "customProperties": {
                    "framework": {"metadataType": "MetadataStringValue", "string_value": "sklearn"},
                    "algorithm": {"metadataType": "MetadataStringValue", "string_value": "KNN"},
                    "task": {"metadataType": "MetadataStringValue", "string_value": "recommendation"}
                }
            }
            print(f"Create payload: {json.dumps(create_payload, indent=2)}")
            
            create_response = requests.post(
                f"{model_registry_url}/api/model_registry/v1alpha3/registered_models",
                json=create_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not create_response.ok:
                print(f"Failed to create registered model: {create_response.status_code}")
                print(f"Response body: {create_response.text}")
                create_response.raise_for_status()
            
            registered_model_id = create_response.json().get('id')
            if not registered_model_id:
                print(f"Error: Created model but 'id' field is missing. Response: {create_response.json()}")
                return
            print(f"Created new model: {registered_model_id}")
        
        # Get MinIO endpoint for storage info
        namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
        minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
        
        # Check if model version already exists
        # API: GET /api/model_registry/v1alpha3/registered_models/{id}/versions
        print(f"Checking for existing version: {model_version}")
        versions_response = requests.get(
            f"{model_registry_url}/api/model_registry/v1alpha3/registered_models/{registered_model_id}/versions"
        )
        
        version_id = None
        if versions_response.ok:
            existing_versions = versions_response.json().get('items', [])
            for v in existing_versions:
                if v.get('name') == model_version:
                    version_id = v['id']
                    print(f"Found existing version '{model_version}': {version_id}")
                    break
        
        if version_id is None:
            # Create model version under the registered model
            # API: POST /api/model_registry/v1alpha3/registered_models/{id}/versions
            # Note: registeredModelId is required even when POSTing to the nested endpoint
            version_payload = {
                "name": model_version,
                "registeredModelId": registered_model_id,
                "customProperties": {
                    "storage_uri": {"metadataType": "MetadataStringValue", "string_value": f"s3://{s3_bucket}/{s3_model_path}"},
                    "model_format": {"metadataType": "MetadataStringValue", "string_value": "joblib"},
                    "minio_endpoint": {"metadataType": "MetadataStringValue", "string_value": minio_endpoint}
                }
            }
            print(f"Creating model version with payload: {json.dumps(version_payload, indent=2)}")
            
            version_response = requests.post(
                f"{model_registry_url}/api/model_registry/v1alpha3/registered_models/{registered_model_id}/versions",
                json=version_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not version_response.ok:
                print(f"Version creation failed: {version_response.status_code}")
                print(f"Response body: {version_response.text}")
                version_response.raise_for_status()
            
            version_id = version_response.json().get('id')
            if not version_id:
                print(f"Error: Created version but 'id' field is missing. Response: {version_response.json()}")
                return
            print(f"Created model version: {version_id}")
        
        # Check if artifact already exists for this version
        # API: GET /api/model_registry/v1alpha3/model_versions/{id}/artifacts
        artifact_name = f"{model_name}-{model_version}"
        print(f"Checking for existing artifact: {artifact_name}")
        
        artifacts_response = requests.get(
            f"{model_registry_url}/api/model_registry/v1alpha3/model_versions/{version_id}/artifacts"
        )
        
        artifact_id = None
        if artifacts_response.ok:
            existing_artifacts = artifacts_response.json().get('items', [])
            for a in existing_artifacts:
                if a.get('name') == artifact_name:
                    artifact_id = a['id']
                    print(f"Found existing artifact '{artifact_name}': {artifact_id}")
                    break
        
        if artifact_id is None:
            # Create model artifact under the model version
            # API: POST /api/model_registry/v1alpha3/model_versions/{id}/artifacts
            artifact_payload = {
                "name": artifact_name,
                "uri": f"s3://{s3_bucket}/{s3_model_path}model.joblib",
                "modelFormatName": "sklearn",
                "modelFormatVersion": "1.0",
                "artifactType": "model-artifact"
            }
            print(f"Creating model artifact with payload: {json.dumps(artifact_payload, indent=2)}")
            
            artifact_response = requests.post(
                f"{model_registry_url}/api/model_registry/v1alpha3/model_versions/{version_id}/artifacts",
                json=artifact_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if not artifact_response.ok:
                print(f"Artifact creation failed: {artifact_response.status_code}")
                print(f"Response body: {artifact_response.text}")
                artifact_response.raise_for_status()
            
            artifact_id = artifact_response.json().get('id')
            if not artifact_id:
                print(f"Warning: Created artifact but 'id' field is missing. Response: {artifact_response.json()}")
            else:
                print(f"Created model artifact: {artifact_id}")
        
        print("Model registration complete!")
        
    except Exception as e:
        print(f"Error registering model: {e}")
        # Don't fail the pipeline if registration fails
        print("Continuing without model registration...")


@dsl.component(base_image=BASE_IMAGE)
def deploy_model(input_artifact: Input[Artifact]):
    """
    Deploy the model as an InferenceService on OpenShift AI.
    
    This task can deploy from two sources:
    1. Pipeline artifact (default) - uses vars.json from save_model task
    2. Model Registry - fetches model info from the registry
    
    Set DEPLOY_FROM_REGISTRY=true to deploy the latest version from Model Registry.
    
    This task:
    1. Creates storage-config secret for MinIO access
    2. Deploys ServingRuntime for MLServer sklearn
    3. Deploys InferenceService pointing to the model in MinIO
    4. Waits for the service to be ready
    """
    import os
    import json
    import time
    import base64
    import requests
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    
    # Check if we should deploy from Model Registry
    deploy_from_registry = os.getenv('DEPLOY_FROM_REGISTRY', 'false').lower() == 'true'
    model_registry_url = os.getenv('MODEL_REGISTRY_URL', '')
    model_name_override = os.getenv('MODEL_NAME', 'alert-recommender')
    model_version_override = os.getenv('MODEL_VERSION_TO_DEPLOY', '')  # Empty means latest
    
    if deploy_from_registry and model_registry_url:
        print(f"Deploying from Model Registry:")
        print(f"  Registry URL: {model_registry_url}")
        print(f"  Model Name: {model_name_override}")
        print(f"  Version: {model_version_override or 'latest'}")
        
        # Fetch model info from Model Registry
        try:
            # Get registered model using the singular search endpoint
            # API: GET /api/model_registry/v1alpha3/registered_model?name=<name>
            # Returns: 200 with single object if found, 404 if not found
            print(f"Searching for registered model: {model_name_override}")
            response = requests.get(
                f"{model_registry_url}/api/model_registry/v1alpha3/registered_model",
                params={"name": model_name_override}
            )
            
            if response.status_code == 404:
                raise RuntimeError(f"Model '{model_name_override}' not found in registry")
            
            response.raise_for_status()
            
            # Response is a single object, not a list
            registered_model = response.json()
            registered_model_id = registered_model.get('id')
            
            if not registered_model_id:
                raise RuntimeError(f"Model found but 'id' field is missing. Response: {registered_model}")
            
            print(f"Found registered model: {registered_model_id}")
            
            # Get model versions under the registered model
            # API: GET /api/model_registry/v1alpha3/registered_models/{id}/versions
            versions_response = requests.get(
                f"{model_registry_url}/api/model_registry/v1alpha3/registered_models/{registered_model_id}/versions"
            )
            
            if not versions_response.ok:
                print(f"Failed to get versions: {versions_response.status_code}")
                print(f"Response: {versions_response.text}")
                versions_response.raise_for_status()
            
            versions = versions_response.json().get('items', [])
            print(f"Found {len(versions)} versions")
            
            if not versions:
                raise RuntimeError(f"No versions found for model '{model_name_override}'")
            
            # Find the requested version or use latest
            target_version = None
            if model_version_override:
                for v in versions:
                    if v['name'] == model_version_override:
                        target_version = v
                        break
                if not target_version:
                    raise RuntimeError(f"Version '{model_version_override}' not found")
            else:
                # Get latest version (sorted by createTimeSinceEpoch descending)
                target_version = sorted(
                    versions, 
                    key=lambda x: x.get('createTimeSinceEpoch', '0'), 
                    reverse=True
                )[0]
            
            model_version = target_version['name']
            version_id = target_version['id']
            print(f"Using version: {model_version} (id: {version_id})")
            
            # Extract storage info from version customProperties
            custom_props = target_version.get('customProperties', {})
            storage_uri = custom_props.get('storage_uri', {}).get('string_value', '')
            minio_endpoint = custom_props.get('minio_endpoint', {}).get('string_value', '')
            
            if not storage_uri:
                # Try to get from model artifact
                # API: GET /api/model_registry/v1alpha3/model_versions/{id}/artifacts
                artifacts_response = requests.get(
                    f"{model_registry_url}/api/model_registry/v1alpha3/model_versions/{version_id}/artifacts"
                )
                
                if artifacts_response.ok:
                    artifacts = artifacts_response.json().get('items', [])
                    print(f"Found {len(artifacts)} artifacts")
                    if artifacts:
                        storage_uri = artifacts[0].get('uri', '')
                else:
                    print(f"Failed to get artifacts: {artifacts_response.status_code}")
                    print(f"Response: {artifacts_response.text}")
            
            if not storage_uri:
                raise RuntimeError("Could not find storage URI in model registry")
            
            print(f"Storage URI from registry: {storage_uri}")
            
            # Parse storage URI (format: s3://bucket/path/)
            if storage_uri.startswith('s3://'):
                uri_parts = storage_uri[5:].split('/', 1)
                bucket = uri_parts[0]
                model_path = uri_parts[1] if len(uri_parts) > 1 else ''
            else:
                raise RuntimeError(f"Unsupported storage URI format: {storage_uri}")
            
            model_name = model_name_override
            
            # Use MinIO endpoint from registry or environment
            if not minio_endpoint:
                namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
                minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
            
            print(f"Resolved deployment info from registry:")
            print(f"  Model: {model_name}")
            print(f"  Version: {model_version}")
            print(f"  Bucket: {bucket}")
            print(f"  Path: {model_path}")
            print(f"  MinIO Endpoint: {minio_endpoint}")
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch from Model Registry: {e}")
    else:
        # Load deployment variables from pipeline artifact (original behavior)
        vars_path = os.path.join(input_artifact.path, 'vars.json')
        with open(vars_path, 'r') as f:
            vars_data = json.load(f)
        
        model_name = vars_data['model_name']
        model_version = vars_data['model_version']
        bucket = vars_data['s3_bucket']
        model_path = vars_data['s3_model_path']
        minio_endpoint = vars_data['minio_endpoint']
    
    # Get configuration
    namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
    deploy_enabled = os.getenv('DEPLOY_MODEL', 'true').lower() == 'true'
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
    serving_runtime = os.getenv('SERVING_RUNTIME', 'alert-recommender-runtime')
    create_serving_runtime = os.getenv('CREATE_SERVING_RUNTIME', 'false').lower() == 'true'
    
    if not deploy_enabled:
        print("Model deployment not enabled. Skipping.")
        return
    
    print(f"Deployment configuration:")
    print(f"  Model: {model_name}")
    print(f"  Version: {model_version}")
    print(f"  Namespace: {namespace}")
    print(f"  Bucket: {bucket}")
    print(f"  Model Path: {model_path}")
    print(f"  Serving Runtime: {serving_runtime}")
    print(f"  Create Serving Runtime: {create_serving_runtime}")
    
    # Initialize Kubernetes client
    try:
        config.load_incluster_config()
        print("Loaded in-cluster Kubernetes config")
    except:
        config.load_kube_config()
        print("Loaded kubeconfig from local")
    
    core_v1 = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    
    # Step 1: Create storage-config secret
    print("\nCreating storage-config secret...")
    
    # Parse MinIO endpoint for host and port
    minio_host = minio_endpoint.replace('http://', '').replace('https://', '')
    
    # KServe expects storage credentials in a specific JSON format
    # The key name should match the bucket name for bucket-specific credentials
    # or use a generic key for default credentials
    # NOTE: All values must be strings - KServe cannot parse booleans
    storage_config_json = json.dumps({
        "type": "s3",
        "access_key_id": minio_access_key,
        "secret_access_key": minio_secret_key,
        "endpoint_url": minio_endpoint,
        "region": "us-east-1",
        "verify_ssl": "false"
    })
    
    storage_secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name="storage-config",
            namespace=namespace,
            annotations={
                "serving.kserve.io/s3-endpoint": minio_host,
                "serving.kserve.io/s3-usehttps": "0",
                "serving.kserve.io/s3-verifyssl": "0",
                "serving.kserve.io/s3-region": "us-east-1"
            }
        ),
        type="Opaque",
        string_data={
            # KServe storage initializer looks for credentials under the bucket name key
            bucket: storage_config_json,
            # Also provide as environment variables for compatibility
            "AWS_ACCESS_KEY_ID": minio_access_key,
            "AWS_SECRET_ACCESS_KEY": minio_secret_key,
            "AWS_DEFAULT_REGION": "us-east-1",
            "S3_ENDPOINT": minio_endpoint,
            "S3_USE_HTTPS": "0",
            "S3_VERIFY_SSL": "0"
        }
    )
    
    try:
        core_v1.create_namespaced_secret(namespace, storage_secret)
        print("Storage config secret created")
    except ApiException as e:
        if e.status == 409:
            core_v1.replace_namespaced_secret("storage-config", namespace, storage_secret)
            print("Storage config secret updated")
        else:
            raise
    
    # Step 1b: Create service account with storage-config secret
    # KServe requires a service account that references the storage secret
    sa_name = f"{model_name}-sa"
    print(f"\nCreating service account: {sa_name}...")
    
    service_account = client.V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=client.V1ObjectMeta(
            name=sa_name,
            namespace=namespace
        ),
        secrets=[client.V1ObjectReference(name="storage-config")]
    )
    
    try:
        core_v1.create_namespaced_service_account(namespace, service_account)
        print(f"Service account {sa_name} created")
    except ApiException as e:
        if e.status == 409:
            # Update existing service account
            core_v1.patch_namespaced_service_account(
                name=sa_name,
                namespace=namespace,
                body=service_account
            )
            print(f"Service account {sa_name} updated")
        else:
            raise
    
    # Step 2: Deploy ServingRuntime (optional - skip if using existing)
    if create_serving_runtime:
        print(f"\nCreating ServingRuntime: {serving_runtime}...")
        
        runtime_image = os.getenv(
            'SERVING_RUNTIME_IMAGE',
            'docker.io/seldonio/mlserver:1.7.0-sklearn'
        )
        print(f"  Using image: {runtime_image}")
        
        # Install cloudpickle via pip at container startup
        install_cmd = (
            'echo "Installing cloudpickle and dependencies to user site-packages..." && '
            'export PYTHONUSERBASE=/tmp/python-packages && '
            'mkdir -p $PYTHONUSERBASE && '
            'pip install --user --no-cache-dir cloudpickle>=3.0.0 "numpy<2.0" "scikit-learn>=1.6.0,<1.7.0" && '
            'export PYTHONPATH=$PYTHONUSERBASE/lib/python3.10/site-packages:$PYTHONPATH && '
            'echo "Verifying cloudpickle installation..." && '
            'python -c "import cloudpickle; print(f\'cloudpickle version: {cloudpickle.__version__}\')" && '
            'echo "Starting MLServer..." && '
            'exec mlserver start /mnt/models'
        )
        
        serving_runtime_spec = {
            "apiVersion": "serving.kserve.io/v1alpha1",
            "kind": "ServingRuntime",
            "metadata": {
                "name": serving_runtime,
                "namespace": namespace,
                "annotations": {
                    "openshift.io/display-name": "MLServer SKLearn Runtime (with cloudpickle)"
                }
            },
            "spec": {
                "supportedModelFormats": [
                    {
                        "name": "sklearn",
                        "version": "1",
                        "autoSelect": True
                    }
                ],
                "protocolVersions": ["v2", "grpc-v2"],
                "multiModel": False,
                "grpcDataEndpoint": "port:8001",
                "grpcEndpoint": "port:8085",
                "containers": [
                    {
                        "name": "kserve-container",
                        "image": runtime_image,
                        "imagePullPolicy": "Always",
                        "command": ["/bin/bash", "-c", install_cmd],
                        "env": [
                            {"name": "MLSERVER_MODEL_IMPLEMENTATION", "value": "mlserver_sklearn.SKLearnModel"},
                            {"name": "MLSERVER_HTTP_PORT", "value": "8080"},
                            {"name": "MLSERVER_GRPC_PORT", "value": "8081"},
                            {"name": "MLSERVER_MODEL_URI", "value": "/mnt/models"},
                            {"name": "MLSERVER_LOAD_MODELS_AT_STARTUP", "value": "true"},
                            {"name": "PYTHONUSERBASE", "value": "/tmp/python-packages"},
                            {"name": "PYTHONPATH", "value": "/tmp/python-packages/lib/python3.10/site-packages"}
                        ],
                        "ports": [
                            {"containerPort": 8080, "name": "http", "protocol": "TCP"},
                            {"containerPort": 8081, "name": "grpc", "protocol": "TCP"}
                        ],
                        "resources": {
                            "requests": {"cpu": "500m", "memory": "512Mi"},
                            "limits": {"cpu": "1", "memory": "1Gi"}
                        }
                    }
                ]
            }
        }
        
        try:
            custom_api.create_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1alpha1",
                namespace=namespace,
                plural="servingruntimes",
                body=serving_runtime_spec
            )
            print("ServingRuntime created")
        except ApiException as e:
            if e.status == 409:
                # Update existing ServingRuntime to ensure correct image is used
                print(f"ServingRuntime {serving_runtime} already exists, updating...")
                custom_api.patch_namespaced_custom_object(
                    group="serving.kserve.io",
                    version="v1alpha1",
                    namespace=namespace,
                    plural="servingruntimes",
                    name=serving_runtime,
                    body=serving_runtime_spec
                )
                print(f"ServingRuntime {serving_runtime} updated with image: {runtime_image}")
            else:
                raise
    else:
        print(f"\nUsing existing ServingRuntime: {serving_runtime}")
    
    # Step 3: Deploy InferenceService
    print("\nDeploying InferenceService...")
    
    # Parse MinIO host for annotations
    minio_host = minio_endpoint.replace('http://', '').replace('https://', '')
    
    inference_service = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": model_name,
            "namespace": namespace,
            "annotations": {
                "serving.kserve.io/deploymentMode": "RawDeployment",
                "serving.kserve.io/storageSecretName": "storage-config",
                "model-version": model_version
            }
        },
        "spec": {
            "predictor": {
                "minReplicas": 1,
                "maxReplicas": 3,
                "model": {
                    "modelFormat": {
                        "name": "sklearn"
                    },
                    "runtime": serving_runtime,
                    "storageUri": f"s3://{bucket}/{model_path}",
                    "storage": {
                        "key": bucket,
                        "parameters": {
                            "endpoint": minio_endpoint,
                            "region": "us-east-1"
                        }
                    }
                },
                "serviceAccountName": f"{model_name}-sa"
            }
        }
    }
    
    try:
        custom_api.create_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=namespace,
            plural="inferenceservices",
            body=inference_service
        )
        print("InferenceService created")
    except ApiException as e:
        if e.status == 409:
            custom_api.patch_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=namespace,
                plural="inferenceservices",
                name=model_name,
                body=inference_service
            )
            print("InferenceService updated")
        else:
            raise
    
    # Step 4: Wait for InferenceService to be ready
    print("\nWaiting for InferenceService to be ready...")
    
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            isvc = custom_api.get_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=namespace,
                plural="inferenceservices",
                name=model_name
            )
            
            status = isvc.get('status', {})
            conditions = status.get('conditions', [])
            
            for condition in conditions:
                if condition['type'] == 'Ready':
                    if condition['status'] == 'True':
                        url = status.get('url', 'N/A')
                        print(f"\nInferenceService is ready!")
                        print(f"Inference endpoint: {url}")
                        return
                    else:
                        reason = condition.get('reason', 'Unknown')
                        print(f"Status: {reason}", end='\r')
            
            elapsed = int(time.time() - start_time)
            print(f"Waiting for InferenceService... ({elapsed}s)", end='\r')
            time.sleep(10)
            
        except ApiException:
            elapsed = int(time.time() - start_time)
            print(f"Waiting for InferenceService... ({elapsed}s)", end='\r')
            time.sleep(10)
    
    print("\nTimeout waiting for InferenceService to be ready")
    print(f"Check status: kubectl get isvc {model_name} -n {namespace}")


@dsl.component(base_image=BASE_IMAGE)
def cleanup_deployment():
    """
    Clean up ML pipeline resources from OpenShift.
    
    This task removes:
    - InferenceService
    - ServingRuntime
    - MinIO resources (optional)
    - Secrets
    - RBAC resources
    """
    import os
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    
    # Get configuration
    namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
    model_name = os.getenv('MODEL_NAME', 'alert-recommender')
    cleanup_minio = os.getenv('CLEANUP_MINIO', 'false').lower() == 'true'
    serving_runtime = os.getenv('SERVING_RUNTIME', 'alert-recommender-runtime')
    # Only delete the ServingRuntime if we created it (not a shared one)
    cleanup_serving_runtime = os.getenv('CLEANUP_SERVING_RUNTIME', 'false').lower() == 'true'
    
    print(f"Cleanup configuration:")
    print(f"  Namespace: {namespace}")
    print(f"  Model: {model_name}")
    print(f"  Cleanup MinIO: {cleanup_minio}")
    print(f"  Serving Runtime: {serving_runtime}")
    print(f"  Cleanup Serving Runtime: {cleanup_serving_runtime}")
    
    # Initialize Kubernetes client
    try:
        config.load_incluster_config()
        print("Loaded in-cluster Kubernetes config")
    except:
        config.load_kube_config()
        print("Loaded kubeconfig from local")
    
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    custom_api = client.CustomObjectsApi()
    rbac_v1 = client.RbacAuthorizationV1Api()
    
    deleted = []
    
    # Delete InferenceService
    print("\nDeleting InferenceService...")
    try:
        custom_api.delete_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=namespace,
            plural="inferenceservices",
            name=model_name
        )
        deleted.append(f"InferenceService/{model_name}")
        print(f"  Deleted InferenceService: {model_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"  InferenceService not found: {model_name}")
        else:
            print(f"  Error deleting InferenceService: {e}")
    
    # Delete ServingRuntime (only if we created it, not if using shared)
    if cleanup_serving_runtime:
        print(f"\nDeleting ServingRuntime: {serving_runtime}...")
        try:
            custom_api.delete_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1alpha1",
                namespace=namespace,
                plural="servingruntimes",
                name=serving_runtime
            )
            deleted.append(f"ServingRuntime/{serving_runtime}")
            print(f"  Deleted ServingRuntime: {serving_runtime}")
        except ApiException as e:
            if e.status == 404:
                print(f"  ServingRuntime not found: {serving_runtime}")
            else:
                print(f"  Error deleting ServingRuntime: {e}")
    else:
        print(f"\nSkipping ServingRuntime deletion (shared): {serving_runtime}")
    
    # Delete secrets
    print("\nDeleting secrets...")
    for secret_name in ['storage-config', 'minio-secret']:
        try:
            core_v1.delete_namespaced_secret(secret_name, namespace)
            deleted.append(f"Secret/{secret_name}")
            print(f"  Deleted Secret: {secret_name}")
        except ApiException as e:
            if e.status == 404:
                print(f"  Secret not found: {secret_name}")
            else:
                print(f"  Error deleting Secret: {e}")
    
    # Optionally delete MinIO resources
    if cleanup_minio:
        print("\nDeleting MinIO resources...")
        
        # Delete MinIO deployment
        try:
            apps_v1.delete_namespaced_deployment("minio", namespace)
            deleted.append("Deployment/minio")
            print("  Deleted Deployment: minio")
        except ApiException as e:
            if e.status == 404:
                print("  Deployment not found: minio")
            else:
                print(f"  Error deleting Deployment: {e}")
        
        # Delete MinIO services
        for svc_name in ['minio-service', 'minio']:
            try:
                core_v1.delete_namespaced_service(svc_name, namespace)
                deleted.append(f"Service/{svc_name}")
                print(f"  Deleted Service: {svc_name}")
            except ApiException as e:
                if e.status == 404:
                    print(f"  Service not found: {svc_name}")
                else:
                    print(f"  Error deleting Service: {e}")
        
        # Delete MinIO PVC
        try:
            core_v1.delete_namespaced_persistent_volume_claim("minio-pvc", namespace)
            deleted.append("PVC/minio-pvc")
            print("  Deleted PVC: minio-pvc")
        except ApiException as e:
            if e.status == 404:
                print("  PVC not found: minio-pvc")
            else:
                print(f"  Error deleting PVC: {e}")
    
    # Delete RBAC resources
    print("\nDeleting RBAC resources...")
    try:
        rbac_v1.delete_namespaced_role("ml-deployment-manager", namespace)
        deleted.append("Role/ml-deployment-manager")
        print("  Deleted Role: ml-deployment-manager")
    except ApiException as e:
        if e.status == 404:
            print("  Role not found: ml-deployment-manager")
        else:
            print(f"  Error deleting Role: {e}")
    
    try:
        rbac_v1.delete_namespaced_role_binding("ml-deployment-manager-binding", namespace)
        deleted.append("RoleBinding/ml-deployment-manager-binding")
        print("  Deleted RoleBinding: ml-deployment-manager-binding")
    except ApiException as e:
        if e.status == 404:
            print("  RoleBinding not found: ml-deployment-manager-binding")
        else:
            print(f"  Error deleting RoleBinding: {e}")
    
    print(f"\n{'='*60}")
    print("Cleanup Summary")
    print(f"{'='*60}")
    print(f"Deleted {len(deleted)} resources:")
    for resource in deleted:
        print(f"  - {resource}")
    print("\nCleanup complete!")

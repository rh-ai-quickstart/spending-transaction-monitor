"""Model training task for Alert Recommender Pipeline."""

from kfp import dsl
from kfp.dsl import Input, Output, Dataset, Model

from .constants import BASE_IMAGE, ALERT_TYPES, FEATURE_COLUMNS


@dsl.component(base_image=BASE_IMAGE)
def train_model(input_data: Input[Dataset], output_model: Output[Model]):
    """
    Train the KNN-based collaborative filtering model.
    
    This task:
    1. Loads and validates input data
    2. Performs feature engineering on user and transaction data
    3. Generates alert labels (using real data or heuristics)
    4. Trains a KNN model for alert recommendations
    5. Saves the trained model and metadata

    Inputs:
        input_data: Dataset from prepare_data containing users.csv, transactions.csv, metadata.json
    
    Outputs:
        output_model: Model containing model.pkl and model_metadata.json
    """
    import os
    import json
    import pickle
    from datetime import datetime
    import pandas as pd
    import numpy as np
    from sklearn.neighbors import NearestNeighbors
    from sklearn.preprocessing import StandardScaler
    
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
    
    FEATURE_COLUMNS = [
        'amount_mean', 'amount_std', 'amount_max', 'amount_sum', 'amount_count',
        'merchant_name_nunique', 'merchant_category_nunique',
        'credit_limit', 'credit_balance', 'credit_utilization'
    ]
    
    def load_config():
        """Load training configuration from environment variables."""
        config = {
            'n_neighbors': int(os.getenv('N_NEIGHBORS', '5')),
            'metric': os.getenv('METRIC', 'cosine'),
            'model_version': os.getenv('MODEL_VERSION', '1.0.0'),
            'data_version': os.getenv('DATA_VERSION', '1'),
        }
        print("Training configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return config
    
    def load_input_data(input_path):
        """Load users, transactions, and metadata from input dataset."""
        users_df = pd.read_csv(os.path.join(input_path, 'users.csv'))
        transactions_df = pd.read_csv(os.path.join(input_path, 'transactions.csv'))
        
        with open(os.path.join(input_path, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        # Load alert preferences if available
        alerts_path = os.path.join(input_path, 'user_alerts.csv')
        user_alerts_df = pd.read_csv(alerts_path) if os.path.exists(alerts_path) else None
        
        print(f"Loaded {len(users_df)} users, {len(transactions_df)} transactions")
        return users_df, transactions_df, metadata, user_alerts_df
    
    def build_user_features(users_df, transactions_df):
        transactions_df = transactions_df.copy()
        transactions_df['amount'] = pd.to_numeric(transactions_df['amount'], errors='coerce')
        
        tx_agg = transactions_df.groupby('user_id').agg({
            'amount': ['count', 'mean', 'std', 'max', 'sum'],
            'merchant_name': pd.Series.nunique,
            'merchant_category': pd.Series.nunique
        })
        
        tx_agg.columns = ['_'.join(col) if isinstance(col, tuple) else col for col in tx_agg.columns]
        tx_agg = tx_agg.reset_index()
        tx_agg.columns = [
            'user_id', 'amount_count', 'amount_mean', 'amount_std',
            'amount_max', 'amount_sum', 'merchant_name_nunique', 'merchant_category_nunique'
        ]
        
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
        
        return user_feats.fillna(0)
    
    def generate_heuristic_labels(df):
        df = df.copy()
        
        df['alert_high_spender'] = (df['amount_sum'] >= df['amount_sum'].quantile(0.75)).astype(int)
        df['alert_high_tx_volume'] = (df['amount_count'] >= df['amount_count'].quantile(0.75)).astype(int)
        df['alert_high_merchant_diversity'] = (df['merchant_name_nunique'] >= df['merchant_name_nunique'].quantile(0.75)).astype(int)
        df['alert_large_transaction'] = (df['amount_max'] >= df['amount_max'].quantile(0.75)).astype(int)
        df['alert_near_credit_limit'] = (df['credit_utilization'] >= 0.7).astype(int)
        df['alert_new_merchant'] = 0
        df['alert_location_based'] = 0
        df['alert_subscription_monitoring'] = 0
        
        return df
    
    def generate_labels_from_real_data(user_features, user_alerts_df, alert_types):
        pivot = user_alerts_df.pivot_table(
            index='user_id',
            columns='alert_type',
            values='enabled',
            fill_value=0,
            aggfunc='max'
        )
        pivot.columns = [f'alert_{col}' if not col.startswith('alert_') else col for col in pivot.columns]
        pivot = pivot.reset_index()
        
        result = user_features.merge(pivot, on='user_id', how='left')
        
        for alert_type in alert_types:
            if alert_type in result.columns:
                result[alert_type] = result[alert_type].fillna(0).astype(int)
            else:
                result[alert_type] = 0
        
        return result
    
    def train_knn_model(X, n_neighbors, metric):
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        knn_model = NearestNeighbors(
            n_neighbors=min(n_neighbors, len(X_scaled)),
            metric=metric,
            algorithm='brute'
        )
        knn_model.fit(X_scaled)
        
        print(f"KNN model trained with {knn_model.n_neighbors} neighbors, metric={metric}")
        return knn_model, scaler, X_scaled
    
    def save_model_artifacts(output_path, knn_model, scaler, feature_columns, alert_types, 
                             user_ids, alert_labels, training_features):
        os.makedirs(output_path, exist_ok=True)
        
        artifacts = {
            'knn_model': knn_model,
            'scaler': scaler,
            'feature_columns': feature_columns,
            'alert_types': alert_types,
            'user_ids': user_ids,
            'alert_labels': alert_labels,
            'training_features': training_features
        }
        
        model_path = os.path.join(output_path, 'model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(artifacts, f)
        
        print(f"Model artifacts saved to {model_path}")
        return model_path
    
    def save_model_metadata(output_path, model_path, config, n_users, use_real_alerts,
                            feature_columns, alert_types):
        metadata = {
            'model_version': config['model_version'],
            'data_version': config['data_version'],
            'trained_at': datetime.now().isoformat(),
            'n_users': n_users,
            'n_neighbors': config['n_neighbors'],
            'metric': config['metric'],
            'feature_columns': feature_columns,
            'alert_types': alert_types,
            'use_real_alerts': use_real_alerts,
            'model_size_bytes': os.path.getsize(model_path)
        }
        
        metadata_path = os.path.join(output_path, 'model_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Model metadata saved to {metadata_path}")
    
    config = load_config()
    users_df, transactions_df, data_metadata, user_alerts_df = load_input_data(input_data.path)
    use_real_alerts = data_metadata.get('use_real_alerts', False)
    
    user_features = build_user_features(users_df, transactions_df)
    print(f"Built features for {len(user_features)} users")
    
    if use_real_alerts and user_alerts_df is not None:
        user_features_with_labels = generate_labels_from_real_data(user_features, user_alerts_df, ALERT_TYPES)
        print("Using real alert labels from data")
    else:
        user_features_with_labels = generate_heuristic_labels(user_features)
        print("Generated heuristic-based alert labels")
    
    X = user_features_with_labels[FEATURE_COLUMNS].values
    y = user_features_with_labels[ALERT_TYPES].values
    user_ids = user_features_with_labels['user_id'].values
    print(f"Training data shape: X={X.shape}, y={y.shape}")
    
    knn_model, scaler, X_scaled = train_knn_model(X, config['n_neighbors'], config['metric'])
    
    model_path = save_model_artifacts(
        output_model.path, knn_model, scaler, FEATURE_COLUMNS, ALERT_TYPES,
        user_ids, y, X_scaled
    )
    
    save_model_metadata(
        output_model.path, model_path, config, len(user_ids), use_real_alerts,
        FEATURE_COLUMNS, ALERT_TYPES
    )
    
    print("Training complete!")

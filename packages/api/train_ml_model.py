#!/usr/bin/env python3
"""
Train ML Alert Recommendation Model
------------------------------------

This script trains the KNN-based collaborative filtering model
using transaction data and user alert preferences.

Usage:
    python train_ml_model.py
"""

import os
from pathlib import Path
import sys

import pandas as pd

# Add the API package to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ml.alert_recommender.feature_engineering import (
    build_user_features,
    get_alert_columns,
)
from src.ml.alert_recommender.recommender import AlertRecommenderModel


def load_data():
    """Load users, transactions, and user alerts from CSV files"""
    data_dir = Path(__file__).parent.parent.parent / 'data'

    print(f'Loading data from {data_dir}...')

    # Load CSV files
    users_df = pd.read_csv(data_dir / 'sample_users.csv')
    transactions_df = pd.read_csv(data_dir / 'sample_transactions.csv')
    user_alerts_df = pd.read_csv(data_dir / 'sample_user_alerts.csv')

    print(f'✅ Loaded {len(users_df)} users')
    print(f'✅ Loaded {len(transactions_df)} transactions')
    print(f'✅ Loaded {len(user_alerts_df)} user alert preferences')

    return users_df, transactions_df, user_alerts_df


def merge_alert_labels(user_features_df, user_alerts_df):
    """
    Merge user alert preferences into feature dataframe.
    Creates binary columns like alert_high_spender, alert_new_merchant, etc.
    """
    # Pivot alerts to create columns for each alert type
    pivot = user_alerts_df.pivot_table(
        index='user_id',
        columns='alert_type',
        values='enabled',
        fill_value=0,
        aggfunc='max',
    )

    pivot = pivot.reset_index()

    # Merge with user features
    merged = user_features_df.merge(pivot, on='user_id', how='left')

    # Fill NaN with 0 for users without alerts
    alert_cols = get_alert_columns()
    for col in alert_cols:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0).astype(int)
        else:
            merged[col] = 0

    return merged


def train_model():
    """Main training function"""
    print('=' * 60)
    print('ML Alert Recommendation Model Training')
    print('=' * 60)

    # Load data
    users_df, transactions_df, user_alerts_df = load_data()

    # Build user behavioral features
    print('\n📊 Building user behavioral features...')
    user_features = build_user_features(users_df, transactions_df)
    print(f'✅ Built features for {len(user_features)} users')

    # Merge with real alert labels
    print('\n🏷️  Merging user alert preferences...')
    user_features_with_alerts = merge_alert_labels(user_features, user_alerts_df)

    # Show alert distribution
    alert_cols = get_alert_columns()
    existing_alert_cols = [
        col for col in alert_cols if col in user_features_with_alerts.columns
    ]

    print('\n📈 Alert distribution:')
    for col in existing_alert_cols:
        count = user_features_with_alerts[col].sum()
        pct = (count / len(user_features_with_alerts)) * 100
        print(f'  {col}: {int(count)} users ({pct:.1f}%)')

    # Train KNN model
    print('\n🤖 Training KNN model...')
    model_path = '/tmp/ml_models/model_knn.pkl'
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    model = AlertRecommenderModel(model_path=None)  # Don't load existing
    model.train(
        user_features_df=user_features_with_alerts, n_neighbors=5, metric='cosine'
    )
    model.save_model()

    print(f'✅ Model saved to {model_path}')

    # Test recommendation for a sample user
    print('\n🧪 Testing recommendations for u-031 (user without alerts)...')

    try:
        result = model.recommend_for_user(
            user_id='u-031',
            user_features_df=user_features_with_alerts,
            k_neighbors=5,
            threshold=0.4,
        )

        print('\n📋 Recommendations for u-031:')
        print(f'  Similar users analyzed: {result["total_similar_users"]}')
        print(f'  Recommendations generated: {len(result["recommendations"])}')

        for rec in result['recommendations']:
            print(f'\n  ✨ {rec["alert_type"]}')
            print(f'     Probability: {rec["probability"]:.2%}')
            print(f'     Confidence: {rec["confidence"]}')
            print(f'     Reason: {rec["reason"]}')

    except Exception as e:
        print(f'⚠️  Could not test u-031: {e}')
        print("   (This is OK if u-031 doesn't exist in the data)")

    print('\n' + '=' * 60)
    print('✅ Training Complete!')
    print('=' * 60)
    print(f'\nModel ready at: {model_path}')
    print('You can now start the API server to use ML recommendations.')


if __name__ == '__main__':
    train_model()

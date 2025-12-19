"""
Feature Engineering Module for Alert Recommendations
-----------------------------------------------------

This module provides:
1. Feature engineering from users + transactions
2. Alert label generation (heuristic and real)
3. User behavior profiling

Based on user transaction history and profile data, we build
feature vectors that capture spending patterns and behavior.
"""

from typing import Any

import numpy as np
import pandas as pd


def build_user_features(
    users_df: pd.DataFrame, transactions_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build per-user behavioral features from transactions + user info.

    Args:
        users_df: DataFrame with user information (id, credit_limit, credit_balance, etc.)
        transactions_df: DataFrame with transaction data (user_id, amount, merchant_name, etc.)

    Returns:
        DataFrame with one row per user and behavioral features
    """
    if transactions_df.empty:
        # Return basic user features if no transactions exist
        return _build_basic_user_features(users_df)

    # Ensure amount is numeric
    transactions_df['amount'] = pd.to_numeric(
        transactions_df['amount'], errors='coerce'
    )

    # Transaction-level aggregations
    tx_agg = transactions_df.groupby('user_id').agg(
        {
            'amount': ['count', 'mean', 'std', 'max', 'sum'],
            'merchant_name': pd.Series.nunique,
            'merchant_category': pd.Series.nunique,
        }
    )

    # Flatten multi-index columns
    tx_agg.columns = [
        '_'.join(col) if isinstance(col, tuple) else col for col in tx_agg.columns
    ]
    tx_agg = tx_agg.reset_index()

    # Rename columns for clarity
    tx_agg.columns = [
        'user_id',
        'amount_count',
        'amount_mean',
        'amount_std',
        'amount_max',
        'amount_sum',
        'merchant_name_nunique',
        'merchant_category_nunique',
    ]

    # Join with user info (ensure numeric types)
    user_cols = ['id', 'credit_limit', 'credit_balance']
    available_user_cols = [col for col in user_cols if col in users_df.columns]

    user_feats = tx_agg.merge(
        users_df[available_user_cols], left_on='user_id', right_on='id', how='left'
    )

    if 'id' in user_feats.columns:
        user_feats = user_feats.drop(columns=['id'])

    # Ensure credit_limit and credit_balance are numeric
    if 'credit_limit' in user_feats.columns:
        user_feats['credit_limit'] = pd.to_numeric(
            user_feats['credit_limit'], errors='coerce'
        )
    if 'credit_balance' in user_feats.columns:
        user_feats['credit_balance'] = pd.to_numeric(
            user_feats['credit_balance'], errors='coerce'
        )

    # Credit utilization (handle division by zero and nulls)
    if 'credit_limit' in user_feats.columns and 'credit_balance' in user_feats.columns:
        user_feats['credit_utilization'] = np.where(
            user_feats['credit_limit'] > 0,
            user_feats['credit_balance'] / user_feats['credit_limit'],
            0,
        )
    else:
        user_feats['credit_utilization'] = 0

    # Fill NaN values with 0
    user_feats = user_feats.fillna(0)

    return user_feats


def _build_basic_user_features(users_df: pd.DataFrame) -> pd.DataFrame:
    """Build basic features for users without transaction history"""
    basic_feats = pd.DataFrame(
        {
            'user_id': users_df['id'],
            'amount_count': 0,
            'amount_mean': 0,
            'amount_std': 0,
            'amount_max': 0,
            'amount_sum': 0,
            'merchant_name_nunique': 0,
            'merchant_category_nunique': 0,
            'credit_limit': pd.to_numeric(
                users_df.get('credit_limit', 0), errors='coerce'
            ).fillna(0),
            'credit_balance': pd.to_numeric(
                users_df.get('credit_balance', 0), errors='coerce'
            ).fillna(0),
        }
    )

    # Calculate credit utilization
    basic_feats['credit_utilization'] = np.where(
        basic_feats['credit_limit'] > 0,
        basic_feats['credit_balance'] / basic_feats['credit_limit'],
        0,
    )

    return basic_feats


def generate_initial_alert_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create initial alert columns using heuristics.
    Later replaced by real user_alerts table.

    Args:
        df: DataFrame with user features

    Returns:
        DataFrame with added alert label columns
    """
    df = df.copy()

    # Use quantiles for thresholds (data-driven approach)
    # High spender: top 25% by total spending
    if df['amount_sum'].max() > 0:
        df['alert_high_spender'] = (
            df['amount_sum'] >= df['amount_sum'].quantile(0.75)
        ).astype(int)
    else:
        df['alert_high_spender'] = 0

    # High transaction volume: top 25% by transaction count
    if df['amount_count'].max() > 0:
        df['alert_high_tx_volume'] = (
            df['amount_count'] >= df['amount_count'].quantile(0.75)
        ).astype(int)
    else:
        df['alert_high_tx_volume'] = 0

    # High merchant diversity: top 25% by unique merchants
    if df['merchant_name_nunique'].max() > 0:
        df['alert_high_merchant_diversity'] = (
            df['merchant_name_nunique'] >= df['merchant_name_nunique'].quantile(0.75)
        ).astype(int)
    else:
        df['alert_high_merchant_diversity'] = 0

    # Near credit limit: utilization >= 70%
    df['alert_near_credit_limit'] = (df['credit_utilization'] >= 0.7).astype(int)

    # Large transaction alert: transactions > 75th percentile
    if df['amount_max'].max() > 0:
        df['alert_large_transaction'] = (
            df['amount_max'] >= df['amount_max'].quantile(0.75)
        ).astype(int)
    else:
        df['alert_large_transaction'] = 0

    return df


def merge_real_alert_labels(
    user_feature_df: pd.DataFrame, user_alerts_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Replace heuristic labels with real labels from user_alerts table.

    Args:
        user_feature_df: DataFrame with user features
        user_alerts_df: DataFrame with columns: user_id, alert_type, enabled (0/1)

    Returns:
        DataFrame with merged real alert labels
    """
    # Pivot user alerts to create alert type columns
    pivot = user_alerts_df.pivot_table(
        index='user_id',
        columns='alert_type',
        values='enabled',
        fill_value=0,
        aggfunc='max',  # Take max in case of duplicates
    )

    # Add 'alert_' prefix to column names if not already present
    pivot.columns = [
        f'alert_{col}' if not col.startswith('alert_') else col for col in pivot.columns
    ]
    pivot = pivot.reset_index()

    # Merge with user features
    merged = user_feature_df.merge(pivot, on='user_id', how='left').fillna(0)

    return merged


def extract_alert_types_from_rules(alert_rules: list[dict[str, Any]]) -> dict[str, int]:
    """
    Extract alert types from user's active alert rules.
    Maps natural language queries to standardized alert types.

    Args:
        alert_rules: List of alert rule dictionaries

    Returns:
        Dictionary mapping alert type names to binary values (0 or 1)
    """
    alert_types = {
        'alert_high_spender': 0,
        'alert_high_tx_volume': 0,
        'alert_high_merchant_diversity': 0,
        'alert_near_credit_limit': 0,
        'alert_large_transaction': 0,
        'alert_new_merchant': 0,
        'alert_location_based': 0,
        'alert_subscription_monitoring': 0,
    }

    # Keywords to identify alert types
    keyword_mapping = {
        'alert_high_spender': ['spending', 'spent', 'spend over', 'total spend'],
        'alert_high_tx_volume': [
            'transaction count',
            'number of transactions',
            'frequent',
        ],
        'alert_high_merchant_diversity': ['different merchant', 'variety', 'diverse'],
        'alert_near_credit_limit': ['credit limit', 'balance', 'utilization'],
        'alert_large_transaction': ['large', 'big purchase', 'amount over', 'exceeds'],
        'alert_new_merchant': ['new merchant', 'unfamiliar', 'first time'],
        'alert_location_based': ['location', 'out of state', 'international', 'travel'],
        'alert_subscription_monitoring': [
            'subscription',
            'recurring',
            'monthly charge',
        ],
    }

    for rule in alert_rules:
        query = rule.get('natural_language_query', '').lower()

        for alert_type, keywords in keyword_mapping.items():
            if any(keyword in query for keyword in keywords):
                alert_types[alert_type] = 1

    return alert_types


def get_alert_columns() -> list[str]:
    """Get list of all possible alert column names"""
    return [
        'alert_high_spender',
        'alert_high_tx_volume',
        'alert_high_merchant_diversity',
        'alert_near_credit_limit',
        'alert_large_transaction',
        'alert_new_merchant',
        'alert_location_based',
        'alert_subscription_monitoring',
    ]


def get_similarity_feature_columns() -> list[str]:
    """Get list of feature columns used for user similarity calculation"""
    return [
        'amount_mean',
        'amount_std',
        'amount_max',
        'amount_sum',
        'amount_count',
        'merchant_name_nunique',
        'merchant_category_nunique',
        'credit_limit',
        'credit_balance',
        'credit_utilization',
    ]

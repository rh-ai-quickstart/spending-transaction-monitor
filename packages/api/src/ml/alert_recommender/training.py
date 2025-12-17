"""
Model Training Module
---------------------

Provides functionality for:
1. Training the KNN model from scratch
2. Retraining with new data
3. Logging user alert choices for continuous learning
"""

from datetime import datetime
import os

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .feature_engineering import (
    build_user_features,
    extract_alert_types_from_rules,
    generate_initial_alert_labels,
    get_alert_columns,
    merge_real_alert_labels,
)
from .recommender import AlertRecommenderModel


async def train_model(
    session: AsyncSession,
    model_path: str | None = None,
    n_neighbors: int = 5,
    use_real_alerts: bool = True,
) -> AlertRecommenderModel:
    """
    Train the alert recommendation model from database data.

    Args:
        session: Database session
        model_path: Path to save the model (optional)
        n_neighbors: Number of neighbors for KNN
        use_real_alerts: Whether to use real user alerts or heuristic labels

    Returns:
        Trained AlertRecommenderModel
    """
    from db.models import AlertRule, Transaction, User

    # Fetch users
    users_result = await session.execute(select(User))
    users = users_result.scalars().all()

    # Fetch transactions
    transactions_result = await session.execute(select(Transaction))
    transactions = transactions_result.scalars().all()

    # Convert to DataFrames
    users_df = pd.DataFrame(
        [
            {
                'id': u.id,
                'credit_limit': float(u.credit_limit) if u.credit_limit else 0,
                'credit_balance': float(u.credit_balance) if u.credit_balance else 0,
            }
            for u in users
        ]
    )

    transactions_df = pd.DataFrame(
        [
            {
                'user_id': t.user_id,
                'amount': float(t.amount),
                'merchant_name': t.merchant_name,
                'merchant_category': t.merchant_category,
                'transaction_date': t.transaction_date,
            }
            for t in transactions
        ]
    )

    # Build user features
    user_features = build_user_features(users_df, transactions_df)

    # Add alert labels
    if use_real_alerts:
        # Fetch alert rules from database
        user_alerts_data = []

        for user in users:
            rules_result = await session.execute(
                select(AlertRule).where(
                    and_(AlertRule.user_id == user.id, AlertRule.is_active)
                )
            )
            alert_rules = rules_result.scalars().all()

            # Extract alert types from rules
            alert_types = extract_alert_types_from_rules(
                [
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'natural_language_query': rule.natural_language_query,
                        'description': rule.description,
                    }
                    for rule in alert_rules
                ]
            )

            # Add to user alerts data
            for alert_type, enabled in alert_types.items():
                if enabled:
                    user_alerts_data.append(
                        {
                            'user_id': user.id,
                            'alert_type': alert_type,
                            'enabled': enabled,
                        }
                    )

        if user_alerts_data:
            user_alerts_df = pd.DataFrame(user_alerts_data)
            user_features = merge_real_alert_labels(user_features, user_alerts_df)
            print(f'Using real alert labels from {len(user_alerts_data)} alert rules')
        else:
            # No real alerts, fall back to heuristic
            user_features = generate_initial_alert_labels(user_features)
            print('No real alert labels found, using heuristic labels')
    else:
        # Use heuristic labels
        user_features = generate_initial_alert_labels(user_features)
        print('Using heuristic alert labels')

    # Ensure all alert columns exist
    for alert_col in get_alert_columns():
        if alert_col not in user_features.columns:
            user_features[alert_col] = 0

    # Train model
    model = AlertRecommenderModel(model_path=model_path)
    model.train(user_features, n_neighbors=n_neighbors)

    # Save model
    model.save_model()

    print(f'Model trained successfully with {len(user_features)} users')

    return model


async def retrain_model(
    session: AsyncSession, model_path: str | None = None, n_neighbors: int = 5
) -> AlertRecommenderModel:
    """
    Retrain the model with updated data.
    Always uses real alert labels from the database.

    Args:
        session: Database session
        model_path: Path to save the model
        n_neighbors: Number of neighbors for KNN

    Returns:
        Retrained AlertRecommenderModel
    """
    print('Retraining model with latest data...')
    return await train_model(
        session=session,
        model_path=model_path,
        n_neighbors=n_neighbors,
        use_real_alerts=True,
    )


async def log_user_alert_action(
    session: AsyncSession,
    user_id: str,
    alert_rule_id: str,
    action: str,  # 'created', 'enabled', 'disabled', 'deleted'
) -> None:
    """
    Log user alert actions for tracking model performance and retraining.

    Args:
        session: Database session
        user_id: User ID
        alert_rule_id: Alert rule ID
        action: Action performed ('created', 'enabled', 'disabled', 'deleted')
    """
    # This could be extended to log to a separate table for model analytics
    # For now, we just trigger a background retraining check

    # TODO: Implement alert action logging table
    # Example structure:
    # - user_id
    # - alert_rule_id
    # - action
    # - timestamp
    # - alert_type (extracted from rule)

    print(
        f'Alert action logged: user={user_id}, alert={alert_rule_id}, action={action}'
    )


def should_retrain_model(
    model_path: str | None = None, days_threshold: int = 7
) -> bool:
    """
    Check if the model should be retrained based on age.

    Args:
        model_path: Path to the model file
        days_threshold: Number of days before model is considered stale

    Returns:
        True if model should be retrained, False otherwise
    """
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'model_knn.pkl')

    # Check if model exists
    if not os.path.exists(model_path):
        return True  # Model doesn't exist, needs training

    # Check model age
    model_modified_time = os.path.getmtime(model_path)
    model_age_days = (datetime.now().timestamp() - model_modified_time) / (24 * 3600)

    return model_age_days > days_threshold

"""ML-based Alert Recommendation Service

Replaces LLM-based recommendations with a custom-trained ML model
that learns from user behavior and alert choices.
"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertRule, Transaction, User
from src.services.recommendations.ml import AlertRecommenderModel
from src.services.recommendations.ml.feature_engineering import (
    build_user_features,
    extract_alert_types_from_rules,
    get_alert_columns,
)
from src.services.recommendations.ml.training import retrain_model, should_retrain_model
from src.services.transactions.transaction_service import TransactionService
from src.services.users.user_service import UserService


class MLAlertRecommendationService:
    """Service for generating ML-based alert recommendations"""

    def __init__(self, model_path: str | None = None):
        self.transaction_service = TransactionService()
        self.user_service = UserService()
        self.model = AlertRecommenderModel(model_path=model_path)

    async def get_recommendations(
        self,
        user_id: str,
        session: AsyncSession,
        k_neighbors: int = 5,
        threshold: float = 0.4,
    ) -> dict[str, Any]:
        """
        Get ML-based alert recommendations for a user.

        Args:
            user_id: User ID to get recommendations for
            session: Database session
            k_neighbors: Number of similar users to consider
            threshold: Minimum probability to recommend an alert

        Returns:
            Dictionary with recommendations
        """
        # Check if model needs retraining
        if should_retrain_model(self.model.model_path):
            print('Model is stale, retraining...')
            await retrain_model(session, model_path=self.model.model_path)
            self.model.load_model()

        # If model is not trained, train it now
        if not self.model.is_trained():
            print('Model not trained, training now...')
            from src.services.recommendations.ml.training import train_model

            await train_model(session, model_path=self.model.model_path)
            self.model.load_model()

        # Get user
        user = await self.user_service.get_user(user_id, session)
        if not user:
            return {'error': 'User not found'}

        # Build user features for all users
        user_features_df = await self._build_user_features(session)

        # Check if target user exists in features
        if user_id not in user_features_df['user_id'].values:
            # Add the user to the features dataframe
            user_features_df = await self._add_user_to_features(
                user_id, user_features_df, session
            )

        try:
            # Get recommendations from model
            result = self.model.recommend_for_user(
                user_id=user_id,
                user_features_df=user_features_df,
                k_neighbors=k_neighbors,
                threshold=threshold,
            )

            # Format recommendations for API response
            formatted_recommendations = self._format_recommendations(
                result['recommendations'], user
            )

            # If no recommendations, fall back to defaults
            if not formatted_recommendations:
                print(
                    f'No ML recommendations generated for user {user_id}, using defaults'
                )
                return self._get_default_recommendations(user_id, user)

            return {
                'user_id': user_id,
                'recommendation_type': 'ml_collaborative_filtering',
                'recommendations': formatted_recommendations,
                'generated_at': datetime.now().isoformat(),
                'model_info': {
                    'similar_users_count': result['total_similar_users'],
                    'k_neighbors': k_neighbors,
                    'threshold': threshold,
                },
            }

        except Exception as e:
            print(f'Error generating recommendations: {e}')
            # Fallback to default recommendations
            return self._get_default_recommendations(user_id, user)

    async def _build_user_features(self, session: AsyncSession) -> pd.DataFrame:
        """Build feature dataframe for all users"""
        # Fetch all users
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()

        # Fetch all transactions
        transactions_result = await session.execute(select(Transaction))
        transactions = transactions_result.scalars().all()

        # Convert to DataFrames
        users_df = pd.DataFrame(
            [
                {
                    'id': u.id,
                    'credit_limit': float(u.credit_limit) if u.credit_limit else 0,
                    'credit_balance': float(u.credit_balance)
                    if u.credit_balance
                    else 0,
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

        # Build features
        user_features = build_user_features(users_df, transactions_df)

        # Add alert labels from existing alert rules
        user_features = await self._add_alert_labels(user_features, session)

        return user_features

    async def _add_alert_labels(
        self, user_features: pd.DataFrame, session: AsyncSession
    ) -> pd.DataFrame:
        """Add alert labels based on existing user alert rules"""
        # Initialize all alert columns with 0
        for alert_col in get_alert_columns():
            if alert_col not in user_features.columns:
                user_features[alert_col] = 0

        # Get all users and their alert rules
        users_result = await session.execute(select(User))
        users = users_result.scalars().all()

        for user in users:
            rules_result = await session.execute(
                select(AlertRule).where(
                    and_(AlertRule.user_id == user.id, AlertRule.is_active)
                )
            )
            alert_rules = rules_result.scalars().all()

            # Extract alert types
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

            # Update user features with alert labels
            user_mask = user_features['user_id'] == user.id
            for alert_type, enabled in alert_types.items():
                if alert_type in user_features.columns:
                    user_features.loc[user_mask, alert_type] = enabled

        return user_features

    async def _add_user_to_features(
        self, user_id: str, user_features_df: pd.DataFrame, session: AsyncSession
    ) -> pd.DataFrame:
        """Add a single user to the features dataframe"""
        user = await self.user_service.get_user(user_id, session)
        if not user:
            return user_features_df

        # Get user transactions
        from datetime import UTC

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=90)

        transactions = await self.transaction_service.get_transactions_with_filters(
            session=session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        # Create single-user dataframes
        users_df = pd.DataFrame(
            [
                {
                    'id': user.id,
                    'credit_limit': float(user.credit_limit)
                    if user.credit_limit
                    else 0,
                    'credit_balance': float(user.credit_balance)
                    if user.credit_balance
                    else 0,
                }
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

        # Build features for this user
        new_user_features = build_user_features(users_df, transactions_df)

        # Add alert labels
        new_user_features = await self._add_alert_labels(new_user_features, session)

        # Ensure all columns match
        for col in user_features_df.columns:
            if col not in new_user_features.columns:
                new_user_features[col] = 0

        for col in new_user_features.columns:
            if col not in user_features_df.columns:
                user_features_df[col] = 0

        # Append to existing features
        user_features_df = pd.concat(
            [user_features_df, new_user_features], ignore_index=True
        )

        return user_features_df

    def _format_recommendations(
        self, recommendations: list[dict[str, Any]], user: User
    ) -> list[dict[str, Any]]:
        """Format recommendations for API response"""
        formatted = []

        alert_type_mapping = {
            'high_spender': {
                'title': 'High Spending Alert',
                'description': 'Monitor when your total spending exceeds a threshold',
                'category': 'spending_threshold',
                'query': f'Notify me when my total spending exceeds ${user.credit_limit * 0.5 if user.credit_limit else 1000:.0f}',
            },
            'high_tx_volume': {
                'title': 'Frequent Transaction Alert',
                'description': 'Get notified when you have many transactions in a short period',
                'category': 'fraud_protection',
                'query': 'Notify me when I have more than 10 transactions in a day',
            },
            'high_merchant_diversity': {
                'title': 'New Merchant Diversity Alert',
                'description': 'Track when you visit multiple different merchants in a day',
                'category': 'merchant_monitoring',
                'query': 'Notify me when I visit more than 5 different merchants in a day',
            },
            'near_credit_limit': {
                'title': 'Credit Limit Alert',
                'description': 'Get warned when approaching your credit limit',
                'category': 'spending_threshold',
                'query': 'Notify me when my credit utilization exceeds 70%',
            },
            'large_transaction': {
                'title': 'Large Transaction Alert',
                'description': 'Monitor unusually large purchases',
                'category': 'fraud_protection',
                'query': f'Notify me when a single transaction exceeds ${user.credit_limit * 0.2 if user.credit_limit else 500:.0f}',
            },
            'new_merchant': {
                'title': 'New Merchant Alert',
                'description': "Track purchases from merchants you haven't used before",
                'category': 'fraud_protection',
                'query': 'Notify me when I make a purchase from a new merchant',
            },
            'location_based': {
                'title': 'Location-Based Alert',
                'description': 'Detect transactions in unusual locations',
                'category': 'location_based',
                'query': 'Notify me of transactions in unusual locations',
            },
            'subscription_monitoring': {
                'title': 'Subscription Monitoring',
                'description': 'Track recurring subscription charges',
                'category': 'subscription_monitoring',
                'query': 'Notify me of recurring subscription charges',
            },
        }

        # Map confidence levels to priority
        def confidence_to_priority(confidence: str) -> str:
            confidence_map = {
                'high': 'high',
                'medium': 'medium',
                'low': 'low',
            }
            return confidence_map.get(confidence.lower(), 'medium')

        for rec in recommendations:
            alert_type = rec['alert_type']
            mapping = alert_type_mapping.get(alert_type, {})

            formatted.append(
                {
                    'title': mapping.get('title', alert_type.replace('_', ' ').title()),
                    'description': mapping.get(
                        'description', f'Alert for {alert_type}'
                    ),
                    'natural_language_query': mapping.get(
                        'query', f'Alert for {alert_type}'
                    ),
                    'category': mapping.get('category', 'fraud_protection'),
                    'priority': confidence_to_priority(rec['confidence']),
                    'reasoning': rec['reason'],
                }
            )

        return formatted

    def _get_default_recommendations(self, user_id: str, user: User) -> dict[str, Any]:
        """Provide default recommendations if ML model fails"""
        default_recs = [
            {
                'title': 'Large Transaction Alert',
                'description': 'Monitor unusually large purchases',
                'natural_language_query': f'Notify me when a transaction exceeds ${user.credit_limit * 0.2 if user.credit_limit else 500:.0f}',
                'category': 'fraud_protection',
                'priority': 'medium',
                'reasoning': 'Default recommendation for fraud protection',
            },
            {
                'title': 'New Merchant Alert',
                'description': "Track purchases from merchants you haven't used before",
                'natural_language_query': 'Notify me when I make a purchase from a new merchant',
                'category': 'fraud_protection',
                'priority': 'medium',
                'reasoning': 'Default recommendation for fraud protection',
            },
        ]

        return {
            'user_id': user_id,
            'recommendation_type': 'default',
            'recommendations': default_recs,
            'generated_at': datetime.now().isoformat(),
        }

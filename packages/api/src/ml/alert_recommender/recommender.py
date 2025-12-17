"""
Alert Recommendation Engine - Core Recommender Module
------------------------------------------------------

This module provides:
1. KNN-based similar-user alert recommendations
2. Model loading and prediction
3. Alert probability scoring

Uses trained KNN model to find similar users and recommend alerts
based on collaborative filtering approach.
"""

import os
import pickle
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from .feature_engineering import (
    get_alert_columns,
    get_similarity_feature_columns,
)


class AlertRecommenderModel:
    """
    KNN-based Alert Recommendation Model

    Uses K-Nearest Neighbors to find similar users and recommend alerts
    based on what similar users have enabled.
    """

    def __init__(self, model_path: str | None = None):
        """
        Initialize the recommender model.

        Args:
            model_path: Path to saved model file. If None, uses default path.
        """
        if model_path is None:
            # Default model path - use /tmp for container compatibility
            model_path = os.path.join('/tmp', 'ml_models', 'model_knn.pkl')

        self.model_path = model_path
        self.knn: NearestNeighbors | None = None
        self.scaler: StandardScaler | None = None
        self.feature_cols: list[str] = []
        self.alert_cols: list[str] = []
        self.user_data: pd.DataFrame | None = None

        # Try to load model if it exists
        if os.path.exists(self.model_path):
            self.load_model()

    def load_model(self) -> None:
        """Load trained model from disk"""
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.knn = model_data['knn']
        self.scaler = model_data['scaler']
        self.feature_cols = model_data['feature_cols']
        self.alert_cols = model_data.get('alert_cols', get_alert_columns())
        self.user_data = model_data.get('user_data')

        print(f'Model loaded from {self.model_path}')

    def save_model(self) -> None:
        """Save trained model to disk"""
        # Ensure model directory exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        model_data = {
            'knn': self.knn,
            'scaler': self.scaler,
            'feature_cols': self.feature_cols,
            'alert_cols': self.alert_cols,
            'user_data': self.user_data,
        }

        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)

        print(f'Model saved to {self.model_path}')

    def train(
        self,
        user_features_df: pd.DataFrame,
        n_neighbors: int = 5,
        metric: str = 'cosine',
    ) -> None:
        """
        Train the KNN model on user features.

        Args:
            user_features_df: DataFrame with user features and alert labels
            n_neighbors: Number of neighbors to use for KNN
            metric: Distance metric for KNN (default: cosine)
        """
        # Store user data for later use
        self.user_data = user_features_df.copy()

        # Get feature columns
        self.feature_cols = get_similarity_feature_columns()

        # Filter to only include columns that exist in the dataframe
        self.feature_cols = [
            col for col in self.feature_cols if col in user_features_df.columns
        ]

        # Get alert columns
        self.alert_cols = [
            col for col in user_features_df.columns if col.startswith('alert_')
        ]

        # Prepare feature matrix
        X = user_features_df[self.feature_cols].fillna(0)

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train KNN model (n_neighbors+1 because the closest neighbor is the user themselves)
        self.knn = NearestNeighbors(n_neighbors=n_neighbors + 1, metric=metric)
        self.knn.fit(X_scaled)

        print(
            f'Model trained with {len(user_features_df)} users and {n_neighbors} neighbors'
        )

    def recommend_for_user(
        self,
        user_id: str,
        user_features_df: pd.DataFrame,
        k_neighbors: int = 5,
        threshold: float = 0.4,
    ) -> dict[str, Any]:
        """
        Recommend alerts for a single user based on similar users.

        Args:
            user_id: ID of the user to recommend alerts for
            user_features_df: DataFrame with all user features (including the target user)
            k_neighbors: Number of similar users to consider
            threshold: Minimum probability threshold to recommend an alert

        Returns:
            Dictionary with recommended alerts and their probabilities
        """
        if self.knn is None or self.scaler is None:
            raise ValueError(
                'Model not trained or loaded. Please train or load a model first.'
            )

        # Get this user's feature row
        user_row = user_features_df[user_features_df['user_id'] == user_id]
        if user_row.empty:
            raise ValueError(f'User {user_id} not found in user_features_df')

        # Get user's current alerts (if any)
        current_alerts = {}
        for alert_col in self.alert_cols:
            if alert_col in user_row.columns:
                current_alerts[alert_col] = int(user_row[alert_col].iloc[0])

        # Extract feature values
        user_X = user_row[self.feature_cols].fillna(0)
        user_scaled = self.scaler.transform(user_X)

        # Find neighbors
        distances, neighbor_indices = self.knn.kneighbors(
            user_scaled, n_neighbors=k_neighbors + 1
        )

        # Get neighbor data (skip first neighbor which is the user themselves)
        neighbor_idx = neighbor_indices[0][1:]
        neighbor_distances = distances[0][1:]

        neighbors = user_features_df.iloc[neighbor_idx]

        # Compute alert probabilities based on neighbors
        alert_probs = {}
        for alert_col in self.alert_cols:
            if alert_col in neighbors.columns:
                # Simple average: fraction of neighbors with this alert enabled
                prob = neighbors[alert_col].mean()
                alert_probs[alert_col] = float(prob)
            else:
                alert_probs[alert_col] = 0.0

        # Filter recommendations
        # Only recommend alerts that:
        # 1. User doesn't already have
        # 2. Have probability >= threshold
        recommendations = []
        for alert_type, prob in alert_probs.items():
            # Remove 'alert_' prefix for cleaner alert type name
            alert_name = alert_type.replace('alert_', '')

            # Skip if user already has this alert
            if current_alerts.get(alert_type, 0) == 1:
                continue

            # Skip if probability is below threshold
            if prob < threshold:
                continue

            recommendations.append(
                {
                    'alert_type': alert_name,
                    'probability': prob,
                    'confidence': self._calculate_confidence(prob, len(neighbor_idx)),
                    'reason': self._generate_reason(
                        alert_name, prob, len(neighbor_idx)
                    ),
                }
            )

        # Sort by probability descending
        recommendations.sort(key=lambda x: x['probability'], reverse=True)

        return {
            'user_id': user_id,
            'recommendations': recommendations,
            'similar_users': self._format_similar_users(neighbors, neighbor_distances),
            'total_similar_users': len(neighbor_idx),
        }

    def _calculate_confidence(self, probability: float, n_neighbors: int) -> str:
        """Calculate confidence level based on probability and sample size"""
        if n_neighbors < 3:
            return 'low'
        elif probability >= 0.7:
            return 'high'
        elif probability >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _generate_reason(
        self, alert_type: str, probability: float, n_neighbors: int
    ) -> str:
        """Generate human-readable reason for recommendation"""
        percentage = int(probability * 100)

        alert_descriptions = {
            'high_spender': 'monitoring high spending patterns',
            'high_tx_volume': 'tracking transaction frequency',
            'high_merchant_diversity': 'detecting diverse merchant usage',
            'near_credit_limit': 'monitoring credit utilization',
            'large_transaction': 'detecting large purchases',
            'new_merchant': 'tracking new merchant visits',
            'location_based': 'monitoring location-based activity',
            'subscription_monitoring': 'tracking subscription services',
        }

        description = alert_descriptions.get(alert_type, 'this type of monitoring')

        return (
            f'{percentage}% of similar users have enabled {description}. '
            f'Based on analysis of {n_neighbors} users with similar spending patterns.'
        )

    def _format_similar_users(
        self, neighbors: pd.DataFrame, distances: np.ndarray
    ) -> list[dict[str, Any]]:
        """Format similar user information for response"""
        similar_users = []

        for idx, (_, user) in enumerate(neighbors.iterrows()):
            similar_users.append(
                {
                    'user_id': user.get('user_id', 'unknown'),
                    'similarity_score': float(
                        1 - distances[idx]
                    ),  # Convert distance to similarity
                    'enabled_alerts': [
                        alert.replace('alert_', '')
                        for alert in self.alert_cols
                        if alert in user and user[alert] == 1
                    ],
                }
            )

        return similar_users

    def is_trained(self) -> bool:
        """Check if model is trained and ready for predictions"""
        return self.knn is not None and self.scaler is not None


def recommend_alerts(
    user_id: str,
    user_features_df: pd.DataFrame,
    model_path: str | None = None,
    k_neighbors: int = 5,
    threshold: float = 0.4,
) -> dict[str, Any]:
    """
    Convenience function to recommend alerts for a user.

    Args:
        user_id: ID of the user to recommend alerts for
        user_features_df: DataFrame with all user features
        model_path: Path to saved model (optional)
        k_neighbors: Number of similar users to consider
        threshold: Minimum probability threshold

    Returns:
        Dictionary with recommendations
    """
    model = AlertRecommenderModel(model_path=model_path)

    if not model.is_trained():
        raise ValueError('Model not trained. Please train the model first.')

    return model.recommend_for_user(
        user_id=user_id,
        user_features_df=user_features_df,
        k_neighbors=k_neighbors,
        threshold=threshold,
    )

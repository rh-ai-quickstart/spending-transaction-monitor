"""Placeholder Recommendation Service - Provides instant generic recommendations"""

from datetime import datetime
from typing import Any

from db.models import User


class PlaceholderRecommendationService:
    """Service for providing instant placeholder recommendations while real ones generate"""

    def get_placeholder_recommendations(self, user: User) -> dict[str, Any]:
        """Get instant placeholder recommendations based on user demographics"""

        # Generic recommendations that can be shown immediately
        placeholder_recommendations = [
            {
                'title': 'High Amount Transaction Alert',
                'description': 'Get notified when any transaction exceeds $500',
                'natural_language_query': 'Alert me when I spend more than $500 in one transaction',
                'category': 'spending_threshold',
                'priority': 'high',
                'reasoning': 'This is a common alert that helps protect against large unauthorized charges',
            },
            {
                'title': 'Dining Spending Alert',
                'description': 'Monitor your dining expenses to stay within budget',
                'natural_language_query': 'Alert me when my dining expenses exceed $200 in a week',
                'category': 'spending_threshold',
                'priority': 'medium',
                'reasoning': 'Dining is often a significant expense category that benefits from monitoring',
            },
            {
                'title': 'Location-Based Security Alert',
                'description': 'Get notified of transactions outside your home state',
                'natural_language_query': 'Alert me if a transaction happens outside my home state',
                'category': 'location_based',
                'priority': 'high',
                'reasoning': 'Location-based alerts help detect potential fraud or unauthorized card usage',
            },
            {
                'title': 'Recurring Charge Monitoring',
                'description': 'Track changes in your subscription and recurring payments',
                'natural_language_query': 'Alert me if any recurring charge increases by more than 20%',
                'category': 'subscription_monitoring',
                'priority': 'medium',
                'reasoning': 'Monitoring recurring charges helps catch unexpected price increases',
            },
        ]

        return {
            'user_id': user.id,
            'recommendation_type': 'placeholder',
            'recommendations': placeholder_recommendations,
            'generated_at': datetime.now().isoformat(),
            'is_placeholder': True,
            'message': 'Personalized recommendations are being generated...',
        }

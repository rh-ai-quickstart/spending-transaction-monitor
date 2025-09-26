"""Alert Recommendation Service - Business logic for recommending alerts to users"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AlertRule, User
from src.services.alerts.agents.alert_recommender import (
    analyze_transaction_patterns,
    find_similar_users,
    recommend_alerts_for_existing_user,
    recommend_alerts_for_new_user,
)
from src.services.alerts.agents.rule_similarity_checker import check_rule_similarity
from src.services.transaction_service import TransactionService
from src.services.user_service import UserService


class AlertRecommendationService:
    """Service for generating personalized alert recommendations"""

    def __init__(self):
        self.transaction_service = TransactionService()
        self.user_service = UserService()

    async def get_recommendations(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Get personalized alert recommendations for a user"""

        user = await self.user_service.get_user(user_id, session)
        if not user:
            return {'error': 'User not found'}

        # Check if user has transaction history
        has_transactions = await self.transaction_service.user_has_transactions(
            user_id, session
        )

        # Prepare user profile
        user_profile = self._prepare_user_profile(user)

        if not has_transactions:
            # First-time user recommendations based on demographics
            result = recommend_alerts_for_new_user(user_profile)
        else:
            # Existing user recommendations based on transaction history
            transaction_data = await self._get_transaction_data(user_id, session)
            transaction_analysis = analyze_transaction_patterns(transaction_data)

            # Get similar users data for collaborative filtering
            similar_users_data = await self._get_similar_users_data(
                user_profile, session
            )

            result = recommend_alerts_for_existing_user(
                user_profile, transaction_analysis, similar_users_data
            )

        # Filter out recommendations similar to existing rules
        filtered_recommendations = await self._filter_existing_rules(
            result.get('recommendations', []), user_id, session
        )

        return {
            'user_id': user_id,
            'recommendation_type': result.get('recommendation_type', 'unknown'),
            'recommendations': filtered_recommendations,
            'generated_at': datetime.now().isoformat(),
        }

    def _prepare_user_profile(self, user: User) -> dict[str, Any]:
        """Prepare user profile data for the recommendation agent"""

        account_age_days = 0
        if user.created_at:
            # Handle timezone-aware datetime comparison
            now = (
                datetime.now(user.created_at.tzinfo)
                if user.created_at.tzinfo
                else datetime.now()
            )
            account_age_days = (now - user.created_at).days

        return {
            'user_id': user.id,
            'address_city': user.address_city,
            'address_state': user.address_state,
            'address_country': user.address_country,
            'location_consent_given': user.location_consent_given,
            'account_age_days': account_age_days,
            'credit_limit': float(user.credit_limit) if user.credit_limit else None,
            'total_credit_limit': float(user.credit_limit) if user.credit_limit else 0,
            'has_location_data': bool(
                user.last_app_location_latitude and user.last_app_location_longitude
            ),
        }

    async def _get_transaction_data(
        self, user_id: str, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get recent transaction data for analysis"""

        # Get last 90 days of transactions
        from datetime import UTC

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=90)

        transactions = await self.transaction_service.get_transactions_with_filters(
            session=session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=500,
        )

        # Convert to dictionaries for the agent
        transaction_data = []
        for t in transactions:
            transaction_data.append(
                {
                    'id': t.id,
                    'amount': float(t.amount),
                    'merchant_name': t.merchant_name,
                    'merchant_category': t.merchant_category,
                    'merchant_state': t.merchant_state,
                    'merchant_city': t.merchant_city,
                    'transaction_date': t.transaction_date.isoformat()
                    if t.transaction_date
                    else None,
                    'transaction_type': t.transaction_type.value
                    if t.transaction_type
                    else None,
                }
            )

        return transaction_data

    async def _get_similar_users_data(
        self, user_profile: dict[str, Any], session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get data about similar users for collaborative filtering"""

        # Get all users with their transaction patterns and alert rules
        users_result = await session.execute(
            select(User).where(User.id != user_profile['user_id'])
        )
        all_users = users_result.scalars().all()

        # Prepare user data with transaction analysis and alert rules
        users_data = []
        for user in all_users:
            # Get user's transactions for pattern analysis
            user_transactions = await self._get_transaction_data(user.id, session)

            if not user_transactions:  # Skip users with no transaction history
                continue

            # Analyze spending patterns
            transaction_analysis = analyze_transaction_patterns(user_transactions)

            # Get user's active alert rules
            rules_result = await session.execute(
                select(AlertRule).where(
                    and_(AlertRule.user_id == user.id, AlertRule.is_active)
                )
            )
            alert_rules = rules_result.scalars().all()

            # Convert alert rules to dict format
            alert_rules_data = []
            for rule in alert_rules:
                alert_rules_data.append(
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'natural_language_query': rule.natural_language_query,
                        'description': rule.description,
                        'trigger_count': rule.trigger_count,
                    }
                )

            # Build user profile for similarity comparison
            user_data = {
                'id': user.id,
                'address_city': user.address_city,
                'address_state': user.address_state,
                'address_country': user.address_country,
                'total_credit_limit': float(user.credit_limit)
                if user.credit_limit
                else 0,
                'top_spending_categories': [
                    cat[0] for cat in transaction_analysis.get('top_categories', [])[:5]
                ],
                'avg_transaction_amount': transaction_analysis.get('average_amount', 0),
                'alert_rules': alert_rules_data,
            }

            users_data.append(user_data)

        # Find similar users using the collaborative filtering algorithm
        similar_users = find_similar_users(user_profile, users_data)
        return similar_users

    async def _filter_existing_rules(
        self, recommendations: list[dict[str, Any]], user_id: str, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Filter out recommendations that are too similar to existing rules"""

        # Get existing active rules for the user
        result = await session.execute(
            select(AlertRule).where(
                and_(AlertRule.user_id == user_id, AlertRule.is_active)
            )
        )
        existing_rules = result.scalars().all()

        if not existing_rules:
            return recommendations

        # Extract natural language queries from existing rules
        existing_queries = set()
        for rule in existing_rules:
            if rule.natural_language_query:
                existing_queries.add(rule.natural_language_query.lower())

        # Filter recommendations - exclude exact matches and similar rules
        filtered = []
        for rec in recommendations:
            rec_query = rec.get('natural_language_query', '').lower().strip()

            # Skip if exact match exists
            if rec_query in existing_queries:
                continue

            # Skip if similar rule exists
            if not self._is_similar_to_existing(rec_query, existing_queries):
                filtered.append(rec)

        return filtered

    def _is_similar_to_existing(self, new_query: str, existing_queries: set) -> bool:
        """Enhanced similarity check using the existing similarity agent"""

        # Convert existing queries to the format expected by the similarity checker
        existing_rules = [
            {'natural_language_query': query} for query in existing_queries
        ]

        # Use the existing similarity checker agent
        similarity_result = check_rule_similarity(new_query, existing_rules)

        # Consider rules similar if similarity score is > 0.5 or explicitly marked as similar
        return (
            similarity_result.get('is_similar', False)
            or similarity_result.get('similarity_score', 0.0) > 0.5
        )

    async def get_recommendation_categories(self) -> dict[str, list[str]]:
        """Get available recommendation categories for UI purposes"""

        return {
            'fraud_protection': [
                'High transaction amounts',
                'New merchant detection',
                'Duplicate charges',
                'Unusual location activity',
            ],
            'spending_threshold': [
                'Daily spending limits',
                'Weekly spending limits',
                'Category-specific limits',
                'Large transaction alerts',
            ],
            'location_based': [
                'Out-of-state transactions',
                'International transactions',
                'Distance-based alerts',
                'Travel notifications',
            ],
            'merchant_monitoring': [
                'Recurring charge increases',
                'New merchant alerts',
                'Merchant category tracking',
                'Subscription monitoring',
            ],
            'subscription_monitoring': [
                'Price increase alerts',
                'New subscription detection',
                'Cancellation reminders',
                'Billing cycle changes',
            ],
        }

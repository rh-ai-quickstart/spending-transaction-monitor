"""
ML Recommendation Generator - Generate alert recommendations from transaction analysis

This module converts transaction analysis into specific alert recommendations
with personalized thresholds. It follows the same pattern as LLM recommendations
but uses rule-based ML logic instead of language models.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_transaction_based_recommendations(
    user_id: str, user_profile: dict, transaction_analysis: dict
) -> list[dict[str, Any]]:
    """
    Generate personalized alert recommendations based on user's transaction patterns.

    This is the ML equivalent of LLM's recommendation generation, but uses
    statistical patterns instead of language model inference.

    Args:
        user_id: User ID
        user_profile: User demographic information
        transaction_analysis: Output from analyze_user_transactions()

    Returns:
        list: Alert recommendations with personalized thresholds
    """

    recommendations = []

    # If no transactions, return new user recommendations
    if transaction_analysis['total_transactions'] == 0:
        return _generate_new_user_recommendations(user_profile)

    spending = transaction_analysis['spending_patterns']
    categories = transaction_analysis['category_behavior']
    merchants = transaction_analysis['merchant_patterns']
    locations = transaction_analysis['location_patterns']
    temporal = transaction_analysis['temporal_patterns']
    thresholds = transaction_analysis['anomaly_thresholds']

    # 1. Large transaction alert (based on user's own spending)
    if spending['mean'] > 0:
        large_tx_threshold = thresholds['single_transaction']
        recommendations.append(
            {
                'title': 'Large Transaction Alert',
                'description': f'Get notified when a single transaction exceeds ${large_tx_threshold:.2f}',
                'natural_language_query': f'Notify me when a single transaction exceeds ${large_tx_threshold:.2f}',
                'category': 'fraud_protection',
                'priority': 'high',
                'reasoning': f'Based on your spending history (avg: ${spending["mean"]:.2f}), transactions over ${large_tx_threshold:.2f} are unusual',
                'threshold_amount': large_tx_threshold,
                'confidence': 0.9,
            }
        )

    # 2. Weekly spending threshold (based on user's patterns)
    if temporal['avg_weekly_spending'] > 0:
        weekly_threshold = thresholds['weekly_spending']
        recommendations.append(
            {
                'title': 'Weekly Spending Limit Alert',
                'description': f'Get alerted when weekly spending exceeds ${weekly_threshold:.2f}',
                'natural_language_query': f'Notify me when my weekly spending exceeds ${weekly_threshold:.2f}',
                'category': 'spending_threshold',
                'priority': 'high',
                'reasoning': f'You typically spend ${temporal["avg_weekly_spending"]:.2f}/week. This helps catch unusual spending spikes.',
                'threshold_amount': weekly_threshold,
                'confidence': 0.85,
            }
        )

    # 3. Category-specific alerts (for top spending categories)
    top_categories_data = categories.get('top_categories_spending', {})
    for idx, (category, stats) in enumerate(
        list(top_categories_data.items())[:2]
    ):  # Top 2 categories
        if category in thresholds['category_thresholds']:
            cat_threshold = thresholds['category_thresholds'][category]
            priority = 'high' if idx == 0 else 'medium'

            recommendations.append(
                {
                    'title': f'{category} Spending Alert',
                    'description': f'Get notified for {category} transactions over ${cat_threshold:.2f}',
                    'natural_language_query': f'Notify me when a {category} transaction exceeds ${cat_threshold:.2f}',
                    'category': 'merchant_monitoring',
                    'priority': priority,
                    'reasoning': f'You spend frequently in {category} (avg: ${stats["mean"]:.2f}). This catches unusual purchases.',
                    'threshold_amount': cat_threshold,
                    'confidence': 0.8,
                }
            )

    # 4. Recurring charge monitoring (if subscriptions detected)
    recurring = merchants.get('recurring_merchants', {})
    subscriptions = {
        k: v for k, v in recurring.items() if v.get('is_likely_subscription')
    }

    if subscriptions:
        subscription_list = ', '.join(list(subscriptions.keys())[:3])
        recommendations.append(
            {
                'title': 'Subscription Price Change Alert',
                'description': 'Monitor subscription charges for unexpected price increases',
                'natural_language_query': 'Notify me if subscription charges change significantly',
                'category': 'subscription_monitoring',
                'priority': 'medium',
                'reasoning': f'Detected recurring charges from {subscription_list}. Monitor for price changes.',
                'confidence': 0.75,
            }
        )

    # 5. Location-based alerts (if user travels)
    if (
        locations.get('travels_frequently')
        or locations.get('out_of_state_frequency', 0) > 0.1
    ):
        home_state = locations.get('home_state', 'your home state')
        recommendations.append(
            {
                'title': 'Out-of-State Transaction Alert',
                'description': f'Get notified of transactions outside {home_state}',
                'natural_language_query': f'Notify me of transactions outside of {home_state}',
                'category': 'location_based',
                'priority': 'medium',
                'reasoning': 'You occasionally travel. This helps detect fraudulent out-of-state charges.',
                'confidence': 0.7,
            }
        )

    # 6. New merchant alert (based on merchant diversity)
    merchant_diversity = merchants.get('merchant_diversity', 0)
    if merchant_diversity > 0.3:  # User shops at many different merchants
        recommendations.append(
            {
                'title': 'New Merchant Alert',
                'description': 'Get notified when making purchases from new merchants',
                'natural_language_query': 'Notify me when I make a purchase from a merchant I have not used before',
                'category': 'fraud_protection',
                'priority': 'medium',
                'reasoning': 'You shop at various merchants. This helps detect fraudulent new merchant charges.',
                'confidence': 0.65,
            }
        )

    # 7. High transaction frequency alert
    if (
        transaction_analysis['total_transactions'] / max(temporal['weeks_with_data'], 1)
        > 10
    ):
        recommendations.append(
            {
                'title': 'Unusual Transaction Volume Alert',
                'description': 'Get notified when you have an unusually high number of transactions in a day',
                'natural_language_query': 'Notify me when I have more than 10 transactions in a single day',
                'category': 'fraud_protection',
                'priority': 'low',
                'reasoning': 'High transaction frequency can indicate card compromise.',
                'confidence': 0.6,
            }
        )

    # Sort by confidence and return top 5
    recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    return recommendations[:5]


def _generate_new_user_recommendations(user_profile: dict) -> list[dict[str, Any]]:
    """
    Generate default recommendations for new users without transaction history.

    Args:
        user_profile: User demographic information

    Returns:
        list: Default alert recommendations
    """

    has_location = user_profile.get('location_consent_given', False)

    recommendations = [
        {
            'title': 'Large Transaction Alert',
            'description': 'Get notified when a single transaction exceeds $500',
            'natural_language_query': 'Notify me when a single transaction exceeds $500',
            'category': 'fraud_protection',
            'priority': 'high',
            'reasoning': 'Protect against unauthorized large purchases',
            'threshold_amount': 500.0,
            'confidence': 0.8,
        },
        {
            'title': 'New Merchant Alert',
            'description': 'Get notified when making purchases from new merchants',
            'natural_language_query': 'Notify me when I make a purchase from a new merchant',
            'category': 'fraud_protection',
            'priority': 'high',
            'reasoning': 'Detect potentially fraudulent charges from unfamiliar merchants',
            'confidence': 0.75,
        },
        {
            'title': 'Subscription Price Increase Alert',
            'description': 'Monitor recurring charges for unexpected price increases',
            'natural_language_query': 'Notify me if any recurring charge increases by more than 10%',
            'category': 'subscription_monitoring',
            'priority': 'medium',
            'reasoning': 'Catch unexpected subscription price hikes',
            'confidence': 0.7,
        },
    ]

    # Add location-based alert if user has given location consent
    if has_location:
        state = user_profile.get('address_state', 'your home state')
        recommendations.append(
            {
                'title': 'Out-of-State Transaction Alert',
                'description': f'Get notified of transactions outside {state}',
                'natural_language_query': f'Notify me of transactions outside of {state}',
                'category': 'location_based',
                'priority': 'medium',
                'reasoning': 'Detect potentially fraudulent out-of-state transactions',
                'confidence': 0.65,
            }
        )

    return recommendations


def combine_recommendations(
    transaction_based: list[dict],
    collaborative_filtering: list[dict],
    transaction_weight: float = 0.7,
    collaborative_weight: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Combine transaction-based and collaborative filtering recommendations.

    Uses ensemble approach: prioritize transaction-based (user's own patterns)
    but supplement with collaborative filtering (similar users' choices).

    Args:
        transaction_based: Recommendations from user's transaction analysis
        collaborative_filtering: Recommendations from similar users
        transaction_weight: Weight for transaction-based recs (default: 0.7)
        collaborative_weight: Weight for collaborative recs (default: 0.3)

    Returns:
        list: Combined and ranked recommendations
    """

    # Tag sources
    for rec in transaction_based:
        rec['source'] = 'transaction_analysis'
        rec['final_score'] = rec.get('confidence', 0.5) * transaction_weight

    for rec in collaborative_filtering:
        rec['source'] = 'collaborative_filtering'
        # Collaborative recommendations have probability scores
        prob = rec.get('probability', 0.5)
        rec['final_score'] = prob * collaborative_weight

    # Combine all recommendations
    all_recs = transaction_based + collaborative_filtering

    # Remove duplicates based on similar titles
    deduplicated = _deduplicate_recommendations(all_recs)

    # Sort by final score
    deduplicated.sort(key=lambda x: x['final_score'], reverse=True)

    # Return top 6 recommendations
    return deduplicated[:6]


def _deduplicate_recommendations(recommendations: list[dict]) -> list[dict]:
    """Remove duplicate recommendations based on title similarity"""

    seen_titles = set()
    unique_recs = []

    for rec in recommendations:
        title_lower = rec['title'].lower()

        # Check for similar titles
        is_duplicate = False
        for seen in seen_titles:
            if _are_titles_similar(title_lower, seen):
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.add(title_lower)
            unique_recs.append(rec)

    return unique_recs


def _are_titles_similar(title1: str, title2: str) -> bool:
    """Check if two titles are similar enough to be considered duplicates"""

    # Simple word-based similarity
    words1 = set(title1.split())
    words2 = set(title2.split())

    # If they share 60%+ of words, consider them similar
    common_words = words1 & words2
    total_words = words1 | words2

    if not total_words:
        return False

    similarity = len(common_words) / len(total_words)
    return similarity > 0.6

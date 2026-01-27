"""Alert Recommender Agent - Generate personalized alert recommendations for users"""

from collections import Counter, defaultdict
import statistics

from .prompts import load_prompt
from .utils import clean_and_parse_json_response, get_llm_client


def recommend_alerts_for_new_user(user_profile: dict) -> dict:
    """
    Generate alert recommendations for first-time users based on demographics.

    Args:
        user_profile: User profile information including demographics

    Returns:
        dict: Recommended alerts with reasoning
    """

    prompt = load_prompt(
        'alert_recommender',
        'new_user',
        address_city=user_profile.get('address_city', 'Unknown'),
        address_state=user_profile.get('address_state', 'Unknown'),
        account_age_days=user_profile.get('account_age_days', 0),
        location_consent_given=user_profile.get('location_consent_given', False),
    )

    try:
        client = get_llm_client()
        response = client.invoke(prompt)
        content = response.content if hasattr(response, 'content') else response

        result = clean_and_parse_json_response(content)
        return result

    except Exception as e:
        print(f'Error generating new user recommendations: {e}')
        return _get_default_new_user_recommendations(user_profile)


def recommend_alerts_for_existing_user(
    user_profile: dict,
    transaction_analysis: dict,
    similar_users_data: list[dict] = None,
) -> dict:
    """
    Generate alert recommendations for existing users based on transaction history and similar users.

    Args:
        user_profile: User profile information
        transaction_analysis: Analysis of user's transaction patterns
        similar_users_data: Optional data about similar users and their alert rules

    Returns:
        dict: Recommended alerts based on spending patterns and collaborative filtering
    """

    # Format similar users data for the prompt
    similar_users_formatted = (
        _format_similar_users_data(similar_users_data)
        if similar_users_data
        else 'No similar user data available'
    )

    prompt = load_prompt(
        'alert_recommender',
        'existing_user',
        address_city=user_profile.get('address_city', 'Unknown'),
        address_state=user_profile.get('address_state', 'Unknown'),
        total_transactions=transaction_analysis.get('total_transactions', 0),
        average_amount=transaction_analysis.get('average_amount', 0),
        max_amount=transaction_analysis.get('max_amount', 0),
        top_categories=transaction_analysis.get('top_categories', []),
        avg_weekly_spending=transaction_analysis.get('avg_weekly_spending', 0),
        home_state=transaction_analysis.get('home_state', 'Unknown'),
        states_visited=transaction_analysis.get('states_visited', []),
        recurring_merchants=list(
            transaction_analysis.get('recurring_merchants', {}).keys()
        )[:3],
        category_stats=transaction_analysis.get('category_stats', {}),
        similar_users_data=similar_users_formatted,
    )

    try:
        client = get_llm_client()
        response = client.invoke(prompt)
        content = response.content if hasattr(response, 'content') else response

        result = clean_and_parse_json_response(content)
        return result

    except Exception as e:
        print(f'Error generating existing user recommendations: {e}')
        return _get_default_existing_user_recommendations(
            user_profile, transaction_analysis
        )


def analyze_transaction_patterns(transactions: list[dict]) -> dict:
    """
    Analyze transaction patterns to extract spending insights.

    Args:
        transactions: List of transaction dictionaries

    Returns:
        dict: Analysis results including spending patterns, categories, locations
    """

    if not transactions:
        return {
            'total_transactions': 0,
            'total_amount': 0,
            'average_amount': 0,
            'category_stats': {},
            'top_categories': [],
            'recurring_merchants': {},
            'home_state': None,
            'states_visited': [],
            'avg_weekly_spending': 0,
        }

    # Basic statistics
    amounts = [float(t.get('amount', 0)) for t in transactions]
    categories = [
        t.get('merchant_category') for t in transactions if t.get('merchant_category')
    ]
    merchants = [t.get('merchant_name') for t in transactions if t.get('merchant_name')]
    states = [t.get('merchant_state') for t in transactions if t.get('merchant_state')]

    # Category analysis
    category_spending = defaultdict(list)
    for t in transactions:
        category = t.get('merchant_category')
        amount = float(t.get('amount', 0))
        if category:
            category_spending[category].append(amount)

    category_stats = {}
    for category, amounts_list in category_spending.items():
        category_stats[category] = {
            'total': sum(amounts_list),
            'count': len(amounts_list),
            'average': statistics.mean(amounts_list),
            'max': max(amounts_list),
        }

    # Merchant frequency for recurring detection
    merchant_frequency = Counter(merchants)
    recurring_merchants = {
        m: count for m, count in merchant_frequency.items() if count >= 3
    }

    # Location analysis
    state_frequency = Counter(states)
    home_state = state_frequency.most_common(1)[0][0] if state_frequency else None

    # Weekly spending estimate (simplified)
    total_amount = sum(amounts)
    num_weeks = max(1, len(transactions) // 7)  # Rough estimate
    avg_weekly_spending = total_amount / num_weeks if num_weeks > 0 else total_amount

    return {
        'total_transactions': len(transactions),
        'total_amount': total_amount,
        'average_amount': statistics.mean(amounts) if amounts else 0,
        'max_amount': max(amounts) if amounts else 0,
        'category_stats': category_stats,
        'top_categories': Counter(categories).most_common(5),
        'recurring_merchants': recurring_merchants,
        'home_state': home_state,
        'states_visited': list(state_frequency.keys()),
        'avg_weekly_spending': avg_weekly_spending,
    }


def _get_default_new_user_recommendations(user_profile: dict) -> dict:
    """Fallback recommendations for new users if LLM fails"""

    state = user_profile.get('address_state', 'your home state')

    return {
        'recommendation_type': 'new_user',
        'recommendations': [
            {
                'title': 'High Transaction Alert',
                'description': 'Get notified when you spend more than $100 in a single transaction',
                'natural_language_query': 'Alert me if I spend more than $100 in one transaction',
                'category': 'fraud_protection',
                'priority': 'high',
                'reasoning': 'Helps catch unusually large purchases or potential fraud',
            },
            {
                'title': 'New Merchant Alert',
                'description': "Get notified when you're charged by a new merchant",
                'natural_language_query': "Alert me if I'm charged by a new merchant for the first time",
                'category': 'fraud_protection',
                'priority': 'medium',
                'reasoning': 'Helps identify unauthorized transactions from unknown merchants',
            },
            {
                'title': 'Out-of-State Alert',
                'description': f'Get notified for transactions outside {state}',
                'natural_language_query': f'Alert me if a transaction occurs outside {state}',
                'category': 'location_based',
                'priority': 'high',
                'reasoning': f'Helps detect potentially fraudulent activity outside {state}',
            },
            {
                'title': 'Daily Spending Limit',
                'description': 'Get notified if you spend more than $300 in one day',
                'natural_language_query': 'Alert me if I spend more than $300 in one day',
                'category': 'spending_threshold',
                'priority': 'medium',
                'reasoning': 'Helps monitor daily spending habits as a new user',
            },
        ],
    }


def _get_default_existing_user_recommendations(
    user_profile: dict, analysis: dict
) -> dict:
    """Fallback recommendations for existing users if LLM fails"""

    avg_weekly = analysis.get('avg_weekly_spending', 200)
    weekly_threshold = avg_weekly * 1.5

    return {
        'recommendation_type': 'transaction_based',
        'recommendations': [
            {
                'title': 'Weekly Spending Alert',
                'description': f'Get notified if you spend more than ${weekly_threshold:.0f} in a week',
                'natural_language_query': f'Alert me if I spend more than ${weekly_threshold:.0f} in a week',
                'category': 'spending_threshold',
                'priority': 'high',
                'reasoning': f'Based on your average weekly spending of ${avg_weekly:.0f}',
            },
            {
                'title': 'Duplicate Transaction Alert',
                'description': 'Get notified for potential duplicate charges',
                'natural_language_query': 'Alert me if the same merchant charges me twice on the same day',
                'category': 'fraud_protection',
                'priority': 'high',
                'reasoning': 'Helps catch processing errors or fraudulent duplicates',
            },
        ],
    }


def find_similar_users(user_profile: dict, all_users: list[dict]) -> list[dict]:
    """
    Find users similar to the current user based on demographics and spending patterns.

    Args:
        user_profile: Current user's profile data
        all_users: List of all user profiles with transaction data

    Returns:
        List of similar user profiles with their alert rules
    """
    similar_users = []
    current_location = (
        user_profile.get('address_city', ''),
        user_profile.get('address_state', ''),
    )

    for user in all_users:
        if user.get('id') == user_profile.get('user_id'):
            continue  # Skip the current user

        similarity_score = 0
        similarity_factors = []

        # Location similarity (same state = +30, same city = +50)
        user_location = (user.get('address_city', ''), user.get('address_state', ''))
        if (
            current_location[1] and user_location[1] == current_location[1]
        ):  # Same state
            similarity_score += 30
            similarity_factors.append(f'both in {current_location[1]}')
            if (
                current_location[0] and user_location[0] == current_location[0]
            ):  # Same city
                similarity_score += 20
                similarity_factors.append(f'both in {current_location[0]}')

        # Spending pattern similarity
        current_categories = set(user_profile.get('top_spending_categories', []))
        user_categories = set(user.get('top_spending_categories', []))
        category_overlap = len(current_categories.intersection(user_categories))
        if category_overlap > 0:
            similarity_score += category_overlap * 15
            similarity_factors.append(f'{category_overlap} shared spending categories')

        # Credit limit similarity (within 20% = +25)
        current_limit = user_profile.get('total_credit_limit', 0)
        user_limit = user.get('total_credit_limit', 0)
        if current_limit > 0 and user_limit > 0:
            limit_ratio = min(current_limit, user_limit) / max(
                current_limit, user_limit
            )
            if limit_ratio >= 0.8:  # Within 20%
                similarity_score += 25
                similarity_factors.append('similar credit limits')

        # Transaction volume similarity
        current_avg = user_profile.get('avg_transaction_amount', 0)
        user_avg = user.get('avg_transaction_amount', 0)
        if current_avg > 0 and user_avg > 0:
            avg_ratio = min(current_avg, user_avg) / max(current_avg, user_avg)
            if avg_ratio >= 0.7:  # Within 30%
                similarity_score += 20
                similarity_factors.append('similar transaction amounts')

        # Only include users with significant similarity and active alert rules
        if similarity_score >= 50 and user.get('alert_rules'):
            similar_users.append(
                {
                    'user_id': user.get('id'),
                    'similarity_score': similarity_score,
                    'similarity_factors': similarity_factors,
                    'location': user_location,
                    'alert_rules': user.get('alert_rules', []),
                    'spending_patterns': {
                        'categories': user.get('top_spending_categories', []),
                        'avg_amount': user.get('avg_transaction_amount', 0),
                        'credit_limit': user.get('total_credit_limit', 0),
                    },
                }
            )

    # Sort by similarity score and return top 5
    similar_users.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar_users[:5]


def _format_similar_users_data(similar_users: list[dict]) -> str:
    """Format similar users data for LLM prompt."""
    if not similar_users:
        return 'No similar user data available'

    formatted_data = []
    for user in similar_users:
        user_info = f"""
Similar User (Score: {user['similarity_score']}):
- Location: {user['location'][0]}, {user['location'][1]}
- Similarity factors: {', '.join(user['similarity_factors'])}
- Spending categories: {user['spending_patterns']['categories']}
- Average transaction: ${user['spending_patterns']['avg_amount']:.2f}
- Active alert rules they find helpful:"""

        for rule in user['alert_rules'][:3]:  # Show top 3 rules
            user_info += f'\n  • {rule.get("name", rule.get("natural_language_query", "Unknown rule"))}'

        formatted_data.append(user_info)

    return '\n'.join(formatted_data)

"""
ML Transaction Analyzer - Analyze user transactions to generate personalized recommendations

This module analyzes a user's transaction history to extract spending patterns,
detect anomalies, and identify opportunities for personalized alert recommendations.
It follows the same pattern as the LLM recommendation system but uses ML-based
statistical analysis instead.
"""

from collections import Counter, defaultdict
from datetime import datetime
import logging
import statistics
from typing import Any

logger = logging.getLogger(__name__)


def analyze_user_transactions(transactions: list[dict]) -> dict[str, Any]:
    """
    Analyze user's transaction history to extract spending patterns.

    This is the ML equivalent of the LLM's transaction analysis, extracting
    features that can be used to generate personalized alert recommendations.

    Args:
        transactions: List of transaction dictionaries with keys:
            - amount: float
            - merchant_name: str
            - merchant_category: str
            - merchant_state: str
            - transaction_date: datetime

    Returns:
        dict: Analysis results including:
            - spending_patterns: Statistical analysis of amounts
            - category_behavior: Spending by category
            - merchant_patterns: Recurring merchants
            - location_patterns: Geographic spending
            - temporal_patterns: Time-based spending
            - anomaly_thresholds: Suggested alert thresholds
    """

    if not transactions:
        return _get_empty_analysis()

    # Basic spending statistics
    spending_patterns = _analyze_spending_patterns(transactions)

    # Category-specific analysis
    category_behavior = _analyze_category_behavior(transactions)

    # Merchant analysis (recurring charges, etc.)
    merchant_patterns = _analyze_merchant_patterns(transactions)

    # Location patterns
    location_patterns = _analyze_location_patterns(transactions)

    # Temporal patterns (weekly, monthly)
    temporal_patterns = _analyze_temporal_patterns(transactions)

    # Calculate anomaly detection thresholds
    anomaly_thresholds = _calculate_anomaly_thresholds(
        spending_patterns, category_behavior, temporal_patterns
    )

    return {
        'total_transactions': len(transactions),
        'spending_patterns': spending_patterns,
        'category_behavior': category_behavior,
        'merchant_patterns': merchant_patterns,
        'location_patterns': location_patterns,
        'temporal_patterns': temporal_patterns,
        'anomaly_thresholds': anomaly_thresholds,
    }


def _analyze_spending_patterns(transactions: list[dict]) -> dict[str, Any]:
    """Analyze overall spending statistics"""

    amounts = [float(t.get('amount', 0)) for t in transactions]

    if not amounts:
        return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0}

    return {
        'mean': statistics.mean(amounts),
        'median': statistics.median(amounts),
        'std': statistics.stdev(amounts) if len(amounts) > 1 else 0,
        'min': min(amounts),
        'max': max(amounts),
        'total': sum(amounts),
        'percentile_75': sorted(amounts)[int(len(amounts) * 0.75)] if amounts else 0,
        'percentile_90': sorted(amounts)[int(len(amounts) * 0.90)] if amounts else 0,
        'percentile_95': sorted(amounts)[int(len(amounts) * 0.95)] if amounts else 0,
    }


def _analyze_category_behavior(transactions: list[dict]) -> dict[str, Any]:
    """Analyze spending behavior by merchant category"""

    category_spending = defaultdict(list)

    for t in transactions:
        category = t.get('merchant_category')
        amount = float(t.get('amount', 0))
        if category:
            category_spending[category].append(amount)

    category_stats = {}
    for category, amounts in category_spending.items():
        category_stats[category] = {
            'count': len(amounts),
            'total': sum(amounts),
            'mean': statistics.mean(amounts),
            'max': max(amounts),
            'frequency': len(amounts) / len(transactions) if transactions else 0,
        }

    # Get top categories by spending
    top_categories = sorted(
        category_stats.items(), key=lambda x: x[1]['total'], reverse=True
    )[:5]

    return {
        'stats_by_category': category_stats,
        'top_categories': [cat for cat, _ in top_categories],
        'top_categories_spending': {cat: stats for cat, stats in top_categories},
    }


def _analyze_merchant_patterns(transactions: list[dict]) -> dict[str, Any]:
    """Analyze merchant patterns to detect recurring charges"""

    merchant_transactions = defaultdict(list)

    for t in transactions:
        merchant = t.get('merchant_name')
        if merchant:
            merchant_transactions[merchant].append(
                {
                    'amount': float(t.get('amount', 0)),
                    'date': t.get('transaction_date'),
                }
            )

    # Identify recurring merchants (appear 3+ times)
    recurring_merchants = {}
    for merchant, txns in merchant_transactions.items():
        if len(txns) >= 3:
            amounts = [t['amount'] for t in txns]

            # Check if amounts are consistent (likely subscription)
            amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
            amount_mean = statistics.mean(amounts)

            # Consider recurring if std is small relative to mean
            is_subscription = (
                (amount_std / amount_mean) < 0.1 if amount_mean > 0 else False
            )

            recurring_merchants[merchant] = {
                'frequency': len(txns),
                'typical_amount': amount_mean,
                'amount_variability': amount_std,
                'is_likely_subscription': is_subscription,
                'amounts': amounts,
            }

    return {
        'unique_merchants': len(merchant_transactions),
        'recurring_merchants': recurring_merchants,
        'merchant_diversity': len(merchant_transactions) / len(transactions)
        if transactions
        else 0,
    }


def _analyze_location_patterns(transactions: list[dict]) -> dict[str, Any]:
    """Analyze geographic spending patterns"""

    states = [t.get('merchant_state') for t in transactions if t.get('merchant_state')]

    if not states:
        return {
            'home_state': None,
            'states_visited': [],
            'out_of_state_frequency': 0,
        }

    state_counts = Counter(states)
    most_common_state = state_counts.most_common(1)[0][0] if state_counts else None

    out_of_state_count = sum(1 for s in states if s != most_common_state)

    return {
        'home_state': most_common_state,
        'states_visited': list(state_counts.keys()),
        'state_distribution': dict(state_counts),
        'out_of_state_frequency': out_of_state_count / len(states) if states else 0,
        'travels_frequently': len(state_counts) > 3,
    }


def _analyze_temporal_patterns(transactions: list[dict]) -> dict[str, Any]:
    """Analyze time-based spending patterns"""

    # Group by week
    weekly_spending = defaultdict(float)
    monthly_spending = defaultdict(float)

    for t in transactions:
        amount = float(t.get('amount', 0))
        date = t.get('transaction_date')

        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue

        if date:
            week_key = f'{date.year}-W{date.isocalendar()[1]}'
            month_key = f'{date.year}-{date.month:02d}'

            weekly_spending[week_key] += amount
            monthly_spending[month_key] += amount

    weekly_amounts = list(weekly_spending.values())
    monthly_amounts = list(monthly_spending.values())

    return {
        'avg_weekly_spending': statistics.mean(weekly_amounts) if weekly_amounts else 0,
        'avg_monthly_spending': statistics.mean(monthly_amounts)
        if monthly_amounts
        else 0,
        'weeks_with_data': len(weekly_amounts),
        'months_with_data': len(monthly_amounts),
    }


def _calculate_anomaly_thresholds(
    spending_patterns: dict, category_behavior: dict, temporal_patterns: dict
) -> dict[str, Any]:
    """
    Calculate recommended thresholds for alert recommendations.

    Uses statistical analysis to determine appropriate thresholds
    that balance between being protective and not too noisy.
    """

    # Overall spending threshold (95th percentile or mean + 2*std)
    mean = spending_patterns.get('mean', 0)
    std = spending_patterns.get('std', 0)
    percentile_95 = spending_patterns.get('percentile_95', 0)

    single_transaction_threshold = max(
        mean + 2 * std,  # Statistical outlier
        percentile_95,  # Top 5%
        mean * 1.5,  # 50% above average
    )

    # Weekly spending threshold
    avg_weekly = temporal_patterns.get('avg_weekly_spending', 0)
    weekly_threshold = avg_weekly * 1.5 if avg_weekly > 0 else 0

    # Monthly spending threshold
    avg_monthly = temporal_patterns.get('avg_monthly_spending', 0)
    monthly_threshold = avg_monthly * 1.3 if avg_monthly > 0 else 0

    # Category-specific thresholds (for top categories)
    category_thresholds = {}
    top_categories = category_behavior.get('top_categories_spending', {})
    for category, stats in top_categories.items():
        cat_mean = stats.get('mean', 0)
        cat_max = stats.get('max', 0)
        category_thresholds[category] = max(
            cat_mean * 2,  # 2x average
            cat_max * 0.8,  # 80% of historical max
        )

    return {
        'single_transaction': round(single_transaction_threshold, 2),
        'weekly_spending': round(weekly_threshold, 2),
        'monthly_spending': round(monthly_threshold, 2),
        'category_thresholds': {k: round(v, 2) for k, v in category_thresholds.items()},
    }


def _get_empty_analysis() -> dict[str, Any]:
    """Return empty analysis for users with no transactions"""
    return {
        'total_transactions': 0,
        'spending_patterns': {
            'mean': 0,
            'median': 0,
            'std': 0,
            'min': 0,
            'max': 0,
            'total': 0,
        },
        'category_behavior': {'stats_by_category': {}, 'top_categories': []},
        'merchant_patterns': {'unique_merchants': 0, 'recurring_merchants': {}},
        'location_patterns': {'home_state': None, 'states_visited': []},
        'temporal_patterns': {'avg_weekly_spending': 0, 'avg_monthly_spending': 0},
        'anomaly_thresholds': {
            'single_transaction': 0,
            'weekly_spending': 0,
            'monthly_spending': 0,
            'category_thresholds': {},
        },
    }

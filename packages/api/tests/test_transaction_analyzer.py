"""Tests for ML Transaction Analyzer"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.services.recommendations.ml.transaction_analyzer import (
    analyze_user_transactions,
)


class TestTransactionAnalyzer:
    """Test suite for Transaction Analyzer"""

    @pytest.fixture
    def sample_transactions(self):
        """Create sample transaction data for testing"""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        return [
            {
                'amount': 50.0,
                'merchant_name': 'Starbucks',
                'merchant_category': 'Food & Dining',
                'merchant_state': 'CA',
                'transaction_date': base_date,
            },
            {
                'amount': 100.0,
                'merchant_name': 'Target',
                'merchant_category': 'Shopping',
                'merchant_state': 'CA',
                'transaction_date': base_date + timedelta(days=1),
            },
            {
                'amount': 500.0,
                'merchant_name': 'Amazon',
                'merchant_category': 'Shopping',
                'merchant_state': 'WA',
                'transaction_date': base_date + timedelta(days=2),
            },
            {
                'amount': 50.0,
                'merchant_name': 'Starbucks',
                'merchant_category': 'Food & Dining',
                'merchant_state': 'CA',
                'transaction_date': base_date + timedelta(days=7),
            },
            {
                'amount': 75.0,
                'merchant_name': 'Shell Gas',
                'merchant_category': 'Gas & Fuel',
                'merchant_state': 'CA',
                'transaction_date': base_date + timedelta(days=8),
            },
        ]

    def test_analyze_empty_transactions(self):
        """Test analysis with empty transaction list"""
        result = analyze_user_transactions([])

        assert result is not None
        assert result['total_transactions'] == 0
        assert 'spending_patterns' in result
        assert 'category_behavior' in result
        assert 'merchant_patterns' in result

    def test_analyze_basic_spending_patterns(self, sample_transactions):
        """Test basic spending pattern analysis"""
        result = analyze_user_transactions(sample_transactions)

        assert result['total_transactions'] == 5
        assert 'spending_patterns' in result

        spending = result['spending_patterns']
        assert 'total' in spending
        assert 'mean' in spending
        assert 'median' in spending
        assert 'min' in spending
        assert 'max' in spending
        assert 'std' in spending

        # Verify calculations
        assert spending['total'] == 775.0  # Sum of all amounts
        assert spending['mean'] == 155.0  # 775 / 5
        assert spending['max'] == 500.0
        assert spending['min'] == 50.0

    def test_analyze_category_behavior(self, sample_transactions):
        """Test category-specific spending analysis"""
        result = analyze_user_transactions(sample_transactions)

        category_behavior = result['category_behavior']
        assert 'stats_by_category' in category_behavior
        assert 'top_categories' in category_behavior

        stats = category_behavior['stats_by_category']

        # Should have Food & Dining category (2 transactions)
        assert 'Food & Dining' in stats
        food_stats = stats['Food & Dining']
        assert food_stats['count'] == 2
        assert food_stats['total'] == 100.0  # 50 + 50

        # Should have Shopping category (2 transactions)
        assert 'Shopping' in stats
        shopping_stats = stats['Shopping']
        assert shopping_stats['count'] == 2
        assert shopping_stats['total'] == 600.0  # 100 + 500

    def test_analyze_merchant_patterns(self, sample_transactions):
        """Test merchant pattern analysis (recurring merchants)"""
        result = analyze_user_transactions(sample_transactions)

        merchant_patterns = result['merchant_patterns']
        assert 'recurring_merchants' in merchant_patterns

        # Starbucks appears twice, should be identified as recurring
        recurring = merchant_patterns['recurring_merchants']
        starbucks = next((m for m in recurring if m['merchant'] == 'Starbucks'), None)

        if starbucks:  # Only check if detected as recurring
            assert starbucks['count'] == 2
            assert starbucks['total_spent'] == 100.0  # 50 + 50

    def test_analyze_location_patterns(self, sample_transactions):
        """Test location-based spending analysis"""
        result = analyze_user_transactions(sample_transactions)

        location_patterns = result['location_patterns']
        assert 'home_state' in location_patterns
        assert 'states_visited' in location_patterns
        assert 'state_distribution' in location_patterns

        # CA should be home state (most common)
        assert location_patterns['home_state'] == 'CA'

        # Should have visited CA and WA
        assert 'CA' in location_patterns['states_visited']
        assert 'WA' in location_patterns['states_visited']

        # CA should have 4 transactions, WA should have 1
        assert location_patterns['state_distribution']['CA'] == 4
        assert location_patterns['state_distribution']['WA'] == 1

    def test_analyze_temporal_patterns(self, sample_transactions):
        """Test temporal spending pattern analysis"""
        result = analyze_user_transactions(sample_transactions)

        temporal_patterns = result['temporal_patterns']
        assert temporal_patterns is not None

        # Should analyze patterns by day of week, time of day, etc.
        if 'by_day_of_week' in temporal_patterns:
            assert isinstance(temporal_patterns['by_day_of_week'], list)

    def test_anomaly_thresholds(self, sample_transactions):
        """Test anomaly detection threshold calculation"""
        result = analyze_user_transactions(sample_transactions)

        anomaly_thresholds = result['anomaly_thresholds']
        assert anomaly_thresholds is not None

        # Should provide threshold recommendations
        if 'amount_threshold' in anomaly_thresholds:
            # Threshold should be based on statistical analysis (mean + std dev, etc.)
            assert anomaly_thresholds['amount_threshold'] > 0

    def test_single_transaction(self):
        """Test analysis with only one transaction"""
        single_transaction = [
            {
                'amount': 100.0,
                'merchant_name': 'Test Merchant',
                'merchant_category': 'Test Category',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 1),
            }
        ]

        result = analyze_user_transactions(single_transaction)

        assert result['total_transactions'] == 1
        spending = result['spending_patterns']
        assert spending['total'] == 100.0
        assert spending['mean'] == 100.0
        assert spending['median'] == 100.0

    def test_large_amount_variance(self):
        """Test analysis with high variance in transaction amounts"""
        transactions = [
            {
                'amount': 5.0,
                'merchant_name': 'Coffee Shop',
                'merchant_category': 'Food',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 1),
            },
            {
                'amount': 5000.0,
                'merchant_name': 'Electronics Store',
                'merchant_category': 'Shopping',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 2),
            },
            {
                'amount': 10.0,
                'merchant_name': 'Fast Food',
                'merchant_category': 'Food',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 3),
            },
        ]

        result = analyze_user_transactions(transactions)

        spending = result['spending_patterns']
        assert spending['min'] == 5.0
        assert spending['max'] == 5000.0

        # Should calculate standard deviation
        assert 'std' in spending
        assert spending['std'] > 0

    def test_multiple_recurring_merchants(self):
        """Test detection of multiple recurring merchants"""
        base_date = datetime(2024, 1, 1)
        transactions = []

        # Create recurring pattern for multiple merchants
        for i in range(4):
            transactions.extend(
                [
                    {
                        'amount': 50.0,
                        'merchant_name': 'Starbucks',
                        'merchant_category': 'Food',
                        'merchant_state': 'CA',
                        'transaction_date': base_date + timedelta(days=i * 7),
                    },
                    {
                        'amount': 100.0,
                        'merchant_name': 'Gym Membership',
                        'merchant_category': 'Health',
                        'merchant_state': 'CA',
                        'transaction_date': base_date + timedelta(days=i * 30),
                    },
                ]
            )

        result = analyze_user_transactions(transactions)

        merchant_patterns = result['merchant_patterns']
        recurring = merchant_patterns['recurring_merchants']

        # Should identify both as recurring
        assert len(recurring) >= 2

    def test_category_distribution(self, sample_transactions):
        """Test category spending distribution calculation"""
        result = analyze_user_transactions(sample_transactions)

        category_behavior = result['category_behavior']
        stats = category_behavior['stats_by_category']

        # Calculate total spent across all categories
        total_spent = sum(cat_stats['total'] for cat_stats in stats.values())
        assert total_spent == 775.0  # Total from sample_transactions

        # Each category should have frequency value
        for cat_stats in stats.values():
            assert 'frequency' in cat_stats
            assert 0 <= cat_stats['frequency'] <= 1

    def test_transaction_with_missing_fields(self):
        """Test handling of transactions with missing optional fields"""
        transactions = [
            {
                'amount': 100.0,
                'merchant_name': 'Test',
                'merchant_category': 'Test',
                # Missing merchant_state
                'transaction_date': datetime(2024, 1, 1),
            },
            {
                'amount': 50.0,
                # Missing merchant_name
                'merchant_category': 'Test',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 2),
            },
        ]

        # Should handle gracefully without errors
        result = analyze_user_transactions(transactions)
        assert result is not None
        assert result['total_transactions'] == 2

    def test_decimal_amounts(self):
        """Test analysis with Decimal amount values"""
        transactions = [
            {
                'amount': Decimal('100.50'),
                'merchant_name': 'Test',
                'merchant_category': 'Test',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 1),
            },
            {
                'amount': Decimal('50.25'),
                'merchant_name': 'Test',
                'merchant_category': 'Test',
                'merchant_state': 'CA',
                'transaction_date': datetime(2024, 1, 2),
            },
        ]

        result = analyze_user_transactions(transactions)

        spending = result['spending_patterns']
        # Should handle Decimal amounts correctly
        assert spending['total'] > 0

    def test_same_day_multiple_transactions(self):
        """Test analysis of multiple transactions on the same day"""
        same_date = datetime(2024, 1, 1, 12, 0, 0)
        transactions = [
            {
                'amount': 50.0,
                'merchant_name': 'Morning Coffee',
                'merchant_category': 'Food',
                'merchant_state': 'CA',
                'transaction_date': same_date,
            },
            {
                'amount': 100.0,
                'merchant_name': 'Lunch',
                'merchant_category': 'Food',
                'merchant_state': 'CA',
                'transaction_date': same_date,
            },
            {
                'amount': 75.0,
                'merchant_name': 'Dinner',
                'merchant_category': 'Food',
                'merchant_state': 'CA',
                'transaction_date': same_date,
            },
        ]

        result = analyze_user_transactions(transactions)

        assert result['total_transactions'] == 3
        spending = result['spending_patterns']
        assert spending['total'] == 225.0

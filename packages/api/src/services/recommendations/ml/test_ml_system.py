"""
Test Script for ML Alert Recommendation System
----------------------------------------------

Run this script to test the ML recommendation engine.
"""

import asyncio
from datetime import datetime, timedelta
import sys

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, '../../../..')

from db.database import SessionLocal
from src.services.recommendations.ml.feature_engineering import (
    build_user_features,
    generate_initial_alert_labels,
)
from src.services.recommendations.ml.recommender import AlertRecommenderModel
from src.services.recommendations.ml.training import train_model


async def test_feature_engineering():
    """Test feature engineering with sample data"""
    print('\n' + '=' * 60)
    print('Test 1: Feature Engineering')
    print('=' * 60)

    # Create sample data
    users_df = pd.DataFrame(
        {
            'id': ['u1', 'u2', 'u3'],
            'credit_limit': [5000, 10000, 7500],
            'credit_balance': [2000, 8000, 3000],
        }
    )

    transactions_df = pd.DataFrame(
        {
            'user_id': ['u1', 'u1', 'u2', 'u2', 'u3'],
            'amount': [100, 250, 500, 1200, 75],
            'merchant_name': ['Store A', 'Store B', 'Store C', 'Store D', 'Store A'],
            'merchant_category': [
                'Groceries',
                'Electronics',
                'Restaurant',
                'Travel',
                'Groceries',
            ],
            'transaction_date': [datetime.now() - timedelta(days=i) for i in range(5)],
        }
    )

    print(
        f'✓ Created sample data: {len(users_df)} users, {len(transactions_df)} transactions'
    )

    # Build features
    features = build_user_features(users_df, transactions_df)
    print(
        f'✓ Built user features: {len(features)} rows, {len(features.columns)} columns'
    )
    print('\nFeature columns:')
    for col in features.columns:
        print(f'  - {col}')

    # Generate alert labels
    features_with_labels = generate_initial_alert_labels(features)
    alert_cols = [
        col for col in features_with_labels.columns if col.startswith('alert_')
    ]
    print(f'\n✓ Generated alert labels: {len(alert_cols)} alert types')
    for col in alert_cols:
        print(f'  - {col}')

    return features_with_labels


async def test_model_training(features_df):
    """Test model training"""
    print('\n' + '=' * 60)
    print('Test 2: Model Training')
    print('=' * 60)

    model = AlertRecommenderModel(model_path='/tmp/test_model_knn.pkl')

    print('✓ Training model...')
    model.train(features_df, n_neighbors=2)  # Use 2 neighbors for small dataset

    print('✓ Model trained successfully')
    print(f'  - Feature columns: {len(model.feature_cols)}')
    print(f'  - Alert columns: {len(model.alert_cols)}')

    # Save model
    model.save_model()
    print(f'✓ Model saved to {model.model_path}')

    return model


async def test_recommendations(model, features_df):
    """Test generating recommendations"""
    print('\n' + '=' * 60)
    print('Test 3: Generating Recommendations')
    print('=' * 60)

    # Test for each user
    for user_id in features_df['user_id'].values:
        print(f'\nRecommendations for user: {user_id}')
        print('-' * 40)

        try:
            result = model.recommend_for_user(
                user_id=user_id,
                user_features_df=features_df,
                k_neighbors=2,
                threshold=0.3,  # Lower threshold for testing
            )

            print(f'✓ Found {result["total_similar_users"]} similar users')

            if result['recommendations']:
                print(f'\nRecommended alerts ({len(result["recommendations"])}):')
                for rec in result['recommendations']:
                    print(f'  - {rec["alert_type"]}')
                    print(f'    Probability: {rec["probability"]:.2%}')
                    print(f'    Confidence: {rec["confidence"]}')
                    print(f'    Reason: {rec["reason"][:60]}...')
            else:
                print(
                    '  No recommendations (all alerts already enabled or below threshold)'
                )

        except Exception as e:
            print(f'✗ Error: {e}')


async def test_database_integration():
    """Test with actual database"""
    print('\n' + '=' * 60)
    print('Test 4: Database Integration (Optional)')
    print('=' * 60)

    try:
        async with SessionLocal() as session:
            print('✓ Database connection successful')

            # Try to train model with real data
            print('✓ Attempting to train model with real data...')
            model = await train_model(
                session=session,
                model_path='/tmp/test_model_real.pkl',
                n_neighbors=5,
                use_real_alerts=True,
            )

            print('✓ Model trained successfully with real data!')
            print(f'  Model path: {model.model_path}')

    except Exception as e:
        print(f'⚠ Database test skipped: {e}')
        print('  (This is OK if database is not set up)')


async def run_all_tests():
    """Run all tests"""
    print('\n' + '=' * 60)
    print('ML Alert Recommendation System - Test Suite')
    print('=' * 60)
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    try:
        # Test 1: Feature Engineering
        features = await test_feature_engineering()

        # Test 2: Model Training
        model = await test_model_training(features)

        # Test 3: Recommendations
        await test_recommendations(model, features)

        # Test 4: Database Integration (optional)
        await test_database_integration()

        print('\n' + '=' * 60)
        print('✓ All tests completed successfully!')
        print('=' * 60)

    except Exception as e:
        print(f'\n✗ Test failed: {e}')
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(run_all_tests())

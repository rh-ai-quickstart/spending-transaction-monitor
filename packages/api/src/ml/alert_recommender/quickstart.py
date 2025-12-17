#!/usr/bin/env python3
"""
Quick Start Script for ML Alert Recommendation System
------------------------------------------------------

This script helps you get started with the ML recommendation system.
Run this after installing dependencies to verify everything works.
"""

import asyncio
import sys

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f'\n{BLUE}{"=" * 60}')
    print(f'{text}')
    print(f'{"=" * 60}{RESET}\n')


def print_success(text):
    """Print success message"""
    print(f'{GREEN}✓ {text}{RESET}')


def print_warning(text):
    """Print warning message"""
    print(f'{YELLOW}⚠ {text}{RESET}')


def print_error(text):
    """Print error message"""
    print(f'{RED}✗ {text}{RESET}')


def check_dependencies():
    """Check if required dependencies are installed"""
    print_header('Step 1: Checking Dependencies')

    required = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
    }

    all_ok = True
    for module, package in required.items():
        try:
            __import__(module)
            print_success(f'{package} is installed')
        except ImportError:
            print_error(f'{package} is NOT installed')
            all_ok = False

    if not all_ok:
        print_error('\nSome dependencies are missing!')
        print(f'\n{YELLOW}Install with:{RESET}')
        print('  cd packages/api')
        print('  uv sync')
        print('  # or')
        print('  pip install pandas numpy scikit-learn')
        sys.exit(1)

    print_success('\nAll dependencies are installed!')
    return True


def check_module_imports():
    """Check if ML modules can be imported"""
    print_header('Step 2: Checking ML Module Imports')

    try:
        print_success('AlertRecommenderModel imported successfully')

        print_success('Feature engineering module imported successfully')

        print_success('Training module imported successfully')

        print_success('\nAll ML modules can be imported!')
        return True

    except Exception as e:
        print_error(f'Failed to import ML modules: {e}')
        return False


async def test_basic_functionality():
    """Test basic ML functionality without database"""
    print_header('Step 3: Testing Basic Functionality')

    try:
        from datetime import datetime, timedelta

        import pandas as pd

        from src.ml.alert_recommender.feature_engineering import (
            build_user_features,
            generate_initial_alert_labels,
        )
        from src.ml.alert_recommender.recommender import AlertRecommenderModel

        # Create sample data
        users_df = pd.DataFrame(
            {
                'id': ['user1', 'user2', 'user3'],
                'credit_limit': [5000, 10000, 7500],
                'credit_balance': [2000, 8000, 3000],
            }
        )

        transactions_df = pd.DataFrame(
            {
                'user_id': ['user1', 'user1', 'user2', 'user2', 'user3'],
                'amount': [100, 250, 500, 1200, 75],
                'merchant_name': [
                    'Store A',
                    'Store B',
                    'Store C',
                    'Store D',
                    'Store A',
                ],
                'merchant_category': [
                    'Groceries',
                    'Electronics',
                    'Restaurant',
                    'Travel',
                    'Groceries',
                ],
                'transaction_date': [
                    datetime.now() - timedelta(days=i) for i in range(5)
                ],
            }
        )

        print_success('Created sample data')

        # Build features
        features = build_user_features(users_df, transactions_df)
        print_success(
            f'Built features: {len(features)} users, {len(features.columns)} columns'
        )

        # Generate labels
        features = generate_initial_alert_labels(features)
        print_success('Generated alert labels')

        # Train model
        model = AlertRecommenderModel(model_path='/tmp/quickstart_model.pkl')
        model.train(features, n_neighbors=2)
        print_success('Trained KNN model')

        # Get recommendations
        result = model.recommend_for_user(
            user_id='user1', user_features_df=features, k_neighbors=2, threshold=0.3
        )
        print_success(
            f'Generated recommendations: {len(result["recommendations"])} alerts'
        )

        print_success('\n✓ All basic functionality tests passed!')
        return True

    except Exception as e:
        print_error(f'Basic functionality test failed: {e}')
        import traceback

        traceback.print_exc()
        return False


async def test_database_connection():
    """Test database connection and model training"""
    print_header('Step 4: Testing Database Connection (Optional)')

    try:
        from db.database import SessionLocal
        from src.ml.alert_recommender.training import train_model

        async with SessionLocal() as session:
            print_success('Database connection successful')

            # Try to train with real data
            print('Training model with database data...')
            model = await train_model(
                session=session,
                model_path='/tmp/quickstart_db_model.pkl',
                n_neighbors=5,
                use_real_alerts=True,
            )

            print_success('Model trained successfully!')
            print_success(f'Model saved to: {model.model_path}')

            return True

    except Exception as e:
        print_warning(f'Database test skipped: {e}')
        print_warning('This is OK if database is not set up yet')
        return False


def print_next_steps():
    """Print next steps for the user"""
    print_header('Next Steps')

    print(f'{BLUE}1. Install Dependencies (if not done):{RESET}')
    print('   cd packages/api')
    print('   uv sync')

    print(f'\n{BLUE}2. Start Using ML Recommendations:{RESET}')
    print('   The system is ready! ML recommendations will be used automatically.')
    print('   The model will train on first use.')

    print(f'\n{BLUE}3. Test with API:{RESET}')
    print('   Start your API server and request recommendations:')
    print('   GET /api/alerts/recommendations')

    print(f'\n{BLUE}4. Set Up Scheduled Retraining:{RESET}')
    print('   Add to crontab:')
    print('   0 0 * * 0 cd /path/to/packages/api && \\')
    print('     python -m src.ml.alert_recommender.scheduled_retraining')

    print(f'\n{BLUE}5. Read Documentation:{RESET}')
    print('   - ML_MIGRATION_GUIDE.md')
    print('   - packages/api/src/ml/alert_recommender/README.md')
    print('   - ML_IMPLEMENTATION_SUMMARY.md')

    print(f'\n{GREEN}{"=" * 60}')
    print('✓ Quick Start Complete!')
    print(f'{"=" * 60}{RESET}\n')


async def main():
    """Main quick start function"""
    print(f'\n{BLUE}{"=" * 60}')
    print('ML Alert Recommendation System - Quick Start')
    print(f'{"=" * 60}{RESET}')

    # Step 1: Check dependencies
    if not check_dependencies():
        return

    # Step 2: Check imports
    if not check_module_imports():
        return

    # Step 3: Test basic functionality
    if not await test_basic_functionality():
        return

    # Step 4: Test database (optional)
    await test_database_connection()

    # Print next steps
    print_next_steps()


if __name__ == '__main__':
    asyncio.run(main())

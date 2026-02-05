"""
Reset database script - Delete all rows from all tables
"""

import asyncio
import os
import sys

from sqlalchemy import text

# Add the parent directory to sys.path to make imports work
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from db.database import SessionLocal


async def reset_database() -> None:
    """
    Reset database by deleting all rows from all tables.
    Deletes in order to respect foreign key constraints.
    """
    print('🔄 Starting database reset...')

    async with SessionLocal() as session:
        try:
            # Use TRUNCATE CASCADE for reliable cleanup regardless of FK order
            # This is faster and handles all dependent tables automatically
            print('🗑️  Truncating all tables with CASCADE...')
            await session.execute(
                text(
                    """
                TRUNCATE TABLE 
                    cached_recommendations,
                    alert_notifications,
                    alert_rules,
                    transactions,
                    credit_cards,
                    users
                CASCADE
                """
                )
            )

            # Commit all deletions
            await session.commit()

            # Verify tables are empty
            print('\n📊 Verifying reset...')
            tables = [
                'users',
                'credit_cards',
                'transactions',
                'alert_rules',
                'alert_notifications',
            ]

            for table in tables:
                result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
                count = result.scalar()
                print(f'  {table}: {count} rows')

            print('\n✅ Database reset completed successfully!')

        except Exception as e:
            print(f'❌ Error during database reset: {e}')
            await session.rollback()
            raise
        finally:
            await session.close()


if __name__ == '__main__':
    asyncio.run(reset_database())

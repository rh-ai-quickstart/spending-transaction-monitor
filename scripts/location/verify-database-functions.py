#!/usr/bin/env python3
"""
Quick database verification script to test location functions
"""

import asyncio
import sys
import os

# Add the packages to the path (scripts are now in scripts/location/)
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(os.path.join(project_root, 'packages', 'api', 'src'))
sys.path.append(os.path.join(project_root, 'packages', 'db', 'src'))

try:
    from db.database import engine
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError as e:
    print(f"❌ Database imports not available: {e}")
    print("Run this script from the project root with: cd packages/api && uv run python ../../scripts/location/verify-database-functions.py")
    sys.exit(1)

async def test_distance_function():
    """Test the haversine_distance_km function directly"""
    
    async with AsyncSession(engine) as session:
        # Test distance calculation: NYC to LA
        ny_lat, ny_lon = 40.7128, -74.0060  # New York
        la_lat, la_lon = 34.0522, -118.2437  # Los Angeles
        
        query = text("""
            SELECT haversine_distance_km(:lat1, :lon1, :lat2, :lon2) as distance_km
        """)
        
        result = await session.execute(query, {
            "lat1": ny_lat, "lon1": ny_lon,
            "lat2": la_lat, "lon2": la_lon
        })
        
        distance = result.scalar()
        print(f"✅ Distance NYC to LA: {distance:.1f} km (expected ~3944 km)")
        
        # Test Brooklyn to NYC (should be short distance)
        brooklyn_lat, brooklyn_lon = 40.6782, -73.9442  # Brooklyn
        
        query2 = text("""
            SELECT haversine_distance_km(:lat1, :lon1, :lat2, :lon2) as distance_km
        """)
        
        result2 = await session.execute(query2, {
            "lat1": ny_lat, "lon1": ny_lon,
            "lat2": brooklyn_lat, "lon2": brooklyn_lon
        })
        
        distance2 = result2.scalar()
        print(f"✅ Distance NYC to Brooklyn: {distance2:.1f} km (expected ~13 km)")

async def test_transaction_location_view():
    """Test the transaction_location_analysis view"""
    
    async with AsyncSession(engine) as session:
        query = text("""
            SELECT 
                transaction_id,
                merchant_name,
                distance_km,
                risk_level,
                user_lat,
                user_lon,
                merchant_lat,
                merchant_lon
            FROM transaction_location_analysis 
            ORDER BY transaction_date DESC 
            LIMIT 5
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        print(f"\n📊 Recent Transactions with Location Analysis:")
        print("-" * 80)
        
        if rows:
            for row in rows:
                print(f"Transaction: {row.merchant_name}")
                print(f"  Distance: {row.distance_km:.1f} km" if row.distance_km else "  Distance: N/A")
                print(f"  Risk Level: {row.risk_level}")
                print(f"  User Location: ({row.user_lat}, {row.user_lon})" if row.user_lat else "  User Location: N/A")
                print(f"  Merchant Location: ({row.merchant_lat}, {row.merchant_lon})")
                print()
        else:
            print("No transaction data with location analysis found")

async def test_user_location_data():
    """Check if user location data is being stored"""
    
    async with AsyncSession(engine) as session:
        query = text("""
            SELECT 
                id,
                email,
                last_app_location_latitude,
                last_app_location_longitude,
                last_app_location_timestamp,
                location_consent_given
            FROM users 
            WHERE last_app_location_latitude IS NOT NULL
            OR location_consent_given = true
            LIMIT 3
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        print(f"👤 Users with Location Data:")
        print("-" * 50)
        
        if rows:
            for row in rows:
                print(f"User: {row.email}")
                if row.last_app_location_latitude:
                    print(f"  Location: ({row.last_app_location_latitude}, {row.last_app_location_longitude})")
                    print(f"  Timestamp: {row.last_app_location_timestamp}")
                else:
                    print(f"  Location: Not captured")
                print(f"  Consent: {row.location_consent_given}")
                print()
        else:
            print("No users with location data found")

async def main():
    """Run all database verification tests"""
    print("🔍 Database Location Functions Verification")
    print("=" * 50)
    
    try:
        await test_distance_function()
        await test_transaction_location_view() 
        await test_user_location_data()
        
        print("✅ Database verification complete!")
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Mock Alert Rule Creator - Bypasses LLM for testing location-based fraud detection
Creates hardcoded SQL rules for location-based alerts
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8002"
HEADERS = {"Content-Type": "application/json"}

def create_mock_location_alert_rule(user_id: str, distance_threshold: int = 500):
    """Create a location-based alert rule with pre-generated SQL (no LLM needed)"""
    
    # Pre-generated SQL for location-based fraud detection
    sql_query = f"""
    SELECT 
        t.id as transaction_id,
        t.user_id,
        t.amount,
        t.merchant_name,
        t.merchant_city,
        t.merchant_state,
        t.transaction_date,
        u.email,
        haversine_distance_km(
            u.last_app_location_latitude, 
            u.last_app_location_longitude,
            t.merchant_latitude, 
            t.merchant_longitude
        ) as distance_km
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    WHERE 
        t.user_id = '{user_id}'
        AND u.location_consent_given = true
        AND u.last_app_location_latitude IS NOT NULL
        AND u.last_app_location_longitude IS NOT NULL
        AND t.merchant_latitude IS NOT NULL
        AND t.merchant_longitude IS NOT NULL
        AND haversine_distance_km(
            u.last_app_location_latitude, 
            u.last_app_location_longitude,
            t.merchant_latitude, 
            t.merchant_longitude
        ) > {distance_threshold}
        AND t.transaction_date = (
            SELECT MAX(transaction_date) 
            FROM transactions 
            WHERE user_id = '{user_id}'
        )
    """
    
    # Create alert rule data with pre-generated SQL
    alert_rule_data = {
        "id": f"mock-location-rule-{int(datetime.now().timestamp())}",
        "user_id": user_id,
        "name": f"Location Fraud Alert - {distance_threshold}km",
        "description": f"Alert for transactions more than {distance_threshold}km from user location",
        "alert_type": "LOCATION_BASED",
        "is_active": True,
        "sql_query": sql_query,
        "natural_language_query": f"Alert me for transactions more than {distance_threshold}km from my location",
        "amount_threshold": 0.0,
        "merchant_category": "",
        "merchant_name": "",
        "location": f">{distance_threshold}km",
        "timeframe": "real-time",
        "notification_methods": ["EMAIL"],
        "trigger_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return alert_rule_data

def insert_mock_alert_rule_directly(user_id: str, distance_threshold: int = 500):
    """Insert alert rule directly into database (bypassing API validation)"""
    try:
        # This would require direct database access
        # For now, let's return the SQL we would use
        
        rule_data = create_mock_location_alert_rule(user_id, distance_threshold)
        
        insert_sql = f"""
        INSERT INTO alert_rules (
            id, user_id, name, description, alert_type, is_active, 
            sql_query, natural_language_query, amount_threshold,
            merchant_category, merchant_name, location, timeframe,
            notification_methods, trigger_count, created_at, updated_at
        ) VALUES (
            '{rule_data["id"]}',
            '{rule_data["user_id"]}',
            '{rule_data["name"]}',
            '{rule_data["description"]}',
            '{rule_data["alert_type"]}',
            {rule_data["is_active"]},
            $${rule_data["sql_query"]}$$,
            '{rule_data["natural_language_query"]}',
            {rule_data["amount_threshold"]},
            '{rule_data["merchant_category"]}',
            '{rule_data["merchant_name"]}',
            '{rule_data["location"]}',
            '{rule_data["timeframe"]}',
            ARRAY{rule_data["notification_methods"]},
            {rule_data["trigger_count"]},
            '{rule_data["created_at"]}',
            '{rule_data["updated_at"]}'
        );
        """
        
        print("🛠️ Mock Alert Rule Generated")
        print("=" * 50)
        print("To test location-based fraud detection without LLM:")
        print("\n1. **Pre-generated SQL Query:**")
        print(rule_data["sql_query"])
        print("\n2. **Direct Database Insert SQL:**")
        print(insert_sql)
        print("\n3. **Rule Details:**")
        print(json.dumps(rule_data, indent=2)[:500] + "...")
        
        return rule_data, insert_sql
        
    except Exception as e:
        print(f"❌ Failed to create mock rule: {e}")
        return None, None

def test_sql_query_directly(user_id: str, distance_threshold: int = 500):
    """Test the location SQL query directly against the database"""
    
    sql_query = f"""
    SELECT 
        t.id as transaction_id,
        t.merchant_name,
        t.amount,
        t.merchant_city,
        t.merchant_state,
        haversine_distance_km(
            u.last_app_location_latitude, 
            u.last_app_location_longitude,
            t.merchant_latitude, 
            t.merchant_longitude
        ) as distance_km,
        u.email,
        u.last_app_location_latitude as user_lat,
        u.last_app_location_longitude as user_lon,
        t.merchant_latitude,
        t.merchant_longitude
    FROM transactions t
    JOIN users u ON t.user_id = u.id
    WHERE 
        t.user_id = '{user_id}'
        AND u.location_consent_given = true
        AND u.last_app_location_latitude IS NOT NULL
        AND u.last_app_location_longitude IS NOT NULL
        AND t.merchant_latitude IS NOT NULL
        AND t.merchant_longitude IS NOT NULL
        AND haversine_distance_km(
            u.last_app_location_latitude, 
            u.last_app_location_longitude,
            t.merchant_latitude, 
            t.merchant_longitude
        ) > {distance_threshold}
    ORDER BY t.transaction_date DESC
    LIMIT 5;
    """
    
    print("📊 SQL Query to Test Location-Based Fraud Detection:")
    print("=" * 60)
    print(sql_query)
    print("\n💡 To test this:")
    print("1. Copy the SQL above")
    print("2. Run it against your PostgreSQL database")
    print("3. It will show transactions that exceed the distance threshold")
    print(f"4. Current threshold: {distance_threshold}km from user's last location")
    
    return sql_query

def main():
    """Demonstrate mock alert rule creation"""
    print("🧪 Mock Location-Based Alert Rules (No LLM Required)")
    print("=" * 60)
    
    # Get user ID (you can customize this)
    user_id = "1c85902a-9ef1-45ed-928d-7aa1d7ec2fe8"  # From our tests
    
    print(f"📍 Creating mock alert rules for user: {user_id}")
    print()
    
    # Test different distance thresholds
    for threshold in [100, 500, 1000]:
        print(f"\n🎯 Testing {threshold}km threshold:")
        print("-" * 40)
        
        # Generate mock rule
        rule_data, insert_sql = insert_mock_alert_rule_directly(user_id, threshold)
        
        # Generate test SQL
        test_sql = test_sql_query_directly(user_id, threshold)
        
        print()

if __name__ == "__main__":
    main()

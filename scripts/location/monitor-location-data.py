#!/usr/bin/env python3
"""
Real-time location data monitor for manual E2E testing
Run this while testing in the browser to see location updates
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "http://localhost:8002"
HEADERS = {"Content-Type": "application/json"}

def clear_screen():
    """Clear terminal screen"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def monitor_user_location(user_id: str, interval: int = 2):
    """Monitor user location data in real-time"""
    
    print("🔄 REAL-TIME LOCATION MONITOR")
    print("=" * 80)
    print("🌐 Frontend: http://localhost:3000")
    print("🚀 Backend:  http://localhost:8002")
    print(f"👤 User ID:  {user_id}")
    print("=" * 80)
    print("💡 Instructions:")
    print("   1. Open frontend in browser")
    print("   2. Look for location consent dialog")  
    print("   3. Grant location permission")
    print("   4. Watch this monitor for updates!")
    print("=" * 80)
    print("⏱️  Monitoring every {} seconds... (Ctrl+C to stop)".format(interval))
    print()
    
    last_location = None
    last_consent = None
    last_timestamp = None
    
    try:
        while True:
            try:
                # Get current user data
                response = requests.get(f"{API_BASE_URL}/users/{user_id}", timeout=5)
                
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Extract location data
                    current_consent = user_data.get("location_consent_given")
                    current_lat = user_data.get("last_app_location_latitude")
                    current_lng = user_data.get("last_app_location_longitude")
                    current_timestamp = user_data.get("last_app_location_timestamp")
                    current_accuracy = user_data.get("last_app_location_accuracy")
                    
                    # Check for changes
                    location_changed = (current_lat != last_location or 
                                      current_consent != last_consent or
                                      current_timestamp != last_timestamp)
                    
                    if location_changed:
                        print(f"\n🔄 {datetime.now().strftime('%H:%M:%S')} - LOCATION UPDATE DETECTED!")
                        print("─" * 60)
                        
                        # Consent status
                        if current_consent != last_consent:
                            consent_emoji = "✅" if current_consent else ("❌" if current_consent is False else "⚪")
                            print(f"🔐 Consent: {consent_emoji} {current_consent}")
                            
                        # Location coordinates  
                        if (current_lat, current_lng) != last_location:
                            if current_lat is not None and current_lng is not None:
                                print(f"📍 Location: {current_lat:.6f}, {current_lng:.6f}")
                                if current_accuracy:
                                    print(f"📏 Accuracy: {current_accuracy} meters")
                                    
                                # Reverse geocode estimate (very rough)
                                if 40.0 < current_lat < 41.0 and -75.0 < current_lng < -73.0:
                                    print("🗽 Estimated: New York City area")
                                elif 37.0 < current_lat < 38.0 and -123.0 < current_lng < -121.0:
                                    print("🌉 Estimated: San Francisco Bay area")
                                elif 34.0 < current_lat < 35.0 and -119.0 < current_lng < -117.0:
                                    print("🌴 Estimated: Los Angeles area")
                                else:
                                    print(f"🌍 Coordinates: {current_lat:.4f}°N, {abs(current_lng):.4f}°W")
                            else:
                                print("📍 Location: Not set")
                        
                        # Timestamp
                        if current_timestamp != last_timestamp:
                            if current_timestamp:
                                print(f"🕒 Updated: {current_timestamp}")
                            else:
                                print("🕒 Updated: Never")
                                
                        print("─" * 60)
                        
                        # Update tracking variables
                        last_consent = current_consent
                        last_location = (current_lat, current_lng)
                        last_timestamp = current_timestamp
                        
                    else:
                        # No changes - show a simple status line
                        status_emoji = "✅" if current_consent else ("❌" if current_consent is False else "⏸️")
                        location_status = f"{current_lat:.4f}, {current_lng:.4f}" if current_lat else "No location"
                        print(f"\r{status_emoji} {datetime.now().strftime('%H:%M:%S')} - Monitoring... | Consent: {current_consent} | Location: {location_status}", end="", flush=True)
                        
                else:
                    print(f"\n❌ {datetime.now().strftime('%H:%M:%S')} - API Error: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"\n🔌 {datetime.now().strftime('%H:%M:%S')} - Connection Error: {e}")
                
            except Exception as e:
                print(f"\n💥 {datetime.now().strftime('%H:%M:%S')} - Unexpected Error: {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        
        # Show final state
        try:
            response = requests.get(f"{API_BASE_URL}/users/{user_id}")
            if response.status_code == 200:
                final_data = response.json()
                print("\n📊 FINAL LOCATION STATE:")
                print(f"   Consent: {final_data.get('location_consent_given')}")
                print(f"   Location: {final_data.get('last_app_location_latitude')}, {final_data.get('last_app_location_longitude')}")
                print(f"   Timestamp: {final_data.get('last_app_location_timestamp')}")
        except:
            pass

if __name__ == "__main__":
    # Use the actual database user ID (auth bypass uses first user in DB)
    user_id = "1c85902a-9ef1-45ed-928d-7aa1d7ec2fe8"
    monitor_user_location(user_id)

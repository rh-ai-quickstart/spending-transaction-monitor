"""
Location services for fraud detection
Provides distance calculation and offline geocoding capabilities
"""

import logging
import math

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth in kilometers
    Uses the Haversine formula for offline distance calculation

    Args:
        lat1, lon1: Latitude and longitude of first point (in decimal degrees)
        lat2, lon2: Latitude and longitude of second point (in decimal degrees)

    Returns:
        Distance between the two points in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371

    return c * r


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate GPS coordinates are within valid ranges

    Args:
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)

    Returns:
        True if coordinates are valid, False otherwise
    """
    return (
        isinstance(latitude, (int, float))
        and -90 <= latitude <= 90
        and isinstance(longitude, (int, float))
        and -180 <= longitude <= 180
    )


# Offline geocoding - Major US cities and international locations
# This is a simple mapping for common locations to avoid external API dependencies
CITY_COORDINATES = {
    # US Major Cities
    'new york, ny': (40.7128, -74.0060),
    'los angeles, ca': (34.0522, -118.2437),
    'chicago, il': (41.8781, -87.6298),
    'houston, tx': (29.7604, -95.3698),
    'phoenix, az': (33.4484, -112.0740),
    'philadelphia, pa': (39.9526, -75.1652),
    'san antonio, tx': (29.4241, -98.4936),
    'san diego, ca': (32.7157, -117.1611),
    'dallas, tx': (32.7767, -96.7970),
    'san jose, ca': (37.3382, -121.8863),
    'austin, tx': (30.2672, -97.7431),
    'jacksonville, fl': (30.3322, -81.6557),
    'fort worth, tx': (32.7555, -97.3308),
    'columbus, oh': (39.9612, -82.9988),
    'charlotte, nc': (35.2271, -80.8431),
    'indianapolis, in': (39.7684, -86.1581),
    'san francisco, ca': (37.7749, -122.4194),
    'seattle, wa': (47.6062, -122.3321),
    'denver, co': (39.7392, -104.9903),
    'boston, ma': (42.3601, -71.0589),
    'el paso, tx': (31.7619, -106.4850),
    'nashville, tn': (36.1627, -86.7816),
    'detroit, mi': (42.3314, -83.0458),
    'oklahoma city, ok': (35.4676, -97.5164),
    'portland, or': (45.5152, -122.6784),
    'las vegas, nv': (36.1699, -115.1398),
    'memphis, tn': (35.1495, -90.0490),
    'louisville, ky': (38.2527, -85.7585),
    'baltimore, md': (39.2904, -76.6122),
    'milwaukee, wi': (43.0389, -87.9065),
    'albuquerque, nm': (35.0844, -106.6504),
    'tucson, az': (32.2226, -110.9747),
    'fresno, ca': (36.7378, -119.7871),
    'sacramento, ca': (38.5816, -121.4944),
    'mesa, az': (33.4152, -111.8315),
    'kansas city, mo': (39.0997, -94.5786),
    'atlanta, ga': (33.7490, -84.3880),
    'long beach, ca': (33.7701, -118.1937),
    'colorado springs, co': (38.8339, -104.8214),
    'raleigh, nc': (35.7796, -78.6382),
    'miami, fl': (25.7617, -80.1918),
    'virginia beach, va': (36.8529, -75.9780),
    'omaha, ne': (41.2524, -95.9980),
    'oakland, ca': (37.8044, -122.2712),
    'minneapolis, mn': (44.9778, -93.2650),
    'tulsa, ok': (36.1540, -95.9928),
    'arlington, tx': (32.7357, -97.1081),
    'new orleans, la': (29.9511, -90.0715),
    'wichita, ks': (37.6872, -97.3301),
    'cleveland, oh': (41.4993, -81.6944),
    'tampa, fl': (27.9506, -82.4572),
    'bakersfield, ca': (35.3733, -119.0187),
    'aurora, co': (39.7294, -104.8319),
    'anaheim, ca': (33.8366, -117.9143),
    'honolulu, hi': (21.3099, -157.8581),
    'santa ana, ca': (33.7455, -117.8677),
    'riverside, ca': (33.9533, -117.3962),
    'corpus christi, tx': (27.8006, -97.3964),
    'lexington, ky': (38.0406, -84.5037),
    'stockton, ca': (37.9577, -121.2908),
    'henderson, nv': (36.0395, -114.9817),
    'saint paul, mn': (44.9537, -93.0900),
    'st. louis, mo': (38.6270, -90.1994),
    'cincinnati, oh': (39.1031, -84.5120),
    'pittsburgh, pa': (40.4406, -79.9959),
    # International Major Cities
    'london, uk': (51.5074, -0.1278),
    'paris, france': (48.8566, 2.3522),
    'tokyo, japan': (35.6762, 139.6503),
    'beijing, china': (39.9042, 116.4074),
    'mumbai, india': (19.0760, 72.8777),
    'sydney, australia': (-33.8688, 151.2093),
    'toronto, canada': (43.6511, -79.3470),
    'mexico city, mexico': (19.4326, -99.1332),
    'rio de janeiro, brazil': (-22.9068, -43.1729),
    'madrid, spain': (40.4168, -3.7038),
    'rome, italy': (41.9028, 12.4964),
    'berlin, germany': (52.5200, 13.4050),
    'amsterdam, netherlands': (52.3676, 4.9041),
    'moscow, russia': (55.7558, 37.6176),
    'dubai, uae': (25.2048, 55.2708),
    'singapore': (1.3521, 103.8198),
    'seoul, south korea': (37.5665, 126.9780),
    'cairo, egypt': (30.0444, 31.2357),
    'lagos, nigeria': (6.5244, 3.3792),
    'buenos aires, argentina': (-34.6118, -58.3960),
}


def geocode_offline(location_string: str) -> tuple[float, float] | None:
    """
    Simple offline geocoding using a predefined city mapping
    For production use, consider integrating with a proper geocoding service

    Args:
        location_string: City name, state/country (e.g., "New York, NY" or "London, UK")

    Returns:
        Tuple of (latitude, longitude) if found, None otherwise
    """
    if not location_string:
        return None

    # Normalize the location string
    normalized = location_string.lower().strip()

    # Try exact match first
    if normalized in CITY_COORDINATES:
        return CITY_COORDINATES[normalized]

    # Try partial matching for more flexible lookups
    for city, coords in CITY_COORDINATES.items():
        if city in normalized or normalized in city:
            logger.info(
                f"Geocoding: Found partial match '{city}' for '{location_string}'"
            )
            return coords

    logger.warning(f"Geocoding: No coordinates found for '{location_string}'")
    return None


def calculate_location_risk_score(
    user_lat: float,
    user_lon: float,
    transaction_lat: float,
    transaction_lon: float,
    max_normal_distance_km: float = 100.0,
) -> float:
    """
    Calculate a risk score based on distance between user and transaction location

    Args:
        user_lat, user_lon: User's last known location
        transaction_lat, transaction_lon: Transaction location
        max_normal_distance_km: Distance considered "normal" (returns score 0.0)

    Returns:
        Risk score from 0.0 (no risk) to 1.0 (high risk)
        Score increases exponentially with distance beyond the normal threshold
    """
    distance = haversine_distance(user_lat, user_lon, transaction_lat, transaction_lon)

    if distance <= max_normal_distance_km:
        return 0.0

    # Exponential risk scoring:
    # 200km = 0.5 score, 500km = 0.8 score, 1000km+ = 1.0 score
    excess_distance = distance - max_normal_distance_km
    normalized_excess = excess_distance / max_normal_distance_km

    # Cap the score at 1.0
    return min(1.0, 1.0 - math.exp(-normalized_excess))


def format_distance_human_readable(distance_km: float) -> str:
    """
    Format distance in a human-readable way

    Args:
        distance_km: Distance in kilometers

    Returns:
        Human-readable distance string
    """
    if distance_km < 1:
        return f'{distance_km * 1000:.0f} meters'
    elif distance_km < 100:
        return f'{distance_km:.1f} km'
    else:
        return f'{distance_km:.0f} km'


# SQL function template for database usage
SQL_DISTANCE_FUNCTION = """
-- SQL function to calculate distance between two points using Haversine formula
-- This can be used in alert rule SQL queries for location-based fraud detection

CREATE OR REPLACE FUNCTION haversine_distance_km(lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION, lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    dlat DOUBLE PRECISION;
    dlon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
    r DOUBLE PRECISION := 6371; -- Earth radius in km
BEGIN
    -- Convert to radians
    lat1 := lat1 * PI() / 180;
    lon1 := lon1 * PI() / 180;
    lat2 := lat2 * PI() / 180;
    lon2 := lon2 * PI() / 180;
    
    -- Haversine formula
    dlat := lat2 - lat1;
    dlon := lon2 - lon1;
    a := SIN(dlat/2) * SIN(dlat/2) + COS(lat1) * COS(lat2) * SIN(dlon/2) * SIN(dlon/2);
    c := 2 * ASIN(SQRT(a));
    
    RETURN r * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Example usage in alert rule SQL query:
-- SELECT * FROM transactions t 
-- JOIN users u ON t.user_id = u.id 
-- WHERE haversine_distance_km(u.last_app_location_latitude, u.last_app_location_longitude, 
--                             t.merchant_latitude, t.merchant_longitude) > 100;
"""

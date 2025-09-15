"""
Tests for location services and fraud detection
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.location import (
    calculate_location_risk_score,
    format_distance_human_readable,
    geocode_offline,
    haversine_distance,
    validate_coordinates,
)
from src.services.location_middleware import (
    capture_user_location,
    get_user_location,
    grant_location_consent,
    revoke_location_consent,
    update_user_location_on_login,
)


class TestLocationUtils:
    """Test location utility functions"""

    def test_haversine_distance_same_point(self):
        """Distance between same point should be 0"""
        distance = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0

    def test_haversine_distance_known_cities(self):
        """Test distance between known cities"""
        # New York to Los Angeles (approximately 3944 km)
        ny_lat, ny_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437

        distance = haversine_distance(ny_lat, ny_lon, la_lat, la_lon)

        # Allow for some variation in calculation
        expected_distance = 3944  # kilometers
        assert abs(distance - expected_distance) < 50  # Within 50km tolerance

    def test_haversine_distance_short_distance(self):
        """Test short distance calculation accuracy"""
        # Two points in Manhattan (approximately 1km apart)
        point1_lat, point1_lon = 40.7589, -73.9851  # Times Square
        point2_lat, point2_lon = 40.7505, -73.9934  # Empire State Building

        distance = haversine_distance(point1_lat, point1_lon, point2_lat, point2_lon)

        # Should be around 1km
        assert 0.8 <= distance <= 1.2

    def test_validate_coordinates_valid(self):
        """Test validation of valid coordinates"""
        assert validate_coordinates(40.7128, -74.0060) is True
        assert validate_coordinates(0, 0) is True
        assert validate_coordinates(-90, -180) is True
        assert validate_coordinates(90, 180) is True

    def test_validate_coordinates_invalid(self):
        """Test validation of invalid coordinates"""
        assert validate_coordinates(91, 0) is False  # Latitude too high
        assert validate_coordinates(-91, 0) is False  # Latitude too low
        assert validate_coordinates(0, 181) is False  # Longitude too high
        assert validate_coordinates(0, -181) is False  # Longitude too low
        assert validate_coordinates('invalid', 0) is False  # Non-numeric

    def test_geocode_offline_major_cities(self):
        """Test offline geocoding for major cities"""
        # Test exact matches
        ny_coords = geocode_offline('new york, ny')
        assert ny_coords is not None
        assert ny_coords[0] == 40.7128
        assert ny_coords[1] == -74.0060

        # Test case insensitive
        la_coords = geocode_offline('LOS ANGELES, CA')
        assert la_coords is not None
        assert la_coords[0] == 34.0522

        # Test partial matching
        london_coords = geocode_offline('london')
        assert london_coords is not None

    def test_geocode_offline_unknown_city(self):
        """Test offline geocoding for unknown cities"""
        coords = geocode_offline('unknown city, zz')
        assert coords is None

        coords = geocode_offline('')
        assert coords is None

        coords = geocode_offline(None)
        assert coords is None

    def test_calculate_location_risk_score(self):
        """Test location risk score calculation"""
        # Same location (no risk)
        risk = calculate_location_risk_score(40.7128, -74.0060, 40.7128, -74.0060)
        assert risk == 0.0

        # Within normal threshold (no risk)
        risk = calculate_location_risk_score(
            40.7128, -74.0060, 40.7200, -74.0100, 100.0
        )
        assert risk == 0.0

        # Far distance (high risk)
        risk = calculate_location_risk_score(
            40.7128, -74.0060, 34.0522, -118.2437, 100.0
        )
        assert risk > 0.8  # Should be high risk for cross-country distance

    def test_format_distance_human_readable(self):
        """Test distance formatting for human readability"""
        assert format_distance_human_readable(0.5) == '500 meters'
        assert format_distance_human_readable(1.0) == '1.0 km'
        assert format_distance_human_readable(15.7) == '15.7 km'
        assert format_distance_human_readable(150.0) == '150 km'
        assert format_distance_human_readable(1500.0) == '1500 km'


class TestLocationMiddleware:
    """Test location middleware functions"""

    def setup_method(self):
        """Setup test mocks"""
        self.mock_session = AsyncMock()
        self.mock_request = Mock()
        self.mock_request.headers = {}

        # Mock database User model
        self.mock_user_query = Mock()
        self.mock_session.execute = AsyncMock(return_value=self.mock_user_query)
        self.mock_session.commit = AsyncMock()
        self.mock_session.rollback = AsyncMock()

    @pytest.mark.asyncio
    async def test_capture_user_location_no_headers(self):
        """Test location capture when no headers are present"""
        result = await capture_user_location(
            self.mock_request, 'user-123', self.mock_session
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_capture_user_location_invalid_coordinates(self):
        """Test location capture with invalid coordinates"""
        self.mock_request.headers = {
            'X-User-Latitude': 'invalid',
            'X-User-Longitude': '-74.0060',
        }

        result = await capture_user_location(
            self.mock_request, 'user-123', self.mock_session
        )

        assert result is False

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.select')
    @patch('src.services.location_middleware.update')
    async def test_capture_user_location_success(
        self, mock_update, mock_select, mock_user_model
    ):
        """Test successful location capture"""
        # Setup valid headers
        self.mock_request.headers = {
            'X-User-Latitude': '40.7128',
            'X-User-Longitude': '-74.0060',
            'X-User-Location-Accuracy': '10.5',
        }

        # Mock user consent query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = True  # User has given consent
        self.mock_session.execute.return_value = mock_result

        result = await capture_user_location(
            self.mock_request, 'user-123', self.mock_session
        )

        assert result is True
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.select')
    async def test_capture_user_location_no_consent(self, mock_select, mock_user_model):
        """Test location capture when user has not given consent"""
        # Setup valid headers
        self.mock_request.headers = {
            'X-User-Latitude': '40.7128',
            'X-User-Longitude': '-74.0060',
        }

        # Mock user consent query result - no consent
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = False
        self.mock_session.execute.return_value = mock_result

        result = await capture_user_location(
            self.mock_request, 'user-123', self.mock_session
        )

        assert result is False

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.update')
    async def test_grant_location_consent(self, mock_update, mock_user_model):
        """Test granting location consent"""
        result = await grant_location_consent('user-123', self.mock_session)

        assert result is True
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.update')
    async def test_revoke_location_consent(self, mock_update, mock_user_model):
        """Test revoking location consent"""
        result = await revoke_location_consent('user-123', self.mock_session)

        assert result is True
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.select')
    async def test_get_user_location_with_consent(self, mock_select, mock_user_model):
        """Test getting user location when consent is given"""
        # Mock database result
        mock_row = Mock()
        mock_row.location_consent_given = True
        mock_row.last_app_location_latitude = 40.7128
        mock_row.last_app_location_longitude = -74.0060
        mock_row.last_app_location_timestamp = datetime.now(UTC)
        mock_row.last_app_location_accuracy = 10.5

        mock_result = Mock()
        mock_result.first.return_value = mock_row
        self.mock_session.execute.return_value = mock_result

        result = await get_user_location('user-123', self.mock_session)

        assert result is not None
        assert result['latitude'] == 40.7128
        assert result['longitude'] == -74.0060
        assert result['accuracy'] == 10.5
        assert result['consent_given'] is True

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.User')
    @patch('src.services.location_middleware.select')
    async def test_get_user_location_no_consent(self, mock_select, mock_user_model):
        """Test getting user location when consent is not given"""
        # Mock database result
        mock_row = Mock()
        mock_row.location_consent_given = False

        mock_result = Mock()
        mock_result.first.return_value = mock_row
        self.mock_session.execute.return_value = mock_result

        result = await get_user_location('user-123', self.mock_session)

        assert result is None

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.capture_user_location')
    async def test_update_user_location_on_login(self, mock_capture):
        """Test location update on login"""
        mock_capture.return_value = True

        current_user = {
            'id': 'user-123',
            'email': 'test@example.com',
            'is_dev_mode': False,
        }

        await update_user_location_on_login(
            self.mock_request, current_user, self.mock_session
        )

        mock_capture.assert_called_once_with(
            request=self.mock_request,
            user_id='user-123',
            session=self.mock_session,
            force_update=False,
        )

    @pytest.mark.asyncio
    @patch('src.services.location_middleware.capture_user_location')
    async def test_update_user_location_on_login_dev_mode_skip(self, mock_capture):
        """Test that dev mode mock users skip location capture"""
        current_user = {
            'id': 'dev-user-123',
            'email': 'developer@example.com',
            'is_dev_mode': True,
        }

        await update_user_location_on_login(
            self.mock_request, current_user, self.mock_session
        )

        # Should not be called for dev mode mock users
        mock_capture.assert_not_called()


class TestLocationIntegration:
    """Integration tests for location services"""

    @pytest.mark.asyncio
    async def test_location_based_fraud_detection_workflow(self):
        """Test the complete location-based fraud detection workflow"""
        # This would be an integration test with real database
        # For now, we'll mock the key components

        # Step 1: User logs in and location is captured
        mock_request = Mock()
        mock_request.headers = {
            'X-User-Latitude': '40.7128',  # New York
            'X-User-Longitude': '-74.0060',
        }

        # Step 2: Transaction occurs in different location
        user_lat, user_lon = 40.7128, -74.0060  # New York
        transaction_lat, transaction_lon = 34.0522, -118.2437  # Los Angeles

        # Step 3: Calculate risk
        risk_score = calculate_location_risk_score(
            user_lat,
            user_lon,
            transaction_lat,
            transaction_lon,
            max_normal_distance_km=100.0,
        )

        # Step 4: High risk should be detected for cross-country transaction
        assert risk_score > 0.8

    def test_sql_distance_function_template(self):
        """Test that SQL function template is valid"""
        from src.services.location import SQL_DISTANCE_FUNCTION

        # Basic validation that template contains required elements
        assert 'haversine_distance_km' in SQL_DISTANCE_FUNCTION
        assert 'DOUBLE PRECISION' in SQL_DISTANCE_FUNCTION
        assert 'PI()' in SQL_DISTANCE_FUNCTION
        assert 'SIN(' in SQL_DISTANCE_FUNCTION
        assert 'COS(' in SQL_DISTANCE_FUNCTION
        assert '6371' in SQL_DISTANCE_FUNCTION  # Earth radius


# Mock location data for tests
MOCK_LOCATIONS = {
    'new_york': {'lat': 40.7128, 'lon': -74.0060, 'city': 'New York, NY'},
    'los_angeles': {'lat': 34.0522, 'lon': -118.2437, 'city': 'Los Angeles, CA'},
    'chicago': {'lat': 41.8781, 'lon': -87.6298, 'city': 'Chicago, IL'},
    'london': {'lat': 51.5074, 'lon': -0.1278, 'city': 'London, UK'},
    'tokyo': {'lat': 35.6762, 'lon': 139.6503, 'city': 'Tokyo, Japan'},
}

MOCK_TRANSACTIONS = [
    {
        'id': 'txn-001',
        'user_id': 'user-123',
        'merchant_name': 'Coffee Shop NYC',
        'merchant_latitude': 40.7589,
        'merchant_longitude': -73.9851,
        'amount': 4.50,
        'transaction_date': '2024-01-15T10:30:00Z',
    },
    {
        'id': 'txn-002',
        'user_id': 'user-123',
        'merchant_name': 'Gas Station LA',
        'merchant_latitude': 34.0522,
        'merchant_longitude': -118.2437,
        'amount': 45.00,
        'transaction_date': '2024-01-15T10:32:00Z',  # 2 minutes later, across country
    },
]

MOCK_USERS = [
    {
        'id': 'user-123',
        'email': 'john.doe@example.com',
        'last_app_location_latitude': 40.7128,
        'last_app_location_longitude': -74.0060,
        'location_consent_given': True,
        'last_app_location_timestamp': '2024-01-15T10:00:00Z',
    },
    {
        'id': 'user-456',
        'email': 'jane.smith@example.com',
        'last_app_location_latitude': None,
        'last_app_location_longitude': None,
        'location_consent_given': False,
        'last_app_location_timestamp': None,
    },
]

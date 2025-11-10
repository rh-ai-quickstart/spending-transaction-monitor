"""
Tests for enhanced dev mode authentication functionality with header-based user selection
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException, Request
import pytest

from src.auth.middleware import (
    get_current_user,
    get_dev_fallback_user,
    get_test_user,
    lookup_user_by_email,
    require_authentication,
)


class TestHeaderBasedUserSelection:
    """Test enhanced dev mode functionality with X-Test-User-Email header"""

    def setup_method(self):
        """Setup mock request and session for each test"""
        self.mock_request = Mock(spec=Request)
        self.mock_session = AsyncMock()

        # Mock user object
        self.mock_user = Mock()
        self.mock_user.id = 'user-123'
        self.mock_user.email = 'testuser@example.com'

    @pytest.mark.asyncio
    async def test_get_current_user_always_returns_u001(self):
        """Test that get_current_user always returns u-001 in bypass mode"""
        # Setup - mock u-001 user
        mock_u001 = Mock()
        mock_u001.id = 'u-001'
        mock_u001.email = 'monica.cohen@example.com'

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_u001
        self.mock_session.execute.return_value = mock_result

        mock_user_class = Mock()
        mock_user_class.id = Mock()

        with (
            patch('src.auth.middleware.settings') as mock_settings,
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_settings.BYPASS_AUTH = True
            mock_select.return_value.where.return_value = Mock()

            # Execute
            user = await get_current_user(
                credentials=None, session=self.mock_session, request=self.mock_request
            )

            # Assert - should always return u-001
            assert user['id'] == 'u-001'
            assert user['email'] == 'monica.cohen@example.com'
            assert user['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_current_user_without_test_header_fallback(self):
        """Test that get_current_user falls back to default behavior when no header"""
        # Setup
        self.mock_request.headers.get.return_value = None

        with (
            patch('src.auth.middleware.settings') as mock_settings,
            patch('src.auth.middleware.get_dev_fallback_user') as mock_fallback,
        ):
            mock_settings.BYPASS_AUTH = True
            expected_user = {
                'id': 'dev-user-123',
                'email': 'developer@example.com',
                'is_dev_mode': True,
            }
            mock_fallback.return_value = expected_user

            # Execute
            user = await get_current_user(
                credentials=None, session=self.mock_session, request=self.mock_request
            )

            # Assert
            assert user == expected_user
            mock_fallback.assert_called_once_with(self.mock_session)

    @pytest.mark.asyncio
    async def test_require_authentication_always_returns_u001(self):
        """Test that require_authentication always returns u-001 in bypass mode"""
        # Setup - mock u-001 user
        mock_u001 = Mock()
        mock_u001.id = 'u-001'
        mock_u001.email = 'monica.cohen@example.com'

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_u001
        self.mock_session.execute.return_value = mock_result

        mock_user_class = Mock()
        mock_user_class.id = Mock()

        # Create async mock for location capture
        mock_capture = AsyncMock()

        # Mock request properly to avoid subscript errors
        mock_request = Mock(spec=Request)
        mock_request.method = 'GET'
        mock_request.url.path = '/test'
        mock_request.headers.get.return_value = 'NOT PRESENT'

        with (
            patch('src.auth.middleware.settings') as mock_settings,
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
            patch('src.auth.middleware._capture_user_location_safe', mock_capture),
        ):
            mock_settings.BYPASS_AUTH = True
            mock_select.return_value.where.return_value = Mock()

            # Execute
            user = await require_authentication(
                credentials=None, session=self.mock_session, request=mock_request
            )

            # Assert - should always return u-001
            assert user['id'] == 'u-001'
            assert user['email'] == 'monica.cohen@example.com'
            assert user['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_production_mode_ignores_test_header(self):
        """Test that test header is ignored in production mode"""
        # Setup
        self.mock_request.headers.get.return_value = 'testuser@example.com'

        with patch('src.auth.middleware.settings') as mock_settings:
            mock_settings.BYPASS_AUTH = False

            # Execute
            user = await get_current_user(
                credentials=None, session=self.mock_session, request=self.mock_request
            )

            # Assert
            assert user is None  # Should return None when no credentials in production


class TestLookupUserByEmail:
    """Test user lookup functionality"""

    def setup_method(self):
        self.mock_session = AsyncMock()
        self.mock_user = Mock()
        self.mock_user.id = 'user-123'
        self.mock_user.email = 'test@example.com'

    @pytest.mark.asyncio
    async def test_lookup_user_by_email_success(self):
        """Test successful user lookup by email"""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_session.execute.return_value = mock_result

        # Mock the User class and the select operation
        mock_user_class = Mock()
        mock_user_class.email = Mock()

        with (
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_select.return_value.where.return_value = Mock()

            # Execute
            result = await lookup_user_by_email('test@example.com', self.mock_session)

            # Assert
            assert result == self.mock_user
            self.mock_session.execute.assert_called_once()
            mock_select.assert_called_once_with(mock_user_class)

    @pytest.mark.asyncio
    async def test_lookup_user_by_email_not_found(self):
        """Test user lookup when user doesn't exist"""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        # Mock the User class and the select operation
        mock_user_class = Mock()
        mock_user_class.email = Mock()

        with (
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_select.return_value.where.return_value = Mock()

            # Execute
            result = await lookup_user_by_email(
                'nonexistent@example.com', self.mock_session
            )

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_user_by_email_no_user_model(self):
        """Test user lookup when User model is not available"""
        # Execute
        with patch('src.auth.middleware.User', None):
            result = await lookup_user_by_email('test@example.com', self.mock_session)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_user_by_email_database_error(self):
        """Test user lookup handles database errors gracefully"""
        # Setup
        self.mock_session.execute.side_effect = Exception('Database connection failed')

        # Mock the User class and the select operation
        mock_user_class = Mock()
        mock_user_class.email = Mock()

        with (
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_select.return_value.where.return_value = Mock()

            # Execute
            result = await lookup_user_by_email('test@example.com', self.mock_session)

            # Assert
            assert result is None


class TestGetTestUser:
    """Test get_test_user functionality"""

    def setup_method(self):
        self.mock_session = AsyncMock()
        self.mock_user = Mock()
        self.mock_user.id = 'user-123'
        self.mock_user.email = 'testuser@example.com'

    @pytest.mark.asyncio
    async def test_get_test_user_success(self):
        """Test successful test user retrieval"""
        # Setup
        with patch('src.auth.middleware.lookup_user_by_email') as mock_lookup:
            mock_lookup.return_value = self.mock_user

            # Execute
            result = await get_test_user('testuser@example.com', self.mock_session)

            # Assert
            assert result['id'] == 'user-123'
            assert result['email'] == 'testuser@example.com'
            assert result['username'] == 'testuser'
            assert result['roles'] == ['user', 'admin']
            assert result['is_dev_mode'] is True

            mock_lookup.assert_called_once_with(
                'testuser@example.com', self.mock_session
            )

    @pytest.mark.asyncio
    async def test_get_test_user_not_found_raises_error(self):
        """Test that get_test_user raises 400 error when user not found"""
        # Setup
        with patch('src.auth.middleware.lookup_user_by_email') as mock_lookup:
            mock_lookup.return_value = None

            # Execute & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_test_user('nonexistent@example.com', self.mock_session)

            assert exc_info.value.status_code == 400
            assert 'Test user not found: nonexistent@example.com' in str(
                exc_info.value.detail
            )


class TestGetDevFallbackUser:
    """Test fallback user functionality"""

    def setup_method(self):
        self.mock_session = AsyncMock()
        self.mock_user = Mock()
        self.mock_user.id = 'user-123'
        self.mock_user.email = 'firstuser@example.com'

    @pytest.mark.asyncio
    async def test_get_dev_fallback_user_with_db_user(self):
        """Test fallback returns first database user when available"""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_session.execute.return_value = mock_result

        # Mock the User class and the select operation
        mock_user_class = Mock()

        with (
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_select.return_value.limit.return_value = Mock()

            # Execute
            result = await get_dev_fallback_user(self.mock_session)

            # Assert
            assert result['id'] == 'user-123'
            assert result['email'] == 'firstuser@example.com'
            assert result['username'] == 'firstuser'
            assert result['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_dev_fallback_user_no_users_in_db(self):
        """Test fallback returns mock user when no users in database"""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        with patch('src.auth.middleware.User', self.mock_user.__class__):
            # Execute
            result = await get_dev_fallback_user(self.mock_session)

            # Assert
            assert result['id'] == 'dev-user-123'
            assert result['email'] == 'developer@example.com'
            assert result['username'] == 'developer'
            assert result['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_dev_fallback_user_no_session(self):
        """Test fallback returns mock user when no database session"""
        # Execute
        result = await get_dev_fallback_user(None)

        # Assert
        assert result['id'] == 'dev-user-123'
        assert result['email'] == 'developer@example.com'
        assert result['username'] == 'developer'
        assert result['is_dev_mode'] is True

    @pytest.mark.asyncio
    async def test_get_dev_fallback_user_database_error(self):
        """Test fallback returns mock user when database error occurs"""
        # Setup
        self.mock_session.execute.side_effect = Exception('Database error')

        with patch('src.auth.middleware.User', self.mock_user.__class__):
            # Execute
            result = await get_dev_fallback_user(self.mock_session)

            # Assert
            assert result['id'] == 'dev-user-123'
            assert result['email'] == 'developer@example.com'
            assert result['is_dev_mode'] is True


class TestIntegrationScenarios:
    """Integration tests for complete dev mode scenarios"""

    def setup_method(self):
        self.mock_request = Mock(spec=Request)
        self.mock_session = AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_flow_always_returns_u001(self):
        """Test complete flow always returns u-001 with proper context"""
        # Mock u-001 database user
        mock_u001 = Mock()
        mock_u001.id = 'u-001'
        mock_u001.email = 'monica.cohen@example.com'

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_u001
        self.mock_session.execute.return_value = mock_result

        # Mock the User class and the select operation
        mock_user_class = Mock()
        mock_user_class.id = Mock()

        with (
            patch('src.auth.middleware.settings') as mock_settings,
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
        ):
            mock_settings.BYPASS_AUTH = True
            mock_select.return_value.where.return_value = Mock()

            # Execute
            user = await get_current_user(
                credentials=None, session=self.mock_session, request=self.mock_request
            )

            # Assert complete user context for u-001
            assert user['id'] == 'u-001'
            assert user['email'] == 'monica.cohen@example.com'
            assert user['username'] == 'monica.cohen'
            assert user['roles'] == ['user', 'admin']
            assert user['is_dev_mode'] is True
            assert 'token_claims' in user
            assert user['token_claims']['sub'] == 'u-001'
            assert user['token_claims']['email'] == 'monica.cohen@example.com'

    @pytest.mark.asyncio
    async def test_fallback_when_u001_not_found(self):
        """Test fallback behavior when u-001 is not found in database"""
        # Setup - u-001 doesn't exist, should fall back
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        # Mock the User class and the select operation
        mock_user_class = Mock()
        mock_user_class.id = Mock()

        with (
            patch('src.auth.middleware.settings') as mock_settings,
            patch('src.auth.middleware.User', mock_user_class),
            patch('src.auth.middleware.select') as mock_select,
            patch('src.auth.middleware.get_dev_fallback_user') as mock_fallback,
        ):
            mock_settings.BYPASS_AUTH = True
            mock_select.return_value.where.return_value = Mock()
            expected_fallback = {
                'id': 'dev-user-123',
                'email': 'developer@example.com',
                'is_dev_mode': True,
            }
            mock_fallback.return_value = expected_fallback

            # Execute - should not raise, should fallback
            user = await get_current_user(
                credentials=None,
                session=self.mock_session,
                request=self.mock_request,
            )

            # Assert - should use fallback user
            assert user == expected_fallback
            mock_fallback.assert_called_once()

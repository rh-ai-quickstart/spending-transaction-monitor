"""
JWT Authentication middleware for Keycloak integration using python-jose
"""

from datetime import datetime, timedelta
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings

# Optional database imports (for development mode user fetching)
try:
    from db import get_db
    from db.models import User
except ImportError:
    # DB package not available during some local dev flows
    get_db = None
    User = None

logger = logging.getLogger(__name__)

# Global cache for OIDC configuration and keys
_oidc_config_cache: dict | None = None
_jwks_cache: dict | None = None
_cache_expiry: datetime | None = None

# Keycloak configuration (loaded from environment variables)
KEYCLOAK_URL = settings.KEYCLOAK_URL
REALM = settings.KEYCLOAK_REALM
CLIENT_ID = settings.KEYCLOAK_CLIENT_ID

security = HTTPBearer(auto_error=False)


class KeycloakJWTBearer:
    """JWT Bearer token validator for Keycloak using python-jose"""

    async def get_oidc_config(self) -> dict:
        """Fetch OIDC configuration from Keycloak with fallback"""
        global _oidc_config_cache, _cache_expiry

        # Check cache validity (cache for 1 hour)
        if _cache_expiry and datetime.now() < _cache_expiry and _oidc_config_cache:
            return _oidc_config_cache

        # Try OIDC discovery first
        discovery_url = (
            f'{KEYCLOAK_URL}/realms/{REALM}/.well-known/openid-configuration'
        )
        logger.info(f'Attempting OIDC discovery from: {discovery_url}')

        try:
            response = requests.get(discovery_url, timeout=10.0)
            response.raise_for_status()

            _oidc_config_cache = response.json()
            _cache_expiry = datetime.now() + timedelta(hours=1)

            logger.info(
                '✅ Successfully loaded OIDC configuration from Keycloak discovery'
            )
            logger.info(f'   Issuer: {_oidc_config_cache.get("issuer", "N/A")}')
            logger.info(f'   JWKS URI: {_oidc_config_cache.get("jwks_uri", "N/A")}')
            return _oidc_config_cache

        except Exception as e:
            logger.warning(f'❌ OIDC discovery failed from {discovery_url}')
            logger.warning(f'   Error: {e}')
            logger.warning('   Falling back to hardcoded OIDC endpoints')

            # Fallback to hardcoded endpoints
            _oidc_config_cache = {
                'issuer': f'{KEYCLOAK_URL}/realms/{REALM}',
                'jwks_uri': f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs',
                'authorization_endpoint': f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth',
                'token_endpoint': f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token',
                'userinfo_endpoint': f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/userinfo',
                'end_session_endpoint': f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/logout',
            }
            _cache_expiry = datetime.now() + timedelta(hours=1)

            logger.info('🔧 Using fallback OIDC configuration:')
            logger.info(f'   Issuer: {_oidc_config_cache["issuer"]}')
            logger.info(f'   JWKS URI: {_oidc_config_cache["jwks_uri"]}')
            return _oidc_config_cache

    async def get_jwks(self) -> dict:
        """Fetch JSON Web Key Set from Keycloak"""
        global _jwks_cache

        # Get OIDC config first (this handles caching)
        oidc_config = await self.get_oidc_config()

        if _jwks_cache:
            logger.debug('Using cached JWKS')
            return _jwks_cache

        jwks_uri = oidc_config['jwks_uri']
        logger.info(f'Fetching JWKS from: {jwks_uri}')

        try:
            response = requests.get(jwks_uri, timeout=10.0)
            response.raise_for_status()

            _jwks_cache = response.json()

            logger.info(
                f'✅ Successfully loaded {len(_jwks_cache.get("keys", []))} keys from JWKS'
            )
            return _jwks_cache

        except Exception as e:
            logger.error(f'❌ Failed to fetch JWKS from {jwks_uri}: {e}')
            raise HTTPException(
                status_code=503, detail='Authentication service unavailable'
            ) from e

    async def validate_token(self, token: str) -> dict:
        """Validate JWT token and return claims using python-jose"""
        logger.info(f'🔍 Validating JWT token (length: {len(token)})')

        try:
            # Get OIDC config and JWKS
            oidc_config = await self.get_oidc_config()
            jwks = await self.get_jwks()

            logger.info('🔐 Token validation parameters:')
            logger.info(f'   Issuer: {oidc_config["issuer"]}')
            logger.info(f'   Audience: {CLIENT_ID}')
            logger.info(f'   Available keys: {len(jwks.get("keys", []))}')

            # Decode and validate token
            # Note: For public clients, audience verification can be problematic
            # We'll verify audience manually if present
            claims = jwt.decode(
                token,
                jwks,
                algorithms=['RS256'],
                issuer=oidc_config['issuer'],
                options={'verify_exp': True, 'verify_aud': False},
            )

            # Manual audience verification (more flexible for public clients)
            if 'aud' in claims:
                audience = claims.get('aud')
                # Handle both string and array audience formats
                valid_audiences = [CLIENT_ID, 'account']  # Common Keycloak audiences
                audience_list = [audience] if isinstance(audience, str) else audience

                if not any(aud in valid_audiences for aud in audience_list):
                    logger.error(
                        f'❌ Invalid audience: {audience}, expected one of: {valid_audiences}'
                    )
                    raise JWTError('Invalid audience')

            logger.info('✅ Token validation successful')
            logger.info(f'   Subject: {claims.get("sub", "N/A")}')
            logger.info(f'   Username: {claims.get("preferred_username", "N/A")}')
            logger.info(f'   Email: {claims.get("email", "N/A")}')

            return claims

        except JWTError as e:
            logger.error(f'❌ JWT validation error: {e}')
            try:
                # Try to get issuer claim for debugging, but don't fail if token is completely malformed
                unverified_claims = jwt.get_unverified_claims(token)
                token_issuer = unverified_claims.get('iss', 'N/A')
                logger.error(f'   Token issuer claim: {token_issuer}')
            except Exception:
                logger.error(
                    '   Token issuer claim: Could not extract (malformed token)'
                )

            expected_issuer = (
                oidc_config.get('issuer', 'N/A') if 'oidc_config' in locals() else 'N/A'
            )
            logger.error(f'   Expected issuer: {expected_issuer}')
            raise HTTPException(status_code=401, detail='Invalid token') from e
        except Exception as e:
            logger.error(f'❌ Token validation error: {e}')
            logger.error(f'   Error type: {type(e).__name__}')
            raise HTTPException(
                status_code=401, detail='Token validation failed'
            ) from e


# Global instance
keycloak_jwt = KeycloakJWTBearer()


async def lookup_user_by_email(email: str, session: AsyncSession) -> 'User | None':
    """Lookup user by email in database (dev mode helper)"""
    if not User or not session:
        return None

    try:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f'Failed to lookup user by email {email}: {e}')
        return None


def create_user_context(db_user: 'User', is_dev_mode: bool = False) -> dict:
    """Create standardized user context from database user"""
    return {
        'id': db_user.id,
        'email': db_user.email,
        'username': db_user.email.split('@')[0],  # Use email prefix as username
        'roles': ['user', 'admin']
        if is_dev_mode
        else ['user'],  # Dev mode gets all roles
        'is_dev_mode': is_dev_mode,
        'token_claims': {
            'sub': db_user.id,
            'preferred_username': db_user.email.split('@')[0],
            'email': db_user.email,
            'realm_access': {'roles': ['user', 'admin'] if is_dev_mode else ['user']},
        },
    }


async def get_test_user(email: str, session: AsyncSession) -> dict:
    """Get specific test user by email (dev mode only)"""
    logger.warning(f'🧪 DEV MODE: Using test user: {email}')

    user = await lookup_user_by_email(email, session)
    if not user:
        logger.error(f'🧪 DEV MODE: Test user not found: {email}')
        raise HTTPException(
            status_code=400,
            detail=f'Test user not found: {email}. Make sure the user exists in the database.',
        )

    logger.info(
        f'🧪 DEV MODE: Successfully loaded test user: {user.email} (ID: {user.id})'
    )
    return create_user_context(user, is_dev_mode=True)


async def get_dev_fallback_user(session: AsyncSession) -> dict:
    """Get fallback dev user (first user or mock) - current behavior"""
    # Try to get first user from database
    if session and User:
        try:
            result = await session.execute(select(User).limit(1))
            db_user = result.scalar_one_or_none()

            if db_user:
                logger.info(
                    f'🔓 DEV MODE: Using first database user: {db_user.email} (ID: {db_user.id})'
                )
                return create_user_context(db_user, is_dev_mode=True)
            else:
                logger.warning(
                    '🔓 DEV MODE: No users found in database, using mock user'
                )
        except Exception as e:
            logger.warning(
                f'🔓 DEV MODE: Failed to fetch user from database: {e}, using mock user'
            )

    # Fallback to mock user if database unavailable or no users found
    logger.info('🔓 DEV MODE: Using mock fallback user')
    return {
        'id': 'dev-user-123',
        'email': 'developer@example.com',
        'username': 'developer',
        'roles': ['user', 'admin'],
        'is_dev_mode': True,
        'token_claims': {
            'sub': 'dev-user-123',
            'preferred_username': 'developer',
            'email': 'developer@example.com',
            'realm_access': {'roles': ['user', 'admin']},
        },
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db) if get_db else None,
    request: Request = None,
) -> dict | None:
    """Extract user info from JWT token with development bypass (returns None if no token)"""

    # Development bypass - check for test user header first
    if settings.BYPASS_AUTH:
        logger.info('🔓 Authentication bypassed - development mode enabled')

        # NEW: Check for test user header (only if request is available)
        if request is not None:
            test_user_email = request.headers.get('X-Test-User-Email')
            if test_user_email:
                return await get_test_user(test_user_email, session)

        # Fallback to current behavior (first user or mock)
        return await get_dev_fallback_user(session)

    if not credentials:
        return None

    claims = await keycloak_jwt.validate_token(credentials.credentials)

    return {
        'id': claims.get('sub'),
        'email': claims.get('email'),
        'username': claims.get('preferred_username'),
        'roles': claims.get('realm_access', {}).get('roles', []),
        'is_dev_mode': False,
        'token_claims': claims,
    }


async def require_authentication(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db) if get_db else None,
    request: Request = None,
) -> dict:
    """Require valid JWT token with development bypass"""

    # Development bypass - check for test user header first
    if settings.BYPASS_AUTH:
        logger.info('🔓 Authentication bypassed - development mode enabled')

        # NEW: Check for test user header (only if request is available)
        if request is not None:
            test_user_email = request.headers.get('X-Test-User-Email')
            if test_user_email:
                return await get_test_user(test_user_email, session)

        # Fallback to current behavior (first user or mock)
        return await get_dev_fallback_user(session)

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail='Authentication required',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user = await get_current_user(credentials, session, request)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid authentication')

    return user


def require_role(required_role: str):
    """Decorator to require specific role"""

    async def role_checker(
        user: dict = Depends(require_authentication), request: Request = None
    ) -> dict:
        user_roles = user.get('roles', [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=403,
                detail=f'Insufficient permissions. Required role: {required_role}',
            )
        return user

    return role_checker


def require_any_role(required_roles: list[str]):
    """Decorator to require any of the specified roles"""

    async def role_checker(
        user: dict = Depends(require_authentication), request: Request = None
    ) -> dict:
        user_roles = user.get('roles', [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f'Insufficient permissions. Required roles: {required_roles}',
            )
        return user

    return role_checker


# Convenience dependencies
require_admin = require_role('admin')
require_user = require_any_role(['user', 'admin'])

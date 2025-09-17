"""
Location middleware for capturing user location during authentication
Updates user location profile when location headers are present
"""

from datetime import UTC, datetime
import logging

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .location import validate_coordinates

# Optional database imports (for development mode user fetching)
try:
    from db.models import User
except ImportError:
    # DB package not available during some local dev flows
    User = None

logger = logging.getLogger(__name__)


async def capture_user_location(
    request: Request, user_id: str, session: AsyncSession, force_update: bool = False
) -> bool:
    """
    Capture user location from request headers and update user profile

    Args:
        request: FastAPI request object containing headers
        user_id: ID of the authenticated user
        session: Database session
        force_update: Whether to update even if user has denied location consent

    Returns:
        True if location was captured and updated, False otherwise
    """
    if not User:
        logger.warning('User model not available, skipping location capture')
        return False

    # Extract location headers
    latitude_header = request.headers.get('X-User-Latitude')
    longitude_header = request.headers.get('X-User-Longitude')
    accuracy_header = request.headers.get('X-User-Location-Accuracy')

    # Check if location headers are present
    if not latitude_header or not longitude_header:
        logger.debug(f'No location headers found for user {user_id}')
        return False

    try:
        latitude = float(latitude_header)
        longitude = float(longitude_header)
        accuracy = float(accuracy_header) if accuracy_header else None
    except (ValueError, TypeError) as e:
        logger.warning(f'Invalid location headers for user {user_id}: {e}')
        return False

    # Validate coordinates
    if not validate_coordinates(latitude, longitude):
        logger.warning(
            f'Invalid coordinates for user {user_id}: lat={latitude}, lon={longitude}'
        )
        return False

    # Validate accuracy if provided (should be positive meters)
    if accuracy is not None and (accuracy < 0 or accuracy > 50000):  # Max 50km accuracy
        logger.warning(f'Invalid accuracy for user {user_id}: {accuracy}m')
        accuracy = None

    try:
        # First, check user's location consent
        result = await session.execute(
            select(User.location_consent_given).where(User.id == user_id)
        )
        user_consent = result.scalar_one_or_none()

        if user_consent is None:
            logger.warning(f'User {user_id} not found')
            return False

        if not user_consent and not force_update:
            logger.info(
                f'User {user_id} has not given location consent, skipping update'
            )
            return False

        # Update user location
        current_time = datetime.now(UTC)

        update_data = {
            'last_app_location_latitude': latitude,
            'last_app_location_longitude': longitude,
            'last_app_location_timestamp': current_time,
            'updated_at': current_time,
        }

        if accuracy is not None:
            update_data['last_app_location_accuracy'] = accuracy

        await session.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )

        # Commit the transaction
        await session.commit()

        logger.info(
            f'Updated location for user {user_id}: '
            f'lat={latitude:.6f}, lon={longitude:.6f}'
            f'{f", accuracy={accuracy}m" if accuracy else ""}'
        )

        return True

    except Exception as e:
        logger.error(f'Failed to update location for user {user_id}: {e}')
        await session.rollback()
        return False


async def grant_location_consent(user_id: str, session: AsyncSession) -> bool:
    """
    Grant location consent for a user

    Args:
        user_id: ID of the user
        session: Database session

    Returns:
        True if consent was granted successfully, False otherwise
    """
    if not User:
        return False

    try:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(location_consent_given=True, updated_at=datetime.now(UTC))
        )
        await session.commit()

        logger.info(f'Granted location consent for user {user_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to grant location consent for user {user_id}: {e}')
        await session.rollback()
        return False


async def revoke_location_consent(user_id: str, session: AsyncSession) -> bool:
    """
    Revoke location consent for a user and clear location data

    Args:
        user_id: ID of the user
        session: Database session

    Returns:
        True if consent was revoked successfully, False otherwise
    """
    if not User:
        return False

    try:
        # Clear location data and revoke consent
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                location_consent_given=False,
                last_app_location_latitude=None,
                last_app_location_longitude=None,
                last_app_location_timestamp=None,
                last_app_location_accuracy=None,
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

        logger.info(f'Revoked location consent and cleared data for user {user_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to revoke location consent for user {user_id}: {e}')
        await session.rollback()
        return False


async def get_user_location(user_id: str, session: AsyncSession) -> dict | None:
    """
    Get user's current location if consent is given

    Args:
        user_id: ID of the user
        session: Database session

    Returns:
        Dictionary with location data if available, None otherwise
    """
    if not User:
        return None

    try:
        result = await session.execute(
            select(
                User.location_consent_given,
                User.last_app_location_latitude,
                User.last_app_location_longitude,
                User.last_app_location_timestamp,
                User.last_app_location_accuracy,
            ).where(User.id == user_id)
        )

        row = result.first()
        if not row or not row.location_consent_given:
            return None

        if (
            row.last_app_location_latitude is None
            or row.last_app_location_longitude is None
        ):
            return None

        return {
            'latitude': row.last_app_location_latitude,
            'longitude': row.last_app_location_longitude,
            'timestamp': row.last_app_location_timestamp,
            'accuracy': row.last_app_location_accuracy,
            'consent_given': row.location_consent_given,
        }

    except Exception as e:
        logger.error(f'Failed to get location for user {user_id}: {e}')
        return None


# Integration with existing auth middleware
async def update_user_location_on_login(
    request: Request, current_user: dict, session: AsyncSession
) -> None:
    """
    Integration point for auth middleware to capture location on login

    Args:
        request: FastAPI request object
        current_user: Authenticated user context from middleware
        session: Database session
    """
    if not current_user or 'id' not in current_user:
        return

    # Skip location capture in dev mode with mock users
    if current_user.get('is_dev_mode', False) and current_user['id'] in [
        'dev-user-123'
    ]:
        logger.debug('Skipping location capture for dev mode mock user')
        return

    # Capture location if headers are present
    await capture_user_location(
        request=request,
        user_id=current_user['id'],
        session=session,
        force_update=False,  # Respect user consent
    )

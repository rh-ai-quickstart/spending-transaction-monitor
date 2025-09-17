# Standard library
from datetime import UTC, datetime
import uuid

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Local
from db import get_db
from db.models import AlertRule, User

from ..auth.middleware import require_authentication
from ..schemas.user import UserOut

router = APIRouter()


class LocationUpdateRequest(BaseModel):
    location_consent_given: bool
    last_app_location_latitude: float
    last_app_location_longitude: float
    last_app_location_accuracy: float | None = None


class UserCreate(BaseModel):
    email: str = Field(..., description='User email')
    first_name: str = Field(..., description='User first name')
    last_name: str = Field(..., description='User last name')
    phone_number: str | None = Field(None, description='User phone number')


class UserUpdate(BaseModel):
    email: str | None = Field(None, description='User email')
    first_name: str | None = Field(None, description='User first name')
    last_name: str | None = Field(None, description='User last name')
    phone_number: str | None = Field(None, description='User phone number')
    is_active: bool | None = Field(None, description='Whether the user is active')
    address_street: str | None = Field(None, description='Street address')
    address_city: str | None = Field(None, description='City')
    address_state: str | None = Field(None, description='State')
    address_zipcode: str | None = Field(None, description='ZIP code')
    address_country: str | None = Field(None, description='Country')
    credit_limit: float | None = Field(None, description='Credit limit')
    credit_balance: float | None = Field(None, description='Current balance')
    location_consent_given: bool | None = Field(
        None, description='Whether location consent is given'
    )
    last_app_location_latitude: float | None = Field(
        None, description='Last app location latitude'
    )
    last_app_location_longitude: float | None = Field(
        None, description='Last app location longitude'
    )
    last_app_location_timestamp: datetime | None = Field(
        None, description='Last app location timestamp'
    )
    lastAppLocationAccuracy: float | None = Field(
        None, description='Last app location accuracy'
    )


@router.get('/', response_model=list[UserOut])
async def get_users(
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """Get all users with optional filtering"""
    try:
        query = select(User).options(
            selectinload(User.creditCards),
            selectinload(User.transactions),
        )

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        users = result.scalars().all()

        return [
            {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': user.phone_number,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                'credit_cards_count': len(user.creditCards),
                'transactions_count': len(user.transactions),
            }
            for user in users
        ]
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get('/{user_id}', response_model=UserOut)
async def get_user(user_id: str, session: AsyncSession = Depends(get_db)):
    try:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.creditCards),
                selectinload(User.transactions),
            )
            .where(User.id == user_id)
        )
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')
    except SQLAlchemyError as err:
        # Surface DB errors with proper exception chaining
        raise HTTPException(status_code=500, detail=str(err)) from err

    # simple aggregation: counts
    credit_cards_count = len(user.creditCards)
    transactions_count = len(user.transactions)

    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': user.phone_number,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'credit_cards_count': credit_cards_count,
        'transactions_count': transactions_count,
        # Location fields
        'location_consent_given': user.location_consent_given,
        'last_app_location_latitude': user.last_app_location_latitude,
        'last_app_location_longitude': user.last_app_location_longitude,
        'last_app_location_timestamp': user.last_app_location_timestamp.isoformat()
        if user.last_app_location_timestamp
        else None,
        'last_app_location_accuracy': user.last_app_location_accuracy,
        'last_transaction_latitude': user.last_transaction_latitude,
        'last_transaction_longitude': user.last_transaction_longitude,
        'last_transaction_timestamp': user.last_transaction_timestamp.isoformat()
        if user.last_transaction_timestamp
        else None,
        'last_transaction_city': user.last_transaction_city,
        'last_transaction_state': user.last_transaction_state,
        'last_transaction_country': user.last_transaction_country,
    }


@router.get('/profile', response_model=UserOut)
async def get_current_user_profile(session: AsyncSession = Depends(get_db)):
    """Get the current logged-in user profile. For now, returns the first user from the database."""
    try:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.creditCards),
                selectinload(User.transactions),
            )
            .limit(1)
        )
        user: User | None = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail='No users found in the system')

    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err

    # Simple aggregation: counts
    credit_cards_count = len(user.creditCards)
    transactions_count = len(user.transactions)

    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': user.phone_number,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'credit_cards_count': credit_cards_count,
        'transactions_count': transactions_count,
    }


@router.post('', response_model=UserOut)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_db)):
    """Create a new user"""
    try:
        # Check if user with email already exists
        existing = await session.execute(
            select(User).where(User.email == payload.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail='User with this email already exists'
            )

        user = User(
            id=str(uuid.uuid4()),
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'credit_cards_count': 0,
            'transactions_count': 0,
        }
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.put('/{user_id}', response_model=UserOut)
async def update_user(
    user_id: str, payload: UserUpdate, session: AsyncSession = Depends(get_db)
):
    """Update an existing user"""
    try:
        # Check if user exists
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.creditCards),
                selectinload(User.transactions),
            )
            .where(User.id == user_id)
        )
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Check if email is being updated and if it already exists
        if payload.email and payload.email != user.email:
            existing = await session.execute(
                select(User).where(User.email == payload.email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=400, detail='User with this email already exists'
                )

        # Build update data
        update_data = {}
        for field, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value

        if update_data:
            from datetime import datetime

            update_data['updated_at'] = datetime.utcnow()

            # Update the user object
            for field, value in update_data.items():
                setattr(user, field, value)

            await session.commit()
            await session.refresh(user)

        credit_cards_count = len(user.creditCards)
        transactions_count = len(user.transactions)

        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'credit_cards_count': credit_cards_count,
            'transactions_count': transactions_count,
        }
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.delete('/{user_id}')
async def delete_user(user_id: str, session: AsyncSession = Depends(get_db)):
    """Delete a user and all associated data"""
    try:
        # Check if user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Delete the user (cascade will handle related data)
        await session.delete(user)
        await session.commit()

        return {'message': 'User deleted successfully'}
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get('/{user_id}/rules')
async def get_user_rules(user_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(AlertRule).where(AlertRule.user_id == user_id)
    )
    rules = result.scalars().all()
    return [
        {
            'id': r.id,
            'user_id': r.user_id,
            'name': r.name,
            'description': r.description,
            'is_active': r.is_active,
            'alert_type': r.alert_type.value,
            'notification_methods': [m.value for m in (r.notification_methods or [])],
        }
        for r in rules
    ]


@router.get('/{user_id}/transactions')
async def get_user_transactions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """Get all transactions for a specific user"""
    try:
        # Check if user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        from db.models import Transaction

        query = select(Transaction).where(Transaction.user_id == user_id)
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        transactions = result.scalars().all()

        return [
            {
                'id': tx.id,
                'amount': float(tx.amount) if tx.amount is not None else None,
                'currency': tx.currency,
                'description': tx.description,
                'merchant_name': tx.merchant_name,
                'merchant_category': tx.merchant_category,
                'transaction_date': tx.transaction_date.isoformat()
                if tx.transaction_date
                else None,
                'transaction_type': tx.transaction_type.value,
                'status': tx.status.value,
            }
            for tx in transactions
        ]
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get('/{user_id}/credit-cards')
async def get_user_credit_cards(
    user_id: str, is_active: bool | None = None, session: AsyncSession = Depends(get_db)
):
    """Get all credit cards for a specific user"""
    try:
        # Check if user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        from db.models import CreditCard

        query = select(CreditCard).where(CreditCard.user_id == user_id)

        if is_active is not None:
            query = query.where(CreditCard.is_active == is_active)

        result = await session.execute(query)
        cards = result.scalars().all()

        return [
            {
                'id': card.id,
                'card_number': card.card_number,
                'card_type': card.card_type,
                'bank_name': card.bank_name,
                'card_holder_name': card.card_holder_name,
                'expiry_month': card.expiry_month,
                'expiry_year': card.expiry_year,
                'is_active': card.is_active,
                'created_at': card.created_at.isoformat() if card.created_at else None,
                'updated_at': card.updated_at.isoformat() if card.updated_at else None,
            }
            for card in cards
        ]
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.patch('/{user_id}/deactivate')
async def deactivate_user(user_id: str, session: AsyncSession = Depends(get_db)):
    """Deactivate a user (soft delete)"""
    try:
        # Check if user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        user.is_active = False
        from datetime import datetime

        user.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(user)

        return {'message': 'User deactivated successfully', 'is_active': user.is_active}
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.patch('/{user_id}/activate')
async def activate_user(user_id: str, session: AsyncSession = Depends(get_db)):
    """Activate a user"""
    try:
        # Check if user exists
        result = await session.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        user.is_active = True
        from datetime import datetime

        user.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(user)

        return {'message': 'User activated successfully', 'is_active': user.is_active}
    except SQLAlchemyError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.post('/location', response_model=dict)
async def update_user_location(
    payload: LocationUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Update user location when frontend captures GPS coordinates"""
    try:
        user_id = current_user['id']

        # Update user location in database
        from datetime import datetime

        current_time = datetime.now(UTC)

        # Get the user first
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Update location fields
        user.location_consent_given = payload.location_consent_given
        user.last_app_location_latitude = payload.last_app_location_latitude
        user.last_app_location_longitude = payload.last_app_location_longitude
        user.last_app_location_timestamp = current_time
        user.last_app_location_accuracy = payload.last_app_location_accuracy
        user.updated_at = current_time

        await session.commit()

        return {
            'success': True,
            'message': 'Location updated successfully',
            'location': {
                'latitude': payload.last_app_location_latitude,
                'longitude': payload.last_app_location_longitude,
                'accuracy': payload.last_app_location_accuracy,
                'timestamp': current_time.isoformat(),
            },
        }

    except SQLAlchemyError as err:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f'Database error: {str(err)}'
        ) from err
    except Exception as err:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f'Unexpected error: {str(err)}'
        ) from err

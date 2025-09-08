"""Transaction endpoints"""

import uuid
from datetime import datetime

from db import get_db
from db.models import CreditCard, Transaction, User
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.transaction import (
    CategorySpending,
    CreditCardCreate,
    CreditCardOut,
    CreditCardUpdate,
    TransactionCreate,
    TransactionOut,
    TransactionSummary,
    TransactionUpdate,
)

router = APIRouter()


@router.get('/', response_model=list[TransactionOut])
async def get_transactions(
    user_id: str | None = Query(None, description='Filter by user ID'),
    credit_card_id: str | None = Query(None, description='Filter by credit card ID'),
    merchant_category: str | None = Query(
        None, description='Filter by merchant category'
    ),
    min_amount: float | None = Query(None, description='Minimum transaction amount'),
    max_amount: float | None = Query(None, description='Maximum transaction amount'),
    start_date: str | None = Query(None, description='Start date (ISO format)'),
    end_date: str | None = Query(None, description='End date (ISO format)'),
    limit: int = Query(100, description='Maximum number of transactions to return'),
    offset: int = Query(0, description='Number of transactions to skip'),
    session: AsyncSession = Depends(get_db),
):
    """Get all transactions with optional filtering"""
    query = select(Transaction)

    if user_id:
        query = query.where(Transaction.user_id == user_id)

    if credit_card_id:
        query = query.where(Transaction.credit_card_num == credit_card_id)

    if merchant_category:
        query = query.where(Transaction.merchant_category == merchant_category)

    if min_amount is not None:
        query = query.where(Transaction.amount >= min_amount)

    if max_amount is not None:
        query = query.where(Transaction.amount <= max_amount)

    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date >= start_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid start date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date <= end_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid end date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    query = query.order_by(Transaction.transaction_date.desc())
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    transactions = result.scalars().all()

    return [
        TransactionOut(
            id=tx.id,
            user_id=tx.user_id,
            credit_card_num=tx.credit_card_num,
            amount=float(tx.amount) if tx.amount is not None else None,
            currency=tx.currency,
            description=tx.description,
            merchant_name=tx.merchant_name,
            merchant_category=tx.merchant_category,
            transaction_date=tx.transaction_date.isoformat()
            if tx.transaction_date
            else None,
            transaction_type=tx.transaction_type,
            merchant_latitude=tx.merchant_latitude,
            merchant_longitude=tx.merchant_longitude,
            merchant_city=tx.merchant_city,
            merchant_state=tx.merchant_state,
            merchant_country=tx.merchant_country,
            merchant_zipcode=tx.merchant_zipcode,
            status=tx.status,
            authorization_code=tx.authorization_code,
            trans_num=tx.trans_num,
            created_at=tx.created_at.isoformat() if tx.created_at else None,
            updated_at=tx.updated_at.isoformat() if tx.updated_at else None,
        )
        for tx in transactions
    ]


@router.get('/{transaction_id}', response_model=TransactionOut)
async def get_transaction(transaction_id: str, session: AsyncSession = Depends(get_db)):
    """Get a specific transaction by ID"""
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx: Transaction | None = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail='Transaction not found')

    return TransactionOut(
        id=tx.id,
        user_id=tx.user_id,
        credit_card_num=tx.credit_card_num,
        amount=float(tx.amount) if tx.amount is not None else None,
        currency=tx.currency,
        description=tx.description,
        merchant_name=tx.merchant_name,
        merchant_category=tx.merchant_category,
        transaction_date=tx.transaction_date.isoformat()
        if tx.transaction_date
        else None,
        transaction_type=tx.transaction_type,
        merchant_latitude=tx.merchant_latitude,
        merchant_longitude=tx.merchant_longitude,
        merchant_city=tx.merchant_city,
        merchant_state=tx.merchant_state,
        merchant_country=tx.merchant_country,
        merchant_zipcode=tx.merchant_zipcode,
        status=tx.status,
        authorization_code=tx.authorization_code,
        trans_num=tx.trans_num,
        created_at=tx.created_at.isoformat() if tx.created_at else None,
        updated_at=tx.updated_at.isoformat() if tx.updated_at else None,
    )


@router.post('', response_model=TransactionOut)
async def create_transaction(
    payload: TransactionCreate, session: AsyncSession = Depends(get_db)
):
    """Create a new transaction"""
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    # Verify credit card exists
    # card_result = await session.execute(
    #     select(CreditCard).where(CreditCard.id == payload.credit_card_num)
    # )
    # card = card_result.scalar_one_or_none()
    # if not card:
    #     raise HTTPException(status_code=404, detail='Credit card not found')

    # Parse the transaction date string to datetime object
    from datetime import datetime

    try:
        transaction_date = datetime.fromisoformat(
            payload.transaction_date.replace('Z', '+00:00')
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
        ) from e

    tx = Transaction(
        id=payload.id,
        user_id=payload.user_id,
        credit_card_num=payload.credit_card_num,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        merchant_name=payload.merchant_name,
        merchant_category=payload.merchant_category,
        transaction_date=transaction_date,
        transaction_type=payload.transaction_type,
        merchant_longitude=payload.merchant_longitude,
        merchant_latitude=payload.merchant_latitude,
        merchant_city=payload.merchant_city,
        merchant_state=payload.merchant_state,
        merchant_country=payload.merchant_country,
        merchant_zipcode=payload.merchant_zipcode,
        status=payload.status,
        authorization_code=payload.authorization_code,
        trans_num=payload.trans_num,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)

    return TransactionOut(
        id=tx.id,
        user_id=tx.user_id,
        credit_card_num=tx.credit_card_num,
        amount=float(tx.amount) if tx.amount is not None else None,
        currency=tx.currency,
        description=tx.description,
        merchant_name=tx.merchant_name,
        merchant_category=tx.merchant_category,
        transaction_date=tx.transaction_date.isoformat()
        if tx.transaction_date
        else None,
        transaction_type=tx.transaction_type,
        merchant_longitude=tx.merchant_longitude,
        merchant_latitude=tx.merchant_latitude,
        merchant_city=tx.merchant_city,
        merchant_state=tx.merchant_state,
        merchant_country=tx.merchant_country,
        merchant_zipcode=tx.merchant_zipcode,
        status=tx.status,
        authorization_code=tx.authorization_code,
        trans_num=tx.trans_num,
        created_at=tx.created_at.isoformat() if tx.created_at else None,
        updated_at=tx.updated_at.isoformat() if tx.updated_at else None,
    )


@router.put('/{transaction_id}', response_model=TransactionOut)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update an existing transaction"""
    # Check if transaction exists
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail='Transaction not found')

    # Build update data
    update_data = {}
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            # Handle date parsing for transaction_date
            if field == 'transaction_date':
                try:
                    from datetime import datetime

                    update_data[field] = datetime.fromisoformat(
                        value.replace('Z', '+00:00')
                    )
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid transaction date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
                    ) from e
            else:
                update_data[field] = value

    if update_data:
        from datetime import datetime

        update_data['updated_at'] = datetime.utcnow()
        await session.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(**update_data)
        )
        await session.commit()
        await session.refresh(tx)

    return TransactionOut(
        id=tx.id,
        user_id=tx.user_id,
        credit_card_num=tx.credit_card_num,
        amount=float(tx.amount) if tx.amount is not None else None,
        currency=tx.currency,
        description=tx.description,
        merchant_name=tx.merchant_name,
        merchant_category=tx.merchant_category,
        transaction_date=tx.transaction_date.isoformat()
        if tx.transaction_date
        else None,
        transaction_type=tx.transaction_type,
        merchant_city=tx.merchant_city,
        merchant_state=tx.merchant_state,
        merchant_country=tx.merchant_country,
        merchant_zipcode=tx.merchant_zipcode,
        merchant_latitude=tx.merchant_latitude,
        merchant_longitude=tx.merchant_longitude,
        status=tx.status,
        authorization_code=tx.authorization_code,
        trans_num=tx.trans_num,
        created_at=tx.created_at.isoformat() if tx.created_at else None,
        updated_at=tx.updated_at.isoformat() if tx.updated_at else None,
    )


@router.delete('/{transaction_id}')
async def delete_transaction(
    transaction_id: str, session: AsyncSession = Depends(get_db)
):
    """Delete a transaction"""
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail='Transaction not found')

    await session.delete(tx)
    await session.commit()

    return {'message': 'Transaction deleted successfully'}


# Credit Card endpoints
@router.get('/cards', response_model=list[CreditCardOut])
async def get_credit_cards(
    user_id: str | None = Query(None, description='Filter by user ID'),
    is_active: bool | None = Query(None, description='Filter by active status'),
    session: AsyncSession = Depends(get_db),
):
    """Get all credit cards with optional filtering"""
    query = select(CreditCard)

    if user_id:
        query = query.where(CreditCard.user_id == user_id)

    if is_active is not None:
        query = query.where(CreditCard.is_active == is_active)

    result = await session.execute(query)
    cards = result.scalars().all()

    return [
        CreditCardOut(
            id=card.id,
            user_id=card.user_id,
            card_number=card.card_number,
            card_type=card.card_type,
            bank_name=card.bank_name,
            card_holder_name=card.card_holder_name,
            expiry_month=card.expiry_month,
            expiry_year=card.expiry_year,
            is_active=card.is_active,
            created_at=card.created_at.isoformat() if card.created_at else None,
            updated_at=card.updated_at.isoformat() if card.updated_at else None,
        )
        for card in cards
    ]


@router.get('/cards/{card_id}', response_model=CreditCardOut)
async def get_credit_card(card_id: str, session: AsyncSession = Depends(get_db)):
    """Get a specific credit card by ID"""
    result = await session.execute(select(CreditCard).where(CreditCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail='Credit card not found')

    return CreditCardOut(
        id=card.id,
        user_id=card.user_id,
        card_number=card.card_number,
        card_type=card.card_type,
        bank_name=card.bank_name,
        card_holder_name=card.card_holder_name,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        is_active=card.is_active,
        created_at=card.created_at.isoformat() if card.created_at else None,
        updated_at=card.updated_at.isoformat() if card.updated_at else None,
    )


@router.post('/cards', response_model=CreditCardOut)
async def create_credit_card(
    payload: CreditCardCreate, session: AsyncSession = Depends(get_db)
):
    """Create a new credit card"""
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    card = CreditCard(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        card_number=payload.card_number,
        card_type=payload.card_type,
        bank_name=payload.bank_name,
        card_holder_name=payload.card_holder_name,
        expiry_month=payload.expiry_month,
        expiry_year=payload.expiry_year,
        is_active=payload.is_active,
    )

    session.add(card)
    await session.commit()
    await session.refresh(card)

    return CreditCardOut(
        id=card.id,
        user_id=card.user_id,
        card_number=card.card_number,
        card_type=card.card_type,
        bank_name=card.bank_name,
        card_holder_name=card.card_holder_name,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        is_active=card.is_active,
        created_at=card.created_at.isoformat() if card.created_at else None,
        updated_at=card.updated_at.isoformat() if card.updated_at else None,
    )


@router.put('/cards/{card_id}', response_model=CreditCardOut)
async def update_credit_card(
    card_id: str, payload: CreditCardUpdate, session: AsyncSession = Depends(get_db)
):
    """Update an existing credit card"""
    # Check if card exists
    result = await session.execute(select(CreditCard).where(CreditCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail='Credit card not found')

    # Build update data
    update_data = {}
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    if update_data:
        from datetime import datetime

        update_data['updated_at'] = datetime.utcnow()
        await session.execute(
            update(CreditCard).where(CreditCard.id == card_id).values(**update_data)
        )
        await session.commit()
        await session.refresh(card)

    return CreditCardOut(
        id=card.id,
        user_id=card.user_id,
        card_number=card.card_number,
        card_type=card.card_type,
        bank_name=card.bank_name,
        card_holder_name=card.card_holder_name,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
        is_active=card.is_active,
        created_at=card.created_at.isoformat() if card.created_at else None,
        updated_at=card.updated_at.isoformat() if card.updated_at else None,
    )


@router.delete('/cards/{card_id}')
async def delete_credit_card(card_id: str, session: AsyncSession = Depends(get_db)):
    """Delete a credit card"""
    result = await session.execute(select(CreditCard).where(CreditCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail='Credit card not found')

    await session.delete(card)
    await session.commit()

    return {'message': 'Credit card deleted successfully'}


# Analysis endpoints
@router.get('/analysis/summary/{user_id}', response_model=TransactionSummary)
async def get_transaction_summary(
    user_id: str,
    start_date: str | None = Query(None, description='Start date (ISO format)'),
    end_date: str | None = Query(None, description='End date (ISO format)'),
    session: AsyncSession = Depends(get_db),
):
    """Get transaction summary for a user"""
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    query = select(Transaction).where(Transaction.user_id == user_id)

    if start_date:
        try:
            from datetime import datetime

            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date >= start_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid start date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    if end_date:
        try:
            from datetime import datetime

            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date <= end_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid end date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    result = await session.execute(query)
    transactions = result.scalars().all()

    if not transactions:
        return TransactionSummary(
            totalTransactions=0,
            totalAmount=0.0,
            averageAmount=0.0,
            largestTransaction=0.0,
            smallestTransaction=0.0,
        )

    amounts = [float(tx.amount) for tx in transactions if tx.amount is not None]

    return TransactionSummary(
        totalTransactions=len(transactions),
        totalAmount=sum(amounts),
        averageAmount=sum(amounts) / len(amounts) if amounts else 0.0,
        largestTransaction=max(amounts) if amounts else 0.0,
        smallestTransaction=min(amounts) if amounts else 0.0,
    )


@router.get('/analysis/categories/{user_id}', response_model=list[CategorySpending])
async def get_category_spending(
    user_id: str,
    start_date: str | None = Query(None, description='Start date (ISO format)'),
    end_date: str | None = Query(None, description='End date (ISO format)'),
    session: AsyncSession = Depends(get_db),
):
    """Get spending breakdown by category for a user"""
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    query = select(Transaction).where(Transaction.user_id == user_id)

    if start_date:
        try:
            from datetime import datetime

            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date >= start_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid start date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    if end_date:
        try:
            from datetime import datetime

            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Transaction.transaction_date <= end_datetime)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid end date format. Use ISO format (e.g., '2024-01-16T14:45:00Z')",
            ) from e

    result = await session.execute(query)
    transactions = result.scalars().all()

    # Group by category
    category_data = {}
    for tx in transactions:
        category = tx.merchant_category
        amount = float(tx.amount) if tx.amount is not None else 0.0

        if category not in category_data:
            category_data[category] = {'total': 0.0, 'count': 0, 'amounts': []}

        category_data[category]['total'] += amount
        category_data[category]['count'] += 1
        category_data[category]['amounts'].append(amount)

    return [
        CategorySpending(
            category=category,
            totalAmount=data['total'],
            transactionCount=data['count'],
            averageAmount=data['total'] / data['count'] if data['count'] > 0 else 0.0,
        )
        for category, data in category_data.items()
    ]

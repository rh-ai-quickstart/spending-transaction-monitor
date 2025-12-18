"""Alert endpoints for managing alert rules and notifications"""

from datetime import UTC, datetime
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from db.models import AlertNotification, AlertRule, NotificationMethod, User
from services.recommendations.alert_recommendation_service import (
    AlertRecommendationService,
)
from services.recommendations.background_recommendation_service import (
    background_recommendation_service,
)
from services.recommendations.recommendation_job_queue import (
    recommendation_job_queue,
)
from services.transactions.transaction_service import TransactionService
from services.users.user_service import UserService

from ..auth.middleware import require_authentication
from ..schemas.alert import (
    AlertNotificationCreate,
    AlertNotificationOut,
    AlertNotificationUpdate,
    AlertRuleOut,
    AlertRuleUpdate,
)
from ..services.alerts.alert_rule_service import AlertRuleService
from ..services.notifications import Context, NoopStrategy, SmtpStrategy

router = APIRouter()
logger = logging.getLogger(__name__)


class AlertRuleCreateRequest(BaseModel):
    alert_rule: dict
    sql_query: str
    natural_language_query: str


class AlertRuleValidationRequest(BaseModel):
    natural_language_query: str


class AlertRuleValidationResponse(BaseModel):
    status: str  # 'valid', 'warning', 'invalid', 'error'
    message: str
    alert_rule: dict | None = None
    sql_query: str | None = None
    sql_description: str | None = None
    similarity_result: dict | None = None
    valid_sql: bool = False
    transaction_used: dict | None = None
    user_id: str | None = None
    validation_timestamp: str | None = None


# Initialize service instances
alert_rule_service = AlertRuleService()
user_service = UserService()
transaction_service = TransactionService()
recommendation_service = AlertRecommendationService()


# Alert Rules endpoints
@router.post('/rules/validate', response_model=AlertRuleValidationResponse)
async def validate_alert_rule(
    payload: AlertRuleValidationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Validate an alert rule with similarity checking and detailed analysis"""
    print('DEBUG: Current user:', current_user)
    print('Validating alert rule for user:', current_user['id'], 'payload:', payload)

    validation_result = await alert_rule_service.validate_alert_rule(
        payload.natural_language_query, current_user['id'], session
    )
    try:
        return AlertRuleValidationResponse(**validation_result)
    except Exception as e:
        print('DEBUG: Error validating alert rule:', e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/rules', response_model=list[AlertRuleOut])
async def get_alert_rules(
    user_id: str | None = Query(None, description='Filter by user ID'),
    is_active: bool | None = Query(None, description='Filter by active status'),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get all alert rules with optional filtering"""
    query = select(AlertRule)

    # Authorization: Non-admin users can only see their own alert rules
    if 'admin' not in current_user.get('roles', []):
        # Force user_id filter to current user for non-admins
        query = query.where(AlertRule.user_id == current_user['id'])
    elif user_id:
        # Admins can filter by any user_id if provided
        query = query.where(AlertRule.user_id == user_id)

    if is_active is not None:
        query = query.where(AlertRule.is_active == is_active)

    result = await session.execute(query)
    rules = result.scalars().all()

    return [
        AlertRuleOut(
            id=rule.id,
            user_id=rule.user_id,
            name=rule.name,
            description=rule.description,
            is_active=rule.is_active,
            alert_type=rule.alert_type,
            amount_threshold=float(rule.amount_threshold)
            if rule.amount_threshold
            else None,
            merchant_category=rule.merchant_category,
            merchant_name=rule.merchant_name,
            location=rule.location,
            timeframe=rule.timeframe,
            natural_language_query=rule.natural_language_query,
            notification_methods=rule.notification_methods,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
            last_triggered=rule.last_triggered.isoformat()
            if rule.last_triggered
            else None,
            trigger_count=rule.trigger_count,
        )
        for rule in rules
    ]


@router.get('/rules/{rule_id}', response_model=AlertRuleOut)
async def get_alert_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get a specific alert rule by ID"""
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail='Alert rule not found')

    return AlertRuleOut(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        description=rule.description,
        is_active=rule.is_active,
        alert_type=rule.alert_type,
        amount_threshold=float(rule.amount_threshold)
        if rule.amount_threshold
        else None,
        merchant_category=rule.merchant_category,
        merchant_name=rule.merchant_name,
        location=rule.location,
        timeframe=rule.timeframe,
        natural_language_query=rule.natural_language_query,
        sql_query=rule.sql_query,
        notification_methods=rule.notification_methods,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
        last_triggered=rule.last_triggered.isoformat() if rule.last_triggered else None,
        trigger_count=rule.trigger_count,
    )


@router.post('/rules', response_model=AlertRuleOut)
async def create_alert_rule(
    payload: AlertRuleCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Create a new alert rule from pre-validated data"""
    print(
        'Creating alert rule from validation for user:',
        current_user['id'],
        'payload:',
        payload,
    )

    # Extract alert rule data from payload
    alert_rule_data = payload.alert_rule
    if not alert_rule_data:
        raise HTTPException(status_code=400, detail='Alert rule data not provided')

    rule = AlertRule(
        id=str(uuid.uuid4()),
        user_id=current_user['id'],
        name=alert_rule_data.get('name'),
        description=alert_rule_data.get('description'),
        is_active=True,
        alert_type=alert_rule_data.get('alert_type'),
        amount_threshold=alert_rule_data.get('amount_threshold'),
        merchant_category=alert_rule_data.get('merchant_category'),
        merchant_name=alert_rule_data.get('merchant_name'),
        location=alert_rule_data.get('location'),
        timeframe=alert_rule_data.get('timeframe'),
        natural_language_query=payload.natural_language_query,
        sql_query=payload.sql_query,
        notification_methods=None,
    )

    session.add(rule)
    await session.commit()
    await session.refresh(rule)

    # Log alert creation for ML model retraining
    try:
        from src.services.recommendations.ml.training import log_user_alert_action

        await log_user_alert_action(session, current_user['id'], rule.id, 'created')
    except Exception as e:
        logger.warning(f'Failed to log alert action: {e}')

    return AlertRuleOut(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        description=rule.description,
        is_active=rule.is_active,
        alert_type=rule.alert_type,
        amount_threshold=float(rule.amount_threshold)
        if rule.amount_threshold
        else None,
        merchant_category=rule.merchant_category,
        merchant_name=rule.merchant_name,
        location=rule.location,
        timeframe=rule.timeframe,
        natural_language_query=rule.natural_language_query,
        sql_query=rule.sql_query,
        notification_methods=rule.notification_methods,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
        last_triggered=rule.last_triggered.isoformat() if rule.last_triggered else None,
        trigger_count=rule.trigger_count,
    )


@router.put('/rules/{rule_id}', response_model=AlertRuleOut)
async def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Update an existing alert rule"""
    # Check if rule exists
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Alert rule not found')

    # Build update data
    update_data = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    if update_data:
        update_data['updated_at'] = datetime.now(UTC)
        await session.execute(
            update(AlertRule).where(AlertRule.id == rule_id).values(**update_data)
        )
        await session.commit()
        await session.refresh(rule)

    return AlertRuleOut(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        description=rule.description,
        is_active=rule.is_active,
        alert_type=rule.alert_type,
        amount_threshold=float(rule.amount_threshold)
        if rule.amount_threshold
        else None,
        merchant_category=rule.merchant_category,
        merchant_name=rule.merchant_name,
        location=rule.location,
        timeframe=rule.timeframe,
        natural_language_query=rule.natural_language_query,
        sql_query=rule.sql_query,
        notification_methods=rule.notification_methods,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
        last_triggered=rule.last_triggered.isoformat() if rule.last_triggered else None,
        trigger_count=rule.trigger_count,
    )


@router.delete('/rules/{rule_id}')
async def delete_alert_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Delete an alert rule and all associated notifications"""
    from sqlalchemy import delete as sql_delete

    # First check if the rule exists
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Alert rule not found')

    # First, delete all associated notifications using bulk delete
    notification_delete_result = await session.execute(
        sql_delete(AlertNotification).where(AlertNotification.alert_rule_id == rule_id)
    )
    notifications_deleted = notification_delete_result.rowcount

    # Now delete the alert rule
    await session.delete(rule)
    await session.commit()

    return {
        'message': f'Alert rule deleted successfully. {notifications_deleted} associated notifications were also deleted.'
    }


# Alert Notifications endpoints
@router.get('/notifications', response_model=list[AlertNotificationOut])
async def get_alert_notifications(
    alert_rule_id: str | None = Query(None, description='Filter by alert rule ID'),
    status: str | None = Query(None, description='Filter by notification status'),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get all alert notifications with optional filtering"""
    query = select(AlertNotification)

    if current_user['id']:
        query = query.where(AlertNotification.user_id == current_user['id'])

    if alert_rule_id:
        query = query.where(AlertNotification.alert_rule_id == alert_rule_id)

    if status:
        query = query.where(AlertNotification.status == status)

    result = await session.execute(query)
    notifications = result.scalars().all()

    return [
        AlertNotificationOut(
            id=notification.id,
            user_id=notification.user_id,
            alert_rule_id=notification.alert_rule_id,
            transaction_id=notification.transaction_id,
            title=notification.title,
            message=notification.message,
            notification_method=notification.notification_method,
            status=notification.status,
            sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
            delivered_at=notification.delivered_at.isoformat()
            if notification.delivered_at
            else None,
            read_at=notification.read_at.isoformat() if notification.read_at else None,
            created_at=notification.created_at.isoformat(),
            updated_at=notification.updated_at.isoformat(),
        )
        for notification in notifications
    ]


@router.get('/notifications/{notification_id}', response_model=AlertNotificationOut)
async def get_alert_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get a specific alert notification by ID"""
    result = await session.execute(
        select(AlertNotification).where(AlertNotification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail='Alert notification not found')

    return AlertNotificationOut(
        id=notification.id,
        user_id=notification.user_id,
        alert_rule_id=notification.alert_rule_id,
        transaction_id=notification.transaction_id,
        title=notification.title,
        message=notification.message,
        notification_method=notification.notification_method,
        status=notification.status,
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        delivered_at=notification.delivered_at.isoformat()
        if notification.delivered_at
        else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
        updated_at=notification.updated_at.isoformat(),
    )


@router.post('/notifications', response_model=AlertNotificationOut)
async def create_alert_notification(
    payload: AlertNotificationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Create a new alert notification"""
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    # Verify alert rule exists
    rule_result = await session.execute(
        select(AlertRule).where(AlertRule.id == payload.alert_rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Alert rule not found')

    notification = AlertNotification(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        alert_rule_id=payload.alert_rule_id,
        transaction_id=payload.transaction_id,
        title=payload.title,
        message=payload.message,
        notification_method=payload.notification_method,
        status=payload.status,
    )

    strategy = NoopStrategy()

    if payload.notification_method == NotificationMethod.EMAIL:
        strategy = SmtpStrategy()

    ctx = Context(strategy)
    notification = await ctx.send_notification(notification, session)

    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    return AlertNotificationOut(
        id=notification.id,
        user_id=notification.user_id,
        alert_rule_id=notification.alert_rule_id,
        transaction_id=notification.transaction_id,
        title=notification.title,
        message=notification.message,
        notification_method=notification.notification_method,
        status=notification.status,
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        delivered_at=notification.delivered_at.isoformat()
        if notification.delivered_at
        else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
        updated_at=notification.updated_at.isoformat(),
    )


@router.put('/notifications/{notification_id}', response_model=AlertNotificationOut)
async def update_alert_notification(
    notification_id: str,
    payload: AlertNotificationUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Update an existing alert notification"""
    # Check if notification exists
    result = await session.execute(
        select(AlertNotification).where(AlertNotification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail='Alert notification not found')

    # Build update data
    update_data = {}
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            if field in ['sent_at', 'delivered_at', 'read_at'] and value:
                update_data[field] = datetime.fromisoformat(value)
            else:
                update_data[field] = value

    if update_data:
        update_data['updated_at'] = datetime.now(UTC)
        await session.execute(
            update(AlertNotification)
            .where(AlertNotification.id == notification_id)
            .values(**update_data)
        )
        await session.commit()
        await session.refresh(notification)

    return AlertNotificationOut(
        id=notification.id,
        user_id=notification.user_id,
        alert_rule_id=notification.alert_rule_id,
        transaction_id=notification.transaction_id,
        title=notification.title,
        message=notification.message,
        notification_method=notification.notification_method,
        status=notification.status,
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        delivered_at=notification.delivered_at.isoformat()
        if notification.delivered_at
        else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
        updated_at=notification.updated_at.isoformat(),
    )


@router.delete('/notifications/{notification_id}')
async def delete_alert_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Delete an alert notification"""
    result = await session.execute(
        select(AlertNotification).where(AlertNotification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail='Alert notification not found')

    await session.delete(notification)
    await session.commit()

    return {'message': 'Alert notification deleted successfully'}


# Additional utility endpoints
@router.get('/rules/{rule_id}/notifications', response_model=list[AlertNotificationOut])
async def get_notifications_for_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get all notifications for a specific alert rule"""
    result = await session.execute(
        select(AlertNotification).where(AlertNotification.alert_rule_id == rule_id)
    )
    notifications = result.scalars().all()

    return [
        AlertNotificationOut(
            id=notification.id,
            user_id=notification.user_id,
            alert_rule_id=notification.alert_rule_id,
            transaction_id=notification.transaction_id,
            title=notification.title,
            message=notification.message,
            notification_method=notification.notification_method,
            status=notification.status,
            sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
            delivered_at=notification.delivered_at.isoformat()
            if notification.delivered_at
            else None,
            read_at=notification.read_at.isoformat() if notification.read_at else None,
            created_at=notification.created_at.isoformat(),
            updated_at=notification.updated_at.isoformat(),
        )
        for notification in notifications
    ]


@router.post('/rules/{rule_id}/trigger')
async def trigger_alert_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Manually trigger an alert rule (for testing purposes)"""
    print(f'DEBUG: Starting trigger_alert_rule endpoint for rule_id: {rule_id}')

    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Alert rule not found')

    print(f'DEBUG: Found rule: {rule.id}, user_id: {rule.user_id}')

    print('DEBUG: About to get latest transaction')
    transaction = await transaction_service.get_latest_transaction(
        rule.user_id, session
    )
    print(f'DEBUG: Got transaction: {transaction}')
    if transaction is None:
        raise ValueError('No transaction found for user')

    print('DEBUG: About to get user')
    user = await user_service.get_user(rule.user_id, session)
    print(f'DEBUG: Got user: {user}')
    if user is None:
        # Fallback to dummy user data for testing
        raise ValueError('User data not found')

    try:
        print('DEBUG: About to call trigger_alert_rule')
        trigger_result = await alert_rule_service.trigger_alert_rule(
            rule, transaction, user, session
        )
        print(f'DEBUG: trigger_alert_rule completed: {trigger_result}')
        return trigger_result
    except ValueError as e:
        # Handle business logic errors (inactive rule, no transaction)
        if 'not active' in str(e):
            raise HTTPException(status_code=400, detail=str(e)) from e
        elif 'No transaction found' in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Alert trigger failed: {str(e)}',
            'error': str(e),
        }


class AlertRecommendationResponse(BaseModel):
    user_id: str
    recommendation_type: str
    recommendations: list[dict]
    generated_at: str


class RecommendationCategoriesResponse(BaseModel):
    categories: dict[str, list[str]]


# Alert Recommendations endpoints
@router.get('/recommendations', response_model=AlertRecommendationResponse)
async def get_alert_recommendations(
    force_refresh: bool = Query(
        False, description='Force regeneration of recommendations'
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get personalized alert recommendations for the current user"""
    try:
        user_id = current_user['id']

        # First, try to get cached recommendations unless force refresh is requested
        if not force_refresh:
            cached_recommendations = (
                await background_recommendation_service.get_cached_recommendations(
                    user_id, session
                )
            )
            if cached_recommendations:
                return AlertRecommendationResponse(**cached_recommendations)

        # If no cached recommendations or force refresh, enqueue background job
        if force_refresh:
            # For force refresh, enqueue job and return placeholder immediately
            await recommendation_job_queue.enqueue_single_user_job(user_id)
            logger.info(f'Enqueued force refresh job for user {user_id}')
        else:
            # No cached recommendations found, enqueue background job
            await recommendation_job_queue.enqueue_single_user_job(user_id)
            logger.info(f'Enqueued background job for user {user_id}')

        # Return placeholder recommendations immediately while background job processes
        from services.recommendations.placeholder_recommendation_service import (
            PlaceholderRecommendationService,
        )

        placeholder_service = PlaceholderRecommendationService()

        # Get user data for placeholder recommendations
        user = await user_service.get_user(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        placeholder_recommendations = (
            placeholder_service.get_placeholder_recommendations(user)
        )
        return AlertRecommendationResponse(**placeholder_recommendations)

    except Exception as e:
        print(f'Error getting recommendations: {e}')
        raise HTTPException(
            status_code=500, detail=f'Failed to get recommendations: {str(e)}'
        ) from e


@router.get(
    '/recommendations/categories', response_model=RecommendationCategoriesResponse
)
async def get_recommendation_categories():
    """Get available recommendation categories for UI purposes"""
    try:
        categories = await recommendation_service.get_recommendation_categories()
        return RecommendationCategoriesResponse(categories=categories)
    except Exception as e:
        print(f'Error getting recommendation categories: {e}')
        raise HTTPException(
            status_code=500, detail=f'Failed to get recommendation categories: {str(e)}'
        ) from e


class RecommendationCreateRequest(BaseModel):
    title: str
    description: str
    natural_language_query: str
    category: str
    priority: str
    reasoning: str


@router.post('/recommendations/create-rule')
async def create_rule_from_recommendation(
    recommendation: RecommendationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Create an alert rule from a specific recommendation"""
    try:
        natural_language_query = recommendation.natural_language_query

        if not natural_language_query:
            raise HTTPException(
                status_code=400, detail='Recommendation does not contain a valid query'
            )

        # First validate the rule
        validation_result = await alert_rule_service.validate_alert_rule(
            natural_language_query, current_user['id'], session
        )

        if validation_result.get('status') not in ['valid', 'warning']:
            raise HTTPException(
                status_code=400,
                detail=f'Rule validation failed: {validation_result.get("message")}',
            )

        # Create the alert rule using the validated data
        alert_rule_data = validation_result.get('alert_rule', {})
        sql_query = validation_result.get('sql_query', '')

        # Create AlertRule object - use the recommendation title as the name
        rule = AlertRule(
            id=str(uuid.uuid4()),
            user_id=current_user['id'],
            name=recommendation.title,  # Always use recommendation title
            description=recommendation.description
            or alert_rule_data.get('description'),
            is_active=True,
            alert_type=alert_rule_data.get('alert_type'),
            amount_threshold=alert_rule_data.get('amount_threshold'),
            merchant_category=alert_rule_data.get('merchant_category'),
            merchant_name=alert_rule_data.get('merchant_name'),
            location=alert_rule_data.get('location'),
            timeframe=alert_rule_data.get('timeframe'),
            natural_language_query=natural_language_query,
            sql_query=sql_query,
            notification_methods=None,
        )

        session.add(rule)
        await session.commit()
        await session.refresh(rule)

        return {
            'message': 'Alert rule created successfully from recommendation',
            'rule_id': rule.id,
            'rule_name': rule.name,
            'recommendation_used': {
                'title': recommendation.title,
                'description': recommendation.description,
                'natural_language_query': recommendation.natural_language_query,
                'category': recommendation.category,
                'priority': recommendation.priority,
                'reasoning': recommendation.reasoning,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f'Error creating rule from recommendation: {e}')
        raise HTTPException(
            status_code=500,
            detail=f'Failed to create rule from recommendation: {str(e)}',
        ) from e


# Background Recommendation Management endpoints
class BackgroundJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class BulkRecommendationResponse(BaseModel):
    status: str
    total_users: int | None = None
    success_count: int | None = None
    error_count: int | None = None
    message: str


@router.post('/recommendations/generate-all', response_model=BulkRecommendationResponse)
async def generate_recommendations_for_all_users(
    current_user: dict = Depends(require_authentication),
):
    """Generate recommendations for all users in background (Admin only)"""

    # Check if user is admin
    if 'admin' not in current_user.get('roles', []):
        raise HTTPException(status_code=403, detail='Admin access required')

    try:
        job_id = await recommendation_job_queue.enqueue_all_users_job()

        return BulkRecommendationResponse(
            status='enqueued',
            message=f'Bulk recommendation generation job {job_id} has been enqueued',
        )

    except Exception as e:
        logger.error(f'Error enqueueing bulk recommendation job: {e}')
        raise HTTPException(
            status_code=500,
            detail=f'Failed to enqueue bulk recommendation job: {str(e)}',
        ) from e


@router.post('/recommendations/cleanup', response_model=BackgroundJobResponse)
async def cleanup_expired_recommendations(
    current_user: dict = Depends(require_authentication),
):
    """Cleanup expired cached recommendations (Admin only)"""

    # Check if user is admin
    if 'admin' not in current_user.get('roles', []):
        raise HTTPException(status_code=403, detail='Admin access required')

    try:
        job_id = await recommendation_job_queue.enqueue_cleanup_job()

        return BackgroundJobResponse(
            job_id=job_id, status='enqueued', message='Cleanup job has been enqueued'
        )

    except Exception as e:
        logger.error(f'Error enqueueing cleanup job: {e}')
        raise HTTPException(
            status_code=500, detail=f'Failed to enqueue cleanup job: {str(e)}'
        ) from e


@router.get('/recommendations/jobs/{job_id}')
async def get_recommendation_job_status(
    job_id: str,
    current_user: dict = Depends(require_authentication),
):
    """Get the status of a recommendation job (Admin only)"""

    # Check if user is admin
    if 'admin' not in current_user.get('roles', []):
        raise HTTPException(status_code=403, detail='Admin access required')

    job = recommendation_job_queue.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    return {
        'job_id': job.job_id,
        'job_type': job.job_type.value,
        'user_id': job.user_id,
        'status': job.status.value,
        'result': job.result,
        'error': job.error,
        'created_at': job.created_at,
    }


@router.get('/recommendations/metrics')
async def get_recommendation_metrics(
    last_n_minutes: int = Query(60, description='Minutes to look back for metrics'),
    current_user: dict = Depends(require_authentication),
):
    """Get recommendation generation performance metrics (Admin only)"""

    # Check if user is admin
    if 'admin' not in current_user.get('roles', []):
        raise HTTPException(status_code=403, detail='Admin access required')

    try:
        from services.recommendations.recommendation_metrics import (
            recommendation_metrics,
        )

        summary = recommendation_metrics.get_performance_summary(last_n_minutes)

        return {
            'time_range_minutes': last_n_minutes,
            'metrics': summary,
            'generated_at': datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f'Error getting recommendation metrics: {e}')
        raise HTTPException(
            status_code=500, detail=f'Failed to get metrics: {str(e)}'
        ) from e


@router.post('/recommendations/test-websocket')
async def test_websocket_notification(
    user_id: str = Query(..., description='User ID to send test notification to'),
    current_user: dict = Depends(require_authentication),
):
    """Test WebSocket notification (Admin only)"""

    # Check if user is admin
    if 'admin' not in current_user.get('roles', []):
        raise HTTPException(status_code=403, detail='Admin access required')

    try:
        from src.routes.websocket import notify_recommendations_ready

        test_recommendations = {
            'user_id': user_id,
            'recommendation_type': 'test',
            'recommendations': [
                {
                    'title': 'Test Recommendation',
                    'description': 'This is a test recommendation',
                    'natural_language_query': 'Test alert',
                    'category': 'test',
                    'priority': 'high',
                    'reasoning': 'This is a test notification',
                }
            ],
            'generated_at': datetime.now(UTC).isoformat(),
            'is_placeholder': False,
        }

        await notify_recommendations_ready(user_id, test_recommendations)

        return {
            'status': 'success',
            'message': f'Test WebSocket notification sent to user {user_id}',
            'user_id': user_id,
        }
    except Exception as e:
        logger.error(f'Error sending test WebSocket notification: {e}')
        raise HTTPException(
            status_code=500, detail=f'Failed to send test notification: {str(e)}'
        ) from e


@router.post('/recommendations/trigger-generation')
async def trigger_recommendation_generation(
    current_user: dict = Depends(require_authentication),
):
    """Manually trigger recommendation generation for the current user"""
    try:
        user_id = current_user['id']

        # Import the background service here to avoid startup issues
        from ..services.recommendations.background_recommendation_service import (
            background_recommendation_service,
        )

        # Generate recommendations synchronously
        result = (
            background_recommendation_service.generate_recommendations_for_user_sync(
                user_id
            )
        )

        return {
            'message': 'Recommendation generation triggered successfully',
            'user_id': user_id,
            'result': result,
        }

    except Exception as e:
        logger.error(f'Error triggering recommendation generation: {e}')
        raise HTTPException(
            status_code=500,
            detail=f'Failed to trigger recommendation generation: {str(e)}',
        ) from e

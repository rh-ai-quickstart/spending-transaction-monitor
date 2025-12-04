"""
FastAPI application entry point
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routes import alerts as alerts_routes
from .routes import health, websocket
from .routes import transactions as transactions_routes
from .routes import users as users_routes
from .services.alerts.alert_job_queue import alert_job_queue
from .services.recommendations.llm_thread_pool import llm_thread_pool
from .services.recommendations.recommendation_job_queue import (
    recommendation_job_queue,
)
from .services.recommendations.recommendation_scheduler import (
    recommendation_scheduler,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info('Starting up application...')

    # The recommendation generation will be triggered on-demand via API calls
    await llm_thread_pool.start()
    logger.info('LLM thread pool started')

    await recommendation_job_queue.start()
    logger.info('Recommendation service started')

    await alert_job_queue.start()
    logger.info('Alert monitoring service started')

    await recommendation_scheduler.start()
    logger.info('Recommendation scheduler started')

    yield

    await alert_job_queue.stop()
    logger.info('Alert monitoring service stopped')

    await recommendation_job_queue.stop()
    logger.info('Recommendation service stopped')

    await recommendation_scheduler.stop()
    logger.info('Recommendation scheduler stopped')

    await llm_thread_pool.stop()
    logger.info('LLM thread pool stopped')
    logger.info('Shutting down application...')


app = FastAPI(
    title='spending-monitor API',
    description='AI-powered alerts for credit card transactions',
    version='0.0.0',
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include all routers
app.include_router(health.router, prefix='/health', tags=['health'])
app.include_router(users_routes.router, prefix='/api/users', tags=['users'])
app.include_router(
    transactions_routes.router, prefix='/api/transactions', tags=['transactions']
)
app.include_router(alerts_routes.router, prefix='/api/alerts', tags=['alerts'])
app.include_router(websocket.router, prefix='/api', tags=['websocket'])


@app.get('/')
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {'message': 'Welcome to spending-monitor API'}

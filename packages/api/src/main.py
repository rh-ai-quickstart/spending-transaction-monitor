"""
FastAPI application entry point
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routes import alerts as alerts_routes
from .routes import health
from .routes import transactions as transactions_routes
from .routes import users as users_routes
from .services.alert_job_queue import alert_job_queue
from .services.recommendation_job_queue import recommendation_job_queue
from .services.recommendation_scheduler import recommendation_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info('Starting up application...')

    # Start the alert job queue
    await alert_job_queue.start()
    logger.info('Alert monitoring service started')

    # Start the recommendation job queue
    await recommendation_job_queue.start()
    logger.info('Recommendation service started')

    # Start the recommendation scheduler
    await recommendation_scheduler.start()
    logger.info('Recommendation scheduler started')

    yield

    await alert_job_queue.stop()
    logger.info('Alert monitoring service stopped')

    await recommendation_job_queue.stop()
    logger.info('Recommendation service stopped')

    await recommendation_scheduler.stop()
    logger.info('Recommendation scheduler stopped')
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

# Include routers
app.include_router(health.router, prefix='/health', tags=['health'])
app.include_router(users_routes.router, prefix='/api/users', tags=['users'])
app.include_router(
    transactions_routes.router, prefix='/api/transactions', tags=['transactions']
)
app.include_router(alerts_routes.router, prefix='/api/alerts', tags=['alerts'])


@app.get('/')
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {'message': 'Welcome to spending-monitor API'}

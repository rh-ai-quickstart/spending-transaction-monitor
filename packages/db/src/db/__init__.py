__version__ = '0.0.0'

# Export main database classes and functions
from .database import DatabaseService, get_db, get_db_service

__all__ = ['DatabaseService', 'get_db_service', 'get_db', '__version__']

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.orm import declarative_base, sessionmaker

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
Base = declarative_base()

# Ensure Alembic uses a sync driver for migrations when the app uses asyncpg
if os.environ.get('DATABASE_URL') or config.get_main_option('sqlalchemy.url'):
    url = os.environ.get('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    if '+asyncpg' in url:
        config.set_main_option('sqlalchemy.url', url.replace('+asyncpg', '+psycopg2'))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel

from db.models import *  # noqa: F401,F403 ensure models are imported for autogenerate

# target metadata for autogenerate
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Get database URL from environment variable first, then fall back to config
    url = os.environ.get('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    # Convert asyncpg URLs to psycopg2 for Alembic compatibility
    if url and 'postgresql+asyncpg://' in url:
        url = url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
    
    print(f'url in env.py: {url}')
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get database URL from environment variable first, then fall back to config, then use default
    database_url = (
        os.environ.get('DATABASE_URL') or 
        config.get_main_option('sqlalchemy.url') or
        'postgresql+psycopg2://user:password@localhost:5432/spending-monitor'  # Default fallback
    )
    
    # Convert asyncpg URLs to psycopg2 for Alembic compatibility
    if database_url and 'postgresql+asyncpg://' in database_url:
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
    
    print(f'database_url in env.py: {database_url}')
    
    # Create a copy of the config section and ensure URL is set
    configuration = config.get_section(config.config_ini_section, {})
    configuration['sqlalchemy.url'] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

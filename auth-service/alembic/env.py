# Import standard libraries
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import Settings  
from app.db.base import Base          

settings = Settings()

# Load the Alembic config object, which holds values from alembic.ini
config = context.config

# Override the database URL from alembic.ini with the one from the app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up logging configuration using alembic.ini's fileConfig section
fileConfig(config.config_file_name)

# Provide Alembic with the SQLAlchemy metadata so it can generate schema diffs
target_metadata = Base.metadata


# Function to run migrations in "offline" mode (no DB connection required)
def run_migrations_offline() -> None:
    # Retrieve the database URL from the config
    url = config.get_main_option("sqlalchemy.url")

    # Configure Alembic context with URL and metadata for generating SQL output
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,  # Embed values directly in the SQL script
        dialect_opts={"paramstyle": "named"},  # Use named parameter syntax like :name
    )

    # Begin a new "transaction" and run migrations
    with context.begin_transaction():
        context.run_migrations()


# Function to run migrations in "online" mode (direct DB connection)
def run_migrations_online() -> None:
    # Create an SQLAlchemy engine using the config values (including the DB URL)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",  # Looks for keys like sqlalchemy.url, sqlalchemy.echo, etc.
        poolclass=pool.NullPool,  # No connection pooling, single-use connection
    )

    # Establish a database connection
    with connectable.connect() as connection:
        # Configure Alembic context with the active DB connection and model metadata
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        # Begin transaction and apply all pending migrations
        with context.begin_transaction():
            context.run_migrations()


# Determine whether to run in offline or online mode, and call the appropriate function
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

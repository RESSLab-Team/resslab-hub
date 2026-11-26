from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import resslab_hub.models.database  # noqa: F401
from alembic import context
from resslab_hub.utils.database import Base, url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# disable_existing_loggers=False: upgrade_database() runs this at app import,
# and the default (True) would silence already-configured loggers (uvicorn's
# included) — which turned startup errors like "address already in use" into a
# bare, traceback-less exit.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The metadata of every model, for autogenerate.
target_metadata = Base.metadata

# The URL is passed straight to SQLAlchemy, never through the config: the
# password in it is quote_plus-escaped, and ConfigParser reads any "%" (an
# escaped "@" is "%40") as an interpolation and raises (#265).


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

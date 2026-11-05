import asyncio
from logging.config import fileConfig
from typing import Any, Literal

from alembic import context
from dishka import make_container
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.infra.config import DatabaseConfig, build_database_url
from app.infra.database.mappings import metadata
from app.infra.database.types import UtcDateTime
from app.infra.di import ConfigProvider

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
with make_container(ConfigProvider()) as dependencies:
    database_url = build_database_url(dependencies.get(DatabaseConfig))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    """Custom TypeDecorators are written as standard types, so migrations do not depend on app code."""
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, compare_type=True, render_item=render_item
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())

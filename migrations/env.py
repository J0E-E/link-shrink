"""Alembic environment for the LinkShrink shared schema (Epic 2).

Async migrations over asyncpg (the only Postgres driver the shared package ships).
The DB URL is resolved as follows:

1. An explicit `sqlalchemy.url` set on the Alembic Config (used by the Testcontainers
   tests, which point Alembic at the throwaway container).
2. Otherwise built from the POSTGRES_* env vars (the same vars in .env.example).

This direct env read is a deliberate Epic-2-era stand-in: linkshrink_shared.config
(pydantic-settings) does not exist until Epic 5, and migrations must run before any
service config is loaded. Epic 5 may later route this through the shared config.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from linkshrink_shared.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Return an explicit configured URL, else build one from POSTGRES_* env vars."""
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url

    user = os.environ.get("POSTGRES_USER", "linkshrink")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "linkshrink")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (`alembic upgrade --sql`)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within a connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()
    engine = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

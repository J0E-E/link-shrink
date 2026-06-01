"""Shared integration-test fixtures: Testcontainers PG + Redis, Alembic, sessions.

Every integration module used to copy these fixtures verbatim. They now live here so a
single throwaway Postgres and Redis are started once per test session and reused, while
each test still starts on a clean schema (``downgrade base`` -> ``upgrade head``) and a
freshly-flushed Redis -- isolation is unchanged, only the container startup cost is paid
once. If Docker is unavailable the container fixtures skip, so the suite still exits 0 on
a Docker-less machine (the convention from Epics 2/5).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_shared import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- Container fixtures (one PG + one Redis for the whole session) ------------------


@pytest.fixture(scope="session")
def database_url() -> str:
    """Start a throwaway Postgres and yield an asyncpg URL; skip if Docker is absent."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError as error:  # pragma: no cover - dev dependency missing
        pytest.skip(f"testcontainers not installed: {error}")

    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as error:  # pragma: no cover - Docker unavailable
        pytest.skip(f"Docker/Postgres container unavailable: {error}")

    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield (
            f"postgresql+asyncpg://{container.username}:{container.password}"
            f"@{host}:{port}/{container.dbname}"
        )
    finally:
        container.stop()


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Start a throwaway Redis and yield its URL; skip if Docker is absent."""
    try:
        from testcontainers.redis import RedisContainer
    except ImportError as error:  # pragma: no cover - dev dependency missing
        pytest.skip(f"testcontainers not installed: {error}")

    try:
        container = RedisContainer("redis:7-alpine")
        container.start()
    except Exception as error:  # pragma: no cover - Docker unavailable
        pytest.skip(f"Docker/Redis container unavailable: {error}")

    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}"
    finally:
        container.stop()


# --- Schema + session fixtures (fresh per test) ------------------------------------


@pytest.fixture(scope="session")
def alembic_config(database_url: str):
    """An Alembic Config pointed at the throwaway container."""
    from alembic.config import Config

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def schema_at_head(alembic_config, database_url: str) -> str:
    """Reset to an empty DB then migrate to head, so each test starts clean."""
    from alembic import command

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    return database_url


@pytest_asyncio.fixture
async def session_factory(schema_at_head: str):
    """A session factory bound to a fresh engine over the migrated container DB."""
    engine = create_async_engine(schema_at_head)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> Redis:
    """A decoded async client against a freshly-flushed DB, closed after each test."""
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def test_settings() -> Settings:
    """Settings isolated from any local ``.env`` with a fixed salt and public host.

    Shared by the api and redirect suites: the api needs the hashids salt for short-code
    generation, and both build/expect ``link-shrink.org`` URLs.
    """
    return Settings(
        _env_file=None, hashids_salt="integration-test-salt", public_host="link-shrink.org"
    )

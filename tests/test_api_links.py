"""Epic 6 — integration tests for ``POST /api/links`` against real PG + Redis.

Spins up throwaway Postgres and Redis via Testcontainers, applies the Alembic
migration, and drives the FastAPI app through an in-process ASGI transport with the
dependencies overridden to point at the containers (and a fake DNS resolver, so no
real network is touched). If Docker is unavailable the whole module skips, matching
the clean-run expectation from Epics 2/5.

Covers the epic's acceptance criteria: 201 shape, 400 (bad URL/scheme/length/
private-IP/bad alias), 409 (reserved + taken alias), 429 with ``Retry-After`` (minute
and day windows), and ``ttl_seconds`` clamping at both bounds.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_api.dependencies import (
    get_db_session,
    get_host_resolver,
    get_redis,
    get_settings_dependency,
)
from linkshrink_api.main import create_app
from linkshrink_shared import RATE_LIMIT_PER_DAY, Settings, ratelimit_day_key

REPO_ROOT = Path(__file__).resolve().parents[1]

PUBLIC_HOST = "link-shrink.org"
PUBLIC_IP = "93.184.216.34"  # a public address the fake resolver returns
PRIVATE_IP = "10.0.0.1"


# --- Container + schema fixtures (mirror tests/test_migrations.py & test_cache.py) ---


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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


# --- App + client fixtures ---------------------------------------------------------


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
def resolver_holder() -> dict:
    """Mutable DNS resolver seam; defaults to resolving everything to a public IP.

    A test that needs the SSRF path swaps in a resolver returning a private address.
    """
    return {"resolver": lambda hostname: [PUBLIC_IP]}


@pytest.fixture
def test_settings() -> Settings:
    """Settings isolated from any local ``.env`` with a fixed salt and public host."""
    return Settings(
        _env_file=None, hashids_salt="integration-test-salt", public_host=PUBLIC_HOST
    )


@pytest_asyncio.fixture
async def client(session_factory, redis_client, test_settings, resolver_holder):
    """An async HTTP client driving the app with container-backed dependencies."""
    app = create_app()

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_settings_dependency] = lambda: test_settings
    app.dependency_overrides[get_host_resolver] = lambda: resolver_holder["resolver"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def _create(client: AsyncClient, ip: str = "203.0.113.1", **body) -> object:
    """POST /api/links as a given client IP (via the trusted X-Real-IP header)."""
    return await client.post("/api/links", json=body, headers={"X-Real-IP": ip})


# --- Tests -------------------------------------------------------------------------


async def test_create_returns_201_with_expected_shape(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com/some/page")
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {
        "short_code",
        "short_url",
        "original_url",
        "created_at",
        "expires_at",
        "qr_url",
    }
    code = data["short_code"]
    assert len(code) >= 6
    assert data["original_url"] == "https://example.com/some/page"
    assert data["short_url"] == f"https://{PUBLIC_HOST}/{code}"
    assert data["qr_url"] == f"https://{PUBLIC_HOST}/api/links/{code}/qr"


async def test_create_with_custom_alias(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="My-Custom-Link")
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "my-custom-link"  # normalized to lowercase
    assert data["short_url"] == f"https://{PUBLIC_HOST}/my-custom-link"


async def test_invalid_scheme_returns_400(client: AsyncClient) -> None:
    response = await _create(client, url="javascript:alert(1)")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_scheme"


async def test_over_length_url_returns_400(client: AsyncClient) -> None:
    long_url = "https://example.com/" + "a" * 2048
    response = await _create(client, url=long_url)
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_length"


async def test_private_address_returns_400(
    client: AsyncClient, resolver_holder: dict
) -> None:
    resolver_holder["resolver"] = lambda hostname: [PRIVATE_IP]
    response = await _create(client, url="http://internal.example.com")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_private_address"


async def test_reserved_alias_returns_409(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="api")
    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "alias_reserved"


async def test_bad_grammar_alias_returns_400(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="bad_alias!")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "alias_grammar"


async def test_taken_alias_returns_409(client: AsyncClient) -> None:
    first = await _create(client, url="https://example.com", alias="taken-alias")
    assert first.status_code == 201
    second = await _create(client, url="https://example.org", alias="taken-alias")
    assert second.status_code == 409
    assert second.json()["detail"]["reason"] == "alias_taken"


async def test_ttl_clamped_to_minimum(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", ttl_seconds=1)
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 3600


async def test_ttl_clamped_to_maximum(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", ttl_seconds=99_999_999)
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 2_592_000


async def test_ttl_defaults_to_thirty_days(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com")
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 2_592_000


async def test_minute_window_rate_limit_returns_429(client: AsyncClient) -> None:
    ip = "203.0.113.10"
    for _ in range(10):
        ok = await _create(client, ip=ip, url="https://example.com")
        assert ok.status_code == 201
    blocked = await _create(client, ip=ip, url="https://example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_day_window_rate_limit_returns_429(
    client: AsyncClient, redis_client: Redis
) -> None:
    ip = "203.0.113.20"
    await redis_client.set(ratelimit_day_key(ip), RATE_LIMIT_PER_DAY)
    blocked = await _create(client, ip=ip, url="https://example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def _lifetime_seconds(data: dict) -> int:
    """Whole seconds between created_at and expires_at in a create response."""
    created_at = datetime.fromisoformat(data["created_at"])
    expires_at = datetime.fromisoformat(data["expires_at"])
    return round((expires_at - created_at).total_seconds())

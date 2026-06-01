"""Epic 11 — integration tests for the redirect service against real PG + Redis.

Spins up throwaway Postgres and Redis via Testcontainers, applies the Alembic
migration, and drives the redirect FastAPI app through an in-process ASGI transport
with its dependencies overridden to point at the containers. If Docker is unavailable
the whole module skips, matching the clean-run expectation from Epics 2/5.

Covers the §5.6 ACs: a known code → 302 + click queued; a warm cache hit serves
without touching Postgres; an expired code never 302s even on a warm path; an unknown
code → 404 + negative cache (served from cache on the next hit); and an analytics
failure still returns the 302.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from linkshrink_redirect.dependencies import get_db_session, get_redis, get_settings_dependency
from linkshrink_redirect.main import create_app
from linkshrink_shared import (
    CLICKS_STREAM,
    METRICS_CACHE_HIT_KEY,
    METRICS_CACHE_MISS_KEY,
    METRICS_REDIRECTS_TOTAL_KEY,
    NEGATIVE_CACHE_TTL_SECONDS,
    CachedTarget,
    Link,
    Settings,
    Source,
    decode_cached_target,
    deserialize_click,
    get_cached,
    is_negative,
    read_counter,
    redirect_key,
)

# The container/schema/session/redis/test_settings fixtures live in tests/conftest.py.


# --- App + client fixtures ---------------------------------------------------------


def _session_override(session_factory):
    """Build a ``get_db_session`` override that yields real sessions from the factory."""

    async def override():
        async with session_factory() as session:
            yield session

    return override


class _FailingSession:
    """A stand-in session whose query raises, proving the warm path never hits the DB."""

    async def scalar(self, *args, **kwargs):
        raise AssertionError("database should not be queried on a warm cache path")


async def _failing_session_override():
    """A ``get_db_session`` override that yields a session refusing to be queried."""
    yield _FailingSession()


@asynccontextmanager
async def _client_for(session_override, redis_client: Redis, test_settings: Settings):
    """Yield an async HTTP client driving the app with the given session override."""
    app = create_app()
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_settings_dependency] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def client(session_factory, redis_client, test_settings):
    """An async HTTP client driving the app with container-backed dependencies."""
    async with _client_for(
        _session_override(session_factory), redis_client, test_settings
    ) as http_client:
        yield http_client


# --- Helpers -----------------------------------------------------------------------


async def _insert_link(
    session_factory, *, short_code: str, original_url: str, expires_at: datetime
) -> int:
    """Insert one link and return its id."""
    async with session_factory() as session:
        link = Link(
            short_code=short_code,
            original_url=original_url,
            is_custom=False,
            expires_at=expires_at,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link.id


async def _queued_clicks(redis_client: Redis) -> list:
    """Read every click queued on the stream, decoded into payloads."""
    entries = await redis_client.xrange(CLICKS_STREAM)
    return [deserialize_click(fields) for _id, fields in entries]


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(days=1)


def _past() -> datetime:
    return datetime.now(UTC) - timedelta(seconds=1)


# --- Tests -------------------------------------------------------------------------


async def test_known_code_redirects_302_and_queues_click(
    client: AsyncClient, session_factory, redis_client: Redis
) -> None:
    link_id = await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com/page",
        expires_at=_future(),
    )

    response = await client.get("/abc123")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"
    assert response.headers["cache-control"] == "no-store"

    clicks = await _queued_clicks(redis_client)
    assert len(clicks) == 1
    assert clicks[0].link_id == link_id
    assert clicks[0].source is Source.direct

    assert await read_counter(redis_client, METRICS_REDIRECTS_TOTAL_KEY) == 1
    assert await read_counter(redis_client, METRICS_CACHE_MISS_KEY) == 1


async def test_source_qr_query_sets_qr_source(
    client: AsyncClient, session_factory, redis_client: Redis
) -> None:
    await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com",
        expires_at=_future(),
    )

    response = await client.get("/abc123?source=qr")

    assert response.status_code == 302
    clicks = await _queued_clicks(redis_client)
    assert len(clicks) == 1
    assert clicks[0].source is Source.qr
    # The query string is read only for the payload — the cache key ignores it.
    assert await get_cached(redis_client, "abc123") is not None


async def test_cache_hit_serves_without_db(
    client: AsyncClient, session_factory, redis_client: Redis, test_settings: Settings
) -> None:
    await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com",
        expires_at=_future(),
    )

    first = await client.get("/abc123")
    assert first.status_code == 302

    # Second request with a session that refuses queries — a warm hit must not touch the DB.
    async with _client_for(_failing_session_override, redis_client, test_settings) as warm_client:
        second = await warm_client.get("/abc123")

    assert second.status_code == 302
    assert second.headers["location"] == "https://example.com"
    assert await read_counter(redis_client, METRICS_CACHE_HIT_KEY) == 1


async def test_expired_code_does_not_302_even_on_warm_path(
    client: AsyncClient, session_factory, redis_client: Redis, test_settings: Settings
) -> None:
    await _insert_link(
        session_factory, short_code="gone99", original_url="https://example.com", expires_at=_past()
    )

    cold = await client.get("/gone99")
    assert cold.status_code == 404
    assert is_negative(await get_cached(redis_client, "gone99"))

    # Warm path: served from the negative cache, never reaching the DB — still 404.
    async with _client_for(_failing_session_override, redis_client, test_settings) as warm_client:
        warm = await warm_client.get("/gone99")

    assert warm.status_code == 404
    assert await read_counter(redis_client, METRICS_REDIRECTS_TOTAL_KEY) == 0


async def test_unknown_code_returns_404_and_negative_caches(
    client: AsyncClient, redis_client: Redis
) -> None:
    response = await client.get("/missing")

    assert response.status_code == 404
    assert is_negative(await get_cached(redis_client, "missing"))
    assert 0 < await redis_client.ttl(redirect_key("missing")) <= NEGATIVE_CACHE_TTL_SECONDS
    assert await read_counter(redis_client, METRICS_CACHE_MISS_KEY) == 1
    assert await read_counter(redis_client, METRICS_REDIRECTS_TOTAL_KEY) == 0


async def test_negative_cache_hit_returns_404_without_db(
    client: AsyncClient, redis_client: Redis, test_settings: Settings
) -> None:
    cold = await client.get("/missing")
    assert cold.status_code == 404

    async with _client_for(_failing_session_override, redis_client, test_settings) as warm_client:
        warm = await warm_client.get("/missing")

    assert warm.status_code == 404
    assert await read_counter(redis_client, METRICS_CACHE_HIT_KEY) == 1


async def test_analytics_failure_still_returns_302(
    client: AsyncClient, session_factory, redis_client: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com",
        expires_at=_future(),
    )

    async def _boom(*args, **kwargs):
        raise RuntimeError("queue is down")

    monkeypatch.setattr("linkshrink_redirect.routers.redirect.add_click", _boom)

    response = await client.get("/abc123")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


async def test_malformed_cache_entry_is_treated_as_miss_and_self_heals(
    client: AsyncClient, session_factory, redis_client: Redis
) -> None:
    link_id = await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com",
        expires_at=_future(),
    )
    # Poison the cache with a value that isn't the JSON cache_target writes.
    await redis_client.set(redirect_key("abc123"), "not-json")

    response = await client.get("/abc123")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"
    # The bad entry counts as a miss (it fell through to Postgres) and is rewritten cleanly.
    assert await read_counter(redis_client, METRICS_CACHE_MISS_KEY) == 1
    healed = decode_cached_target(await get_cached(redis_client, "abc123"))
    assert healed == CachedTarget(link_id=link_id, original_url="https://example.com")


async def test_health_is_not_shadowed_by_catch_all(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_case_insensitive_code_match(
    client: AsyncClient, session_factory, redis_client: Redis
) -> None:
    await _insert_link(
        session_factory,
        short_code="abc123",
        original_url="https://example.com",
        expires_at=_future(),
    )

    response = await client.get("/ABC123")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"

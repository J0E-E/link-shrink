"""Epic 19 — system-level integration tests across all three backend services.

Every other integration module drives a single service. This suite wires the **API**,
the **redirect** service, and the **worker** coroutines onto **one shared Postgres and
one shared Redis** (the conftest containers) and proves the cross-service behaviours the
design depends on end-to-end:

* the happy path — create (API) -> 302 (redirect) -> worker drains the click -> the click
  shows up in the API's analytics;
* rate-limit 429 with ``Retry-After`` at the create seam;
* the §5.6 cache-hit expiry AC — a warm positive cache entry's TTL is capped to the link's
  remaining lifetime, so it can never outlive the link (asserted on the TTL, no ``sleep``);
* the purge job removing an expired-past-retention link so the redirect then 404s;
* queue recovery / DLQ — a poison click is dead-lettered after the delivery-attempt cap.

Like every container-backed module, the whole suite skips cleanly when Docker is absent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from linkshrink_api.dependencies import (
    get_db_session as api_get_db_session,
)
from linkshrink_api.dependencies import (
    get_host_resolver,
)
from linkshrink_api.dependencies import (
    get_redis as api_get_redis,
)
from linkshrink_api.dependencies import (
    get_settings_dependency as api_get_settings,
)
from linkshrink_api.main import create_app as create_api_app
from linkshrink_redirect.dependencies import (
    get_db_session as redirect_get_db_session,
)
from linkshrink_redirect.dependencies import (
    get_redis as redirect_get_redis,
)
from linkshrink_redirect.dependencies import (
    get_settings_dependency as redirect_get_settings,
)
from linkshrink_redirect.main import create_app as create_redirect_app
from linkshrink_shared import (
    DEAD_LETTER_STREAM,
    RATE_LIMIT_PER_MINUTE,
    ClickPayload,
    DeviceType,
    Link,
    Source,
    add_click,
    ensure_consumer_group,
    get_cached,
    is_negative,
    pending_count,
    redirect_key,
    worker_consumer_name,
)
from linkshrink_worker.consumer import run_consumer_once, run_recovery_once
from linkshrink_worker.purge import run_purge_once

PUBLIC_IP = "93.184.216.34"  # the fake resolver's public address (no real DNS)


# --- Cross-service harness ---------------------------------------------------------


def _override_session(session_factory):
    """Build a ``get_db_session`` override yielding real sessions from the factory."""

    async def override():
        async with session_factory() as session:
            yield session

    return override


@pytest_asyncio.fixture
async def api_client(session_factory, redis_client, test_settings):
    """The API app wired to the shared PG + Redis with a fake (public-IP) DNS resolver."""
    app = create_api_app()
    app.dependency_overrides[api_get_db_session] = _override_session(session_factory)
    app.dependency_overrides[api_get_redis] = lambda: redis_client
    app.dependency_overrides[api_get_settings] = lambda: test_settings
    app.dependency_overrides[get_host_resolver] = lambda: (lambda hostname: [PUBLIC_IP])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def redirect_client(session_factory, redis_client, test_settings):
    """The redirect app wired to the *same* shared PG + Redis, not following redirects."""
    app = create_redirect_app()
    app.dependency_overrides[redirect_get_db_session] = _override_session(session_factory)
    app.dependency_overrides[redirect_get_redis] = lambda: redis_client
    app.dependency_overrides[redirect_get_settings] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as client:
        yield client


def _consumer() -> str:
    return worker_consumer_name(1)


async def _create_link(api_client: AsyncClient, *, ip: str = "203.0.113.50", **body) -> dict:
    """POST /api/links as a given client IP (trusted X-Real-IP header) and return the body."""
    response = await api_client.post("/api/links", json=body, headers={"X-Real-IP": ip})
    assert response.status_code == 201, response.text
    return response.json()


async def _seed_link(
    session_factory, *, short_code: str, expires_at: datetime, original_url: str | None = None
) -> int:
    """Insert one link straight into the shared DB and return its id."""
    async with session_factory() as session:
        link = Link(
            short_code=short_code,
            original_url=original_url or f"https://example.com/{short_code}",
            is_custom=False,
            expires_at=expires_at,
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link.id


# --- Tests -------------------------------------------------------------------------


async def test_happy_path_create_redirect_worker_analytics(
    api_client: AsyncClient, redirect_client: AsyncClient, redis_client: Redis, session_factory
) -> None:
    """Create -> 302 -> worker drains the queued click -> it surfaces in API analytics."""
    await ensure_consumer_group(redis_client)

    created = await _create_link(api_client, url="https://example.com/destination")
    code = created["short_code"]

    redirect = await redirect_client.get(f"/{code}")
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/destination"

    # The redirect queued exactly one click; the worker turns it into a ClickEvent row.
    processed = await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=200)
    assert processed == 1

    analytics = await api_client.get(f"/api/links/{code}/analytics")
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["short_code"] == code
    assert data["total_clicks"] == 1
    assert data["by_source"] == [{"value": "direct", "count": 1}]


async def test_qr_source_redirect_attributes_click_to_qr(
    api_client: AsyncClient, redirect_client: AsyncClient, redis_client: Redis, session_factory
) -> None:
    """A ``?source=qr`` redirect is attributed to the qr source through the whole pipeline."""
    await ensure_consumer_group(redis_client)
    created = await _create_link(api_client, url="https://example.com/qr-target")
    code = created["short_code"]

    redirect = await redirect_client.get(f"/{code}?source=qr")
    assert redirect.status_code == 302

    assert await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=200) == 1

    data = (await api_client.get(f"/api/links/{code}/analytics")).json()
    assert data["by_source"] == [{"value": "qr", "count": 1}]


async def test_minute_rate_limit_returns_429_with_retry_after(api_client: AsyncClient) -> None:
    """The create endpoint enforces the per-minute window at the system seam."""
    ip = "203.0.113.99"
    for _ in range(RATE_LIMIT_PER_MINUTE):
        ok = await api_client.post(
            "/api/links", json={"url": "https://example.com"}, headers={"X-Real-IP": ip}
        )
        assert ok.status_code == 201
    blocked = await api_client.post(
        "/api/links", json={"url": "https://example.com"}, headers={"X-Real-IP": ip}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_warm_cache_ttl_is_capped_to_remaining_lifetime(
    redirect_client: AsyncClient, redis_client: Redis, session_factory
) -> None:
    """§5.6 AC: a warm positive cache entry's TTL never exceeds the link's remaining life.

    The API clamps ``ttl_seconds`` to >= 3600s, so a short-lived link is seeded directly.
    Warming the cache with one redirect must write an entry whose TTL is capped at the
    seconds-until-expiry, which is what guarantees a stale entry can never keep serving a
    302 for an already-expired code — proven on the TTL, with no ``sleep``.
    """
    remaining_seconds = 120
    expires_at = datetime.now(UTC) + timedelta(seconds=remaining_seconds)
    await _seed_link(session_factory, short_code="shortlived", expires_at=expires_at)

    warm = await redirect_client.get("/shortlived")
    assert warm.status_code == 302

    ttl = await redis_client.ttl(redirect_key("shortlived"))
    assert 0 < ttl <= remaining_seconds


async def test_purge_makes_redirect_404(
    redirect_client: AsyncClient, redis_client: Redis, session_factory
) -> None:
    """A link expired past retention is purged, after which the redirect 404s and neg-caches."""
    now = datetime.now(UTC)
    purged_id = await _seed_link(
        session_factory, short_code="ancient", expires_at=now - timedelta(days=100)
    )
    kept_id = await _seed_link(
        session_factory, short_code="stillhere", expires_at=now - timedelta(days=1)
    )

    deleted = await run_purge_once(session_factory)
    assert deleted == 1

    async with session_factory() as session:
        assert await session.get(Link, purged_id) is None
        assert await session.get(Link, kept_id) is not None

    response = await redirect_client.get("/ancient")
    assert response.status_code == 404
    assert is_negative(await get_cached(redis_client, "ancient"))


async def test_poison_click_is_dead_lettered_after_attempt_cap(
    redis_client: Redis, session_factory
) -> None:
    """A click for a nonexistent link is dead-lettered once the delivery-attempt cap is hit."""
    await ensure_consumer_group(redis_client)
    await add_click(
        redis_client,
        ClickPayload(
            link_id=999_999,  # no such link — the FK fails on every attempt
            ts=datetime.now(UTC),
            referrer=None,
            ua=None,
            source=Source.direct,
        ),
    )

    # Initial delivery fails (attempt 1) and stays pending; the first reclaim (attempt 2)
    # still retries, and the second reclaim hits attempt 3 (the cap) and dead-letters.
    assert await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=100) == 0
    await run_recovery_once(redis_client, session_factory, _consumer(), min_idle_ms=0)
    assert await pending_count(redis_client) == 1
    assert await redis_client.xlen(DEAD_LETTER_STREAM) == 0

    await run_recovery_once(redis_client, session_factory, _consumer(), min_idle_ms=0)
    assert await pending_count(redis_client) == 0
    dead = await redis_client.xrange(DEAD_LETTER_STREAM)
    assert len(dead) == 1
    assert dead[0][1]["link_id"] == "999999"


async def test_unknown_device_default_when_no_user_agent(
    api_client: AsyncClient, redirect_client: AsyncClient, redis_client: Redis, session_factory
) -> None:
    """A redirect with no User-Agent header derives the ``unknown`` device type end-to-end."""
    await ensure_consumer_group(redis_client)
    created = await _create_link(api_client, url="https://example.com/no-ua")
    code = created["short_code"]

    redirect = await redirect_client.get(f"/{code}", headers={"user-agent": ""})
    assert redirect.status_code == 302

    assert await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=200) == 1

    data = (await api_client.get(f"/api/links/{code}/analytics")).json()
    assert data["by_device_type"] == [{"value": DeviceType.unknown.value, "count": 1}]

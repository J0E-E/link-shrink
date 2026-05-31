"""Epic 12 — tests for the analytics worker.

Pure-unit tests cover the PII-free derivation (UA → device/browser/OS, Referer → host)
and need no services. The integration tests spin up throwaway Postgres and Redis via
Testcontainers, apply the Alembic migration, and drive single consumer/recovery passes
directly (the loops in ``main`` just call these in a cycle), so the whole module skips
cleanly when Docker is absent — matching Epics 2/5/11.

Covers the §5.7 ACs: an ``XADD`` becomes a ``ClickEvent`` row with coarse fields and no
raw UA/referrer; a crashed consumer's pending entry is reclaimed; a poison message is
dead-lettered after three delivery attempts; and the heartbeat key updates each pass.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_shared import (
    DEAD_LETTER_STREAM,
    ClickEvent,
    ClickPayload,
    DeviceType,
    Link,
    Source,
    add_click,
    ensure_consumer_group,
    pending_count,
    read_clicks,
    read_heartbeat,
    worker_consumer_name,
)
from linkshrink_worker.consumer import run_consumer_once, run_recovery_once
from linkshrink_worker.parsing import DerivedUserAgent, parse_user_agent, referrer_host
from linkshrink_worker.purge import run_purge_once

REPO_ROOT = Path(__file__).resolve().parents[1]

_IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
_DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_IPAD_UA = (
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)


# --- Unit tests: derivation (no Docker) --------------------------------------------


@pytest.mark.parametrize(
    ("ua", "expected_device", "expected_browser", "expected_os"),
    [
        (_DESKTOP_UA, DeviceType.desktop, "Chrome", "Windows"),
        (_IPHONE_UA, DeviceType.mobile, "Mobile Safari", "iOS"),
        (_IPAD_UA, DeviceType.tablet, "Mobile Safari", "iOS"),
        (None, DeviceType.unknown, None, None),
        ("", DeviceType.unknown, None, None),
        ("   ", DeviceType.unknown, None, None),
    ],
)
def test_parse_user_agent_maps_to_coarse_fields(
    ua: str | None,
    expected_device: DeviceType,
    expected_browser: str | None,
    expected_os: str | None,
) -> None:
    assert parse_user_agent(ua) == DerivedUserAgent(expected_device, expected_browser, expected_os)


def test_parse_user_agent_unrecognized_families_become_none() -> None:
    """An unparseable agent has no families and is classed ``unknown`` (not a device)."""
    derived = parse_user_agent("definitely-not-a-real-user-agent")
    assert derived.device_type is DeviceType.unknown
    assert derived.browser_family is None
    assert derived.os_family is None


@pytest.mark.parametrize(
    ("referrer", "expected"),
    [
        ("https://www.Google.com/search?q=secret", "www.google.com"),
        ("http://t.co/abc", "t.co"),
        ("https://news.ycombinator.com", "news.ycombinator.com"),
        (None, None),
        ("", None),
        ("   ", None),
        ("not a url", None),
    ],
)
def test_referrer_host_keeps_only_the_host(referrer: str | None, expected: str | None) -> None:
    assert referrer_host(referrer) == expected


# --- Container + schema fixtures (mirror tests/test_redirect.py) --------------------


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


# --- Helpers -----------------------------------------------------------------------


async def _insert_link(session_factory) -> int:
    """Insert one link and return its id."""
    async with session_factory() as session:
        link = Link(
            short_code="abc123",
            original_url="https://example.com/page",
            is_custom=False,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link.id


async def _click_events(session_factory, link_id: int) -> list[ClickEvent]:
    """Read every ClickEvent row stored for a link."""
    async with session_factory() as session:
        result = await session.scalars(
            select(ClickEvent).where(ClickEvent.link_id == link_id)
        )
        return list(result)


async def _seed_link_with_click(session_factory, short_code: str, expires_at: datetime) -> int:
    """Insert one link with an explicit expiry plus a single click; return the link id."""
    async with session_factory() as session:
        link = Link(
            short_code=short_code,
            original_url=f"https://example.com/{short_code}",
            is_custom=False,
            expires_at=expires_at,
        )
        session.add(link)
        await session.flush()
        session.add(
            ClickEvent(
                link_id=link.id,
                device_type=DeviceType.desktop,
                source=Source.direct,
            )
        )
        await session.commit()
        return link.id


async def _link_exists(session_factory, link_id: int) -> bool:
    """True if the link row is still present."""
    async with session_factory() as session:
        return await session.get(Link, link_id) is not None


def _consumer() -> str:
    return worker_consumer_name(1)


# --- Integration tests -------------------------------------------------------------


async def test_consumer_writes_clickevent_with_coarse_fields(
    session_factory, redis_client: Redis
) -> None:
    """An XADD'd click becomes one ClickEvent row with derived fields and host-only referrer."""
    link_id = await _insert_link(session_factory)
    clicked_at = datetime.now(UTC)
    await ensure_consumer_group(redis_client)
    await add_click(
        redis_client,
        ClickPayload(
            link_id=link_id,
            ts=clicked_at,
            referrer="https://t.co/path?utm=1",
            ua=_IPHONE_UA,
            source=Source.qr,
        ),
    )

    processed = await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=100)

    assert processed == 1
    rows = await _click_events(session_factory, link_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.device_type is DeviceType.mobile
    assert row.browser_family == "Mobile Safari"
    assert row.os_family == "iOS"
    assert row.referrer_domain == "t.co"  # host only — no path/query reaches Postgres
    assert row.source is Source.qr
    assert row.clicked_at == clicked_at
    # Acked: nothing left pending for the group.
    assert await pending_count(redis_client) == 0


async def test_recovery_reclaims_pending_entry_after_crash(
    session_factory, redis_client: Redis
) -> None:
    """A consumer that reads but never acks (a crash) has its entry reclaimed and processed."""
    link_id = await _insert_link(session_factory)
    await ensure_consumer_group(redis_client)
    await add_click(
        redis_client,
        ClickPayload(
            link_id=link_id,
            ts=datetime.now(UTC),
            referrer=None,
            ua=_DESKTOP_UA,
            source=Source.direct,
        ),
    )

    # Simulate a crash: worker-1 reads the entry into its PEL but never acks it.
    await read_clicks(redis_client, worker_consumer_name(1), block_ms=100)
    assert await _click_events(session_factory, link_id) == []

    # A surviving worker reclaims the idle entry and processes it.
    await run_recovery_once(
        redis_client, session_factory, worker_consumer_name(2), min_idle_ms=0
    )

    rows = await _click_events(session_factory, link_id)
    assert len(rows) == 1
    assert rows[0].device_type is DeviceType.desktop
    assert await pending_count(redis_client) == 0


async def test_poison_message_dead_lettered_after_three_attempts(
    session_factory, redis_client: Redis
) -> None:
    """A click for a nonexistent link fails the FK forever and is dead-lettered after 3 tries."""
    missing_link_id = 999_999
    await ensure_consumer_group(redis_client)
    await add_click(
        redis_client,
        ClickPayload(
            link_id=missing_link_id,
            ts=datetime.now(UTC),
            referrer=None,
            ua=_DESKTOP_UA,
            source=Source.direct,
        ),
    )

    # Attempt 1 (initial delivery): processing fails, entry stays pending, no DLQ yet.
    processed = await run_consumer_once(
        redis_client, session_factory, _consumer(), block_ms=100
    )
    assert processed == 0
    assert await pending_count(redis_client) == 1
    assert await redis_client.xlen(DEAD_LETTER_STREAM) == 0

    # Attempt 2 (first reclaim): still failing, still pending.
    await run_recovery_once(redis_client, session_factory, _consumer(), min_idle_ms=0)
    assert await pending_count(redis_client) == 1
    assert await redis_client.xlen(DEAD_LETTER_STREAM) == 0

    # Attempt 3 (cap reached): dead-lettered and acked, so the PEL clears.
    await run_recovery_once(redis_client, session_factory, _consumer(), min_idle_ms=0)
    assert await pending_count(redis_client) == 0
    dead = await redis_client.xrange(DEAD_LETTER_STREAM)
    assert len(dead) == 1
    _id, fields = dead[0]
    assert fields["link_id"] == str(missing_link_id)
    # The poison click was never persisted.
    assert await _click_events(session_factory, missing_link_id) == []


async def test_consumer_writes_heartbeat_each_pass(
    session_factory, redis_client: Redis
) -> None:
    """Every consumer pass refreshes the liveness heartbeat, even with an empty stream."""
    await ensure_consumer_group(redis_client)
    assert await read_heartbeat(redis_client) is None

    await run_consumer_once(redis_client, session_factory, _consumer(), block_ms=50)

    beat = await read_heartbeat(redis_client)
    assert beat is not None
    assert float(beat) > 0


async def test_purge_deletes_links_expired_past_retention_and_cascades(session_factory) -> None:
    """A link expired >3 months ago is purged with its clicks; nearer ones are retained."""
    now = datetime.now(UTC)
    old_id = await _seed_link_with_click(
        session_factory, "expired-old", now - timedelta(days=100)
    )
    # 85 days is safely inside even the shortest 3-month window (~89 days), so it stays.
    boundary_id = await _seed_link_with_click(
        session_factory, "expired-boundary", now - timedelta(days=85)
    )
    recent_id = await _seed_link_with_click(
        session_factory, "expired-recent", now - timedelta(days=1)
    )

    purged = await run_purge_once(session_factory)

    assert purged == 1
    # The long-expired link and its cascaded click events are gone.
    assert await _link_exists(session_factory, old_id) is False
    assert await _click_events(session_factory, old_id) == []
    # Links expired more recently than the retention window keep their row (they still 404
    # via redirect, but aren't purged) along with their clicks.
    for retained_id in (boundary_id, recent_id):
        assert await _link_exists(session_factory, retained_id) is True
        assert len(await _click_events(session_factory, retained_id)) == 1

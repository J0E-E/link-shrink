"""Click-payload and Streams tests for Epic 5.

The serialize→deserialize round-trip is pure and runs without Docker; the Streams
wrappers exercise a real Redis via Testcontainers and skip cleanly when Docker is
unavailable (same pattern as ``test_migrations.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from linkshrink_shared.models import Source
from linkshrink_shared.queue import (
    DEAD_LETTER_STREAM,
    ClickPayload,
    ack_click,
    add_click,
    claim_stale_clicks,
    dead_letter,
    deserialize_click,
    ensure_consumer_group,
    read_clicks,
    read_heartbeat,
    serialize_click,
    stream_length,
    worker_consumer_name,
    write_heartbeat,
)

# --- Pure unit tests (no Docker) ---------------------------------------------------


def test_serialize_deserialize_roundtrip() -> None:
    payload = ClickPayload(
        link_id=42,
        ts=datetime(2026, 5, 31, 12, 30, 0, tzinfo=UTC),
        referrer="https://news.example.com/post",
        ua="Mozilla/5.0",
        source=Source.qr,
    )
    assert deserialize_click(serialize_click(payload)) == payload


def test_serialize_deserialize_roundtrip_with_missing_optionals() -> None:
    payload = ClickPayload(
        link_id=1,
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        referrer=None,
        ua=None,
        source=Source.direct,
    )
    restored = deserialize_click(serialize_click(payload))
    assert restored == payload
    assert restored.referrer is None
    assert restored.ua is None


def test_serialize_click_normalizes_naive_ts_to_utc() -> None:
    payload = ClickPayload(
        link_id=1,
        ts=datetime(2026, 5, 31, 12, 0, 0),  # naive — assumed UTC
        referrer=None,
        ua=None,
        source=Source.direct,
    )
    assert serialize_click(payload)["ts"] == "2026-05-31T12:00:00+00:00"


def test_serialize_click_converts_aware_ts_to_utc() -> None:
    eastern = timezone(timedelta(hours=-5))
    payload = ClickPayload(
        link_id=1,
        ts=datetime(2026, 5, 31, 7, 0, 0, tzinfo=eastern),  # 12:00 UTC
        referrer=None,
        ua=None,
        source=Source.direct,
    )
    assert serialize_click(payload)["ts"] == "2026-05-31T12:00:00+00:00"


def test_worker_consumer_name() -> None:
    assert worker_consumer_name(1) == "worker-1"


# --- Testcontainers Redis ----------------------------------------------------------


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


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> Redis:
    """A decoded async client against a freshly-flushed DB, closed after each test."""
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


def _payload(link_id: int = 7) -> ClickPayload:
    return ClickPayload(
        link_id=link_id,
        ts=datetime(2026, 5, 31, 9, 0, 0, tzinfo=UTC),
        referrer="https://example.com",
        ua="curl/8",
        source=Source.direct,
    )


async def test_xadd_xreadgroup_xack_cycle(redis_client: Redis) -> None:
    await ensure_consumer_group(redis_client)
    await add_click(redis_client, _payload())

    consumer = worker_consumer_name(1)
    batches = await read_clicks(redis_client, consumer, block_ms=100)
    _stream, entries = batches[0]
    message_id, fields = entries[0]
    assert deserialize_click(fields) == _payload()

    assert await ack_click(redis_client, message_id) == 1
    # Nothing new to read after the ACK (redis-py returns None/[] on a timed-out read).
    assert not await read_clicks(redis_client, consumer, block_ms=100)


async def test_ensure_consumer_group_is_idempotent(redis_client: Redis) -> None:
    await ensure_consumer_group(redis_client)
    await ensure_consumer_group(redis_client)  # BUSYGROUP swallowed, no raise.


async def test_claim_stale_clicks_recovers_pending_entries(redis_client: Redis) -> None:
    await ensure_consumer_group(redis_client)
    await add_click(redis_client, _payload())

    # First consumer reads (entry now pending) but never ACKs, simulating a crash.
    await read_clicks(redis_client, worker_consumer_name(1), block_ms=100)
    _cursor, claimed, *_ = await claim_stale_clicks(
        redis_client, worker_consumer_name(2), min_idle_ms=0
    )
    assert len(claimed) == 1
    _message_id, fields = claimed[0]
    assert deserialize_click(fields) == _payload()


async def test_stream_length_counts_entries(redis_client: Redis) -> None:
    await add_click(redis_client, _payload(1))
    await add_click(redis_client, _payload(2))
    assert await stream_length(redis_client) == 2


async def test_dead_letter_appends_to_dead_stream(redis_client: Redis) -> None:
    await dead_letter(redis_client, serialize_click(_payload()))
    assert await redis_client.xlen(DEAD_LETTER_STREAM) == 1


async def test_heartbeat_write_then_read(redis_client: Redis) -> None:
    await write_heartbeat(redis_client, 1_750_000_000.5)
    assert await read_heartbeat(redis_client) == "1750000000.5"

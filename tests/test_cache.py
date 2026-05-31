"""Cache/rate-limit/metrics tests for Epic 5.

``cap_positive_ttl`` math is pure and runs without Docker; the rest exercise a real
Redis via Testcontainers and skip cleanly when Docker is unavailable (same pattern as
``test_migrations.py``).
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from linkshrink_shared.cache import (
    NEGATIVE_CACHE_SENTINEL,
    NEGATIVE_CACHE_TTL_SECONDS,
    POSITIVE_CACHE_MAX_TTL_SECONDS,
    RATE_LIMIT_PER_MINUTE,
    CachedTarget,
    cache_negative,
    cache_target,
    cap_positive_ttl,
    check_rate_limit,
    decode_cached_target,
    get_cached,
    hit_window,
    increment_cache_hit,
    is_negative,
    ratelimit_minute_key,
    read_counter,
    redirect_key,
)

# --- Pure unit tests (no Docker) ---------------------------------------------------


def test_cap_positive_ttl_caps_at_24h() -> None:
    assert cap_positive_ttl(100_000) == POSITIVE_CACHE_MAX_TTL_SECONDS


def test_cap_positive_ttl_passes_through_under_cap() -> None:
    assert cap_positive_ttl(50) == 50


def test_cap_positive_ttl_floors_at_one_second() -> None:
    assert cap_positive_ttl(0) == 1
    assert cap_positive_ttl(-10) == 1


def test_is_negative() -> None:
    assert is_negative(NEGATIVE_CACHE_SENTINEL)
    assert not is_negative("https://example.com")
    assert not is_negative(None)


def test_decode_cached_target_roundtrip() -> None:
    encoded = json.dumps({"id": 42, "url": "https://example.com"})
    assert decode_cached_target(encoded) == CachedTarget(link_id=42, original_url="https://example.com")
    assert not is_negative(encoded)


def test_redirect_key_lowercases_code() -> None:
    assert redirect_key("AbC") == redirect_key("abc") == "redirect:abc"


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


async def test_set_get_roundtrip(redis_client: Redis) -> None:
    await cache_target(redis_client, "abc123", 42, "https://example.com", 3600)
    value = await get_cached(redis_client, "abc123")
    assert decode_cached_target(value) == CachedTarget(link_id=42, original_url="https://example.com")
    assert await redis_client.ttl(redirect_key("abc123")) <= POSITIVE_CACHE_MAX_TTL_SECONDS


async def test_negative_sentinel_roundtrip(redis_client: Redis) -> None:
    await cache_negative(redis_client, "missing")
    value = await get_cached(redis_client, "missing")
    assert is_negative(value)
    assert 0 < await redis_client.ttl(redirect_key("missing")) <= NEGATIVE_CACHE_TTL_SECONDS


async def test_hit_window_increments_and_expires_on_first_hit(redis_client: Redis) -> None:
    key = ratelimit_minute_key("1.2.3.4")
    assert await hit_window(redis_client, key, 60) == 1
    assert 0 < await redis_client.ttl(key) <= 60
    assert await hit_window(redis_client, key, 60) == 2
    # The window's TTL is set once (on the first hit) and not refreshed by later hits.
    assert 0 < await redis_client.ttl(key) <= 60


async def test_check_rate_limit_allows_under_the_minute_cap(redis_client: Redis) -> None:
    result = await check_rate_limit(redis_client, "10.0.0.1")
    assert result.is_allowed
    assert result.retry_after_seconds is None


async def test_check_rate_limit_blocks_over_the_minute_cap(redis_client: Redis) -> None:
    ip = "10.0.0.2"
    for _ in range(RATE_LIMIT_PER_MINUTE):
        assert (await check_rate_limit(redis_client, ip)).is_allowed
    blocked = await check_rate_limit(redis_client, ip)
    assert not blocked.is_allowed
    assert 1 <= blocked.retry_after_seconds <= 60


async def test_metrics_counter_increments_and_reads_back(redis_client: Redis) -> None:
    from linkshrink_shared.cache import METRICS_CACHE_HIT_KEY

    assert await read_counter(redis_client, METRICS_CACHE_HIT_KEY) == 0
    await increment_cache_hit(redis_client)
    await increment_cache_hit(redis_client)
    assert await read_counter(redis_client, METRICS_CACHE_HIT_KEY) == 2

"""Resolve a short code to its target, cache-aside with negative caching (TDD §5.6).

Kept out of the HTTP handler so the cache → DB → cache flow is testable on its own.
The flow is exactly §5.6:

- Redis HIT → return the target (no expiry check; correctness comes from the capped TTL).
- Redis NEG-HIT (``"__404__"``) → return ``None`` (404).
- MISS → look up ``lower(short_code)`` in Postgres; positive-cache a live link and return
  it, or negative-cache an unknown/expired code and return ``None``.

A malformed positive entry is treated as a miss and re-resolved from Postgres, so a
corrupt or stale-shape cache value can never 500 the hot path (it self-heals).

Metric counters are bumped here, best-effort, and deliberately track **only real links**
so the cache-hit ratio measures cache effectiveness for traffic the cache can actually
help with — not the flood of 404s for paths that were never short codes (bot scans,
browser icon probes, etc.), which would otherwise swamp the ratio toward zero:

- A cache hit counts only on a warm *positive* entry (a real link served without Postgres).
- A cache miss counts only once Postgres confirms a real, live link that wasn't warm —
  i.e. a lookup the cache *should* have served but didn't.
- An unknown/expired code (a 404, positive- or negative-cached) counts as **neither**: it
  is still negatively cached to shield Postgres, but it never enters the hit/miss ratio.

Observability must never break the redirect, so a counter hiccup is swallowed and logged.
The served-redirect counter belongs to the router, since only an actual 302 should bump it.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_shared import (
    CachedTarget,
    Link,
    cache_negative,
    cache_target,
    decode_cached_target,
    get_cached,
    increment_cache_hit,
    increment_cache_miss,
    is_negative,
)

logger = logging.getLogger(__name__)


async def resolve_code(redis: Redis, session: AsyncSession, code: str) -> CachedTarget | None:
    """Resolve a code to a live target, or ``None`` if it is unknown or expired.

    Reads the cache first; on a miss (or a malformed positive entry), falls through to
    Postgres and back-fills the cache. Returning ``None`` always means "serve a 404" — the
    negative cache entry, when one is written, has already been set by the time this returns.
    """
    cached = await get_cached(redis, code)
    if cached is not None:
        if is_negative(cached):
            # A negative (404) cache hit. Deliberately uncounted: the hit/miss ratio
            # tracks cache effectiveness for real links only, so junk/unknown codes
            # never enter it (they would otherwise swamp the ratio toward zero).
            return None
        target = _decode_or_none(cached, code)
        if target is not None:
            await _count(increment_cache_hit, redis, code)
            return target
        # A malformed positive entry: treat it as a miss and re-resolve from Postgres,
        # which rewrites the cache value in the current format.

    link = await session.scalar(select(Link).where(func.lower(Link.short_code) == code.lower()))

    now = datetime.now(UTC)
    if link is None or link.expires_at <= now:
        # Unknown or expired code: negatively cache it to shield Postgres from repeats,
        # but do NOT count a cache miss — this is a 404 (junk), not a missed lookup for a
        # real link, and counting it would distort the cache-hit ratio.
        await cache_negative(redis, code)
        return None

    # A real, live link that wasn't warm in cache — the only thing that counts as a miss:
    # a lookup the cache should have served but didn't. Counted after Postgres confirms it.
    await _count(increment_cache_miss, redis, code)
    seconds_until_expires_at = int((link.expires_at - now).total_seconds())
    await cache_target(redis, code, link.id, link.original_url, seconds_until_expires_at)
    return CachedTarget(link_id=link.id, original_url=link.original_url)


def _decode_or_none(value: str, code: str) -> CachedTarget | None:
    """Decode a positive cache value, or ``None`` if it is malformed.

    A corrupt or stale-shape entry must not 500 the hot path; the caller treats ``None``
    as a cache miss and re-resolves from Postgres, self-healing the entry.
    """
    try:
        return decode_cached_target(value)
    except (ValueError, KeyError, TypeError) as error:
        logger.warning("discarding malformed cache entry for code %s: %s", code, error)
        return None


async def _count(increment: Callable[[Redis], Awaitable[None]], redis: Redis, code: str) -> None:
    """Bump a metrics counter, best-effort: observability must never break resolution."""
    try:
        await increment(redis)
    except Exception as error:  # noqa: BLE001 - metrics must never break the redirect
        logger.warning("metric counter failed for code %s: %s", code, error)

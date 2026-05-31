"""Redis cache-aside helpers and key conventions (TDD §5.6, §5.7, §5.9).

The single source of truth for the redirect cache keys, the negative-cache sentinel,
the TTL cap, the creation rate-limit windows, and the live metrics counters — so the
redirect service (Epic 11), the API (Epic 6), and the metrics endpoint (Epic 10) all
agree on the same Redis layout.

All helpers are async and take an injected ``redis.asyncio.Redis`` client (built with
``decode_responses=True`` by :func:`linkshrink_shared.config.get_redis_client`), so they
deal in ``str`` and test cleanly against a Testcontainers Redis. The operational limits
here are fixed design decisions (§6 #13), so they live as module constants rather than
env-tunable settings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# --- Redirect cache (§5.6) ---------------------------------------------------------

#: Prefix for the redirect cache key; the full key is ``redirect:{code}``.
REDIRECT_KEY_PREFIX = "redirect:"

#: Value stored to negatively cache an unknown/expired code so repeated misses do not
#: hammer Postgres. Distinct from any real (always non-empty) URL.
NEGATIVE_CACHE_SENTINEL = "__404__"

#: Hard cap on a positive cache entry's TTL (24h) — the redirect 24h cache window.
POSITIVE_CACHE_MAX_TTL_SECONDS = 86400

#: How long a negative (404) entry lives (§6 #13).
NEGATIVE_CACHE_TTL_SECONDS = 60


@dataclass(frozen=True)
class CachedTarget:
    """A decoded positive redirect cache entry: the link's id and its target URL.

    Carrying ``link_id`` in the cache value lets a warm cache hit build a click event
    (which needs ``link_id``, see :class:`linkshrink_shared.queue.ClickPayload`) without
    a Postgres round-trip on the hot path (§5.6).
    """

    link_id: int
    original_url: str


def redirect_key(code: str) -> str:
    """Build the redirect cache key for a code, lowercased to match case-insensitive
    storage so ``/AbC`` and ``/abc`` share one cache entry (the key ignores the query
    string — ``?source=qr`` is read only for the click payload, §5.6)."""
    return f"{REDIRECT_KEY_PREFIX}{code.lower()}"


def cap_positive_ttl(seconds_until_expires_at: int) -> int:
    """Cap a link's remaining lifetime to 24h, floored at 1s.

    ``min(86400, seconds_until_expires_at)`` so a positive cache entry can never outlive
    its link and keep serving a 302 for an expired code (§5.6); the floor keeps the TTL
    a valid positive ``EX`` value.
    """
    return max(1, min(POSITIVE_CACHE_MAX_TTL_SECONDS, seconds_until_expires_at))


async def get_cached(redis: Redis, code: str) -> str | None:
    """Read the cached value for a code: a URL, the negative sentinel, or ``None`` (miss)."""
    return await redis.get(redirect_key(code))


async def cache_target(
    redis: Redis, code: str, link_id: int, original_url: str, seconds_until_expires_at: int
) -> None:
    """Positively cache ``code → {link_id, original_url}`` with TTL capped at the link's lifetime.

    The value is JSON ``{"id": link_id, "url": original_url}`` so a later cache hit has the
    ``link_id`` needed to build a click event without touching Postgres. The negative
    sentinel stays a plain string, so :func:`is_negative` can still tell the two apart.
    """
    payload = json.dumps({"id": link_id, "url": original_url})
    await redis.set(redirect_key(code), payload, ex=cap_positive_ttl(seconds_until_expires_at))


async def cache_negative(redis: Redis, code: str) -> None:
    """Negatively cache an unknown/expired code for the short fixed window."""
    await redis.set(redirect_key(code), NEGATIVE_CACHE_SENTINEL, ex=NEGATIVE_CACHE_TTL_SECONDS)


def is_negative(value: str | None) -> bool:
    """True if a cached value is the negative (404) sentinel."""
    return value == NEGATIVE_CACHE_SENTINEL


def decode_cached_target(value: str) -> CachedTarget:
    """Parse a positive cache value into a :class:`CachedTarget`.

    The caller must have already ruled out a miss (``None``) and a negative hit (see
    :func:`is_negative`); this only decodes the JSON written by :func:`cache_target`.
    """
    data = json.loads(value)
    return CachedTarget(link_id=int(data["id"]), original_url=data["url"])


# --- Creation rate limiting (§5.9) -------------------------------------------------

#: Fixed-window creation caps and their window lengths (§6 #13).
RATE_LIMIT_PER_MINUTE = 10
RATE_LIMIT_PER_DAY = 100
RATE_LIMIT_MINUTE_WINDOW_SECONDS = 60
RATE_LIMIT_DAY_WINDOW_SECONDS = 86400

RATE_LIMIT_MINUTE_PREFIX = "ratelimit:min:"
RATE_LIMIT_DAY_PREFIX = "ratelimit:day:"


def ratelimit_minute_key(ip: str) -> str:
    """Per-minute fixed-window counter key for a client IP."""
    return f"{RATE_LIMIT_MINUTE_PREFIX}{ip}"


def ratelimit_day_key(ip: str) -> str:
    """Per-day fixed-window counter key for a client IP."""
    return f"{RATE_LIMIT_DAY_PREFIX}{ip}"


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a fixed-window rate-limit check for one client IP.

    ``retry_after_seconds`` is the remaining TTL of the exceeded window when blocked,
    so Epic 6 can put it straight into a ``Retry-After`` header; it is ``None`` when allowed.
    """

    is_allowed: bool
    retry_after_seconds: int | None = None


async def hit_window(redis: Redis, key: str, window_seconds: int) -> int:
    """``INCR`` a fixed-window counter, setting its expiry only on the first hit.

    Uses ``EXPIRE … NX`` so the TTL is attached exactly when the window opens (the
    first ``INCR`` creates the key with no TTL) and never reset by later hits — the
    fixed-window-with-EXPIRE-on-first-hit behavior of §5.9, done atomically in one
    pipeline. Returns the post-increment count.
    """
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = await pipe.execute()
    return int(count)


async def check_rate_limit(redis: Redis, ip: str) -> RateLimitResult:
    """Count this creation against both windows and report whether it is allowed.

    Increments the minute and day counters (fixed-window, §5.9). If either is now over
    its cap, the result is blocked and ``retry_after_seconds`` is the exceeded window's
    remaining TTL — the day window when both are over, since it is the longer wait.
    """
    minute_count = await hit_window(
        redis, ratelimit_minute_key(ip), RATE_LIMIT_MINUTE_WINDOW_SECONDS
    )
    day_count = await hit_window(redis, ratelimit_day_key(ip), RATE_LIMIT_DAY_WINDOW_SECONDS)

    over_day = day_count > RATE_LIMIT_PER_DAY
    over_minute = minute_count > RATE_LIMIT_PER_MINUTE
    if not over_day and not over_minute:
        return RateLimitResult(is_allowed=True)

    exceeded_key = ratelimit_day_key(ip) if over_day else ratelimit_minute_key(ip)
    # TTL is -1 (no expiry) / -2 (missing) in edge cases; floor at 1 for a sane header.
    retry_after = max(1, await redis.ttl(exceeded_key))
    return RateLimitResult(is_allowed=False, retry_after_seconds=retry_after)


# --- Live metrics counters (§5.7) --------------------------------------------------

#: Counters the redirect service ``INCR``s; the metrics endpoint (Epic 10) reads them.
METRICS_CACHE_HIT_KEY = "metrics:cache:hit"
METRICS_CACHE_MISS_KEY = "metrics:cache:miss"
METRICS_REDIRECTS_TOTAL_KEY = "metrics:redirects:total"


async def increment_cache_hit(redis: Redis) -> None:
    """Count one redirect cache hit."""
    await redis.incr(METRICS_CACHE_HIT_KEY)


async def increment_cache_miss(redis: Redis) -> None:
    """Count one redirect cache miss."""
    await redis.incr(METRICS_CACHE_MISS_KEY)


async def increment_redirects_total(redis: Redis) -> None:
    """Count one served redirect."""
    await redis.incr(METRICS_REDIRECTS_TOTAL_KEY)


async def read_counter(redis: Redis, key: str) -> int:
    """Read a metrics counter as an int, treating a missing key as 0."""
    value = await redis.get(key)
    return int(value) if value is not None else 0

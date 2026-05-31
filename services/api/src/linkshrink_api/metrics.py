"""Live operational metrics derived from Redis (Epic 10, TDD §5.7).

Reads the counters/keys the redirect service (Epic 11) and worker (Epic 12) write —
cache hit/miss, total redirects, the click stream, and the worker heartbeat — and
derives the live numbers ``GET /api/metrics`` exposes. Kept in its own module so the
router stays thin (like ``analytics.py`` / ``pagination.py``).

Every number is read-only and best-effort: until Epic 11 produces traffic the counters
are simply zero, so a freshly-started stack reports zeros rather than erroring.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis

from linkshrink_shared import (
    METRICS_CACHE_HIT_KEY,
    METRICS_CACHE_MISS_KEY,
    METRICS_REDIRECTS_TOTAL_KEY,
    WORKER_HEARTBEAT_STALE_SECONDS,
    pending_count,
    read_counter,
    read_heartbeat,
    stream_length,
)

#: Decimal places the cache hit ratio is rounded to for a clean payload.
HIT_RATIO_PRECISION = 4


@dataclass(frozen=True)
class MetricsSnapshot:
    """The live numbers assembled by :func:`collect_metrics`, mapped to the wire model."""

    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    total_redirects: int
    queue_pending: int
    queue_stream_length: int
    worker_healthy: bool
    worker_heartbeat_age_seconds: float | None


async def collect_metrics(redis: Redis, *, now: float | None = None) -> MetricsSnapshot:
    """Read the Redis counters/keys and derive the live operational numbers (§5.7).

    ``now`` (epoch seconds) defaults to the current time and is injectable so tests can
    pin the worker-heartbeat age deterministically.
    """
    current_time = time.time() if now is None else now

    cache_hits = await read_counter(redis, METRICS_CACHE_HIT_KEY)
    cache_misses = await read_counter(redis, METRICS_CACHE_MISS_KEY)
    total_redirects = await read_counter(redis, METRICS_REDIRECTS_TOTAL_KEY)
    queue_pending = await pending_count(redis)
    queue_stream_length = await stream_length(redis)
    heartbeat = await read_heartbeat(redis)

    total_lookups = cache_hits + cache_misses
    cache_hit_ratio = (
        round(cache_hits / total_lookups, HIT_RATIO_PRECISION) if total_lookups else 0.0
    )

    # ``max(0.0, ...)`` guards against clock skew between the worker (which writes the
    # heartbeat) and the API (which reads it) reporting a nonsensical negative age.
    heartbeat_age = None if heartbeat is None else max(0.0, current_time - float(heartbeat))
    worker_healthy = heartbeat_age is not None and heartbeat_age <= WORKER_HEARTBEAT_STALE_SECONDS

    return MetricsSnapshot(
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        cache_hit_ratio=cache_hit_ratio,
        total_redirects=total_redirects,
        queue_pending=queue_pending,
        queue_stream_length=queue_stream_length,
        worker_healthy=worker_healthy,
        worker_heartbeat_age_seconds=heartbeat_age,
    )

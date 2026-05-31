"""Liveness probe for the worker's Docker healthcheck (TDD §5.2).

The worker has no HTTP surface, so liveness is the heartbeat it writes each consumer
pass. This script reads ``metrics:worker:heartbeat`` and exits non-zero if it is missing
or older than the staleness threshold, which Docker reads as unhealthy. Run it with
``python -m linkshrink_worker.healthcheck``.
"""

from __future__ import annotations

import asyncio
import sys
import time

from linkshrink_shared import (
    WORKER_HEARTBEAT_STALE_SECONDS,
    get_redis_client,
    get_settings,
    read_heartbeat,
)


async def is_healthy() -> bool:
    """Return whether the worker's heartbeat exists and is within the staleness threshold."""
    redis = get_redis_client(get_settings())
    try:
        raw = await read_heartbeat(redis)
    finally:
        await redis.aclose()

    if raw is None:
        return False
    try:
        last_beat = float(raw)
    except ValueError:
        return False
    return (time.time() - last_beat) <= WORKER_HEARTBEAT_STALE_SECONDS


def main() -> None:
    """Exit ``0`` when the worker is live, ``1`` when its heartbeat is missing or stale."""
    sys.exit(0 if asyncio.run(is_healthy()) else 1)


if __name__ == "__main__":
    main()

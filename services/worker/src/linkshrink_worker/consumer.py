"""The consumer loop and crash-recovery passes (TDD §5.7).

Two single-pass coroutines do all the work and the entrypoint just calls them on a
schedule, which also makes each pass directly drivable from integration tests:

* :func:`run_consumer_once` — heartbeat, then ``XREADGROUP`` one batch of new entries and
  process each (``XACK`` on success, leave pending on failure).
* :func:`run_recovery_once` — ``XAUTOCLAIM`` a crashed consumer's idle pending entries,
  dead-letter any that hit the delivery-attempt cap, and reprocess the rest.

At-least-once: a failed entry is never ``XACK``ed, so it stays in the pending list and is
retried by the next recovery pass until it succeeds or is dead-lettered.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from linkshrink_shared import (
    CLICKS_CONSUMER_GROUP,
    CLICKS_STREAM,
    MAX_DELIVERY_ATTEMPTS,
    ack_click,
    claim_stale_clicks,
    dead_letter,
    read_clicks,
    write_heartbeat,
)
from linkshrink_worker.config import CONSUMER_BATCH_COUNT, CONSUMER_BLOCK_MS
from linkshrink_worker.processing import process_message

logger = logging.getLogger(__name__)


async def _process_entry(
    redis: Redis,
    session_factory: async_sessionmaker,
    message_id: str,
    fields: dict[str, str],
) -> bool:
    """Insert one click and ``XACK`` it; on failure log and leave it pending.

    Returns ``True`` if the entry was processed and acked, ``False`` if it failed and was
    left in the pending list for a later recovery pass.
    """
    try:
        async with session_factory() as session:
            await process_message(session, fields)
    except Exception:
        logger.exception("failed to process click %s; leaving pending for recovery", message_id)
        return False
    await ack_click(redis, message_id)
    return True


async def run_consumer_once(
    redis: Redis,
    session_factory: async_sessionmaker,
    consumer: str,
    *,
    count: int = CONSUMER_BATCH_COUNT,
    block_ms: int = CONSUMER_BLOCK_MS,
) -> int:
    """Write the heartbeat, read one batch of new entries, and process each.

    The heartbeat is written every pass — even when the read returns nothing — so an idle
    worker stays live. Returns the number of entries successfully processed this pass.
    """
    await write_heartbeat(redis, time.time())
    batches = await read_clicks(redis, consumer, count=count, block_ms=block_ms)

    processed = 0
    for _stream, entries in batches or []:
        for message_id, fields in entries:
            if await _process_entry(redis, session_factory, message_id, fields):
                processed += 1
    return processed


async def _delivery_counts(
    redis: Redis, consumer: str, message_ids: list[str]
) -> dict[str, int]:
    """Map each just-claimed message id to its delivery count via ``XPENDING``.

    Scoped to the reclaiming ``consumer`` (which now owns every claimed entry after the
    ``XAUTOCLAIM``) and to the claimed id range — ``message_ids`` arrives in ascending id
    order from the claim. A global ``-``/``+`` lookup would return the group's *first* N
    pending entries, so a larger backlog or another consumer's not-yet-idle entries could
    crowd a claimed entry out of the window, default its count to 1, and retry a poison
    message forever instead of dead-lettering it at the cap.
    """
    if not message_ids:
        return {}
    pending = await redis.xpending_range(
        CLICKS_STREAM,
        CLICKS_CONSUMER_GROUP,
        min=message_ids[0],
        max=message_ids[-1],
        count=len(message_ids),
        consumername=consumer,
    )
    return {entry["message_id"]: int(entry["times_delivered"]) for entry in pending}


async def _recover_entry(
    redis: Redis,
    session_factory: async_sessionmaker,
    message_id: str,
    fields: dict[str, str],
    attempts: int,
) -> None:
    """Dead-letter an entry that hit the attempt cap, otherwise reprocess it.

    At or beyond :data:`MAX_DELIVERY_ATTEMPTS` the entry is copied to the dead-letter
    stream and ``XACK``ed so it leaves the pending list; below the cap it is retried like a
    fresh entry (acked on success, left pending on failure).
    """
    if attempts >= MAX_DELIVERY_ATTEMPTS:
        logger.warning("dead-lettering poison click %s after %d attempts", message_id, attempts)
        await dead_letter(redis, fields)
        await ack_click(redis, message_id)
        return
    await _process_entry(redis, session_factory, message_id, fields)


async def run_recovery_once(
    redis: Redis,
    session_factory: async_sessionmaker,
    consumer: str,
    *,
    min_idle_ms: int,
) -> None:
    """Reclaim and handle every idle pending entry left by a crashed consumer.

    Pages through ``XAUTOCLAIM`` until its cursor wraps to ``0-0``, dead-lettering entries
    past the attempt cap and reprocessing the rest. Reclaiming a healthy worker's in-flight
    entries is avoided by the ``min_idle_ms`` floor.
    """
    cursor: Any = "0-0"
    while True:
        cursor, claimed, _deleted = await claim_stale_clicks(
            redis, consumer, min_idle_ms=min_idle_ms, start_id=cursor
        )
        if claimed:
            counts = await _delivery_counts(
                redis, consumer, [message_id for message_id, _ in claimed]
            )
            for message_id, fields in claimed:
                await _recover_entry(
                    redis, session_factory, message_id, fields, counts.get(message_id, 1)
                )
        if cursor == "0-0":
            return

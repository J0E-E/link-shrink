"""Redis Streams helpers and the click-event payload contract (TDD §5.6, §5.7).

Owns the one authoritative click-event payload — ``{link_id, ts, referrer, ua,
source}`` — plus its (de)serializer, so the redirect producer (Epic 11) and the
worker consumer (Epic 12) agree on a single contract and can be built in parallel.
Also holds the stream/group/consumer naming, the worker heartbeat key, and thin
async wrappers over the Streams commands; the heavy consumer/recovery logic lives in
the worker (Epic 12).

All wrappers take an injected ``redis.asyncio.Redis`` client built with
``decode_responses=True`` (so stream fields read back as ``str``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from linkshrink_shared.models import Source

logger = logging.getLogger(__name__)

# --- Stream / group / consumer naming (§5.7) ---------------------------------------

#: The analytics click stream, its consumer group, and the dead-letter stream.
CLICKS_STREAM = "clicks"
CLICKS_CONSUMER_GROUP = "analytics"
DEAD_LETTER_STREAM = "clicks:dead"

#: Delivery attempts before a poison message is dead-lettered and ``XACK``ed (§5.7).
MAX_DELIVERY_ATTEMPTS = 3

#: Approximate cap on the stream length (``MAXLEN ~``) to bound Redis memory (§5.7).
CLICKS_STREAM_MAXLEN = 100_000

#: Approximate cap on the dead-letter stream so poison messages can't grow unbounded;
#: smaller than the main stream since the DLQ is only for forensics on failed messages.
DEAD_LETTER_STREAM_MAXLEN = 10_000

#: Worker liveness key and the staleness threshold the Docker healthcheck uses. The
#: consumer loop blocks ≤ ~5s between heartbeats, so 15s avoids false flaps (§5.2).
WORKER_HEARTBEAT_KEY = "metrics:worker:heartbeat"
WORKER_HEARTBEAT_STALE_SECONDS = 15


def worker_consumer_name(worker_number: int) -> str:
    """Build the consumer name for a worker (``worker-{worker_number}``)."""
    return f"worker-{worker_number}"


# --- Click-event payload contract (§5.6) -------------------------------------------


@dataclass(frozen=True)
class ClickPayload:
    """The authoritative click-event contract shared by redirect + worker (§5.6).

    The redirect service produces this and ``XADD``s it; the worker consumes it,
    derives the coarse PII-free fields (device/browser/OS, referrer host), and
    discards the raw ``ua``/``referrer``. ``ts`` is the click time (timezone-aware UTC).
    """

    link_id: int
    ts: datetime
    referrer: str | None
    ua: str | None
    source: Source


def serialize_click(payload: ClickPayload) -> dict[str, str]:
    """Flatten a payload into Redis Stream string fields (inverse of
    :func:`deserialize_click`). ``None`` referrer/ua become ``""`` and round-trip back
    to ``None``.

    ``ts`` is normalized to timezone-aware UTC so the stored value is unambiguous: a
    naive datetime is assumed to be UTC, and an aware value in another zone is converted.
    """
    ts = payload.ts if payload.ts.tzinfo is not None else payload.ts.replace(tzinfo=UTC)
    return {
        "link_id": str(payload.link_id),
        "ts": ts.astimezone(UTC).isoformat(),
        "referrer": payload.referrer or "",
        "ua": payload.ua or "",
        "source": payload.source.value,
    }


def deserialize_click(fields: dict[str, str]) -> ClickPayload:
    """Rebuild a :class:`ClickPayload` from Redis Stream fields (inverse of
    :func:`serialize_click`)."""
    return ClickPayload(
        link_id=int(fields["link_id"]),
        ts=datetime.fromisoformat(fields["ts"]),
        referrer=fields["referrer"] or None,
        ua=fields["ua"] or None,
        source=Source(fields["source"]),
    )


# --- Stream wrappers ---------------------------------------------------------------


async def add_click(
    redis: Redis, payload: ClickPayload, *, maxlen: int = CLICKS_STREAM_MAXLEN
) -> str:
    """``XADD`` a click onto the stream with approximate ``MAXLEN ~`` trimming.

    Returns the new entry's stream id. Best-effort on the hot path — the redirect
    service swallows and logs failures so a queue hiccup never blocks the 302 (§5.6).
    """
    return await redis.xadd(
        CLICKS_STREAM, serialize_click(payload), maxlen=maxlen, approximate=True
    )


async def ensure_consumer_group(
    redis: Redis, *, stream: str = CLICKS_STREAM, group: str = CLICKS_CONSUMER_GROUP
) -> None:
    """Create the consumer group (and the stream, via ``MKSTREAM``) if it does not exist.

    Idempotent: a pre-existing group raises ``BUSYGROUP``, which is swallowed; any other
    error propagates.
    """
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as error:
        if "BUSYGROUP" not in str(error):
            raise


async def read_clicks(
    redis: Redis,
    consumer: str,
    *,
    group: str = CLICKS_CONSUMER_GROUP,
    stream: str = CLICKS_STREAM,
    count: int = 100,
    block_ms: int = 5000,
) -> list[Any]:
    """``XREADGROUP`` a batch of new (never-delivered) entries for this consumer."""
    return await redis.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)


async def ack_click(
    redis: Redis,
    message_id: str,
    *,
    group: str = CLICKS_CONSUMER_GROUP,
    stream: str = CLICKS_STREAM,
) -> int:
    """``XACK`` a processed entry so it leaves the pending-entries list."""
    return await redis.xack(stream, group, message_id)


async def claim_stale_clicks(
    redis: Redis,
    consumer: str,
    *,
    min_idle_ms: int,
    group: str = CLICKS_CONSUMER_GROUP,
    stream: str = CLICKS_STREAM,
    count: int = 100,
    start_id: str = "0-0",
) -> tuple[Any, ...]:
    """``XAUTOCLAIM`` entries idle beyond ``min_idle_ms`` to recover a crashed consumer's PEL."""
    return await redis.xautoclaim(
        stream, group, consumer, min_idle_time=min_idle_ms, start_id=start_id, count=count
    )


async def dead_letter(
    redis: Redis,
    fields: dict[str, str],
    *,
    stream: str = DEAD_LETTER_STREAM,
    maxlen: int = DEAD_LETTER_STREAM_MAXLEN,
) -> str:
    """``XADD`` a poison message's fields onto the dead-letter stream after the attempt cap.

    Trimmed with approximate ``MAXLEN ~`` so the DLQ can't grow without bound.
    """
    return await redis.xadd(stream, fields, maxlen=maxlen, approximate=True)


async def stream_length(redis: Redis, *, stream: str = CLICKS_STREAM) -> int:
    """``XLEN`` of the stream — total recent entries (capped by ``MAXLEN ~``), a volume
    gauge for ``/api/metrics``; note entries persist past ``XACK`` so this is not backlog."""
    return await redis.xlen(stream)


async def pending_count(
    redis: Redis, *, group: str = CLICKS_CONSUMER_GROUP, stream: str = CLICKS_STREAM
) -> int:
    """``XPENDING`` summary count — entries delivered but not yet ``XACK``ed, i.e. the real
    unprocessed backlog for ``/api/metrics`` (Epic 10).

    Returns ``0`` when the consumer group does not exist yet (the worker has never started),
    which ``XPENDING`` reports as a ``NOGROUP`` ``ResponseError``.
    """
    try:
        summary = await redis.xpending(stream, group)
    except ResponseError as error:
        if "NOGROUP" in str(error):
            return 0
        raise
    return int(summary["pending"])


# --- Worker heartbeat (§5.2) -------------------------------------------------------


async def write_heartbeat(redis: Redis, timestamp: float) -> None:
    """Record the worker's liveness timestamp (epoch seconds) for the Docker healthcheck."""
    await redis.set(WORKER_HEARTBEAT_KEY, str(timestamp))


async def read_heartbeat(redis: Redis) -> str | None:
    """Read the last worker heartbeat timestamp, or ``None`` if never written."""
    return await redis.get(WORKER_HEARTBEAT_KEY)

"""Process wiring and the long-running loops for the analytics worker (TDD §5.2, §5.7).

Builds the long-lived resources (async engine + session factory, Redis client), ensures
the consumer group exists, then runs three asyncio tasks: the consumer loop as the main
task, a periodic recovery task, and the periodic purge task (Epic 13) — the last two share
the same ``create_task`` + interval pattern. SIGTERM/SIGINT trigger a graceful shutdown that
cancels the tasks and disposes the connections. Run it with ``python -m linkshrink_worker.main``.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_shared import (
    ensure_consumer_group,
    get_redis_client,
    get_settings,
    worker_consumer_name,
)
from linkshrink_worker.config import (
    ERROR_BACKOFF_SECONDS,
    PURGE_INTERVAL_SECONDS,
    RECOVERY_IDLE_MS,
    RECOVERY_INTERVAL_SECONDS,
    get_worker_number,
)
from linkshrink_worker.consumer import run_consumer_once, run_recovery_once
from linkshrink_worker.purge import run_purge_once

logger = logging.getLogger(__name__)


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    """Wait up to ``seconds``, returning early if shutdown is requested."""
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def _consumer_loop(redis, session_factory, consumer, stop: asyncio.Event) -> None:
    """Run consumer passes back-to-back until shutdown is requested.

    A pass that raises (e.g. a transient Redis disconnect) is logged and retried after a
    short backoff rather than killing the loop, so a blip self-heals instead of leaving the
    worker alive-but-idle until the stale heartbeat trips a restart.
    """
    while not stop.is_set():
        try:
            await run_consumer_once(redis, session_factory, consumer)
        except Exception:
            logger.exception("consumer pass failed; backing off before retry")
            await _sleep_or_stop(stop, ERROR_BACKOFF_SECONDS)


async def _recovery_loop(redis, session_factory, consumer, stop: asyncio.Event) -> None:
    """Run a recovery pass on a fixed interval until shutdown is requested.

    Sleeps the interval as a cancellable wait on ``stop`` so a shutdown wakes it
    immediately instead of waiting out the full interval. A pass that raises is logged and
    retried on the next interval rather than killing the loop.
    """
    while not stop.is_set():
        try:
            await run_recovery_once(redis, session_factory, consumer, min_idle_ms=RECOVERY_IDLE_MS)
        except Exception:
            logger.exception("recovery pass failed; retrying next interval")
        await _sleep_or_stop(stop, RECOVERY_INTERVAL_SECONDS)


async def _purge_loop(session_factory, stop: asyncio.Event) -> None:
    """Permanently delete long-expired links on a fixed interval until shutdown.

    Follows the recovery loop: a pass that raises is logged and retried on the next
    interval rather than killing the loop, and the wait is a cancellable ``stop`` wait so
    shutdown is immediate. Needs only the session factory — the purge never touches Redis.
    """
    while not stop.is_set():
        try:
            await run_purge_once(session_factory)
        except Exception:
            logger.exception("purge pass failed; retrying next interval")
        await _sleep_or_stop(stop, PURGE_INTERVAL_SECONDS)


async def run() -> None:
    """Open resources, ensure the consumer group, and run the loops until shutdown."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    redis = get_redis_client(settings)
    consumer = worker_consumer_name(get_worker_number())

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for received_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(received_signal, stop.set)
        except NotImplementedError:  # pragma: no cover - Windows has no signal handlers
            # ``Event.set`` isn't thread-safe; hop back onto the loop from the handler.
            signal.signal(received_signal, lambda *_: loop.call_soon_threadsafe(stop.set))

    await ensure_consumer_group(redis)
    logger.info("worker %s started, consuming %s", consumer, "clicks")

    tasks = [
        asyncio.create_task(_consumer_loop(redis, session_factory, consumer, stop)),
        asyncio.create_task(_recovery_loop(redis, session_factory, consumer, stop)),
        asyncio.create_task(_purge_loop(session_factory, stop)),
    ]
    try:
        await stop.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await redis.aclose()
        await engine.dispose()
        logger.info("worker %s stopped", consumer)


def main() -> None:
    """Console entrypoint: run the worker until interrupted."""
    asyncio.run(run())


if __name__ == "__main__":
    main()

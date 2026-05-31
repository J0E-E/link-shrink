"""The scheduled purge pass: permanent deletion 3 months after expiry (TDD §5.2, §5.12).

Like the consumer, the work is one pure single-pass coroutine (:func:`run_purge_once`)
that the ``main`` loop calls on a fixed interval and the integration tests drive directly.

A single bulk ``DELETE FROM links`` does all the work: Postgres compares ``expires_at``
against its own clock and the ``click_events`` rows go with each link via the table's
``ON DELETE CASCADE`` foreign key — so this stays purge-only, no per-row loading and no
separate delete of the cascaded events.
"""

from __future__ import annotations

import logging

from sqlalchemy import String, bindparam, cast, delete, func
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.ext.asyncio import async_sessionmaker

from linkshrink_shared import Link
from linkshrink_worker.config import PURGE_RETENTION_INTERVAL

logger = logging.getLogger(__name__)


async def run_purge_once(
    session_factory: async_sessionmaker,
    *,
    retention_interval: str = PURGE_RETENTION_INTERVAL,
) -> int:
    """Permanently delete links expired longer than ``retention_interval`` and cascade.

    Uses the database clock (``now()``) for the cutoff so it matches the redirect service's
    expiry check, and relies on the ``ON DELETE CASCADE`` FK to remove each link's
    ``click_events``. Returns the number of links deleted this pass.
    """
    # Bind the retention as text and let Postgres cast it to an interval — sending it as a
    # parameter keeps it injection-proof, and the explicit String type stops asyncpg from
    # trying to encode the plain string as an interval object itself.
    cutoff = func.now() - cast(
        bindparam("retention_interval", retention_interval, type_=String), INTERVAL
    )
    async with session_factory() as session:
        result = await session.execute(
            delete(Link)
            .where(Link.expires_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
    purged = result.rowcount or 0
    if purged:
        logger.info("purged %d expired links (cascaded their click events)", purged)
    return purged

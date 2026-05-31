"""Per-link analytics aggregation queries (Epic 8, TDD §5.8/§7).

Reads the PII-free ``click_events`` rows written by the worker (Epic 12) and rolls them
up for one link: a total, a daily time series, and a breakdown per dimension. Kept in
its own module so the router stays thin (like ``pagination.py`` / ``persistence.py``).

Two decisions are baked in here:

* **UTC daily buckets** — ``date_trunc('day', clicked_at AT TIME ZONE 'UTC')`` floors to
  a real UTC calendar day regardless of the database session timezone (§7 decided).
* **NULL → "unknown"** — the nullable text dimensions coalesce to the literal
  ``"unknown"`` so each breakdown's counts always sum to the total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from linkshrink_shared import ClickEvent

#: Label used for a missing value in a nullable-dimension breakdown.
UNKNOWN_VALUE = "unknown"


@dataclass(frozen=True)
class LinkAnalytics:
    """The aggregated pieces for one link, assembled by :func:`aggregate_link_analytics`."""

    total_clicks: int
    daily: list[tuple[date, int]]
    by_device_type: list[tuple[str, int]]
    by_browser_family: list[tuple[str, int]]
    by_os_family: list[tuple[str, int]]
    by_referrer_domain: list[tuple[str, int]]
    by_source: list[tuple[str, int]]


async def aggregate_link_analytics(session: AsyncSession, link_id: int) -> LinkAnalytics:
    """Roll up every ``click_events`` row for ``link_id`` into one analytics bundle.

    Runs the aggregates sequentially on the one request session; each scan is backed by
    the ``ix_click_events_link_id_clicked_at`` index. A link with no clicks yields a
    zeroed bundle (total 0, every list empty).

    Seven round trips is the deliberate, readable choice for this unthrottled per-link
    read. If it ever shows up hot, collapse them into a single index scan with
    ``GROUP BY GROUPING SETS`` ((), (day), (device_type), …) and demultiplex the rows by
    which grouping key is non-NULL (use ``GROUPING()`` to tell a real NULL apart).
    """
    return LinkAnalytics(
        total_clicks=await _count_total(session, link_id),
        daily=await _daily_buckets(session, link_id),
        by_device_type=await _breakdown(session, link_id, ClickEvent.device_type),
        by_browser_family=await _breakdown(
            session, link_id, ClickEvent.browser_family, coalesce_null=True
        ),
        by_os_family=await _breakdown(
            session, link_id, ClickEvent.os_family, coalesce_null=True
        ),
        by_referrer_domain=await _breakdown(
            session, link_id, ClickEvent.referrer_domain, coalesce_null=True
        ),
        by_source=await _breakdown(session, link_id, ClickEvent.source),
    )


async def _count_total(session: AsyncSession, link_id: int) -> int:
    """Total clicks for the link."""
    query = select(func.count()).where(ClickEvent.link_id == link_id)
    return await session.scalar(query) or 0


async def _daily_buckets(session: AsyncSession, link_id: int) -> list[tuple[date, int]]:
    """Clicks per UTC day, oldest first (sparse — only days with clicks)."""
    day_bucket = func.date_trunc("day", ClickEvent.clicked_at.op("AT TIME ZONE")("UTC"))
    query = (
        select(day_bucket.label("day"), func.count().label("count"))
        .where(ClickEvent.link_id == link_id)
        .group_by(day_bucket)
        .order_by(day_bucket.asc())
    )
    rows = (await session.execute(query)).all()
    # ``date_trunc`` of an "AT TIME ZONE" value is a naive timestamp at UTC midnight.
    return [(row.day.date(), row.count) for row in rows]


async def _breakdown(
    session: AsyncSession,
    link_id: int,
    column: InstrumentedAttribute,
    *,
    coalesce_null: bool = False,
) -> list[tuple[str, int]]:
    """Clicks grouped by ``column``, ordered most-clicks-first (value asc breaks ties).

    Nullable text dimensions pass ``coalesce_null=True`` so a missing value is reported
    as ``UNKNOWN_VALUE`` instead of dropping the row; the NOT-NULL enum columns don't.

    The tiebreak casts the value to text so enum dimensions order alphabetically by their
    string value (a raw ``enum ASC`` would sort by the type's declaration order instead).
    """
    value = func.coalesce(column, UNKNOWN_VALUE) if coalesce_null else column
    query = (
        select(value.label("value"), func.count().label("count"))
        .where(ClickEvent.link_id == link_id)
        .group_by(value)
        .order_by(func.count().desc(), cast(value, String).asc())
    )
    rows = (await session.execute(query)).all()
    # Enum columns come back as StrEnum members; ``str`` yields their string value.
    return [(str(row.value), row.count) for row in rows]

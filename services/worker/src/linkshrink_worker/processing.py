"""Turn one raw stream entry into a persisted ``ClickEvent`` (TDD §5.7).

The single place a click crosses from the queue into Postgres: deserialize the payload,
derive the coarse PII-free fields, and insert one row. The raw ``ua``/``referrer`` are
read only to derive categories and are never written. Any failure (bad payload, a click
for a link that no longer exists) propagates so the caller leaves the entry pending for
recovery and eventual dead-lettering.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_shared import ClickEvent, deserialize_click
from linkshrink_worker.parsing import parse_user_agent, referrer_host


def build_click_event(fields: dict[str, str]) -> ClickEvent:
    """Map a raw stream entry's fields to a ``ClickEvent`` with only coarse fields.

    The raw User-Agent and Referer are consumed here to derive device/browser/OS and the
    referrer host; neither raw value is carried onto the row.
    """
    payload = deserialize_click(fields)
    derived = parse_user_agent(payload.ua)
    return ClickEvent(
        link_id=payload.link_id,
        clicked_at=payload.ts,
        referrer_domain=referrer_host(payload.referrer),
        device_type=derived.device_type,
        browser_family=derived.browser_family,
        os_family=derived.os_family,
        source=payload.source,
    )


async def process_message(session: AsyncSession, fields: dict[str, str]) -> None:
    """Insert one click as a ``ClickEvent`` and commit.

    Raises on a malformed payload or a foreign-key violation (a click for a link that no
    longer exists), which the caller treats as a processing failure: the entry stays in
    the pending list and is retried, then dead-lettered after the attempt cap.
    """
    session.add(build_click_event(fields))
    await session.commit()

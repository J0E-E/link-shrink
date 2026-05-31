"""Database insert helpers for the create flow.

Implements the ``try_persist`` contract that ``generate_unique_short_code`` (Epic 3)
expects: attempt to insert a ``Link`` and return ``True`` on success, ``False`` only
when the short code collides with an existing one (the ``lower(short_code)`` unique
violation), letting every other error propagate. The insert runs inside a savepoint
(``begin_nested``) so a collision rolls back just that attempt and leaves the outer
transaction usable for a retry.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_shared import Link

logger = logging.getLogger(__name__)

#: The unique index guarding case-insensitive short-code uniqueness (see models.py).
#: A functional unique index does not always populate asyncpg's ``constraint_name``,
#: so we match the index name in the error text to identify a code collision.
SHORT_CODE_UNIQUE_INDEX = "uq_links_lower_short_code"


def is_short_code_conflict(error: IntegrityError) -> bool:
    """True if ``error`` is the short-code unique-index violation (vs. some other one)."""
    original = getattr(error, "orig", None)
    constraint = getattr(original, "constraint_name", None)
    if constraint == SHORT_CODE_UNIQUE_INDEX:
        return True
    # Fall back to matching the index name in the message (functional indexes often
    # leave constraint_name empty).
    return SHORT_CODE_UNIQUE_INDEX in str(original or error)


async def try_insert_link(session: AsyncSession, link: Link) -> bool:
    """Insert ``link`` inside a savepoint; return ``False`` only on a code collision.

    Any non-collision ``IntegrityError`` (or any other error) propagates, so a
    transient failure is never silently retried as if it were a collision.
    """
    try:
        async with session.begin_nested():
            session.add(link)
            await session.flush()
    except IntegrityError as error:
        if is_short_code_conflict(error):
            return False
        raise
    return True

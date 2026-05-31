"""The hot-path redirect endpoint — ``GET /{code}`` (TDD §5.6).

Resolves a code (see :mod:`linkshrink_redirect.resolution`) and either serves a
``302`` to the target or a ``404``. On a redirect it queues a click event, but
strictly best-effort: a queue or metrics failure is swallowed and logged so it can
never block or break the 302. The ``302`` carries ``Cache-Control: no-store`` so it
stays deliberately non-cacheable.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_redirect.dependencies import get_db_session, get_redis
from linkshrink_redirect.resolution import resolve_code
from linkshrink_shared import ClickPayload, Source, add_click, increment_redirects_total

logger = logging.getLogger(__name__)

router = APIRouter()

#: The query value that marks a click as coming from a scanned QR code (§5.6). The
#: query string is read only for this; it is never part of the cache key.
QR_SOURCE_VALUE = "qr"


@router.get("/{code}")
async def redirect_to_target(
    code: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    source: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """Resolve ``code`` to a 302, or 404 if it is unknown or expired (§5.6)."""
    resolved = await resolve_code(redis, session, code)
    if resolved is None:
        raise HTTPException(status_code=404)

    await _queue_click(redis, request, code, resolved.link_id, source)
    return RedirectResponse(
        url=resolved.original_url, status_code=302, headers={"Cache-Control": "no-store"}
    )


async def _queue_click(
    redis: Redis, request: Request, code: str, link_id: int, source: str | None
) -> None:
    """Best-effort: queue the click and bump the served-redirect counter.

    Wrapped so a Redis hiccup on either side-effect is swallowed and logged — the 302 is
    already decided and must not depend on analytics (§5.6).
    """
    click_source = Source.qr if source == QR_SOURCE_VALUE else Source.direct
    payload = ClickPayload(
        link_id=link_id,
        ts=datetime.now(UTC),
        referrer=request.headers.get("Referer"),
        ua=request.headers.get("User-Agent"),
        source=click_source,
    )
    try:
        await add_click(redis, payload)
        await increment_redirects_total(redis)
    except Exception as error:  # noqa: BLE001 - analytics must never break the 302
        logger.warning("click enqueue failed for code %s: %s", code, error)

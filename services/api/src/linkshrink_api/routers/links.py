"""``POST /api/links`` — create a short link (Epic 6, TDD §5.8/§5.12).

The create flow runs in the §5.12 order: rate-limit check → URL validation → the
alias-vs-generated branch → insert → 201. Rate limiting is first, so an over-limit
client is rejected before any work (and a fixed-window hit is counted even when a
later step fails). The blocking DNS check inside ``validate_url`` is run off the event
loop with ``asyncio.to_thread`` so the async handler never stalls.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_api.dependencies import (
    get_client_ip,
    get_db_session,
    get_host_resolver,
    get_redis,
    get_settings_dependency,
)
from linkshrink_api.errors import (
    alias_taken_error,
    alias_validation_error,
    invalid_cursor_error,
    link_not_found_error,
    rate_limited_error,
    short_code_exhausted_error,
    url_validation_error,
)
from linkshrink_api.pagination import decode_cursor, encode_cursor
from linkshrink_api.persistence import try_insert_link
from linkshrink_api.schemas import (
    CreateLinkRequest,
    CreateLinkResponse,
    LinkView,
    ListLinksResponse,
    clamp_limit,
    clamp_ttl,
)
from linkshrink_api.urls import build_qr_url, build_short_url
from linkshrink_shared import (
    HostResolver,
    Link,
    Settings,
    ShortCodeCollisionError,
    ShortCodeGenerator,
    ValidationError,
    check_rate_limit,
    fetch_next_sequence_value,
    generate_unique_short_code,
    validate_alias,
    validate_url,
)

router = APIRouter()


@lru_cache(maxsize=8)
def _generator_for_salt(salt: str) -> ShortCodeGenerator:
    """A short-code generator for a given salt, built once and reused.

    The salt is process-stable, so memoizing avoids rebuilding the underlying hashids
    instance on every generated-code create while still honoring the injected settings.
    """
    return ShortCodeGenerator(salt)


@router.post("/api/links", status_code=201, response_model=CreateLinkResponse)
async def create_link(
    body: CreateLinkRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    resolver: Annotated[HostResolver, Depends(get_host_resolver)],
    client_ip: Annotated[str, Depends(get_client_ip)],
) -> CreateLinkResponse:
    """Validate, allocate a short code, persist, and return the created link."""
    rate_limit = await check_rate_limit(redis, client_ip)
    if not rate_limit.is_allowed:
        raise rate_limited_error(rate_limit.retry_after_seconds)

    try:
        original_url = await asyncio.to_thread(
            validate_url, body.url, public_host=settings.public_host, resolver=resolver
        )
    except ValidationError as error:
        raise url_validation_error(error) from error

    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(seconds=clamp_ttl(body.ttl_seconds))

    if body.alias is not None:
        short_code = await _create_with_alias(
            session, body.alias, original_url, created_at, expires_at
        )
    else:
        short_code = await _create_with_generated_code(
            session, settings, original_url, created_at, expires_at
        )

    await session.commit()

    return CreateLinkResponse(
        short_code=short_code,
        short_url=build_short_url(settings.public_host, short_code),
        original_url=original_url,
        created_at=created_at,
        expires_at=expires_at,
        qr_url=build_qr_url(settings.public_host, short_code),
    )


def _link_to_view(link: Link, public_host: str) -> LinkView:
    """Build the public read view of a link, shared by listing and detail."""
    return LinkView(
        short_code=link.short_code,
        short_url=build_short_url(public_host, link.short_code),
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
        qr_url=build_qr_url(public_host, link.short_code),
        is_custom=link.is_custom,
    )


@router.get("/api/links", response_model=ListLinksResponse)
async def list_links(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    cursor: str | None = None,
    limit: int | None = None,
) -> ListLinksResponse:
    """Keyset-paginated, newest-first feed of links (§5.8).

    Pages over the ``(created_at DESC, id DESC)`` index: an opaque ``cursor`` carries
    the last row's ``(created_at, id)``, and one extra row beyond ``limit`` is fetched
    to tell whether a next page exists. Expired links are included (this is the
    management view, not the redirect hot path).
    """
    page_size = clamp_limit(limit)

    query = select(Link).order_by(Link.created_at.desc(), Link.id.desc())
    if cursor is not None:
        try:
            cursor_created_at, cursor_id = decode_cursor(cursor)
        except ValueError as error:
            raise invalid_cursor_error() from error
        query = query.where(
            tuple_(Link.created_at, Link.id) < tuple_(cursor_created_at, cursor_id)
        )

    # Fetch one extra row so we can tell if there is a following page without a count.
    rows = (await session.scalars(query.limit(page_size + 1))).all()
    has_next_page = len(rows) > page_size
    page = rows[:page_size]

    next_cursor = None
    if has_next_page:
        last = page[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return ListLinksResponse(
        items=[_link_to_view(link, settings.public_host) for link in page],
        next_cursor=next_cursor,
    )


@router.get("/api/links/{code}", response_model=LinkView)
async def get_link(
    code: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> LinkView:
    """Single-link detail by short code → 200, or 404 if no such code (§5.8)."""
    query = select(Link).where(func.lower(Link.short_code) == code.lower())
    link = await session.scalar(query)
    if link is None:
        raise link_not_found_error(code)
    return _link_to_view(link, settings.public_host)


async def _create_with_alias(
    session: AsyncSession,
    raw_alias: str,
    original_url: str,
    created_at: datetime,
    expires_at: datetime,
) -> str:
    """Validate and insert a custom alias; raise 409 if reserved or already taken."""
    try:
        alias = validate_alias(raw_alias)
    except ValidationError as error:
        raise alias_validation_error(error) from error

    link = Link(
        short_code=alias,
        original_url=original_url,
        is_custom=True,
        created_at=created_at,
        expires_at=expires_at,
    )
    if not await try_insert_link(session, link):
        raise alias_taken_error(alias)
    return alias


async def _create_with_generated_code(
    session: AsyncSession,
    settings: Settings,
    original_url: str,
    created_at: datetime,
    expires_at: datetime,
) -> str:
    """Generate a unique short code from the sequence, retrying on rare collisions."""
    generator = _generator_for_salt(settings.hashids_salt)

    async def get_next() -> int:
        return await fetch_next_sequence_value(session)

    async def try_persist(code: str) -> bool:
        link = Link(
            short_code=code,
            original_url=original_url,
            is_custom=False,
            created_at=created_at,
            expires_at=expires_at,
        )
        return await try_insert_link(session, link)

    try:
        return await generate_unique_short_code(get_next, try_persist, generator=generator)
    except ShortCodeCollisionError as error:
        raise short_code_exhausted_error() from error

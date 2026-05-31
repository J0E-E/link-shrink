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
    rate_limited_error,
    short_code_exhausted_error,
    url_validation_error,
)
from linkshrink_api.persistence import try_insert_link
from linkshrink_api.schemas import CreateLinkRequest, CreateLinkResponse, clamp_ttl
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

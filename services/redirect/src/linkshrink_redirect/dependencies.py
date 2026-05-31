"""FastAPI dependency providers for the redirect service.

Small, override-friendly seams so the endpoint never reaches for globals directly:
the database session, the Redis client, and the resolved settings. In production these
are built once at startup and held on ``app.state`` (see :mod:`linkshrink_redirect.main`);
tests override them via ``app.dependency_overrides`` to point at throwaway containers, so
no real network or app lifespan is needed.

The redirect path is unthrottled (§5.9) and never re-resolves DNS (§5.5), so unlike the
API service this has no client-IP or SSRF-resolver provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_shared import Settings


def get_settings_dependency(request: Request) -> Settings:
    """The settings loaded once at startup and held on ``app.state``."""
    return request.app.state.settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one database session per request from the app's session factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    """The shared async Redis client built at startup."""
    return request.app.state.redis

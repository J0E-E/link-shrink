"""FastAPI dependency providers.

Small, override-friendly seams so the endpoint never reaches for globals directly:
the database session, the Redis client, the resolved settings, the DNS resolver, and
the trusted client IP. In production the session factory and Redis client are built
once at startup and held on ``app.state`` (see :mod:`linkshrink_api.main`); tests
override these via ``app.dependency_overrides`` to point at throwaway containers, so
no real network or app lifespan is needed.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from linkshrink_shared import HostResolver, Settings, default_host_resolver

#: The single, app-controlled header carrying the real client IP. Nginx's real_ip
#: module sets it (Epic 18b); the API trusts only this header and never parses a raw,
#: spoofable ``X-Forwarded-For`` chain (§5.9).
REAL_IP_HEADER = "X-Real-IP"


def get_settings_dependency(request: Request) -> Settings:
    """The settings loaded once at startup and held on ``app.state``.

    Reuses the same :class:`Settings` the lifespan built the engine and Redis client
    from (see :mod:`linkshrink_api.main`), rather than re-reading the environment and
    ``.env`` file on every request. Tests override this via ``app.dependency_overrides``.
    """
    return request.app.state.settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one database session per request from the app's session factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    """The shared async Redis client built at startup."""
    return request.app.state.redis


def get_host_resolver() -> HostResolver:
    """The DNS resolver used for SSRF validation (overridable in tests)."""
    return default_host_resolver


def get_client_ip(request: Request) -> str:
    """The trusted client IP: the ``X-Real-IP`` header, else the socket peer.

    Falls back to ``request.client.host`` when the header is absent (local dev and
    tests), and to ``"unknown"`` if even that is missing, so the rate-limit key is
    always well-formed.
    """
    header_ip = request.headers.get(REAL_IP_HEADER)
    if header_ip:
        return header_ip.strip()
    if request.client is not None:
        return request.client.host
    return "unknown"

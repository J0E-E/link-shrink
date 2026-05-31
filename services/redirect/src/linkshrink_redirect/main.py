"""FastAPI application factory and process wiring for the redirect service.

Builds the redirect app and, via a lifespan handler, the long-lived resources it
shares across requests: the async SQLAlchemy engine + session factory and the Redis
client, all held on ``app.state`` and disposed on shutdown. Run it with
``uvicorn linkshrink_redirect.main:app``.

The system router (``/health``) is mounted before the redirect router so the literal
``/health`` path is never shadowed by the ``/{code}`` catch-all (§5.6).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_redirect.routers import redirect, system
from linkshrink_shared import get_redis_client, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open shared resources at startup and close them at shutdown."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.redis = get_redis_client(settings)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    """Build the redirect application with its routers mounted.

    ``system`` is included first so ``/health`` resolves before the ``/{code}``
    catch-all in ``redirect`` (route matching is registration-ordered).
    """
    app = FastAPI(title="LinkShrink Redirect", lifespan=lifespan)
    app.include_router(system.router)
    app.include_router(redirect.router)
    return app


app = create_app()

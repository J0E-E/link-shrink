"""FastAPI application factory and process wiring.

Builds the API app and, via a lifespan handler, the long-lived resources it shares
across requests: the async SQLAlchemy engine + session factory and the Redis client,
all held on ``app.state`` and disposed on shutdown. Run it with
``uvicorn linkshrink_api.main:app``.

Epic 6 mounts only the create router (``POST /api/links``). Later epics add the
dashboard, analytics, QR, metrics, and health routers onto the same app.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_api.routers import links
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
    """Build the API application with its routers mounted."""
    app = FastAPI(title="LinkShrink API", lifespan=lifespan)
    app.include_router(links.router)
    return app


app = create_app()

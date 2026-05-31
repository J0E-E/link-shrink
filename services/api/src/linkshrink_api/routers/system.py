"""Operational endpoints — ``GET /health`` and ``GET /api/metrics`` (Epic 10, TDD §5.7).

``/health`` is a pure liveness probe (always 200, no dependency checks) used as the api
container's Docker healthcheck (Epic 18a). ``/api/metrics`` exposes the live operational
numbers the frontend renders (§5.10/§14), derived in :mod:`linkshrink_api.metrics`.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from linkshrink_api.dependencies import get_redis
from linkshrink_api.metrics import collect_metrics
from linkshrink_api.schemas import HealthResponse, MetricsResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe → always 200; does no dependency checks so it can't flap (§5.7)."""
    return HealthResponse(status="ok")


@router.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    redis: Annotated[Redis, Depends(get_redis)],
) -> MetricsResponse:
    """Live operational metrics derived from the Redis counters/keys → 200 (§5.7)."""
    snapshot = await collect_metrics(redis)
    # The snapshot's fields match the wire model one-for-one, so map by name rather than
    # by hand — a new metric only needs adding in the dataclass and the schema, not here.
    return MetricsResponse(**asdict(snapshot))

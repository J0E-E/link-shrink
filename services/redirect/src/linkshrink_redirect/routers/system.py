"""Operational endpoint — ``GET /health`` (TDD §5.7).

A pure liveness probe (always 200, no dependency checks) used as the redirect
container's Docker healthcheck (Epic 18a). It is registered before the ``/{code}``
catch-all so the literal path is never shadowed.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """The liveness probe body."""

    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe → always 200; does no dependency checks so it can't flap (§5.7)."""
    return HealthResponse(status="ok")

"""Request and response models for the API service (Pydantic).

The wire contract for ``POST /api/links`` (TDD §5.8). A single ``ttl_seconds`` field
is the only lifetime input — there is no ``expires_at`` on the wire, which avoids
client clock-skew; the server computes ``expires_at`` itself (§5.8). ``ttl_seconds``
is clamped (not rejected) to the allowed range in the handler, so it is intentionally
a plain optional integer here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

#: Lifetime clamp bounds (§5.8/§6 decision #13): 1 hour minimum, 30 days maximum and
#: default. Kept here in the API service since they are the create-endpoint's contract;
#: they may be promoted to shared config later if another service needs them.
TTL_MIN_SECONDS = 3600
TTL_MAX_SECONDS = 2592000
TTL_DEFAULT_SECONDS = 2592000


def clamp_ttl(ttl_seconds: int | None) -> int:
    """Clamp a requested lifetime into [TTL_MIN_SECONDS, TTL_MAX_SECONDS].

    A missing value uses the default; out-of-range values are clamped (never rejected),
    so a client asking for too short or too long simply gets the nearest allowed bound.
    """
    if ttl_seconds is None:
        return TTL_DEFAULT_SECONDS
    return max(TTL_MIN_SECONDS, min(TTL_MAX_SECONDS, ttl_seconds))


class CreateLinkRequest(BaseModel):
    """Body for ``POST /api/links``.

    ``url`` is required; ``alias`` opts into a custom short code; ``ttl_seconds`` opts
    into a shorter lifetime (clamped to [TTL_MIN_SECONDS, TTL_MAX_SECONDS], default
    TTL_DEFAULT_SECONDS).
    """

    url: str
    alias: str | None = None
    ttl_seconds: int | None = None


class CreateLinkResponse(BaseModel):
    """201 body for a created link (§5.8).

    ``qr_url`` points at the QR endpoint that does not exist until Epic 9 — it is only
    a constructed string here, with no code dependency.
    """

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime
    qr_url: str

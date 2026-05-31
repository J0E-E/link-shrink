"""Request and response models for the API service (Pydantic).

The wire contract for ``POST /api/links`` (TDD §5.8). A single ``ttl_seconds`` field
is the only lifetime input — there is no ``expires_at`` on the wire, which avoids
client clock-skew; the server computes ``expires_at`` itself (§5.8). ``ttl_seconds``
is clamped (not rejected) to the allowed range in the handler, so it is intentionally
a plain optional integer here.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

#: Lifetime clamp bounds (§5.8/§6 decision #13): 1 hour minimum, 30 days maximum and
#: default. Kept here in the API service since they are the create-endpoint's contract;
#: they may be promoted to shared config later if another service needs them.
TTL_MIN_SECONDS = 3600
TTL_MAX_SECONDS = 2592000
TTL_DEFAULT_SECONDS = 2592000

#: Listing page-size bounds (§5.8): default 20, clamped to a maximum of 100 so this
#: public, unauthenticated endpoint can't be asked for an unbounded page.
LIST_LIMIT_DEFAULT = 20
LIST_LIMIT_MAX = 100


def clamp_ttl(ttl_seconds: int | None) -> int:
    """Clamp a requested lifetime into [TTL_MIN_SECONDS, TTL_MAX_SECONDS].

    A missing value uses the default; out-of-range values are clamped (never rejected),
    so a client asking for too short or too long simply gets the nearest allowed bound.
    """
    if ttl_seconds is None:
        return TTL_DEFAULT_SECONDS
    return max(TTL_MIN_SECONDS, min(TTL_MAX_SECONDS, ttl_seconds))


def clamp_limit(limit: int | None) -> int:
    """Clamp a requested page size into [1, LIST_LIMIT_MAX].

    A missing value uses LIST_LIMIT_DEFAULT; out-of-range values are clamped (never
    rejected), mirroring ``clamp_ttl`` — too large is capped at LIST_LIMIT_MAX and a
    non-positive value floors at 1.
    """
    if limit is None:
        return LIST_LIMIT_DEFAULT
    return max(1, min(LIST_LIMIT_MAX, limit))


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


class LinkView(BaseModel):
    """Read-side view of a link, shared by the listing and detail endpoints (§5.8).

    These are the ``CreateLinkResponse`` fields plus ``is_custom`` (whether the code
    is a user-chosen alias or generated), so the dashboard (Epic 16) can tell the two
    apart. Expired links are included here — they are filtered out only on the redirect
    hot path, not in this management view.
    """

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime
    qr_url: str
    is_custom: bool


class ListLinksResponse(BaseModel):
    """200 body for ``GET /api/links`` — a page of links plus the next cursor (§5.8).

    ``next_cursor`` is an opaque token to pass back as ``?cursor=`` for the following
    page, or ``None`` when this is the last page.
    """

    items: list[LinkView]
    next_cursor: str | None


class DailyClickBucket(BaseModel):
    """One UTC day in the clicks-over-time series.

    ``day`` is a UTC calendar date (the click's ``clicked_at`` floored with
    ``date_trunc('day', … AT TIME ZONE 'UTC')``); ``count`` is the clicks on that day.
    The series is sparse — only days that actually have clicks appear.
    """

    day: date
    count: int


class BreakdownItem(BaseModel):
    """One row of a breakdown — a dimension value and how many clicks had it.

    Nullable dimensions (referrer_domain, browser_family, os_family) report a missing
    value as the literal ``"unknown"``, so a breakdown's counts always sum to
    ``total_clicks``.
    """

    value: str
    count: int


class LinkAnalyticsResponse(BaseModel):
    """200 body for ``GET /api/links/{code}/analytics`` — aggregated server-side (§5.8).

    ``total_clicks`` is the overall count; ``daily`` is the sparse UTC time series; the
    ``by_*`` lists are per-dimension breakdowns, each ordered most-clicks-first. A link
    with no clicks returns ``total_clicks=0`` and every list empty.
    """

    short_code: str
    total_clicks: int
    daily: list[DailyClickBucket]
    by_device_type: list[BreakdownItem]
    by_browser_family: list[BreakdownItem]
    by_os_family: list[BreakdownItem]
    by_referrer_domain: list[BreakdownItem]
    by_source: list[BreakdownItem]


class HealthResponse(BaseModel):
    """200 body for ``GET /health`` — a pure liveness probe (§5.7, Epic 18a healthcheck).

    Always ``{"status": "ok"}``; the endpoint does no dependency checks so it can't flap
    on a slow database or Redis.
    """

    status: str


class MetricsResponse(BaseModel):
    """200 body for ``GET /api/metrics`` — live operational numbers (§5.7).

    Derived from Redis counters the redirect service and worker write, so the values are
    all zero until Epic 11 produces traffic. ``cache_hit_ratio`` is ``0.0`` when there
    have been no lookups; ``queue_pending`` is the real unprocessed backlog (PEL size)
    while ``queue_stream_length`` is the total recent stream entries (capped, not backlog);
    ``worker_heartbeat_age_seconds`` is ``None`` when the worker has never written a heartbeat.
    """

    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    total_redirects: int
    queue_pending: int
    queue_stream_length: int
    worker_healthy: bool
    worker_heartbeat_age_seconds: float | None

"""linkshrink_api — the LinkShrink API service (FastAPI).

Epic 6 ships the first endpoint, ``POST /api/links`` (link creation + rate
limiting). Later epics add the dashboard listing, per-link detail, analytics,
QR generation, metrics, and health endpoints. All core logic (models, short-code
generation, validation, cache/rate-limit helpers) lives in ``linkshrink_shared``;
this package only wires it into HTTP.
"""

__version__ = "0.1.0"

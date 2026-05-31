"""Public URL construction for API responses.

Builds the canonical ``https://{public_host}/...`` forms returned in the create
response (§5.8). These are plain strings: the ``qr_url`` target does not exist until
Epic 9, and local/http deployments simply yield non-resolving strings — the proxy
(Epic 18b) is what actually serves these paths.
"""

from __future__ import annotations


def build_short_url(public_host: str, short_code: str) -> str:
    """The public short link for a code, e.g. ``https://link-shrink.org/abc123``."""
    return f"https://{public_host}/{short_code}"


def build_qr_url(public_host: str, short_code: str) -> str:
    """The QR endpoint URL for a code (served from Epic 9 onward)."""
    return f"https://{public_host}/api/links/{short_code}/qr"

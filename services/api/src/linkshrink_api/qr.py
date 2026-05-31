"""On-demand QR image rendering for short links (Epic 9, TDD §5.8).

QR codes are generated per request and never stored. We use ``segno`` (pure-Python,
no Pillow) so one library renders both the PNG default and the SVG option with error
correction level M. The encoded payload is built by the caller (``build_qr_payload``)
so it carries the ``?source=qr`` attribution the redirect service reads (§5.6).
"""

from __future__ import annotations

import io

import segno

QR_TARGET_SIZE_PX = 512
"""Roughly the pixel width we aim for (the AC says ~512px, not exact)."""

QR_ERROR_CORRECTION = "m"
"""Error correction level M, per the §6 decision."""

QR_BORDER = 4
"""Quiet-zone width in modules (the standard QR border)."""

QR_MEDIA_TYPES = {"png": "image/png", "svg": "image/svg+xml"}
"""The two supported formats and their response content types."""

QR_CACHE_MAX_AGE_SECONDS = 86400
"""How long a QR image may be cached (1 day).

A QR for a given code+format is immutable — it only encodes the short URL, which never
changes — so the response is safe to reuse. This is served as ``Cache-Control`` to let
the *client/proxy/CDN* keep a copy (the server never stores the image; it re-renders
only when a request actually reaches it). See Epic 18b for the Nginx ``proxy_cache`` /
CDN edge-cache that builds on this header.
"""

QR_CACHE_CONTROL = f"public, max-age={QR_CACHE_MAX_AGE_SECONDS}, immutable"
"""The ``Cache-Control`` header value for QR responses (``public`` = shared caches/CDN
may store it; ``immutable`` = compliant browsers skip revalidation)."""


def render_qr(payload: str, image_format: str) -> tuple[bytes, str]:
    """Render ``payload`` as a QR image of ``image_format`` (``"png"`` or ``"svg"``).

    Returns the image bytes and their media type. The scale is chosen so the image is
    close to ``QR_TARGET_SIZE_PX`` wide regardless of how many modules the payload needs.

    Raises ``ValueError`` for an unsupported ``image_format`` so the module is safe to
    reuse even if a caller forgets to pre-validate (the QR endpoint validates first).
    """
    if image_format not in QR_MEDIA_TYPES:
        raise ValueError(f"unsupported qr format {image_format!r}; use png or svg")

    code = segno.make(payload, error=QR_ERROR_CORRECTION)
    modules_with_border = code.symbol_size(scale=1, border=QR_BORDER)[0]
    scale = max(1, round(QR_TARGET_SIZE_PX / modules_with_border))

    buffer = io.BytesIO()
    code.save(buffer, kind=image_format, scale=scale, border=QR_BORDER)
    return buffer.getvalue(), QR_MEDIA_TYPES[image_format]

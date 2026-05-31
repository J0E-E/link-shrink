"""Opaque keyset-pagination cursors for the listing endpoint (§5.8).

The dashboard feed pages with keyset (not offset) pagination over the
``(created_at DESC, id DESC)`` index, so each cursor carries the ``(created_at, id)``
of the last row returned. The token is base64url-encoded purely to keep it opaque to
clients — it is not a security boundary, just a "don't depend on the format" signal.

``decode_cursor`` raises ``ValueError`` on anything it cannot parse; the router
translates that into a 400 (``invalid_cursor``).
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime

#: Separator between the two fields in the pre-encoding string. The ``id`` is an
#: integer and ``created_at`` is an ISO-8601 timestamp (which never contains ``|``),
#: so a single split on the last separator is unambiguous.
_CURSOR_SEPARATOR = "|"


def encode_cursor(created_at: datetime, link_id: int) -> str:
    """Build an opaque cursor token from the last row's ``(created_at, id)``."""
    raw = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{link_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    """Reverse :func:`encode_cursor`; raise ``ValueError`` on a malformed token."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise ValueError("cursor is not valid base64url") from error

    timestamp_text, separator, id_text = raw.rpartition(_CURSOR_SEPARATOR)
    if not separator:
        raise ValueError("cursor is missing its separator")

    created_at = datetime.fromisoformat(timestamp_text)
    # The listing endpoint only ever emits tz-aware timestamps; reject a naive one so
    # a crafted-but-decodable token can't slip a naive datetime into the timestamptz
    # comparison (keeps the opaque-token contract fully enforced).
    if created_at.tzinfo is None:
        raise ValueError("cursor timestamp is missing its timezone")
    return created_at, int(id_text)

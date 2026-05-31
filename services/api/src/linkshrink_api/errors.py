"""HTTP error mapping for the API service.

Translates the shared layer's ``ValidationError`` (which carries a machine-readable
``reason``) into FastAPI ``HTTPException``s with the status codes the TDD specifies
(§5.8, §5.12). Error bodies use ``detail = {"reason", "message"}`` so the frontend
(Epic 15) can branch on the symbolic reason instead of matching message strings.

Most validation failures are 400, but a **reserved** alias is a 409 (it is a
namespace conflict, not malformed input), matching the "reserved/taken → 409" rule.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from linkshrink_shared import REASON_ALIAS_RESERVED, ValidationError


def _detail(reason: str, message: str) -> dict[str, str]:
    """Structured error body the frontend can branch on."""
    return {"reason": reason, "message": message}


def url_validation_error(error: ValidationError) -> HTTPException:
    """Map a ``validate_url`` failure to a 400."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_detail(error.reason, str(error)),
    )


def alias_validation_error(error: ValidationError) -> HTTPException:
    """Map a ``validate_alias`` failure: reserved → 409, everything else → 400."""
    if error.reason == REASON_ALIAS_RESERVED:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_detail(error.reason, str(error)),
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_detail(error.reason, str(error)),
    )


def alias_taken_error(alias: str) -> HTTPException:
    """A custom alias that is already in use → 409."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=_detail("alias_taken", f"alias {alias!r} is already taken"),
    )


def short_code_exhausted_error() -> HTTPException:
    """The (effectively impossible) case of exhausting short-code retries → 500."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=_detail("short_code_unavailable", "could not allocate a short code"),
    )


def invalid_cursor_error() -> HTTPException:
    """A malformed/undecodable pagination cursor → 400."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_detail("invalid_cursor", "the pagination cursor is malformed"),
    )


def invalid_qr_format_error(value: str) -> HTTPException:
    """An unsupported QR ``format`` (anything but ``png``/``svg``) → 400."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_detail("invalid_format", f"unsupported qr format {value!r}; use png or svg"),
    )


def link_not_found_error(code: str) -> HTTPException:
    """No link exists for the requested short code → 404."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_detail("not_found", f"no link found for code {code!r}"),
    )


def rate_limited_error(retry_after_seconds: int | None) -> HTTPException:
    """Creation rate limit exceeded → 429 with a ``Retry-After`` header (§5.9)."""
    headers = {}
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=_detail("rate_limited", "too many create requests; slow down"),
        headers=headers,
    )

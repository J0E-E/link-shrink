"""URL + alias validation and the reserved-word list.

Creation-time guards for the ``POST /api/links`` flow (TDD §5.4, §5.5): URL scheme,
length, self-reference, and SSRF (DNS-resolve + private-IP reject) checks, plus the
custom-alias grammar and the reserved-word list. Lives in the shared package so the
API (Epic 6) and every other consumer validate identically.

Both validators follow one contract: they **raise** :class:`ValidationError` with a
machine-readable ``reason`` on failure and **return the normalized value** on
success, so the API layer can map a failure to a 400 and produce a precise message
without string-matching the exception text.

The SSRF check needs DNS, which is blocking I/O. Rather than make this pure-logic
module async, ``validate_url`` takes an injectable synchronous ``resolver`` (default
wraps ``socket.getaddrinfo``); Epic 6 runs the validator off-thread, and tests pass a
fake resolver so private-IP rejection is verified with no real DNS.

The reserved-word list must stay a superset of every proxy/frontend-served path so an
alias can never shadow a real route; :func:`proxy_served_paths` is the source of truth
the anti-drift coverage test ranges over (§5.10).
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

#: Words that may never be claimed as a custom alias because they collide with a
#: proxy/frontend-served path or are reserved defensively. MUST remain a superset of
#: :func:`proxy_served_paths` — the coverage test asserts containment (§5.4/§5.10).
RESERVED_WORDS: frozenset[str] = frozenset(
    {
        "api",
        "dashboard",
        "how-it-works",
        "health",
        "metrics",
        "assets",
        "static",
        "qr",
        "admin",
    }
)

#: Custom-alias length bounds, inclusive (§5.4/§6 decision #13).
ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 32

#: Allowed alias characters. Single case (aliases are lowercased before matching),
#: digits, and the hyphen; leading/trailing hyphens are rejected separately.
_ALIAS_PATTERN = re.compile(r"[a-z0-9-]+")

#: Maximum accepted original-URL length (§5.5/§6 decision #13).
MAX_URL_LENGTH = 2048

#: URL schemes we shorten. Anything else (``javascript:``, ``data:``, ``ftp:`` …) is
#: rejected to keep links to real, fetchable web resources only.
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})

#: Env var holding the public host used for self-reference rejection. Read directly
#: here as a deliberate Epic-4 stand-in (mirroring Epic 3's ``HASHIDS_SALT`` read);
#: Epic 5's ``config.py`` will later route this through shared config.
PUBLIC_HOST_ENV_VAR = "PUBLIC_HOST"

#: Reasons attached to :class:`ValidationError`. Exposed so the API (Epic 6) and tests
#: branch on a symbol instead of matching message strings.
REASON_ALIAS_LENGTH = "alias_length"
REASON_ALIAS_GRAMMAR = "alias_grammar"
REASON_ALIAS_HYPHEN = "alias_leading_or_trailing_hyphen"
REASON_ALIAS_RESERVED = "alias_reserved"
REASON_URL_LENGTH = "url_length"
REASON_URL_MALFORMED = "url_malformed"
REASON_URL_SCHEME = "url_scheme"
REASON_URL_NO_HOST = "url_no_host"
REASON_URL_SELF_REFERENTIAL = "url_self_referential"
REASON_URL_UNRESOLVABLE = "url_unresolvable"
REASON_URL_PRIVATE_ADDRESS = "url_private_address"

#: A DNS resolver: maps a hostname to the list of IP-address strings it resolves to.
#: The injection seam that lets :func:`validate_url` be unit-tested without real DNS.
HostResolver = Callable[[str], list[str]]


class ValidationError(Exception):
    """Raised when a submitted URL or alias fails a creation-time guard.

    Carries a machine-readable ``reason`` (one of the ``REASON_*`` constants) so the
    API layer can map the failure to a 400 and produce a precise message without
    matching on the exception text.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


def default_host_resolver(hostname: str) -> list[str]:
    """Resolve ``hostname`` to its IP addresses via the system resolver.

    The default :data:`HostResolver` — the blocking-I/O seam that tests replace.
    Returns the deduplicated address strings, or an empty list if the name does not
    resolve (the caller treats empty as unresolvable and rejects).
    """
    try:
        results = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, OSError):
        return []
    seen: dict[str, None] = {}
    for result in results:
        address = result[4][0]
        seen.setdefault(address, None)
    return list(seen)


def default_public_host() -> str:
    """Read the public host from the ``PUBLIC_HOST`` environment variable.

    Epic-4 stand-in until Epic 5's ``config.py`` provides centralized config; mirrors
    :func:`linkshrink_shared.shortcode.default_short_code_generator`.
    """
    public_host = os.environ.get(PUBLIC_HOST_ENV_VAR, "")
    if not public_host:
        raise RuntimeError(
            f"{PUBLIC_HOST_ENV_VAR} is not set; cannot reject self-referential URLs"
        )
    return public_host


def _normalize_public_host(public_host: str) -> str:
    """Reduce a configured public host to the bare lowercase hostname for comparison.

    ``PUBLIC_HOST`` is meant to be a bare hostname, but tolerate a value that carries
    a scheme and/or port (e.g. ``https://link-shrink.org:8443``) so a self-referential
    URL can never slip through just because config was set with extra parts. Falls back
    to a lowercased strip of the raw value if it has no parseable host.
    """
    candidate = public_host.strip()
    # urlsplit only fills ``.hostname`` when a scheme (and ``//``) is present; prepend a
    # dummy scheme for the bare-host / host:port forms so the port is stripped uniformly.
    to_parse = candidate if "//" in candidate else f"//{candidate}"
    try:
        host = urlsplit(to_parse).hostname
    except ValueError:
        host = None
    return (host or candidate).lower()


def validate_alias(alias: str) -> str:
    """Validate a custom alias and return it normalized to lowercase.

    Enforces the §5.4 grammar: ``[a-z0-9-]``, 3–32 characters, no leading or trailing
    hyphen, and not a reserved word. Raises :class:`ValidationError` with the matching
    ``REASON_ALIAS_*`` otherwise.

    Scope note: the "already taken → 409" uniqueness check is **not** done here — that
    is a DB concern handled by the API in Epic 6. This function is pure grammar +
    reserved-word validation.
    """
    normalized = alias.strip().lower()
    if not ALIAS_MIN_LENGTH <= len(normalized) <= ALIAS_MAX_LENGTH:
        raise ValidationError(
            REASON_ALIAS_LENGTH,
            f"alias must be {ALIAS_MIN_LENGTH}-{ALIAS_MAX_LENGTH} characters",
        )
    if not _ALIAS_PATTERN.fullmatch(normalized):
        raise ValidationError(
            REASON_ALIAS_GRAMMAR, "alias may only contain a-z, 0-9, and hyphens"
        )
    if normalized.startswith("-") or normalized.endswith("-"):
        raise ValidationError(
            REASON_ALIAS_HYPHEN, "alias may not start or end with a hyphen"
        )
    if normalized in RESERVED_WORDS:
        raise ValidationError(REASON_ALIAS_RESERVED, f"alias {normalized!r} is reserved")
    return normalized


def _is_disallowed_address(address: str) -> bool:
    """True if a resolved address is private/loopback/link-local/otherwise non-public.

    Unparseable resolver output is treated as disallowed (reject conservatively rather
    than crash). IPv4-mapped IPv6 addresses are unwrapped first so an embedded private
    IPv4 (e.g. ``::ffff:10.0.0.1``) cannot bypass the check.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_url(
    url: str,
    *,
    public_host: str | None = None,
    resolver: HostResolver | None = None,
) -> str:
    """Validate an original URL for creation and return it unchanged on success.

    Applies the §5.5 guards in cheap-to-expensive order: length ≤ 2048 → scheme ∈
    {http, https} → host present → host is not the public host (self-reference) → DNS
    resolve → reject if **any** resolved address is private/loopback/link-local (SSRF
    defense-in-depth). Raises :class:`ValidationError` with the matching ``REASON_URL_*``
    otherwise.

    ``public_host`` defaults to :func:`default_public_host` and ``resolver`` to
    :func:`default_host_resolver`; tests inject explicit values.

    Known limitations (§7): validation is creation-time only, so DNS rebinding after
    creation is not caught — the redirect hot path deliberately does not re-resolve.
    Self-reference is also an exact-host match (§5.5: ``host == public host``), so a
    subdomain pointing at the public host (e.g. ``www.<public host>``) is not rejected
    by the self-reference guard — it is still subject to the DNS/SSRF check below.
    """
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError(
            REASON_URL_LENGTH, f"URL exceeds {MAX_URL_LENGTH} characters"
        )

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
    except ValueError:
        # urlsplit/.hostname raise ValueError on malformed input (e.g. an
        # unbalanced-bracket IPv6 host like ``http://[::1``). Surface it as a
        # ValidationError so the API maps it to a 400, never a 500.
        raise ValidationError(REASON_URL_MALFORMED, "URL is malformed") from None

    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValidationError(REASON_URL_SCHEME, "URL scheme must be http or https")

    if not host:
        raise ValidationError(REASON_URL_NO_HOST, "URL has no host")

    if public_host is None:
        public_host = default_public_host()
    if host == _normalize_public_host(public_host):
        raise ValidationError(
            REASON_URL_SELF_REFERENTIAL, "URL points back at the public host"
        )

    if resolver is None:
        resolver = default_host_resolver
    addresses = resolver(host)
    if not addresses:
        raise ValidationError(REASON_URL_UNRESOLVABLE, f"host {host!r} did not resolve")
    if any(_is_disallowed_address(address) for address in addresses):
        raise ValidationError(
            REASON_URL_PRIVATE_ADDRESS, f"host {host!r} resolves to a private address"
        )

    return url


def proxy_served_paths() -> frozenset[str]:
    """Return the alias-collidable path segments the proxy/frontend serves.

    The source of truth for the anti-drift coverage test, which asserts
    ``proxy_served_paths() <= RESERVED_WORDS`` (superset, not equality) so the reserved
    list can never drift behind a newly served route (§5.10, Nginx blocks 1–4).

    Dotted files (``favicon.ico``, ``robots.txt``) and the root path are excluded: the
    alias grammar forbids ``.`` and requires ≥3 characters, so none of them can ever be
    claimed as an alias and reserving them adds no protection (§5.4). When Epic 18b
    adds or changes an Nginx served path, update this set to match.
    """
    return frozenset(
        {
            "api",
            "health",
            "metrics",
            "assets",
            "static",
            "dashboard",
            "how-it-works",
        }
    )

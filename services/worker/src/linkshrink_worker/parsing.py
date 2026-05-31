"""Pure derivation of the coarse PII-free fields from a raw click (TDD §5.7).

The worker stores only categories, never the raw User-Agent or full Referer: this
module turns the raw ``ua`` string into a ``DeviceType`` plus browser/OS families and
reduces a ``referrer`` URL to its host. Everything here is a pure function so it can be
unit-tested without Redis, Postgres, or Docker.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from user_agents import parse as parse_user_agent_string

from linkshrink_shared import DeviceType

#: ``user_agents`` reports an unrecognized browser/OS family as the literal "Other";
#: we store that as ``None`` so analytics breakdowns coalesce it to "unknown" (Epic 8).
_UNKNOWN_FAMILY = "Other"


@dataclass(frozen=True)
class DerivedUserAgent:
    """The coarse, PII-free fields derived from a raw User-Agent string."""

    device_type: DeviceType
    browser_family: str | None
    os_family: str | None


def _normalize_family(family: str | None) -> str | None:
    """Turn a ``user_agents`` family into a stored value: blank/"Other" become ``None``."""
    if not family or family == _UNKNOWN_FAMILY:
        return None
    return family


def parse_user_agent(ua: str | None) -> DerivedUserAgent:
    """Derive device class and browser/OS families from a raw User-Agent string.

    A missing or blank UA yields ``unknown`` with no families. Device class maps the
    ``user_agents`` flags onto :class:`DeviceType` (mobile/tablet/desktop), defaulting to
    ``unknown`` when none apply (e.g. a bot or an unparseable agent).
    """
    if not ua or not ua.strip():
        return DerivedUserAgent(DeviceType.unknown, None, None)

    parsed = parse_user_agent_string(ua)
    if parsed.is_tablet:
        device_type = DeviceType.tablet
    elif parsed.is_mobile:
        device_type = DeviceType.mobile
    elif parsed.is_pc:
        device_type = DeviceType.desktop
    else:
        device_type = DeviceType.unknown

    return DerivedUserAgent(
        device_type=device_type,
        browser_family=_normalize_family(parsed.browser.family),
        os_family=_normalize_family(parsed.os.family),
    )


def referrer_host(referrer: str | None) -> str | None:
    """Reduce a Referer URL to its lowercased host, or ``None`` if absent/hostless.

    Only the host is kept — never the path or query — so no per-page browsing trail
    reaches Postgres. A blank, hostless, or unparseable value yields ``None``.
    """
    if not referrer or not referrer.strip():
        return None

    try:
        host = urlparse(referrer.strip()).hostname
    except ValueError:
        return None
    return host.lower() if host else None

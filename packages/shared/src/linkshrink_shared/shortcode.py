"""Short-code generation: hashids encode/decode + sequence consumption.

The one authoritative way LinkShrink turns a database sequence value into a short
URL slug. A generated code is ``hashids.encode(nextval('link_code_seq'))`` using an
env-provided salt, a single-case alphabet, and a minimum length of 6 (TDD §5.4).

Because every ``nextval`` returns a fresh integer and hashids is deterministic, the
only way a generated code can collide is with a pre-existing *custom alias* sharing
the same code space. ``generate_unique_short_code`` handles that rare case with a
bounded retry loop (advance the sequence + re-encode, capped, logged) per §7.

The alphabet is lowercase letters + digits only. hashids emits characters solely
from its alphabet (its internal separators/guards are themselves drawn from the
alphabet), so a generated code is always ``[a-z0-9]`` — a subset of the alias
grammar ``[a-z0-9-]`` — and always at least 6 characters. The hyphen that the alias
grammar allows is for *custom* aliases (Epic 4), never for generated codes.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from hashids import Hashids

from linkshrink_shared.models import link_code_seq

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

#: Lowercase letters + digits. Single case, no hyphen — keeps generated codes a
#: subset of the alias grammar ``[a-z0-9-]``.
SHORT_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

#: Minimum length of a generated code (hashids pads shorter encodings up to this).
SHORT_CODE_MIN_LENGTH = 6

#: How many sequence values to try before giving up on finding a free code. A
#: collision only happens against a pre-existing custom alias and ``nextval``
#: advances on every call, so five consecutive collisions is effectively
#: impossible — this is a safety cap, not an expected-to-be-hit limit.
DEFAULT_MAX_ATTEMPTS = 5

#: Env var holding the hashids salt. Read directly here as a deliberate Epic-3
#: stand-in (mirroring Epic 2's direct env read in ``migrations/env.py``); Epic 5's
#: ``config.py`` will later route this through shared pydantic-settings config.
HASHIDS_SALT_ENV_VAR = "HASHIDS_SALT"


class ShortCodeCollisionError(Exception):
    """Raised when a free short code could not be found within the attempt cap."""


class ShortCodeGenerator:
    """Deterministic hashids encode/decode for short codes.

    Encoding is deterministic per ``(salt, alphabet, min_length)``: the same
    sequence value always maps to the same code, so any service holding the same
    salt resolves codes identically.
    """

    def __init__(
        self,
        salt: str,
        *,
        alphabet: str = SHORT_CODE_ALPHABET,
        min_length: int = SHORT_CODE_MIN_LENGTH,
    ) -> None:
        if not salt:
            raise ValueError("ShortCodeGenerator requires a non-empty salt")
        self._hashids = Hashids(salt=salt, alphabet=alphabet, min_length=min_length)

    def encode(self, n: int) -> str:
        """Encode a positive sequence value into a short code.

        ``nextval('link_code_seq')`` starts at 1, so ``n`` is always >= 1. hashids
        silently returns an empty string for ``n < 1``, which would violate the
        length-6 invariant, so guard against it explicitly.
        """
        if n < 1:
            raise ValueError(f"short-code sequence value must be >= 1, got {n}")
        return self._hashids.encode(n)

    def decode(self, code: str) -> int | None:
        """Decode a code back to its sequence value, or ``None`` if it does not decode.

        The redirect hot path never decodes (it matches ``lower(short_code)``
        directly); this exists for completeness, debugging, and tests.
        """
        decoded = self._hashids.decode(code)
        return decoded[0] if decoded else None


def default_short_code_generator() -> ShortCodeGenerator:
    """Build a generator from the ``HASHIDS_SALT`` environment variable.

    Epic-3 stand-in until Epic 5's ``config.py`` provides centralized config.
    """
    salt = os.environ.get(HASHIDS_SALT_ENV_VAR, "")
    if not salt:
        raise RuntimeError(
            f"{HASHIDS_SALT_ENV_VAR} is not set; cannot generate short codes"
        )
    return ShortCodeGenerator(salt)


async def fetch_next_sequence_value(session: AsyncSession) -> int:
    """Consume one value from ``link_code_seq`` via the given async session.

    Thin wrapper over ``nextval('link_code_seq')``; exercised end-to-end through the
    API insert path in Epic 6 / the integration suite in Epic 19.
    """
    return await session.scalar(link_code_seq.next_value())


async def generate_unique_short_code(
    get_next_sequence_value: Callable[[], Awaitable[int]],
    try_persist: Callable[[str], Awaitable[bool]],
    *,
    generator: ShortCodeGenerator | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Generate a short code and persist it, retrying on collision up to a cap.

    ``get_next_sequence_value`` returns the next sequence integer (advances on every
    call). ``try_persist`` attempts to store a row with the candidate code and
    returns ``True`` on success or ``False`` only when the code collides with an
    existing one (the ``lower(short_code)`` unique violation). It MUST let every
    other error propagate — otherwise a transient failure would be silently retried
    as if it were a collision.

    Returns the code that was successfully persisted; raises
    :class:`ShortCodeCollisionError` if no free code is found within ``max_attempts``.
    """
    generator = generator or default_short_code_generator()
    for _ in range(max_attempts):
        n = await get_next_sequence_value()
        code = generator.encode(n)
        if await try_persist(code):
            return code
        logger.warning("short-code collision on %r, advancing sequence and retrying", code)
    raise ShortCodeCollisionError(
        f"could not generate a free short code within {max_attempts} attempts"
    )

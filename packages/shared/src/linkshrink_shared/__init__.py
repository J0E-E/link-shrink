"""linkshrink_shared — the one authoritative copy of LinkShrink's core logic.

Holds the SQLAlchemy models, short-code generation, URL/alias validation and
reserved words, env-driven config, and the Redis cache/queue helpers, so the
API, redirect, and worker services all resolve codes and read keys identically.

Modules are filled in by later epics (see each module's docstring); this scaffold
ships them empty so `import linkshrink_shared` works from Epic 1 onward.
"""

from linkshrink_shared.models import (
    Base,
    ClickEvent,
    DeviceType,
    Link,
    Source,
    link_code_seq,
)
from linkshrink_shared.shortcode import (
    DEFAULT_MAX_ATTEMPTS,
    SHORT_CODE_ALPHABET,
    SHORT_CODE_MIN_LENGTH,
    ShortCodeCollisionError,
    ShortCodeGenerator,
    default_short_code_generator,
    fetch_next_sequence_value,
    generate_unique_short_code,
)
from linkshrink_shared.validation import (
    ALIAS_MAX_LENGTH,
    ALIAS_MIN_LENGTH,
    ALLOWED_URL_SCHEMES,
    MAX_URL_LENGTH,
    REASON_ALIAS_GRAMMAR,
    REASON_ALIAS_HYPHEN,
    REASON_ALIAS_LENGTH,
    REASON_ALIAS_RESERVED,
    REASON_URL_LENGTH,
    REASON_URL_MALFORMED,
    REASON_URL_NO_HOST,
    REASON_URL_PRIVATE_ADDRESS,
    REASON_URL_SCHEME,
    REASON_URL_SELF_REFERENTIAL,
    REASON_URL_UNRESOLVABLE,
    RESERVED_WORDS,
    HostResolver,
    ValidationError,
    default_host_resolver,
    default_public_host,
    proxy_served_paths,
    validate_alias,
    validate_url,
)

__version__ = "0.1.0"

__all__ = [
    "ALIAS_MAX_LENGTH",
    "ALIAS_MIN_LENGTH",
    "ALLOWED_URL_SCHEMES",
    "DEFAULT_MAX_ATTEMPTS",
    "MAX_URL_LENGTH",
    "REASON_ALIAS_GRAMMAR",
    "REASON_ALIAS_HYPHEN",
    "REASON_ALIAS_LENGTH",
    "REASON_ALIAS_RESERVED",
    "REASON_URL_LENGTH",
    "REASON_URL_MALFORMED",
    "REASON_URL_NO_HOST",
    "REASON_URL_PRIVATE_ADDRESS",
    "REASON_URL_SCHEME",
    "REASON_URL_SELF_REFERENTIAL",
    "REASON_URL_UNRESOLVABLE",
    "RESERVED_WORDS",
    "SHORT_CODE_ALPHABET",
    "SHORT_CODE_MIN_LENGTH",
    "Base",
    "ClickEvent",
    "DeviceType",
    "HostResolver",
    "Link",
    "ShortCodeCollisionError",
    "ShortCodeGenerator",
    "Source",
    "ValidationError",
    "default_host_resolver",
    "default_public_host",
    "default_short_code_generator",
    "fetch_next_sequence_value",
    "generate_unique_short_code",
    "link_code_seq",
    "proxy_served_paths",
    "validate_alias",
    "validate_url",
    "__version__",
]

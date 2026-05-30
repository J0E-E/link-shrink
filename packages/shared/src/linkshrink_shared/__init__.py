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

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "SHORT_CODE_ALPHABET",
    "SHORT_CODE_MIN_LENGTH",
    "Base",
    "ClickEvent",
    "DeviceType",
    "Link",
    "ShortCodeCollisionError",
    "ShortCodeGenerator",
    "Source",
    "default_short_code_generator",
    "fetch_next_sequence_value",
    "generate_unique_short_code",
    "link_code_seq",
    "__version__",
]

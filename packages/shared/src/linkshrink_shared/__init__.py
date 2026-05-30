"""linkshrink_shared — the one authoritative copy of LinkShrink's core logic.

Holds the SQLAlchemy models, short-code generation, URL/alias validation and
reserved words, env-driven config, and the Redis cache/queue helpers, so the
API, redirect, and worker services all resolve codes and read keys identically.

Modules are filled in by later epics (see each module's docstring); this scaffold
ships them empty so `import linkshrink_shared` works from Epic 1 onward.
"""

__version__ = "0.1.0"

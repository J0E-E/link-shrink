"""linkshrink_redirect — the LinkShrink redirect service (FastAPI).

The hot path: a single endpoint ``GET /{code}`` that resolves a short code to a
``302`` via a Redis cache-aside lookup (with negative caching) and emits a
best-effort click event that never blocks or breaks the redirect (TDD §5.6). All
core logic (the ``Link`` model, cache helpers, the click payload contract) lives in
``linkshrink_shared``; this package only wires it into HTTP.
"""

__version__ = "0.1.0"

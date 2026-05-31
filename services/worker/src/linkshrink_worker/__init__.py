"""linkshrink_worker — the LinkShrink analytics consumer (asyncio).

The durable side of the click pipeline (TDD §5.7): a consumer-group worker that
``XREADGROUP``s click events off the ``clicks`` stream, derives the coarse PII-free
fields (device/browser/OS from the User-Agent, host from the Referer), inserts a
``ClickEvent``, and ``XACK``s. It reclaims a crashed consumer's pending entries via
``XAUTOCLAIM``, dead-letters poison messages after three attempts, and writes a
liveness heartbeat each loop for the Docker healthcheck.

The click payload contract and all thin stream/heartbeat wrappers live in
``linkshrink_shared.queue``; this package owns the consumer loop, recovery, the
derivation logic, and the process wiring.
"""

__version__ = "0.1.0"

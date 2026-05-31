"""Worker-only tunables for the consumer loop and recovery cadence (TDD §5.7).

These are operational knobs specific to this process, so they live here rather than in
the shared ``Settings`` (which the api/redirect services also load). The contract
constants — stream/group names, the attempt cap, the heartbeat key and threshold — stay
in ``linkshrink_shared.queue`` since the producer and the metrics endpoint share them.
"""

from __future__ import annotations

import os

#: How many entries to pull per ``XREADGROUP`` and how long to block waiting for them.
#: A 5s block keeps the heartbeat well inside its 15s staleness threshold under no load.
CONSUMER_BATCH_COUNT = 100
CONSUMER_BLOCK_MS = 5000

#: Recovery reclaims pending entries idle beyond this, and runs on this interval. The
#: idle floor must exceed a normal processing pass so healthy in-flight work is left alone.
RECOVERY_IDLE_MS = 30_000
RECOVERY_INTERVAL_SECONDS = 30

#: After a loop pass raises (e.g. a transient Redis disconnect) the loop logs and waits
#: this long before retrying, so a hard outage backs off instead of spinning a tight error
#: loop. Kept well under the 15s heartbeat threshold so a brief blip doesn't trip a restart.
ERROR_BACKOFF_SECONDS = 1


def get_worker_number() -> int:
    """Read this worker's number (for the ``worker-{n}`` consumer name) from the env.

    Defaults to ``1`` for the single-worker deployment; a non-integer value falls back to
    ``1`` so a misconfigured env never crashes startup.
    """
    raw = os.environ.get("WORKER_NUMBER", "1")
    try:
        return int(raw)
    except ValueError:
        return 1

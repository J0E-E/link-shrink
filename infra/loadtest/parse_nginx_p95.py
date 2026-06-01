"""Compute the redirect cache-hit p95 from the Nginx access log (Epic 20, TDD §9.10).

The ``< 50 ms p95`` redirect budget is a *server-side* figure: it is measured at Nginx
from ``$request_time`` (logged as ``rt=`` by ``infra/nginx/nginx.conf``), not from the
load generator's own client-side timing (which would include client RTT) and not from
``/api/metrics`` (Redis keeps no latency histogram, §5.7).

Usage — pipe the running Nginx access log through this script, filtering to the short code
the load test hammered::

    docker compose -f infra/docker-compose.yml exec -T nginx \\
        cat /var/log/nginx/access.log | python infra/loadtest/parse_nginx_p95.py --code abc123

It prints p50/p95/p99 over the matching redirect ``302`` lines and **exits non-zero if
p95 >= 0.050 s**, so the latency budget is a hard pass/fail check (usable in CI/Make).

The parsing/percentile logic lives in pure functions so it is unit-tested with no Docker
(see ``tests/test_loadtest_parse.py``).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence

#: The redirect latency budget (§2/§9.10): p95 of ``$request_time`` must stay under this.
P95_BUDGET_SECONDS = 0.050

#: Matches the ``infra/nginx/nginx.conf`` ``main`` log format, pulling out the request line,
#: the status, and the ``rt=`` request time. The log line looks like::
#:
#:     1.2.3.4 real=1.2.3.4 "GET /abc123 HTTP/2.0" 302 rt=0.004 cache=-
_LOG_LINE = re.compile(
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+[^"]*"\s+'
    r"(?P<status>\d{3})\s+"
    r"rt=(?P<request_time>\d+\.\d+)"
)


def parse_request_times(lines: Iterable[str], code: str) -> list[float]:
    """Return the ``$request_time`` (seconds) of every redirect cache-hit line for ``code``.

    A redirect cache hit is a ``GET /{code}`` that returned ``302`` — the bare short-code hot
    path Nginx forwards to the redirect service (the 302 itself is never Nginx-cached, so each
    line is a real end-to-end redirect served from the Redis cache). Any query string on the
    path (e.g. ``/{code}?source=qr``) still counts; non-matching lines are ignored.
    """
    target_path = f"/{code}"
    request_times: list[float] = []
    for line in lines:
        match = _LOG_LINE.search(line)
        if match is None:
            continue
        if match["method"] != "GET" or match["status"] != "302":
            continue
        path = match["path"].split("?", 1)[0]
        if path != target_path:
            continue
        request_times.append(float(match["request_time"]))
    return request_times


def percentile(values: Sequence[float], rank: float) -> float:
    """Return the ``rank``-th percentile (0–100) of ``values`` via nearest-rank.

    Nearest-rank needs no interpolation and is stable for the modest sample sizes a portfolio
    load test produces. Raises ``ValueError`` on an empty sample (there is no percentile of
    nothing — the caller should report "no matching requests" instead).
    """
    if not values:
        raise ValueError("cannot take a percentile of an empty sample")
    if not 0 <= rank <= 100:
        raise ValueError("rank must be between 0 and 100")
    ordered = sorted(values)
    if rank == 0:
        return ordered[0]
    # Nearest-rank: the smallest index whose position covers `rank` percent of the sample.
    # `-(-x // 100)` is a ceil that works for fractional ranks too (e.g. 99.9).
    index = max(0, int(-(-len(ordered) * rank // 100)) - 1)
    return ordered[index]


def summarize(request_times: Sequence[float]) -> dict[str, float]:
    """Return count + min/p50/p95/p99/max over the request times (all in seconds)."""
    return {
        "count": len(request_times),
        "min": min(request_times),
        "p50": percentile(request_times, 50),
        "p95": percentile(request_times, 95),
        "p99": percentile(request_times, 99),
        "max": max(request_times),
    }


def _parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--code",
        required=True,
        help="the short code the load test hammered (filters GET /{code} 302 lines)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=P95_BUDGET_SECONDS,
        help=f"p95 budget in seconds (default {P95_BUDGET_SECONDS})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Read the Nginx log from stdin, print the latency summary, return the exit status."""
    arguments = _parse_arguments(argv)
    request_times = parse_request_times(sys.stdin, arguments.code)

    if not request_times:
        print(
            f"No redirect cache-hit lines found for GET /{arguments.code} (302) in the log. "
            "Did the load test run, and is --code correct?",
            file=sys.stderr,
        )
        return 2

    stats = summarize(request_times)
    print(f"Redirect cache-hit latency at Nginx (GET /{arguments.code}, 302):")
    print(f"  samples : {int(stats['count'])}")
    print(f"  min     : {stats['min'] * 1000:.1f} ms")
    print(f"  p50     : {stats['p50'] * 1000:.1f} ms")
    print(f"  p95     : {stats['p95'] * 1000:.1f} ms")
    print(f"  p99     : {stats['p99'] * 1000:.1f} ms")
    print(f"  max     : {stats['max'] * 1000:.1f} ms")

    if stats["p95"] >= arguments.budget:
        print(
            f"FAIL: p95 {stats['p95'] * 1000:.1f} ms >= budget {arguments.budget * 1000:.1f} ms",
            file=sys.stderr,
        )
        return 1

    print(f"PASS: p95 {stats['p95'] * 1000:.1f} ms < budget {arguments.budget * 1000:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

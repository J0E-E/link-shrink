"""Generate redirect cache-hit traffic for the p95 load test (Epic 20, TDD §9.10).

This is the *load generator*: it makes one short link, warms it into the Redis cache with a
single redirect, then fires many concurrent ``GET /{code}`` requests at Nginx so there is a
burst of cache-hit ``302``s in the access log. The authoritative ``< 50 ms p95`` figure comes
from Nginx's ``$request_time`` (parse it with ``parse_nginx_p95.py``) — the client-side timing
this script prints is only a sanity check (it includes localhost RTT and TLS handshakes).

Run the full stack first (``make up`` / ``infra/up.ps1``), then::

    python infra/loadtest/run_load_test.py --requests 2000 --concurrency 50

By default it talks to ``https://localhost`` with certificate verification **off** (the local
stack uses a self-signed cert, Epic 18b). Pass ``--code`` to reuse an existing short code and
skip creation (e.g. to avoid the 10/min create rate limit on repeated runs).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence

import httpx

#: A real public URL to shorten when the script creates its own link. Must pass the API's
#: creation-time URL validation (public host, SSRF check) — if that validation ever tightens
#: (allowlist, reachability probe), update this. The redirect only ever returns a 302 to this
#: target; it is never fetched by the load test.
DEFAULT_TARGET_URL = "https://example.com/linkshrink-load-test"


async def _create_short_code(client: httpx.AsyncClient, target_url: str) -> str:
    """Create a link via the public API and return its short code."""
    response = await client.post("/api/links", json={"url": target_url})
    response.raise_for_status()
    return response.json()["short_code"]


async def _redirect_once(client: httpx.AsyncClient, code: str) -> tuple[int, float]:
    """Issue one ``GET /{code}`` and return its (status, client-side elapsed seconds)."""
    start = time.perf_counter()
    response = await client.get(f"/{code}")
    elapsed = time.perf_counter() - start
    return response.status_code, elapsed


async def _run_load(
    client: httpx.AsyncClient, code: str, *, total_requests: int, concurrency: int
) -> list[tuple[int, float]]:
    """Fire ``total_requests`` redirects, at most ``concurrency`` in flight at once."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _one() -> tuple[int, float]:
        async with semaphore:
            return await _redirect_once(client, code)

    return await asyncio.gather(*(_one() for _ in range(total_requests)))


def _print_client_summary(results: Sequence[tuple[int, float]], wall_seconds: float) -> None:
    """Print a client-side sanity summary (the real p95 is measured at Nginx)."""
    statuses = [status for status, _ in results]
    redirects = sum(1 for status in statuses if status == 302)
    elapsed_ms = sorted(elapsed * 1000 for _, elapsed in results)
    throughput = len(results) / wall_seconds if wall_seconds else 0.0
    p95_index = max(0, -(-len(elapsed_ms) * 95 // 100) - 1)

    print("Client-side summary (sanity only — authoritative p95 is at Nginx):")
    print(f"  requests     : {len(results)}")
    print(f"  302 redirects: {redirects}")
    print(f"  non-302      : {len(results) - redirects}")
    print(f"  wall time    : {wall_seconds:.2f} s")
    print(f"  throughput   : {throughput:.0f} req/s")
    if elapsed_ms:
        print(f"  client p95   : {elapsed_ms[p95_index]:.1f} ms (incl. localhost RTT + TLS)")


def _parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://localhost", help="Nginx edge base URL")
    parser.add_argument(
        "--code",
        default=None,
        help="reuse an existing short code (skips creation + the create rate limit)",
    )
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help="URL to shorten")
    parser.add_argument("--requests", type=int, default=2000, help="total redirect requests")
    parser.add_argument("--concurrency", type=int, default=50, help="max requests in flight")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="verify the TLS cert (off by default for the local self-signed cert)",
    )
    return parser.parse_args(argv)


async def _main_async(arguments: argparse.Namespace) -> int:
    async with httpx.AsyncClient(
        base_url=arguments.base_url,
        verify=arguments.verify_tls,
        follow_redirects=False,
        timeout=10.0,
    ) as client:
        if arguments.code:
            code = arguments.code
            print(f"Reusing existing short code: {code}")
        else:
            code = await _create_short_code(client, arguments.target_url)
            print(f"Created short code: {code} -> {arguments.target_url}")

        # Warm the Redis cache so every measured request is a cache hit, not a cold DB miss.
        warm_status, _ = await _redirect_once(client, code)
        print(f"Warmed cache (first redirect status {warm_status}).")

        print(
            f"Firing {arguments.requests} redirects at {arguments.base_url}/{code} "
            f"(concurrency {arguments.concurrency})..."
        )
        start = time.perf_counter()
        results = await _run_load(
            client, code, total_requests=arguments.requests, concurrency=arguments.concurrency
        )
        wall_seconds = time.perf_counter() - start

    _print_client_summary(results, wall_seconds)
    print()
    print("Now measure the server-side p95 at Nginx:")
    print(
        "  docker compose -f infra/docker-compose.yml exec -T nginx "
        "cat /var/log/nginx/access.log \\"
    )
    print(f"    | python infra/loadtest/parse_nginx_p95.py --code {code}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    try:
        return asyncio.run(_main_async(arguments))
    except httpx.HTTPError as error:
        print(f"Load test failed talking to {arguments.base_url}: {error}", file=sys.stderr)
        print("Is the stack up (make up / infra/up.ps1)?", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

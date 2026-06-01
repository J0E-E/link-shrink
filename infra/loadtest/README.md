# Load test — redirect cache-hit p95 (Epic 20, TDD §9.10)

This harness proves the headline performance budget: **redirect `< 50 ms` p95 on a cache
hit, measured server-side at Nginx**. The budget is measured from Nginx's `$request_time`
(logged as `rt=` in [`../nginx/nginx.conf`](../nginx/nginx.conf)), **not** from the load
generator's client-side timing (which includes client RTT + TLS) and **not** from
`/api/metrics` (Redis keeps no latency histogram, §5.7).

## What's here

| File | Role |
|---|---|
| `run_load_test.py` | Generator — creates + warms a short link, then fires concurrent `GET /{code}` redirects at Nginx (asyncio + httpx). |
| `parse_nginx_p95.py` | Analyzer — reads the Nginx access log, keeps the `GET /{code}` `302` lines, computes p50/p95/p99 from `rt=`, and exits non-zero if p95 ≥ 50 ms. |

The parsing/percentile logic is pure and unit-tested with no Docker in
[`../../tests/test_loadtest_parse.py`](../../tests/test_loadtest_parse.py).

## Procedure

1. **Bring the stack up** from the repo root and wait for all services healthy:

   ```bash
   make up          # Linux/macOS
   ./infra/up.ps1   # Windows
   make ps          # confirm everything is healthy
   ```

2. **Generate load** (creates its own link, warms the cache, then hammers it):

   ```bash
   python infra/loadtest/run_load_test.py --requests 2000 --concurrency 50
   ```

   It prints the short code and a client-side sanity summary. Pass `--code <code>` to reuse an
   existing link and skip the 10/min create rate limit on repeat runs.

3. **Measure the server-side p95** by piping the Nginx access log through the analyzer
   (use the code the generator printed):

   ```bash
   docker compose -f infra/docker-compose.yml exec -T nginx \
       cat /var/log/nginx/access.log \
       | python infra/loadtest/parse_nginx_p95.py --code <code>
   ```

   It prints the latency summary and exits `0` if **p95 < 50 ms**, non-zero otherwise.

On platforms with `make`, `make loadtest CODE=<code>` runs steps 2–3 together; on Windows use
`infra/loadtest.ps1 -Code <code>`.

> The access log accumulates across runs. To measure a single run cleanly, either filter by a
> fresh `--code` (each `run_load_test.py` invocation makes a new one unless you pass `--code`),
> or truncate the log first with
> `docker compose -f infra/docker-compose.yml exec -T nginx truncate -s 0 /var/log/nginx/access.log`.

## Report template

Fill this in after a run and keep it with the epic results:

```
LinkShrink redirect cache-hit load test
=======================================
Date        : <YYYY-MM-DD>
Host        : <CPU / RAM / OS — e.g. local dev laptop, or the prod VM spec>
Stack       : docker compose (api, redirect, worker, redis, postgres, nginx)
Command     : python infra/loadtest/run_load_test.py --requests <N> --concurrency <C>
Short code  : <code>

Server-side $request_time at Nginx (GET /<code>, 302):
  samples : <N>
  min     : <..> ms
  p50     : <..> ms
  p95     : <..> ms      <-- budget: < 50 ms
  p99     : <..> ms
  max     : <..> ms

Result      : PASS / FAIL  (p95 < 50 ms)
Notes       : <warm-up, anomalies, retries, etc.>
```

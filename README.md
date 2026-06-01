# LinkShrink

A public, account-less **URL shortener and QR-code generator**, built as a portfolio
piece to show what production-grade architecture looks like when it's scoped to run on
a single VM. Paste a long URL, get a short `link-shrink.org` link plus a downloadable QR
code, and watch coarse, privacy-safe analytics roll in — no sign-up, no tracking of you.

This repository exists to be **read**, not deployed. The sections below walk through the
architecture and the decisions behind it. For the full detail, see the
[Technical Design Document](.development-docs/LinkShrink_TDD.md) and the
[Epic Plan](.development-docs/LinkShrink_Epic_Plan.md) that delivered it.

> **Built with AI, end to end.** This whole project was vibecoded using a workflow
> inspired by the [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) automated method —
> design → technical spec → epic plan → implementation, each stage feeding the next. I
> don't fully automate the method, though: I review every step along the way. From the
> first design note to the full implementation, it took a little over **10 hours**.

**Stack:** Python · FastAPI · SQLAlchemy 2.0 + Alembic · PostgreSQL · Redis (cache +
Streams) · React + Vite · Nginx · Docker Compose.

---

## What it does

- **Shorten** any `http(s)` URL into a compact `link-shrink.org/{code}` link, with an
  optional custom alias that shares a single namespace with generated codes.
- **Generate a QR code** for any short link on demand (PNG or SVG, never stored), tagged
  with a `?source=qr` attribution parameter so QR scans are distinguishable from direct
  clicks.
- **Redirect fast** — a `302` served from a Redis cache, with a target budget of
  **< 50 ms p95 on a cache hit**, measured server-side.
- **Show analytics** — click counts over time plus device / browser / OS category,
  referrer domain, and source — all derived and **PII-free** (no IPs, no raw user agents
  ever stored).
- **Explain itself** — a How-It-Works page and an Educational Mode surface the
  architecture to visitors, which is the whole point of a portfolio piece.

---

## Architecture

A monorepo with one shared Python package and three independent FastAPI services behind
an Nginx reverse proxy. Redis does double duty as the redirect cache **and** the
analytics queue; PostgreSQL is the source of truth.

```
                          ┌─────────────────────────────┐
   Browser  ──HTTPS──▶    │            Nginx            │   TLS termination, routing,
                          │      (reverse proxy)        │   p95 measurement point
                          └──────────────┬──────────────┘
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
      ┌───────────────┐         ┌─────────────────┐         ┌───────────────┐
      │  Static SPA   │         │   API service   │         │   Redirect    │
      │ (React+Vite)  │         │   (FastAPI)     │         │   service     │
      └───────────────┘         │ create · list · │         │ (FastAPI)     │
                                │ analytics · QR  │         │ GET /{code}   │
                                │ metrics         │         │  → 302 (hot)  │
                                └───────┬─────────┘         └──────┬────────┘
                                        │                          │
                                        ▼              cache-aside │ XADD click
                            ┌───────────────────┐ ◀────────────────┘
                            │       Redis        │  redirect cache · negative cache
                            │                    │  rate-limit counters · metrics
                            │   clicks  Stream   │  analytics queue
                            └─────────┬──────────┘
                                      │ XREADGROUP
                                      ▼
                            ┌───────────────────┐         ┌───────────────────┐
                            │   Worker service   │ ──────▶ │     PostgreSQL    │
                            │ (asyncio consumer) │  insert │  links ·          │
                            │ derive UA/referrer │         │  click_events     │
                            │ purge job          │         │  link_code_seq    │
                            └───────────────────┘         └───────────────────┘
```

### The three services

- **API** — link creation (with validation and rate limiting), the paginated public
  dashboard, per-link analytics aggregation, QR generation, and the `/api/metrics`
  endpoint. Reads and writes PostgreSQL.
- **Redirect** — a single deliberately tiny hot endpoint, `GET /{code}`: a cache-aside
  lookup that returns a `302`, then fires a click event onto a Redis Stream
  (best-effort, never blocking the redirect). Kept minimal precisely because it owns the
  latency budget.
- **Worker** — an asyncio consumer of the `clicks` Stream. It parses the raw user agent
  into device/browser/OS *categories* and extracts the referrer *host*, then discards
  the raw values and writes only the coarse, PII-free row. It also reclaims work from
  crashed consumers, dead-letters poison messages, and runs the scheduled purge job.

All three import a single `linkshrink_shared` package — the one authoritative copy of
the short-code logic, SQLAlchemy models, validation rules, and config — so the API and
Redirect services resolve codes identically.

---

## Repository layout

```
linkshrink/
├── packages/
│   └── shared/                  # importable Python package: linkshrink_shared
│       └── src/linkshrink_shared/
│           ├── models.py        # SQLAlchemy 2.0 models (Link, ClickEvent)
│           ├── shortcode.py     # hashids encode/decode + sequence handling
│           ├── validation.py    # URL + alias validation, reserved words
│           ├── config.py        # pydantic-settings (env-driven)
│           ├── cache.py         # Redis cache-aside helpers + keys
│           └── queue.py         # Redis Streams add/read/ack helpers
├── services/
│   ├── api/                     # FastAPI: create, dashboard, analytics, qr, metrics
│   ├── redirect/                # FastAPI: GET /{code} -> 302 (hot path)
│   └── worker/                  # asyncio consumer of the clicks stream
├── frontend/                    # React + Vite SPA (static build)
├── migrations/                  # Alembic env + versions (shared schema)
├── infra/
│   ├── nginx/                   # Nginx config + TLS
│   ├── docker/                  # base image(s) for the Python services
│   └── loadtest/                # p95 load-test harness + procedure
├── pyproject.toml               # tooling config (ruff, pytest)
└── requirements-dev.txt         # dev / tooling dependencies
```

Alembic owns the schema; services never auto-create tables.

---

## Design decisions

The choices that shaped the build, and why each one was made.

| Decision | Chosen | Why |
|---|---|---|
| **Backend stack** | Python + FastAPI (async) across all three services | Clean async service story, mature libraries (hashids, qrcode, user-agents, redis-py), and strong portfolio readability. |
| **Repo layout** | Monorepo with one shared package | A single authoritative copy of short-code, validation, and models so the API and Redirect services resolve codes identically — no drift. |
| **Short codes** | Monotonic Postgres sequence → hashids encode | Unique and deterministic *by construction*; no random-collision retry loop in the common path. Custom aliases share the same namespace, guarded by a unique index. |
| **Frontend** | Vite SPA (static build) | No SSR/SEO need for an account-less demo — smallest footprint, simplest stack. |
| **DB + migrations** | SQLAlchemy 2.0 async + Alembic | Battle-tested async ORM and de-facto migrations; handles the sequence and functional indexes cleanly. |
| **Pagination** | Keyset/cursor on `(created_at DESC, id DESC)` | Stable under constant inserts, O(1) per page, no deep-offset slowdown on an unbounded public feed. |
| **Cache strategy** | Cache-aside + negative-caching of 404s (60 s) | Negative caching protects PostgreSQL from floods of unknown/expired codes — it's what makes the p95 budget hold under abuse. |
| **Analytics queue** | Redis Streams consumer group + ACK + retry + dead-letter | At-least-once delivery that survives worker crashes and isolates poison messages, while analytics *never* block or break a redirect. |
| **Validation timing** | Creation-time only (incl. DNS private-IP reject) | Keeps the hot redirect path a pure cache lookup. DNS-rebinding after creation is accepted as a documented limitation. |
| **Metrics exposure** | A simple JSON `/api/metrics` for the UI | Shortest path to the live-metrics demo feature; a Prometheus endpoint was deferred as a future enhancement. |
| **Testing** | pytest + Testcontainers (real PG/Redis) | Highest fidelity — exercises the real Streams and cache behavior the design depends on, not a stubbed approximation. |
| **Reverse proxy** | Nginx | Industry-standard, maximum control over routing and TLS, and the natural place to measure latency. |

---

## Design details worth a closer look

A few mechanisms that are more interesting than the summary suggests.

**The redirect hot path stays a pure cache lookup.** On a cache hit the Redirect service
does *no* expiry check — correctness comes entirely from capping the cache TTL at the
link's remaining lifetime (`EX min(86400, seconds_until_expires)`), so a cached `302` can
never outlive its link. That removes a branch from the hottest code path and means there
is no separate cache-cleanup sweep to run: stale entries simply self-expire.

**One cache entry per code, regardless of query string.** The cache key is derived from
the path segment only, so `?source=qr` and a direct hit on the same code share a single
entry. The query parameter is read solely for the click-event payload, not for caching.

**Analytics are durable without being in the way.** The redirect fires the click onto a
Redis Stream and returns immediately; if that write fails it's swallowed and logged. The
Worker consumes the Stream as a consumer group, so a crashed worker's in-flight messages
are reclaimed via `XAUTOCLAIM` and retried, and a message that fails three times is moved
to a dead-letter stream rather than blocking the queue.

**Privacy is structural, not a setting.** Raw user agents and full referrers reach the
Worker transiently and are never written to PostgreSQL — only the derived
device/browser/OS *category* and the referrer *host* are stored. There is no table that
could leak an IP or a raw UA because none is ever persisted.

**Rate limiting that can't be spoofed past the proxy.** Creation is limited to
10/min and 100/day per client IP via Redis fixed-window counters. The API trusts **only**
the app-controlled `X-Real-IP` that Nginx sets from the genuine TCP peer — it never
parses a client-supplied `X-Forwarded-For` chain — and the backend services bind to the
internal Docker network, so the limiter can't be bypassed unless the proxy itself is.

**The p95 budget is measured where it's honest.** The `< 50 ms p95 on cache hits` figure
is taken **server-side at Nginx** from `$request_time` in the access log — excluding
client↔server network transit — not from the client's stopwatch. A small asyncio load-test
harness lives in [`infra/loadtest/`](infra/loadtest/README.md) and turns that budget into
a hard pass/fail check.

---

## Operational metrics

`GET /api/metrics` returns live operational numbers derived from Redis counters that the
Redirect service and Worker maintain. The shape is intentionally minimal — nine fields,
no latency histogram. The average redirect time is an app-side mean (a latency sum kept in
Redis, divided by the served-redirect count); the `< 50 ms p95` budget is still measured at
Nginx during load testing, since a sum can't yield true percentiles:

| Field | Meaning |
|---|---|
| `cache_hits` | Redirect cache hits (including negative-cache hits). |
| `cache_misses` | Redirect cache misses that fell through to PostgreSQL. |
| `cache_hit_ratio` | `cache_hits / (cache_hits + cache_misses)`, or `0.0` with no lookups. |
| `total_redirects` | Total `302`s served — the throughput counter. |
| `average_redirect_latency_ms` | Mean redirect handler time in ms (app-side, excludes proxy/network), or `null` with no traffic. |
| `queue_pending` | Real unprocessed analytics backlog (consumer-group PEL size). |
| `queue_stream_length` | Recent click-stream entries (capped via `MAXLEN ~`; a volume gauge, not backlog). |
| `worker_healthy` | `true` when the worker heartbeat is ≤ 15 s old. |
| `worker_heartbeat_age_seconds` | Age of the last worker heartbeat, or `null` if never written. |

---

## Deliberate scope boundaries

This is a single-VM portfolio piece, and a few things are out of scope **on purpose**:

- **DNS rebinding** — URLs are SSRF-checked at *creation* time (private/loopback/link-local
  targets are rejected), but a domain that later re-resolves to a private IP is not
  re-checked on the redirect hot path. Re-validating on redirect would cost latency; it
  could be added behind a flag.
- **Public abuse** — anyone can create a link pointing anywhere that passes validation;
  there is no external malware/reputation scanning. The persistent demo banner and the
  rate limits are the only mitigations, and the public dashboard means **no private or
  sensitive URLs should ever be shortened here**.
- **The p95 budget is environment-dependent** — `< 50 ms` holds on cache hits but must be
  load-tested per deployment. The redirect path is kept deliberately minimal to protect it.
- **No accounts, no edits, no custom domains, no cloud-managed data stores** — by design.
  See the [TDD's Goals / Non-Goals](.development-docs/LinkShrink_TDD.md) for the full list.

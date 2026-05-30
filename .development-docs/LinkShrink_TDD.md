# LinkShrink — Technical Design Document

## 1. Summary

LinkShrink is a public, account-less URL shortener and QR-code generator built as a
portfolio piece to showcase production-grade architecture on a single VM. A
React (Vite) single-page app lets anyone shorten a URL — with an optional custom
alias — receive a `link-shrink.org` short link, and download a QR code. Behind an
Nginx reverse proxy sit three independent Python/FastAPI services: an **API
service** (link creation, dashboard, analytics, metrics, QR), a **Redirect
service** (fast cached `302` resolution), and a **Worker service** (consumes a
Redis Stream and writes derived, PII-free analytics to PostgreSQL). Redis provides
both the redirect cache (24h TTL, cache-aside with negative caching) and the
analytics queue (Streams consumer group with ACK + retry + dead-letter). The whole
system comes up with a single `docker compose up`. An optional Educational Mode and
a How-It-Works page surface the architecture for visitors.

## 2. Business Requirements

Lifted from [LinkShrink_BRD.md](LinkShrink_BRD.md):

- Shorten long URLs into compact shareable links on `link-shrink.org`.
- Generate downloadable QR codes for short links, on demand (not stored), with a
  `?source=qr` attribution parameter.
- Optional custom aliases sharing a **single namespace** with generated codes.
- Short codes generated from a monotonic PostgreSQL sequence encoded via **hashids**
  (project salt, custom single-case alphabet, min length 6); deterministic and
  unique by construction.
- Codes matched **case-insensitively**, stored lowercase; aliases `[a-z0-9-]`,
  3–32 chars, no leading/trailing hyphen.
- Reserved-word list protects application routes from being claimed as aliases.
- Expiration: default **and** maximum 30 days; users may pick shorter; expired or
  unknown codes return **404**.
- Purge job permanently deletes links + click events **3 months after expiry**;
  `short_code` stays reserved (unusable, returns 404) until purged.
- Redirects return **302 Found** (deliberately non-cacheable) with **async**
  analytics; redirects must work even if analytics fail.
- Coarse, PII-free analytics: click counts, referrer **domain** only, device/
  browser/OS **category** (derived at processing time, raw UA discarded), source
  (direct/qr), timestamps. **No IPs or raw UAs stored.**
- Public, paginated, account-less dashboard sorted newest-first; view analytics and
  download QR for any link; no edit/delete in the UI; persistent public-demo
  warning notice.
- Performance: redirect **< 50 ms p95 server-side on a cache hit**; frequently
  accessed links cached in Redis (24h TTL); analytics never block the redirect.
- Security: accept only `http(s)` schemes; max URL length; reject targets resolving
  to private/loopback/link-local IPs and self-referential `link-shrink.org` loops;
  IP-based rate limiting on **creation only** in Redis (→ 429); secrets via env vars.
- Specified HTTP status codes: 200 / 201 / 302 / 400 / 404 / 409 / 429.
- Deployment: Docker Compose on a single AWS VM; only AWS VM compute + Route 53 DNS;
  self-hosted PostgreSQL + Redis; TLS terminated at the proxy; persistent volumes;
  health checks.
- Portfolio layer: optional Educational Mode, architecture annotations, technology
  badges, a How-It-Works page, and optional live operational metrics.

## 3. Goals / Non-Goals

**Goals**

- Correct, fast, cache-backed redirects meeting the < 50 ms p95 (cache-hit) budget.
- Clean, demonstrable separation between API, Redirect, and Worker services.
- Durable-enough async analytics that never block or break redirects.
- A single, consistent, case-insensitive short-code namespace for generated codes
  and custom aliases.
- One-command local + single-VM deployment via Docker Compose.
- A clear educational/portfolio narrative surfaced in the UI.

**Non-Goals**

- No accounts, authentication, ownership, or per-user data.
- No edit/delete of links from the public UI.
- No custom domains or branded links.
- No cloud-managed data stores (no RDS/ElastiCache); only raw VM + Route 53.
- No external reputation/malware scanning (noted as a future enhancement).
- No SSR/SEO infrastructure for the dashboard.

## 4. Current State

Greenfield. The repository currently contains only documentation and project rules:

- [CLAUDE.md](../CLAUDE.md) — project rules: **every** rendered HTML element must carry
  a unique descriptive `id`; React components kept small and focused; descriptive,
  natural-language, non-abbreviated naming; booleans prefixed `is/has/can/should/did`.
- [LinkShrink_BRD.md](LinkShrink_BRD.md) — business requirements
  (Section 2 above).
- [LinkShrink_UI_UX_Guide.md](LinkShrink_UI_UX_Guide.md) — dark mode
  only; palette (bg `#0F1117`, surface `#1E2230`, text `#FFFFFF`, secondary `#B4BAC8`,
  purple accent `#A855F7`, green success `#22C55E`); Inter font; centered content,
  max width 1200px, card layouts; mobile single-column with collapsible nav; URL
  input is the primary focus; paste → shorten → copy → QR in seconds.

The unrelated `.joeys-hub/` directory is a separate git repository (personal
portfolio) and is **out of scope**; it is git-excluded. No application source,
package manifests, or infra exist yet.

## 5. Proposed Design

### 5.1 High-level approach

A monorepo containing a shared Python package plus three FastAPI services, a Vite
React frontend, and infra (Docker Compose + Nginx). The shared package holds the one
authoritative copy of the short-code logic, SQLAlchemy models, validation rules,
reserved-word list, and config — so the API and Redirect services resolve codes
identically.

```
linkshrink/
├── packages/
│   └── shared/                  # importable Python package: linkshrink_shared
│       ├── models.py            # SQLAlchemy 2.0 models (Link, ClickEvent)
│       ├── shortcode.py         # hashids encode/decode + sequence handling
│       ├── validation.py        # URL + alias validation, reserved words
│       ├── config.py            # pydantic-settings (env-driven)
│       ├── cache.py             # Redis cache-aside helpers + keys
│       └── queue.py             # Redis Streams add/read/ack helpers
├── services/
│   ├── api/                     # FastAPI: create, dashboard, analytics, qr, metrics
│   ├── redirect/                # FastAPI: GET /{code} -> 302 (hot path)
│   └── worker/                  # asyncio consumer of the clicks stream
├── frontend/                    # React + Vite SPA (static build)
├── migrations/                  # Alembic env + versions (shared schema)
├── infra/
│   ├── nginx/                   # Nginx config + TLS
│   └── docker-compose.yml
├── pyproject.toml               # workspace / tooling (ruff, pytest)
└── README.md
```

> The shared package is installed (editable) into each service image so all three
> import `linkshrink_shared`. Alembic owns the schema; services never auto-create
> tables.

### 5.2 Services & responsibilities

- **API service (FastAPI, async)** — link creation (with validation + rate limit),
  paginated dashboard listing, per-link analytics, QR generation, `/api/metrics`,
  `/health`. Reads/writes PostgreSQL; reads Redis (metrics, cache invalidation on
  create not required since codes are new); writes negative/positive cache opt-in.
- **Redirect service (FastAPI, async, minimal)** — single hot endpoint
  `GET /{short_code}`: cache-aside lookup → `302` to original URL, then fire a click
  event onto the Redis Stream (non-blocking, best-effort). Kept deliberately small
  for latency.
- **Worker service (asyncio)** — `XREADGROUP` from the `clicks` stream as a consumer
  group; parses the raw UA into device/browser/OS categories and extracts the
  referrer **host**, inserts a `ClickEvent`, `XACK`s. Reclaims stale pending entries;
  dead-letters poison messages after 3 attempts. Also runs the scheduled **purge**
  job.
  **Scheduling:** the consumer loop runs as the main task; the periodic jobs
  (`XAUTOCLAIM` recovery, purge) run as separate `asyncio` background tasks on fixed
  intervals (`asyncio.create_task` + interval sleep) — no external scheduler
  dependency, kept simple for the portfolio piece.
  **No expiry-cache cleanup job is needed:** the positive cache TTL is capped at the
  link's remaining lifetime (§5.6), so a `302` cache entry can never outlive its
  link — stale entries self-expire and there is nothing to sweep.
  **Health:** the worker has no HTTP surface, so liveness is a heartbeat — it
  writes `metrics:worker:heartbeat` (a timestamp) to Redis each consumer-loop
  iteration; the Docker `healthcheck` runs a small script that fails if the
  heartbeat is older than a threshold. Because the consumer loop does
  `BLOCK 5000` (≤ ~5 s between heartbeats), the staleness threshold must sit
  comfortably above that — **15 s** — to avoid false "unhealthy" flaps under low
  traffic.
- **PostgreSQL** — source of truth (links, click events, the short-code sequence).
- **Redis** — redirect cache (24h TTL), negative cache (60s TTL), rate-limit
  counters, analytics Stream, and metrics counters.
- **Nginx** — TLS termination, routing, and the authoritative **server-side**
  measurement point for redirect p95 (via `$request_time`, excluding client↔server
  network transit).

### 5.3 Data model (PostgreSQL, via SQLAlchemy 2.0 + Alembic)

**Sequence**

```sql
CREATE SEQUENCE link_code_seq START 1 INCREMENT 1;  -- feeds hashids
```

**`links`**

| column        | type          | notes                                              |
|---------------|---------------|----------------------------------------------------|
| `id`          | bigint PK     | identity                                           |
| `short_code`  | text          | **unique**, stored lowercase; generated or alias   |
| `original_url`| text          | validated `http(s)`, ≤ 2048 chars                  |
| `is_custom`   | boolean       | true if user-supplied alias                        |
| `created_at`  | timestamptz   | default `now()`                                    |
| `expires_at`  | timestamptz   | ≤ created_at + 30 days                             |

Indexes: **unique functional index on `lower(short_code)`** — `short_code` is
plain `text` (codes are already normalized to lowercase on write, so the index is
the case-insensitive guard). Chosen over `citext` to avoid the `CREATE EXTENSION`
privilege requirement in the migration, keeping the initial Alembic migration
runnable by an unprivileged app role. Plus a composite `(created_at DESC, id DESC)`
for keyset pagination and `expires_at` for purge scans.

**`click_events`**

| column            | type        | notes                                  |
|-------------------|-------------|----------------------------------------|
| `id`              | bigint PK   | identity                               |
| `link_id`         | bigint FK   | → `links.id` ON DELETE CASCADE         |
| `clicked_at`      | timestamptz | default `now()`                        |
| `referrer_domain` | text null   | host only                              |
| `device_type`     | enum        | desktop / mobile / tablet / unknown    |
| `browser_family`  | text null   | e.g. Chrome, Safari                    |
| `os_family`       | text null   | e.g. Windows, iOS                      |
| `source`          | enum        | direct / qr                            |

Index `(link_id, clicked_at)` for per-link analytics aggregation. No IPs, no raw UA.
`ON DELETE CASCADE` makes the purge a single `DELETE FROM links WHERE …`.

### 5.4 Short-code generation

1. `nextval('link_code_seq')` → integer `n`.
2. `code = hashids.encode(n)` using salt (env), single-case alphabet, min length 6.
3. Insert `links` row with `short_code = code`. The unique constraint guards against
   the rare collision with an existing **custom alias**; on conflict, advance to the
   next sequence value and re-encode until insertion succeeds (BRD §3).

Custom alias path: normalize to lowercase → validate `[a-z0-9-]`, 3–32 chars, no
leading/trailing hyphen (else **400**) → reject if reserved or already taken
(**409**) → insert with `is_custom = true`.

**Reserved words** (maintained in `validation.py`): `api`, `dashboard`,
`how-it-works`, `health`, `metrics`, `assets`, `static`, `qr`, `admin`. These are
the only entries that can realistically collide with the alias grammar and so are
the meaningful aliasing guard. Paths containing a dot (`robots.txt`,
`favicon.ico`) **cannot** be claimed as aliases anyway — the `[a-z0-9-]` grammar
forbids `.` — so they need no aliasing reservation; they are reserved only at the
**proxy-routing** layer (§5.10, blocks 1–4). The list must remain a superset of
every proxy/frontend-served path, asserted by the coverage test in §7.

### 5.5 URL validation (creation-time only)

- Parse; require scheme ∈ {`http`, `https`} (else 400).
- Enforce length ≤ 2048 (else 400).
- Reject host == `link-shrink.org` / configured public host (self-referential, 400).
- Resolve the hostname (DNS) and reject if **any** resolved address is
  private/loopback/link-local (RFC 1918, 127/8, 169.254/16, `::1`, `fc00::/7`, etc.)
  as SSRF defense-in-depth (400). Redirects do **not** re-resolve (latency).
- Known limitation: DNS-rebinding after creation is not mitigated (see §7).

### 5.6 Redirect flow (hot path)

```
GET /{code}  (Nginx → Redirect service)
  └─ key = redirect:{code}
  ├─ Redis HIT  → 302 Location: original_url ; XADD clicks
  ├─ Redis NEG-HIT ("__404__") → 404
  └─ MISS → SELECT … WHERE lower(short_code)=:code
        ├─ found & not expired → SET redirect:{code} url EX min(86400, seconds_until_expires_at) → 302 ; XADD clicks
        └─ not found / expired → SET redirect:{code} "__404__" EX 60 → 404
```

**Cache TTL is capped at the link's remaining lifetime** — `EX min(86400,
seconds_until_expires_at)` — so a positive cache entry can never outlive the link
and keep serving a `302` for an already-expired code (BRD §3, §8). The HIT branch
deliberately performs **no** expiry check to stay minimal; correctness comes
entirely from the capped TTL — there is no separate cache-cleanup sweep (§5.2).
This must be an explicit acceptance criterion on the Redirect-service ticket, since
the §8.8 expiry test would otherwise pass via the DB miss-path while real cache-hit
traffic stayed broken.

**Cache key ignores the query string.** The key is `redirect:{code}` derived from
the path segment only; the `?source=qr` query parameter is **not** part of the key.
It is read solely for the click-event payload (`source`), so QR and direct hits on
the same code share one cache entry rather than splitting into two.

Click event payload onto the stream (best-effort; failure is swallowed and logged,
never blocks the 302): `{link_id, ts, referrer (Referer header), ua (raw, transient),
source (`qr` if `?source=qr` else `direct`)}`. The **worker** is what derives and
stores the coarse fields; the raw UA/referrer never reach PostgreSQL.

### 5.7 Analytics pipeline (durable)

- Stream `clicks`; consumer group `analytics`; consumers `worker-{n}`.
- Worker loop: `XREADGROUP GROUP analytics worker-1 COUNT 100 BLOCK 5000` →
  for each: parse UA (`user-agents`/`ua-parser`) → device/browser/OS; extract
  Referer host → `referrer_domain`; insert `ClickEvent`; `XACK`.
- Recovery: periodic `XAUTOCLAIM` of entries idle > N seconds (crashed consumer);
  after 3 delivery attempts, copy to `clicks:dead` and `XACK` to unblock the PEL.
- Stream trimmed with `MAXLEN ~` to bound memory.
- Metrics counters (`metrics:cache:hit`, `:miss`, `metrics:redirects:total`)
  are simple `INCR`s updated by the redirect service; queue depth read via `XLEN` /
  PEL size. **No latency histogram in Redis** — computing p95 from counters is
  out of scope for the portfolio piece. The `<50ms p95` SLO is a **server-side**
  figure measured at Nginx from the access log (`$request_time`) during load
  testing (§9.10); `/api/metrics` exposes only derived live numbers (cache hit
  ratio, queue depth, total redirects / throughput).

### 5.8 API surface (REST, JSON)

| Method & path                       | Purpose                              | Codes                |
|-------------------------------------|--------------------------------------|----------------------|
| `POST /api/links`                   | Create link (url, optional alias, optional `ttl_seconds`) | 201, 400, 409, 429 |
| `GET /api/links?cursor=&limit=`     | Keyset-paginated list, newest first  | 200                  |
| `GET /api/links/{code}`             | Link detail                          | 200, 404             |
| `GET /api/links/{code}/analytics`   | Aggregated analytics for a link      | 200, 404             |
| `GET /api/links/{code}/qr?format=png\|svg` | QR image (PNG 512px ECC=M default; SVG option) | 200, 404 |
| `GET /api/metrics`                  | Live operational metrics (JSON)      | 200                  |
| `GET /health` (API + Redirect)      | HTTP health check                    | 200                  |
| `GET /{code}` (Redirect service)    | Resolve + redirect                   | 302, 404             |

**Create request** (example): `{ "url": "...", "alias": "my-link"?, "ttl_seconds": 86400? }`.
A single `ttl_seconds` field is the only lifetime input (no `expires_at` on the
wire — avoids client clock-skew): clamped to **[3600, 2592000]** (1 hour – 30 days);
default `2592000` (30 days). The server computes `expires_at = created_at +
ttl_seconds`. **Create response**: `{ short_code, short_url, original_url,
created_at, expires_at, qr_url }`.

**Keyset pagination**: opaque base64 cursor encoding `(created_at, id)` of the last
row; response `{ items: [...], next_cursor: "..."|null }`. `limit` defaults to 20
and is **clamped to a maximum of 100** so this public, unauthenticated endpoint
can't be asked for an unbounded page.

**Analytics response** (aggregated server-side): total clicks, clicks over time
(daily buckets in **UTC** — `date_trunc('day', clicked_at)` at UTC), breakdown by
device_type / browser_family / os_family / referrer_domain / source.

### 5.9 Rate limiting (creation only)

Redis **fixed-window** counters keyed by client IP: **10 creates/min** and
**100 creates/day**. Each create does one `INCR` per window key with an `EXPIRE`
set on first hit (e.g. `ratelimit:min:{ip}` TTL 60 s, `ratelimit:day:{ip}` TTL
86400 s); exceeding either → **429** with `Retry-After`. Fixed-window is chosen
over sliding-window for simplicity — a couple of `INCR`s, no sorted-set eviction —
which is more than adequate for a demo. Redirects are unthrottled. The IP is used
transiently for the counter key only; it is never persisted.

**Trusting the client IP.** Nginx resolves the real client IP with the `real_ip`
module (`set_real_ip_from` the trusted proxy hop + `real_ip_recursive on`) and
passes it to the API in a single, app-controlled header. The API trusts **only**
that header — it does **not** parse a raw, client-supplied `X-Forwarded-For`
chain, which is spoofable. Defense in depth: bind the API service to the internal
Docker network so it is unreachable except through Nginx (§7).

### 5.10 Frontend (React + Vite SPA)

- Pages/areas: **Home** (URL input primary focus → result card with copy + QR
  download), **Dashboard** (paginated link list + per-link analytics view), **How
  It Works** (architecture annotations, badges, scaling story), persistent
  **public-demo warning** banner, and an **Educational Mode** toggle.
- **Public-visibility warning (required on the landing page).** Because the
  dashboard is account-less and public, **every shortened link — its destination
  URL and analytics — is visible to anyone**. The Home page must carry a clear,
  persistent notice that this is a demo site and users should **not shorten any
  private, sensitive, or confidential links**. This is a hard acceptance criterion
  on the Frontend ticket, not just banner copy.
- Educational content (annotations, badge explanations, How-It-Works copy) is
  **static** React content in the frontend; only live numbers come from
  `/api/metrics`.
- Styling per the UI/UX guide: dark-only, Inter, purple actions / green success,
  card layouts, 1200px max width, mobile single-column + collapsible nav.
- **CLAUDE.md compliance**: every rendered element gets a unique descriptive `id`;
  components kept small and single-responsibility; descriptive naming; booleans
  `is/has/can/should/did`.
- API client calls `/api/*`; the proxy serves the static build and routes `/api/*`
  to the API service and bare `/{code}` to the Redirect service.

**Routing precedence (Nginx).** Because the SPA owns client-side routes
(`/dashboard`, `/how-it-works`) that a visitor can hard-navigate or refresh
directly, the proxy must serve `index.html` for those paths rather than forward
them to the Redirect service (which would `404` them as unknown codes). Nginx
evaluates `location` blocks in this order:

1. `/api/*` → API service.
2. `/health`, `/api/metrics` → respective services.
3. Static assets (`/assets/*`, `favicon.ico`, `robots.txt`, hashed bundles) →
   static build.
4. Known SPA routes (`/`, `/dashboard`, `/how-it-works`) → serve `index.html`.
5. **Fallback** `/{code}` → Redirect service.

The set of paths handled by blocks 1–4 **is** the source of truth for the
reserved-word list (§5.4): every path the proxy/frontend serves must also be
reserved from aliasing, and a test asserts `reserved_words ⊇ proxy_served_paths`
(**superset, not equality**) so the two never drift. The list is deliberately
allowed to over-reserve (e.g. `static`, `qr`, `admin` are reserved defensively even
though they are not bare served paths) — extra reserved words are harmless and must
not fail the test, so it checks containment only.

### 5.11 Deployment

- `docker compose up` brings up: `postgres`, `redis`, `api`, `redirect`, `worker`,
  `frontend-build` (produces static assets), `nginx`.
- Persistent named volumes for Postgres data and Redis (AOF) persistence.
- Health checks on every service; Nginx terminates TLS for `link-shrink.org`
  (Let's Encrypt via certbot on the VM; self-signed/HTTP for local).
- Alembic migrations run as a one-shot init step before services accept traffic.
  Migrations are **forward-only in deployed environments** (local-shared, staging,
  production): `downgrade()` is never run there — to undo a shipped change you write
  a new forward migration. Each migration still implements a real `downgrade()`, used
  only for local test teardown and migration-authoring round-trips.
- All secrets (hashids salt, PG creds, Redis creds) via env / `.env` (gitignored),
  never committed.

### 5.12 Primary flow sequences

**Create:** Frontend → `POST /api/links` → rate-limit check → validate URL/alias →
(alias? check reserved/taken : `nextval` + hashids, retry on conflict) → insert →
`201` with short_url + qr_url.

**Redirect + analytics:** Browser → Nginx → Redirect svc → cache-aside → `302` →
`XADD clicks` → Worker `XREADGROUP` → parse/derive → insert ClickEvent → `XACK`.

**Purge:** Worker scheduled job → `DELETE FROM links WHERE expires_at < now() -
interval '3 months'` (cascades to click_events).

## 6. Decisions

| # | Decision | Chosen | Alternatives considered | Rationale |
|---|----------|--------|-------------------------|-----------|
| 1 | Backend stack | **Python + FastAPI** (async) for API/Redirect/Worker | Node+TS/Fastify; Go | Clean async service story, mature libs (hashids, qrcode, user-agents, redis-py); strong portfolio readability. |
| 2 | Repo layout | **Monorepo with shared package** | Monorepo w/ per-service duplication | One authoritative copy of short-code + validation + models so API and Redirect resolve codes identically. |
| 3 | Reverse proxy | **Nginx** | Caddy | Industry-standard, maximum familiarity and control; TLS via certbot. |
| 4 | Frontend | **Vite SPA (static build)** | Next.js | No SSR/SEO need for an account-less demo; smallest footprint, simplest stack. |
| 5 | DB access + migrations | **SQLAlchemy 2.0 async + Alembic** | SQLModel+Alembic; raw asyncpg+SQL | Mature, battle-tested async ORM + de-facto migrations; handles sequence/indexes cleanly. |
| 6 | Pagination | **Keyset/cursor on (created_at DESC, id DESC)** | Offset/limit + total | Stable under constant inserts, O(1) per page, no deep-offset slowdown for an unbounded feed. |
| 7 | Testing | **pytest + Testcontainers (real PG/Redis)** + unit tests | pytest + fakeredis/SQLite | Highest fidelity; exercises real Streams/cache behavior the design depends on. |
| 8 | QR output | **PNG default (512px, ECC=M) + SVG option** | PNG only; SVG only | Universal raster download plus a crisp scalable variant; generated on demand, not stored. |
| 9 | Analytics queue | **Streams consumer group + ACK + retry + DLQ** | Simple ACK no DLQ; fire-and-forget | At-least-once, survives worker crashes, isolates poison messages; analytics never block redirect. |
| 10 | Cache strategy | **Cache-aside + negative-cache 404s (60s)** | Cache-aside, no negative caching | Protects Postgres from floods of unknown/expired codes; supports the 50ms p95 budget. |
| 11 | URL validation timing | **Creation-time only (incl. DNS private-IP reject)** | Creation + re-check on redirect | Keeps the hot redirect path a pure cache lookup; DNS-rebinding accepted as known limitation. |
| 12 | Metrics exposure | **JSON `/api/metrics` for the UI** | Prometheus `/metrics` + JSON | Simplest path to the live-metrics demo feature; Prometheus deferred as future enhancement. |
| 13 | Operational defaults | **Recommended defaults accepted** | Looser limits; custom | 10/min + 100/day creates; maxURL 2048; expiry 30d max / 1h min / 30d default; alias [a-z0-9-] 3–32; QR 512px PNG ECC=M; neg-cache 60s. |
| 14 | Educational content | **Static frontend content** | API-served | Essentially static text; no backend coupling; live numbers still from `/api/metrics`. |

## 7. Risks and Open Questions

- **DNS rebinding** — creation-time IP validation does not catch a domain that later
  resolves to a private IP (decision #11). Mitigation: documented as a known
  limitation; redirect re-validation could be added later behind a flag.
- **p95 < 50 ms budget** — achievable on cache hits but must be load-tested; keep the
  Redirect service minimal (no ORM overhead on the hot path — consider a lightweight
  query or direct asyncpg there if SQLAlchemy adds latency on misses).
- **Rate limiting behind a proxy** — depends on Nginx's `real_ip` module deriving
  the client IP from the trusted hop and passing it in the app-controlled header
  the API trusts (§5.9); raw client-supplied `X-Forwarded-For` is never parsed. On
  the single VM this is controlled, but spoofing is possible if the proxy is
  bypassed — so bind the API/Redirect services to the internal Docker network only.
- **Public abuse** — anyone can create links pointing anywhere (within validation).
  External malware/reputation scanning is explicitly out of scope; the demo banner
  and rate limits are the only mitigations.
- **Sequence + alias collision retry** — bounded but should be tested under
  contention; ensure the retry loop has a sane cap and logs.
- **Reserved-word completeness** — the list must stay in sync with any new
  frontend/proxy route; owned in `validation.py` with a test asserting coverage.
- **Decided** — analytics daily buckets use **UTC** (`date_trunc('day',
  clicked_at)` at UTC). No per-viewer timezone conversion for the portfolio piece.

## 8. Rollout / Verification

**Manual verification (maps to BRD §8 success criteria)**

1. `docker compose up` → all services healthy; migrations applied.
2. Create a link (UI + `POST /api/links`) → `201`, short link resolves via `302` to
   the target.
3. Hit the short link repeatedly → confirm cache hit and measure redirect latency at
   Nginx (< 50 ms p95 on hits).
4. Confirm a click appears in `/api/links/{code}/analytics` within ~1s, without
   slowing the redirect; kill the worker mid-stream and confirm clicks are reclaimed.
5. Download QR (PNG + SVG); scan → arrives with `?source=qr` and is attributed as a
   QR source.
6. Dashboard paginates newest-first via cursor; analytics render per link.
7. Exceed creation rate limit → `429`. Submit `javascript:`/private-IP/self URL →
   `400`. Claim a reserved/taken alias → `409`. Hit unknown/expired code → `404`.
8. Set a short TTL, let it expire → `404`; verify `short_code` stays reserved.

**Rollout / compatibility**

- No backwards-compat constraints (greenfield). Alembic migrations are forward-only
  **in deployed environments** — `downgrade()` is never run in staging/production; to
  undo a shipped change you write a new forward migration. Each migration nonetheless
  implements a working `downgrade()` for local test teardown and round-trip
  validation. Ship the initial migration with the first release.
- Feature flags not required; Educational Mode is a client-side toggle.
- Local vs prod differ only in TLS (self-signed/HTTP locally; Let's Encrypt on VM)
  and `.env` values.

## 9. Work Breakdown

1. **Repo & tooling scaffold** — monorepo layout, `pyproject.toml`, ruff, pytest,
   `linkshrink_shared` package skeleton, `.env.example`, Docker base images.
2. **Database & migrations** — SQLAlchemy 2.0 models (`Link`, `ClickEvent`), the
   `link_code_seq` sequence, indexes; Alembic env + initial migration.
3. **Shared core** — hashids short-code generate/encode/decode + collision retry;
   URL + alias validation + reserved-word list; Redis cache/queue/config helpers.
4. **API service** — create endpoint (validation + rate limit), keyset dashboard
   listing, link detail, analytics aggregation, QR (PNG/SVG), `/api/metrics`,
   `/health`.
5. **Redirect service** — minimal cache-aside `GET /{code}` → `302`/`404`, negative
   caching, `XADD` click event, latency metrics counters, `/health`.
6. **Worker service** — Streams consumer group loop, UA/referrer derivation, click
   insert + `XACK`, `XAUTOCLAIM` recovery + DLQ; scheduled purge + neg-cache cleanup.
7. **Frontend** — Vite React SPA: Home/result card, Dashboard + analytics views, How
   It Works, demo-warning banner, Educational Mode toggle, tech badges; UI/UX-guide
   styling; unique `id`s on all elements; API client.
8. **Infra** — Nginx config (TLS, routing API vs Redirect vs static), Docker Compose
   (postgres, redis, api, redirect, worker, frontend build, nginx), volumes, health
   checks, migration init step.
9. **Testing** — unit (short-code, validation, UA parsing, cursor); integration with
   Testcontainers (PG+Redis): create→redirect→analytics, rate limit, expiry/404,
   purge, queue recovery/DLQ; reserved-word coverage test.
10. **Observability & docs** — metrics wiring + JSON shape (cache hit ratio, queue
    depth, total redirects / throughput); README run instructions; load test
    confirming the < 50 ms p95 cache-hit budget, measured **server-side at Nginx**
    via `$request_time`.

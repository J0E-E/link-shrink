# LinkShrink — Epic Plan

Source TDD: [.development-docs/LinkShrink_TDD.md](.development-docs/LinkShrink_TDD.md)

This breaks the TDD into small, independently deliverable epics. Backend foundation
and the shared package come first; each service is layered on top; the frontend and
infra wire everything together; integration testing and observability close it out.
Every epic is sized to a single reviewable commit and leaves `development` working
(its own tests/lint pass and nothing previously merged breaks).

---

## Epic 1 — Repo & tooling scaffold — COMPLETED
- **Intent:** Stand up the monorepo skeleton so every later epic has a home, shared tooling, and a one-command lint/test entry point.
- **Scope:** Directory layout from §5.1 (`packages/shared/`, `services/{api,redirect,worker}/`, `frontend/`, `migrations/`, `infra/`); root `pyproject.toml` with ruff + pytest config; `linkshrink_shared` package skeleton (empty modules `models.py`, `shortcode.py`, `validation.py`, `config.py`, `cache.py`, `queue.py` with docstrings); `.env.example` (hashids salt, PG creds, Redis creds, public host); `.gitignore` entries for `.env`; base `README.md`; base Dockerfile(s) for the Python services (a common base image whose layer installs the editable `linkshrink_shared` package, reused by api/redirect/worker images per §9.1).
- **Verification:** `ruff check` and `pytest` run clean (no tests yet, exit 0); `pip install -e packages/shared` succeeds and `import linkshrink_shared` works; `docker build` of the base Python image succeeds with `linkshrink_shared` importable inside it.
- **Depends on:** none.
- **Implementation notes (delivered):**
  - **Python 3.12**, plain pip + **setuptools** build backend (no uv/poetry), matching the TDD's `pip install -e` flow.
  - The shared package uses a **src layout** — `packages/shared/src/linkshrink_shared/` (refines the TDD §5.1 flat sketch) — to keep editable installs clean and prevent importing an uninstalled copy. Its modules (`models/shortcode/validation/config/cache/queue.py`, plus `__init__.py` with `__version__`) are docstring-only stubs naming the epic that fills each.
  - **Shared runtime deps declared now** in `packages/shared/pyproject.toml`: `sqlalchemy[asyncio]>=2.0,<2.1`, `asyncpg>=0.29`, `pydantic-settings>=2`, `redis>=5`, `hashids>=1.3`. Service-specific deps (fastapi, uvicorn, qrcode, user-agents) are deferred to their own epics since `services/*` are empty placeholders (`.gitkeep`).
  - Root `pyproject.toml` is **tooling-config only** (no `[project]` table): `[tool.ruff]` (target py312, line-length 100, rule set E/F/I/UP/B) and `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`). Dev/tooling deps live in `requirements-dev.txt` (`ruff`, `pytest`, `pytest-asyncio`, `alembic`, `testcontainers[postgres,redis]`).
  - Added `tests/test_smoke.py` (imports `linkshrink_shared`, asserts `__version__`). **Reason:** `pytest` with zero collected tests exits **5**, not 0 — one trivial import test satisfies both the "pytest exit 0" *and* "`import linkshrink_shared` works" checks. (The "no tests yet" wording is met by a single smoke test.)
  - Base image lives at `infra/docker/python-base.Dockerfile` (`python:3.12-slim`, `COPY packages/shared` + editable install), built from the repo root: `docker build -f infra/docker/python-base.Dockerfile -t linkshrink-base .`. Epic 18a's api/redirect/worker images build `FROM` it.
  - Also added `.gitignore` (`.env`, Python/build caches, `node_modules`, `dist/build`), `.env.example` (hashids salt, PG/Redis creds, `PUBLIC_HOST`), and base `README.md` (layout + dev-setup + base-image build). `.gitignore` ignores `.env` exactly, so the tracked `.env.example` is preserved.
  - **Added in review:** `.dockerignore` and `.gitattributes`.
    - `.dockerignore` — the base image builds from the repo root, so the whole repo is the build context; this excludes `*.egg-info/`, `__pycache__/`, `.venv/`, `node_modules/`, `.git/`, etc. so host build cruft is neither shipped to the daemon nor copied into the shared editable-install layer.
    - `.gitattributes` — `* text=auto eol=lf` (plus explicit `*.sh text eol=lf`) so text files commit as LF and never leak CRLF into the Linux service containers, ahead of the shell health-check scripts arriving in Epics 12/18a. **Caveat:** this normalizes on next touch only; run `git add --renormalize .` if a full-tree normalization is ever wanted.
  - **Verified:** editable install + `import linkshrink_shared` ✓; `ruff check .` exit 0 ✓; `pytest` exit 0 (1 passed) ✓; `docker build` of the base image + in-container `import linkshrink_shared` ✓.

## Epic 2 — Database models & Alembic migration — COMPLETED
- **Intent:** Define the source-of-truth schema so all services share one set of models.
- **Scope:** SQLAlchemy 2.0 models `Link` and `ClickEvent` in `shared/models.py` (§5.3) with enums for `device_type` and `source`; the `link_code_seq` sequence; unique functional index on `lower(short_code)`, composite `(created_at DESC, id DESC)`, `expires_at`, and `(link_id, clicked_at)` indexes; `ON DELETE CASCADE` FK; Alembic env + initial forward-only migration in `migrations/`.
- **Verification:** `alembic upgrade head` against a local/Testcontainers Postgres creates tables, sequence, and all indexes; `alembic downgrade base` then `upgrade head` round-trips; a quick model insert/select sanity test passes.
- **Depends on:** Epic 1.
- **Note:** the initial migration implements a real `downgrade()` (trivially drops everything back to an empty DB — lossless by definition for the first revision), used only for the round-trip consistency check above and local test teardown. This does **not** contradict the "forward-only" policy (§5.11/§8), which means *downgrades are never run in staging/production* — to undo a shipped change you write a new forward migration. See the clarified §5.11/§8 wording.
- **Implementation notes (delivered):**
  - **Models** in `packages/shared/src/linkshrink_shared/models.py`: SQLAlchemy 2.0 declarative `Base` carrying a shared `MetaData` with a **naming convention** (`ix/uq/ck/fk/pk` templates) so ORM- and migration-side constraint/index names always agree. `Link` and `ClickEvent` use `Mapped[...]` + `mapped_column`; both PKs are `BigInteger` + `Identity()` → `GENERATED BY DEFAULT AS IDENTITY` (TDD's "identity", not serial). Exported from `__init__.py` so `from linkshrink_shared import Link, ClickEvent, DeviceType, Source, link_code_seq` works.
  - **Enums are native PostgreSQL enum types** (`device_type`, `source`), not varchar+CHECK — matches the TDD wording. Modeled as `enum.StrEnum` subclasses (`DeviceType`, `Source`); values are fixed so there is no `ALTER TYPE` evolution concern.
  - **`link_code_seq`** is a standalone `Sequence` attached to `Base.metadata` (not bound to a column) — it feeds hashids in Epic 3 via `nextval('link_code_seq')`.
  - **Functional/DESC index** decision: the `lower(short_code)` unique index and the `(created_at DESC, id DESC)` index are declared with `sa.text(...)` in the model `__table_args__` and emitted via raw `op.execute(CREATE [UNIQUE] INDEX ...)` in the migration, because Alembic autogenerate does not reliably reproduce functional indexes or per-column `DESC` ordering. The migration is therefore **hand-authored** (not autogenerated) so the DDL matches §5.3 exactly (verified via `alembic upgrade head --sql`).
  - **Alembic env is async** (`migrations/env.py`, `asyncio.run(run_async_migrations())`) because the shared package ships **only `asyncpg`** — no sync driver (psycopg2). `alembic.ini` lives at the **repo root** (`script_location = migrations`, `path_separator = os`), with a zero-padded sortable `file_template`.
  - **DB URL resolution forward-reference:** `config.py` (pydantic-settings) is Epic 5, so `env.py` resolves the URL itself — an explicit `sqlalchemy.url` set on the `Config` (used by the tests) else a `postgresql+asyncpg://` URL built directly from the `POSTGRES_*` env vars (those in `.env.example`). This direct env read is a deliberate Epic-2-era stand-in; Epic 5 may later route it through shared config.
  - **Migration `downgrade()`** reverses in dependency order: drop indexes → drop tables → `DROP SEQUENCE` → drop the two enum types (the enum types are created explicitly with `checkfirst` and the columns use `create_type=False`, so type creation/teardown order is deterministic).
  - **Tests** (`tests/test_migrations.py`, Testcontainers Postgres `postgres:16-alpine`): `upgrade head` then assert the two tables, the sequence, and all four indexes exist; `downgrade base → upgrade head` round-trip; ORM insert/select of a `Link` + `ClickEvent`, `nextval('link_code_seq')` usability, and a **core `DELETE FROM links`** to prove the DB-level `ON DELETE CASCADE` (not just ORM cascade). Alembic is driven from **sync** fixtures/tests (env.py's `asyncio.run` cannot run inside a live loop); data assertions use a fresh async engine. The module **`pytest.skip`s if Docker is unavailable** so `pytest` still exits 0 on a Docker-less machine (matching Epic 1's clean-run expectation).
  - Removed the now-stale `migrations/.gitkeep` (the directory has real content).
  - **Verified:** `ruff check .` exit 0 ✓; `pytest` 4 passed (smoke + 3 migration tests) against a real PG container ✓; `alembic upgrade head --sql` emits the exact §5.3 DDL (native enums, IDENTITY PKs, timestamptz `now()` defaults, cascade FK, functional `lower(short_code)` unique + `(created_at DESC, id DESC)` indexes) ✓.

## Epic 3 — Short-code generation (shared) — COMPLETED
- **Intent:** One authoritative, deterministic short-code generator with collision retry.
- **Scope:** `shared/shortcode.py` — hashids encode/decode using env salt, single-case alphabet, min length 6 (§5.4); `nextval('link_code_seq')` consumption; bounded conflict-retry loop (advance sequence + re-encode on unique violation, sane cap, logs) per §7.
- **Verification:** Unit tests: encode is deterministic per `n`, decode round-trips, output matches alias grammar `[a-z0-9-]` (single case) with length ≥ 6, retry loop advances on simulated conflict and gives up after the cap.
- **Depends on:** Epic 2.
- **Implementation notes (delivered):**
  - **Alphabet** is `SHORT_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"` (36 lowercase letters + digits, **no hyphen**) with `SHORT_CODE_MIN_LENGTH = 6`. hashids only emits characters from its alphabet — and its internal separators/guards for this alphabet are themselves drawn from it (verified against hashids 1.3: separators `shufticab`, guards `85l`, all `[a-z0-9]`) — so a generated code is **always `[a-z0-9]` ⊂ alias grammar `[a-z0-9-]`**, single-case, length ≥ 6. The hyphen the grammar allows is for *custom* aliases (Epic 4), never for generated codes, so it is deliberately absent from the alphabet.
  - **`ShortCodeGenerator`** wraps a `Hashids(salt, alphabet, min_length)` instance: `encode(n)` (guards `n < 1` → `ValueError`, since hashids silently returns `""` for non-positive `n` which would break the length-6 invariant; `nextval` starts at 1 so this never fires in practice) and `decode(code) -> int | None` (`hashids.decode` returns a tuple → first element or `None`). Construction rejects an empty salt.
  - **Retry contract is a bool callback.** `generate_unique_short_code(get_next_sequence_value, try_persist, *, generator=None, max_attempts=DEFAULT_MAX_ATTEMPTS)` is fully decoupled from the DB (no SQLAlchemy import), which is what lets the retry path be **unit-tested with no container**. `try_persist(code)` returns `True` on success / `False` only on the `lower(short_code)` unique violation (retry), and MUST let every other error propagate so a transient failure is never silently retried as a collision. Epic 6 supplies the adapter that wraps its `INSERT` in `session.begin_nested()` (savepoint) and translates only the `uq_links_lower_short_code` `IntegrityError` to `False`.
  - **`DEFAULT_MAX_ATTEMPTS = 5`** — a safety cap, not an expected limit: collisions only occur against a pre-existing custom alias and `nextval` advances on every call, so consecutive collisions are effectively impossible. Each retry logs a `WARNING`; exhausting the cap raises `ShortCodeCollisionError`. This establishes the shared-package logging convention (`logger = logging.getLogger(__name__)`).
  - **Salt source is a deliberate Epic-3 stand-in.** `default_short_code_generator()` reads `HASHIDS_SALT` directly from the environment (raising `RuntimeError` if unset/empty), mirroring Epic 2's direct env read in `migrations/env.py`. Epic 5's `config.py` (pydantic-settings, still a stub) will later route this through shared config. Tests inject a fixed salt and never touch the real env.
  - **`fetch_next_sequence_value(session)`** is a thin `await session.scalar(link_code_seq.next_value())` wrapper (ties to the `link_code_seq` model object). It needs a live DB, so it is **not** unit-tested here — the `nextval` SQL is already proven against a real container in `tests/test_migrations.py`, and the wrapper is exercised end-to-end through the API insert path in Epic 6 / the integration suite in Epic 19. This keeps Epic 3 unit-only per its acceptance criteria.
  - **Exports** added to `linkshrink_shared.__init__`: `ShortCodeGenerator`, `ShortCodeCollisionError`, `generate_unique_short_code`, `fetch_next_sequence_value`, `default_short_code_generator`, `SHORT_CODE_ALPHABET`, `SHORT_CODE_MIN_LENGTH`, `DEFAULT_MAX_ATTEMPTS`.
  - **Tests** in `tests/test_shortcode.py` (next to the existing tests, per repo convention — no `packages/shared/tests/`): determinism, decode round-trip, alias-grammar match, no-uppercase/no-hyphen, min-length padding for small `n`, salt-affects-output, invalid/empty decode → `None`, `encode` rejects non-positive, empty-salt rejection (constructor + env factory via `monkeypatch`), and three retry-loop cases (advances on conflict and uses the *next* sequence value; gives up after **exactly** `max_attempts` calls; succeeds on the last allowed attempt). All async tests use injected callables — no DB.
  - **Verified:** `ruff check .` exit 0 ✓; `pytest` 16 passed (smoke + 3 migration tests against a real PG container + 12 shortcode unit tests) ✓; REPL spot-check with `HASHIDS_SALT=changeme` → `encode(1) == "e53ml3"` (6 chars, `[a-z0-9]`, `decode` → 1) ✓.

## Epic 4 — URL & alias validation + reserved words (shared)
- **Intent:** Creation-time validation guards (scheme, length, SSRF, self-reference) and the reserved-word list, with the drift-prevention coverage test.
- **Scope:** `shared/validation.py` — URL parse + scheme ∈ {http,https}, length ≤ 2048, reject self-referential public host, DNS-resolve + reject private/loopback/link-local IPs (§5.5); alias normalize-to-lowercase + grammar `[a-z0-9-]` 3–32 no leading/trailing hyphen; reserved-word list (§5.4); helper exposing `proxy_served_paths` for the superset assertion.
- **Verification:** Unit tests for each reject/accept case (valid http(s), over-length, `javascript:`, private-IP host, self-host, good/bad aliases); reserved-word coverage test asserts `reserved_words ⊇ proxy_served_paths` (containment, not equality, per §5.10).
- **Depends on:** Epic 1.

## Epic 5 — Config + Redis cache/queue helpers (shared)
- **Intent:** Centralize env-driven config and the Redis key conventions (cache, negative cache, stream, rate-limit, metrics, heartbeat) so services agree on keys.
- **Scope:** `shared/config.py` (pydantic-settings, env-driven); `shared/cache.py` (cache-aside get/set helpers, `redirect:{code}` keys, negative sentinel `__404__`, TTL capping helper `min(86400, seconds_until_expires_at)`, metrics `INCR` helpers, **rate-limit key helpers** — `ratelimit:min:{ip}`/`ratelimit:day:{ip}` with fixed-window `INCR`-and-`EXPIRE`-on-first-hit per §5.9, owned here so the API in Epic 6 only consumes them); `shared/queue.py` (Streams `XADD`/`XREADGROUP`/`XACK`/`XAUTOCLAIM` wrappers, group/consumer naming, heartbeat key, **the authoritative click-event payload schema + (de)serializer** — `{link_id, ts, referrer, ua, source}` per §5.6 — so the redirect producer (Epic 11) and worker consumer (Epic 12) agree on one contract and can be built in parallel).
- **Verification:** Unit/integration tests (Testcontainers Redis): set→get round-trip, negative sentinel handling, TTL cap math, rate-limit key `INCR`/`EXPIRE` and over-limit detection, click payload serialize→deserialize round-trip, `XADD`→`XREADGROUP`→`XACK` cycle, metrics `INCR` reads back.
- **Depends on:** Epic 1.

## Epic 6 — API: create endpoint + rate limiting
- **Intent:** The core `POST /api/links` flow — the first user-visible backend behavior.
- **Scope:** `services/api/` FastAPI app; `POST /api/links` (§5.8, §5.12): rate-limit check (fixed-window 10/min + 100/day, §5.9, trusting only the app-controlled real-IP header), URL/alias validation, alias-vs-generated branch (reserved/taken → 409, generated via shortcode with retry), `ttl_seconds` clamp [3600, 2592000] default 2592000, insert, `201` response `{ short_code, short_url, original_url, created_at, expires_at, qr_url }`; status codes 201/400/409/429 with `Retry-After`.
- **Verification:** Integration tests (Testcontainers PG+Redis): create returns 201 with correct shape; invalid URL → 400; reserved/taken alias → 409; exceeding minute or day window → 429 with `Retry-After`; `ttl_seconds` clamping at both bounds.
- **Depends on:** Epics 2, 3, 4, 5.
- **Note (minor):** the 201 response includes a `qr_url` string pointing at the QR endpoint that does not exist until Epic 9. This is only a constructed URL (no code dependency), but the returned link will not resolve until Epic 9 ships. Rate limiting consumes the rate-limit helper added to Epic 5.

## Epic 7 — API: dashboard listing + link detail
- **Intent:** Public read endpoints for the dashboard feed and single-link lookup.
- **Scope:** `GET /api/links?cursor=&limit=` keyset pagination on `(created_at DESC, id DESC)` with opaque base64 cursor, `limit` default 20 clamped to 100, response `{ items, next_cursor }` (§5.8); `GET /api/links/{code}` detail → 200/404.
- **Verification:** Integration tests: newest-first ordering, cursor paging across multiple pages is stable under inserts, `limit` clamp at 100, malformed cursor handled, unknown code → 404.
- **Depends on:** Epic 6.

## Epic 8 — API: per-link analytics aggregation
- **Intent:** Server-side aggregated analytics for a link.
- **Scope:** `GET /api/links/{code}/analytics` → 200/404 (§5.8): total clicks, daily buckets via `date_trunc('day', clicked_at)` at UTC (§7 decided), breakdowns by device_type / browser_family / os_family / referrer_domain / source.
- **Verification:** Integration tests: seed `click_events`, assert totals, UTC daily bucketing, and each breakdown grouping; unknown code → 404; empty link returns zeroed structure.
- **Depends on:** Epic 6 (reads `click_events` written later by the worker; tests seed rows directly).

## Epic 9 — API: QR generation
- **Intent:** On-demand QR images for short links.
- **Scope:** `GET /api/links/{code}/qr?format=png|svg` → 200/404 (§5.8): PNG default 512px ECC=M, SVG option; not stored; encodes the short URL with `?source=qr` attribution.
- **Verification:** Integration tests: PNG returns `image/png` ~512px, SVG returns `image/svg+xml`, encoded payload includes `?source=qr`, unknown code → 404.
- **Depends on:** Epic 6.

## Epic 10 — API: metrics + health
- **Intent:** Live operational metrics for the UI and an HTTP health check.
- **Scope:** `GET /api/metrics` → JSON derived live numbers (cache hit ratio from `metrics:cache:hit`/`:miss`, queue depth via `XLEN`/PEL, total redirects / throughput) per §5.7; `GET /health` → 200.
- **Verification:** Integration tests: seed Redis counters/stream, assert computed hit ratio and queue depth; `/health` returns 200.
- **Depends on:** Epics 5, 6.
- **Note (minor):** the `metrics:cache:hit`/`:miss`/`metrics:redirects:total` counters are written by the redirect service (Epic 11). The dependency list (5, 6) is correct for building and testing this endpoint (tests seed the counters directly, same pattern as Epic 8), but the live numbers are only meaningful once Epic 11 is producing traffic.

## Epic 11 — Redirect service
- **Intent:** The minimal hot-path redirect with cache-aside, negative caching, and best-effort click emission.
- **Scope:** `services/redirect/` FastAPI app; `GET /{code}` (§5.6): Redis HIT → 302 (no expiry check, correctness via capped TTL); NEG-HIT → 404; MISS → DB lookup `lower(short_code)`, positive cache with `EX min(86400, seconds_until_expires_at)` or negative `__404__` EX 60; `XADD` click payload (best-effort, swallow+log failures, never blocks 302); cache key ignores query string; `?source=qr`→source field; metrics `INCR` counters; `/health`.
- **Verification:** Integration tests: known code → 302 to target + click queued; cache hit serves without DB; **expired code does not 302 even on a warm path** (explicit AC, §5.6); unknown → 404 with negative cache; analytics failure still returns 302.
- **Depends on:** Epics 2, 5. (The redirect path is a pure string lookup `lower(short_code)=:code` — it never decodes hashids — so the short-code generator from Epic 3 is not needed. The click payload it `XADD`s uses the shared schema from Epic 5.)

## Epic 12 — Worker: analytics consumer
- **Intent:** Durable at-least-once consumption that derives PII-free fields and survives crashes.
- **Scope:** `services/worker/` asyncio consumer group `analytics` (§5.7): `XREADGROUP` loop, UA parse → device/browser/OS, Referer → host only, insert `ClickEvent`, `XACK`; `XAUTOCLAIM` recovery of idle entries; DLQ to `clicks:dead` + `XACK` after 3 attempts; `MAXLEN ~` trim; heartbeat `metrics:worker:heartbeat` each loop with 15 s health threshold (§5.2); healthcheck script.
- **Verification:** Integration tests (Testcontainers): `XADD` → row appears with derived coarse fields and no raw UA/IP; kill/restart mid-stream → pending entries reclaimed; poison message dead-lettered after 3 tries; heartbeat key updates.
- **Depends on:** Epics 2, 5. The worker consumes the **click-event payload schema defined in Epic 5** (`shared/queue.py`), not the redirect service itself — its tests `XADD` directly — so it can be built in parallel with Epic 11. Epic 11 is only a runtime/integration prerequisite (it is the real producer of the stream), exercised together in Epic 19.

## Epic 13 — Worker: scheduled purge job
- **Intent:** Permanent deletion 3 months after expiry, on a background interval.
- **Scope:** `asyncio` background task on a fixed interval (§5.2, §5.12): `DELETE FROM links WHERE expires_at < now() - interval '3 months'` (cascades to `click_events`); runs alongside the consumer loop.
- **Verification:** Integration test: seed an expired-3-months link with clicks → purge deletes both link and cascaded events; a recently-expired link is retained (still 404s via redirect but row stays).
- **Depends on:** Epic 12.
- **Note (recommended — resolves a TDD inconsistency):** §9.6 lists "neg-cache cleanup" as worker scope, but §5.2 establishes that **no cache-cleanup job is needed** — the positive cache TTL is capped at `min(86400, seconds_until_expires_at)` so a `302` entry can never outlive its link, and negative entries self-expire at 60 s. The TTL caps are sufficient; this epic is deliberately purge-only. Do not add a sweep job back in (a reviewer should not treat its absence as an omission).

## Epic 14 — Frontend: scaffold, theme, layout, API client, demo banner
- **Intent:** Vite React SPA foundation with the design system, routing shell, and the required public-demo warning.
- **Scope:** `frontend/` Vite + React; dark-only theme per UI/UX guide (palette, Inter, 1200px max width, card layout, mobile single-column + collapsible nav); app shell + client-side routes (`/`, `/dashboard`, `/how-it-works`); typed API client for `/api/*`; persistent public-demo warning banner + landing-page "do not shorten private/sensitive links" notice (§5.10, hard AC); CLAUDE.md compliance (unique `id` on every element, small components, descriptive naming, boolean prefixes).
- **Verification:** `npm run build` succeeds; app renders shell, nav, and the demo/visibility warning; routes navigate client-side; manual check that every rendered element carries a unique `id`.
- **Depends on:** Epic 1.
- **Note (minor — sizing):** this is one of the heavier epics (scaffold + theme + layout + API client + banner). It is cohesive enough to ship as one commit, but if it grows during implementation it is a fair candidate to split (e.g. scaffold+theme+layout vs. typed API client + demo/visibility warning).

## Epic 15 — Frontend: Home (shorten → result card)
- **Intent:** The primary paste → shorten → copy → QR flow.
- **Scope:** Home page URL input as primary focus; submit → `POST /api/links`; result card with short URL, copy button (green success), QR download (PNG/SVG via `/qr`); inline validation/error states (400/409/429 surfaced clearly); small focused components per CLAUDE.md.
- **Verification:** Manual: paste a URL → get short link, copy works, QR downloads; error cases (bad URL, taken alias, rate limited) show clear messages. Against the running API stack.
- **Depends on:** Epics 6, 9, 14.

## Epic 16 — Frontend: Dashboard + analytics views
- **Intent:** Public paginated link list and per-link analytics rendering.
- **Scope:** Dashboard page consuming `GET /api/links` with cursor paging (newest-first, "load more"/next-cursor); per-link analytics view consuming `/analytics` (totals, daily chart, breakdowns); per-link QR download; no edit/delete (§3); unique `id`s, small components.
- **Verification:** Manual: dashboard lists newest-first and pages via cursor; opening a link shows analytics charts/breakdowns; QR downloadable. Against the running stack.
- **Depends on:** Epics 7, 8, 9, 14.

## Epic 17 — Frontend: How It Works + Educational Mode + badges
- **Intent:** The portfolio/educational narrative layer.
- **Scope:** Static How-It-Works page (architecture annotations, tech badges, scaling story); Educational Mode client-side toggle surfacing annotations; live numbers only from `/api/metrics` (§5.10, §14); static content in React, unique `id`s, small components.
- **Verification:** Manual: How-It-Works renders; Educational Mode toggles annotations on/off; live metrics numbers populate from `/api/metrics`.
- **Depends on:** Epics 10, 14.

## Epic 18a — Infra: Compose core (data stores, services, migration init, health)
- **Intent:** Bring up the backend half of the stack — data stores, the three Python services, the migration init step, and health checks — on an internal network, without the proxy yet. Reviewable on its own.
- **Scope:** `infra/docker-compose.yml` for `postgres`, `redis` (AOF), `api`, `redirect`, `worker`; service Dockerfiles built on the Epic 1 base image with the shared package installed editable into each; named volumes for Postgres data and Redis AOF; per-service health checks (HTTP `/health` for api/redirect, worker heartbeat script checking `metrics:worker:heartbeat` staleness ≤ 15 s per §5.2); Alembic one-shot migration init that runs and completes before the services accept traffic; **bind `api`/`redirect`/`worker` to an internal Docker network only** so they are unreachable except through the proxy added in 18b (defense-in-depth for the trusted-IP-header model, §5.9/§7).
- **Verification:** `docker compose up` (this subset) → postgres + redis + api + redirect + worker all reach healthy; migration init applies the schema before services start serving; api/redirect answer `/health` on the internal network; worker heartbeat health check passes and flaps to unhealthy if the worker is stopped; the three services are **not** reachable from outside the Docker network.
- **Depends on:** Epics 2, 6–13 (containerizes the API, redirect, and worker services + the migration).

## Epic 18b — Infra: Nginx proxy, frontend build, TLS, routing
- **Intent:** Wire the public edge — Nginx routing precedence, the static frontend build, TLS, and the trusted real-IP header — completing the one-command full-system bring-up.
- **Scope:** `infra/nginx/` config with routing precedence blocks 1–5 (§5.10: `/api/*`→API, `/health` & `/api/metrics`, static assets, SPA routes serve `index.html`, fallback `/{code}`→redirect), `real_ip` module (`set_real_ip_from` trusted hop + `real_ip_recursive on`) passing the single app-controlled IP header the API trusts (§5.9), TLS termination (self-signed/HTTP local, Let's Encrypt/certbot prod); add `frontend-build` (produces the static assets) and `nginx` services to the compose file from 18a; mount the built assets into Nginx. **Reserved-word anti-drift:** add a scope note/checklist tying the Nginx served-path blocks (1–4) to `proxy_served_paths` in `shared/validation.py` — whenever a served path is added/changed in this config, the helper list must be updated so the Epic 4 coverage test (`reserved_words ⊇ proxy_served_paths`) keeps protecting against drift (the test compares against the helper, not the live config, §5.10/§7).
- **Verification:** `docker compose up` (full stack) → all services healthy, migrations applied; create via UI/API resolves via 302; nginx routes SPA refresh on `/dashboard` to `index.html` and bare `/{code}` to redirect (§8.1–8.2); `/api/*` reaches the API and the client IP seen by the rate limiter is the real client IP from the trusted header, not a spoofable raw `X-Forwarded-For`.
- **Depends on:** Epic 18a; Epics 14–17 (serves the built SPA). Composes the full system; can be staged but the green run needs the services it routes to.

## Epic 19 — Integration & system tests (Testcontainers)
- **Intent:** End-to-end confidence across the real PG/Redis behaviors the design depends on.
- **Scope:** pytest + Testcontainers suite (§9.9): create→redirect→analytics happy path, rate-limit 429, expiry/404 (including the cache-hit expiry AC), purge, queue recovery/DLQ, reserved-word coverage; consolidate/round out per-epic tests into a system-level suite.
- **Verification:** Full suite passes against real PG + Redis containers in CI/local.
- **Depends on:** Epics 11, 12, 13 (and the API epics they exercise).

## Epic 20 — Observability & docs + load test
- **Intent:** Finalize the metrics story, run instructions, and prove the latency budget.
- **Scope:** `/api/metrics` JSON shape finalized (cache hit ratio, queue depth, total redirects/throughput); README run instructions (local + VM, TLS differences); load test confirming **< 50 ms p95 cache-hit** measured server-side at Nginx via `$request_time` (§9.10); document known limitations (DNS rebinding, public abuse) from §7.
- **Verification:** README reproduces a clean bring-up; load test report shows p95 < 50 ms on cache hits measured at Nginx; metrics endpoint values match observed traffic.
- **Depends on:** Epics 10, 11, 18b (the load test measures p95 at Nginx via `$request_time`, so it needs the proxy from 18b in place).

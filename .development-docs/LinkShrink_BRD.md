# LinkShrink --- Business Requirements Document

## 1. Overview

LinkShrink is a lightweight URL shortener and QR code generator designed
as a portfolio project to demonstrate full-stack development, system
design, scalability thinking, and practical deployment using Docker on a
single VM.

The system should feel simple to users but expose thoughtful engineering
choices behind the scenes: redirect performance, analytics collection,
rate limiting, caching, background processing, and clean service
boundaries.

## 2. Goals

-   Allow users to shorten long URLs into compact shareable links.
-   Generate QR codes for shortened links.
-   Track basic analytics for each link.
-   Demonstrate scalable architecture patterns.
-   Allow for custom links.
-   Keep the system simple enough to build, explain, and demo clearly.

### Non-Goals

-   No user accounts, authentication, or per-user ownership.
-   No editing or deleting links from the public UI.
-   No custom domains or branded links.
-   No AWS-managed or other cloud-managed services.

### Constraints

-   Runs locally or on a single VM using Docker Compose.
-   Production is deployed on a single AWS VM (EC2-style instance). "No
    cloud-managed services" means no managed data stores (e.g. RDS,
    ElastiCache); the only AWS services used are the raw VM (compute) and
    Route 53 (DNS for link-shrink.org). All application dependencies
    remain self-hosted in containers.
-   Self-hosted dependencies only (PostgreSQL, Redis).
-   Public short-link domain: **link-shrink.org**.

## 3. Core Features

### URL Shortening

-   User submits a long URL.
-   **Short-code generation:** each link is assigned a monotonically
    increasing integer from a PostgreSQL sequence, which is then encoded
    into a short code using hashids (configured with a project salt, a
    custom alphabet, and a minimum length, e.g. 6 characters). The
    integer→code mapping is deterministic, so generated codes are unique
    by construction. Note: hashids obfuscates the sequence order, it is
    **not** encryption — short codes are not secrets.
-   **Single namespace:** generated codes and custom aliases live in one
    namespace backed by a single unique `short_code` column.
    -   A custom alias is rejected if it is already taken **or** if it
        matches a reserved path. The TDD should maintain an explicit
        reserved-word list covering application routes (e.g. `/api`,
        `/dashboard`, `/how-it-works`, `/health`, `/metrics`, static
        asset paths).
    -   In the rare case a freshly generated code equals an existing
        custom alias, the generator advances to the next sequence value
        and re-encodes until the code is free.
-   Optional custom aliases; rejected with an error if already taken or
    reserved.
    -   **Alias rules:** custom aliases accept lowercase letters, digits,
        and hyphens only (`[a-z0-9-]`), must be 3–32 characters, and may
        not start or end with a hyphen.
    -   **Case sensitivity:** short codes are matched
        **case-insensitively** and stored normalized to lowercase. The
        hashids alphabet is therefore restricted to a single case so that
        generated codes and custom aliases share one consistent,
        case-insensitive namespace.
-   **Expiration:** default and **maximum** lifetime is 30 days from
    creation. Users may choose a shorter expiration but not a longer one.
    Accessing an expired (or unknown) short code returns **HTTP 404**.
-   **Purge:** a background job permanently deletes links (and their
    associated click events) **3 months after they expire**, keeping the
    dataset bounded. Between expiration and purge the code is unusable
    (returns 404) but its `short_code` remains reserved so it cannot be
    silently reassigned.

### Redirect Service

-   Fast redirects, returned as **HTTP 302 (Found)**. A temporary
    redirect is used deliberately so browsers and intermediaries do not
    cache the resolution — every visit re-hits the redirect service,
    which is what allows per-click analytics to be collected.
-   Async analytics collection.

### QR Code Generation

-   Generate QR codes on demand from the short link (not stored).
-   QR codes encode the short URL with a `?source=qr` parameter so scans
    are attributed separately from direct clicks in analytics.
-   Download QR codes as an image. (Image format, size, and error-correction
    level are to be determined in the TDD.)

### Analytics

Analytics are stored as coarse, derived buckets only — no raw,
per-visitor identifiers — so there is no personally identifiable
information to protect:

-   Click counts
-   Referrer **domain** only (host, never the full URL or query string)
-   Device / browser / OS **category**, derived from the user agent at
    processing time (the raw user agent is not stored)
-   Traffic source (direct vs. QR scan)
-   Click history (timestamps)
-   No IP addresses are ever stored; client IPs are used only
    transiently, in memory, for rate limiting.

### Dashboard

The application is fully user-agnostic --- no accounts, logins, or
ownership. A single public dashboard, viewable by anyone, can:

-   Browse all shortened links, **paginated** and sorted by creation time
    (newest first) by default. Because creation is public and
    unauthenticated, the link set is unbounded, so the dashboard never
    loads all links at once.
-   View analytics for any link
-   Download QR codes

Anyone can create links and view the dashboard, which keeps the project
frictionless to demo. Destructive actions (editing or deleting links)
are disabled in the public UI to protect the live demo; links instead
expire automatically.

**Demo warning:** because every shortened link and its original URL is
publicly visible on the dashboard, the main page must display a clear,
persistent notice that this is a public demo / portfolio project and
that **no private, sensitive, or confidential URLs should be
shortened**.

### HTTP Status Codes

| Code | Used when |
|---|---|
| `200 OK` | Successful read (dashboard, analytics, QR retrieval). |
| `201 Created` | Link successfully created. |
| `302 Found` | Short code resolved; redirect to the original URL. |
| `400 Bad Request` | Invalid submission — disallowed URL scheme, URL exceeds max length, target resolves to a private/loopback/link-local range, self-referential link, or a custom alias that violates the alias rules. |
| `404 Not Found` | Unknown or expired short code. |
| `409 Conflict` | Custom alias is already taken or reserved. |
| `429 Too Many Requests` | Link-creation rate limit exceeded. |

## 4. Non-Functional Requirements

### Performance

-   Redirects served in under 50 ms (p95) **server-side** on a cache
    hit — measured at the reverse proxy as the time from receiving the
    request to sending the response, excluding client↔server network
    transit.
-   Frequently accessed links cached in Redis (24-hour TTL)
-   Analytics written asynchronously, never blocking the redirect

### Scalability

-   Stateless services
-   Database indexing
-   Redis caching
-   Background workers
-   Containerized deployment

### Reliability

-   Redirects function even if analytics fail
-   Graceful handling of invalid links

### Security

-   **URL validation:** accept only `http://` and `https://` schemes
    (reject `javascript:`, `data:`, `file:`, etc.); enforce a maximum URL
    length (e.g. 2048 characters); reject targets that resolve to
    private / loopback / link-local IP ranges as defense-in-depth; and
    reject URLs that point back at `link-shrink.org` to prevent redirect
    loops. (Reputation / malware checking via an external service such as
    Google Safe Browsing is out of scope to preserve the
    no-external-services constraint, but is noted as a future
    enhancement.)
-   **Rate limiting:** IP-based rate limiting on link creation, enforced
    in Redis — e.g. 10 link creations per minute and 100 per day per
    client IP, returning **HTTP 429** when exceeded. (Final thresholds to
    be confirmed in the TDD.) Rate limiting applies to link **creation**
    only; redirects are intentionally unthrottled since they are served
    from the Redis cache.
-   No authentication or user data stored (nothing to breach)
-   Secure configuration management — secrets (hashids salt, PostgreSQL
    and Redis credentials) provided via environment variables, never
    committed to source control.

## 5. Proposed Architecture

### Services

-   Frontend (React)
-   API Service
-   Redirect Service
-   Worker Service
-   PostgreSQL
-   Redis (caching + Streams for the analytics queue)
-   Nginx / Caddy (reverse proxy)

## 6. Data Model

### Links

-   id
-   short_code (unique; holds the generated code or the custom alias —
    single namespace)
-   original_url
-   is_custom (whether `short_code` was user-supplied)
-   created_at
-   expires_at

The system is user-agnostic: links have no owner, and no Users table
exists.

### Click Events

-   id
-   link_id
-   clicked_at
-   referrer_domain (host only)
-   device_type (desktop / mobile / tablet / unknown)
-   browser_family
-   os_family
-   source (direct / qr)

No raw user agent or IP address is stored.

## 7. Deployment Requirements

-   Docker Compose
-   Single AWS VM deployment (EC2-style instance)
-   Domain `link-shrink.org` pointed at the VM, with HTTPS/TLS
    terminated at the reverse proxy
-   Persistent volumes
-   Reverse proxy
-   Health checks

## 8. Success Criteria

-   A user can create a short link and be redirected to the original URL.
-   Redirects return the correct target in under 50 ms (p95) server-side on a cache hit.
-   A click is recorded in analytics within 1 second, without slowing the
    redirect.
-   QR codes generate and download correctly.
-   The dashboard displays all links and their analytics.
-   Exceeding the link-creation rate limit returns HTTP 429.
-   Accessing an expired or unknown short code returns HTTP 404.
-   The system runs end-to-end via a single `docker compose up`.

## 9. Portfolio Demonstration Requirements

### Educational Mode

The application should include an optional Educational Mode that exposes
architectural and implementation details to visitors.

### Architecture Annotations

Provide contextual explanations for:

-   Redirect flow
-   Cache strategy
-   Analytics pipeline
-   Rate limiting
-   QR generation
-   Database indexing

### Technology Badges

Optional badges may appear throughout the application:

-   PostgreSQL
-   Redis
-   Docker
-   Async Processing
-   Event Queue
-   Rate Limiting
-   Caching
-   Analytics Pipeline

Each badge should explain why the technology was selected and what
problem it solves.

### How It Works Page

Include a dedicated page covering:

#### System Architecture

The API service (create links, dashboard) and the redirect service
(resolve short codes) are independent entry points behind the proxy:

    Reverse Proxy ─┬─→ API Service ──────┬─→ PostgreSQL
                   │                     │
                   └─→ Redirect Service ─┴─→ Redis (cache + analytics queue)

    The API Service reads PostgreSQL (links, analytics) and Redis (cache
    invalidation, live operational metrics such as cache hit ratio and
    queue depth). The Redirect Service reads Redis (cache) and PostgreSQL
    (cache misses) and writes click events onto the Redis analytics
    queue. The Worker Service (not shown) consumes that queue and writes
    derived analytics to PostgreSQL.

#### Redirect Flow

User → Reverse Proxy → Redirect Service → Cache → Database

#### Analytics Flow

Redirect → Queue → Worker → Database

#### Scaling Strategy

Explain how the system could evolve from a single VM to:

-   Multiple redirect instances
-   Dedicated worker pools
-   Distributed caching
-   Container orchestration

### Live Operational Metrics

Optionally expose:

-   Cache hit ratio
-   Queue depth
-   Redirect latency
-   Redirect throughput

### Demonstration Goal

Visitors should understand:

-   What the application does
-   How the application works
-   Why architectural decisions were made
-   How the system could scale

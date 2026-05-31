# LinkShrink

A public, account-less URL shortener and QR-code generator built as a portfolio
piece to showcase production-grade architecture on a single VM. A React (Vite)
SPA sits behind an Nginx reverse proxy in front of three Python/FastAPI services
— **API** (create, dashboard, analytics, metrics, QR), **Redirect** (fast cached
`302` resolution), and **Worker** (consumes a Redis Stream and writes derived,
PII-free analytics to PostgreSQL). Redis backs both the redirect cache and the
analytics queue. The whole system comes up with a single `docker compose up`.

See [.development-docs/LinkShrink_TDD.md](.development-docs/LinkShrink_TDD.md) for
the full technical design and [.development-docs/LinkShrink_Epic_Plan.md](.development-docs/LinkShrink_Epic_Plan.md)
for the delivery plan.

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
│   └── docker/                  # base image(s) for the Python services
├── pyproject.toml               # tooling config (ruff, pytest)
└── requirements-dev.txt         # dev / tooling dependencies
```

The shared package is installed (editable) into each service image so all three
services import `linkshrink_shared`. Alembic owns the schema; services never
auto-create tables.

## Development setup

Requires **Python 3.12**.

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# macOS/Linux:          source .venv/bin/activate

pip install -e packages/shared
pip install -e services/api
pip install -e services/redirect
pip install -r requirements-dev.txt

ruff check .     # lint
pytest           # tests
```

## Running the stack

The containerized full stack (`docker compose up` — Postgres, Redis, the three
services, the frontend build, and Nginx) is wired up in later epics (18a/18b).
The common Python base image can be built today from the repo root:

```bash
docker build -f infra/docker/python-base.Dockerfile -t linkshrink-base .
```

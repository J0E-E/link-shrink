"""Epic 6/7 — integration tests for the ``/api/links`` endpoints against real PG + Redis.

Spins up throwaway Postgres and Redis via Testcontainers, applies the Alembic
migration, and drives the FastAPI app through an in-process ASGI transport with the
dependencies overridden to point at the containers (and a fake DNS resolver, so no
real network is touched). If Docker is unavailable the whole module skips, matching
the clean-run expectation from Epics 2/5.

Covers the create ACs (Epic 6): 201 shape, 400 (bad URL/scheme/length/private-IP/bad
alias), 409 (reserved + taken alias), 429 with ``Retry-After`` (minute and day
windows), and ``ttl_seconds`` clamping at both bounds; and the read ACs (Epic 7):
newest-first listing, cursor paging stable under inserts, ``limit`` clamp at 100,
malformed cursor → 400, and link detail 200/404.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_api.dependencies import (
    get_db_session,
    get_host_resolver,
    get_redis,
    get_settings_dependency,
)
from linkshrink_api.main import create_app
from linkshrink_shared import (
    RATE_LIMIT_PER_DAY,
    ClickEvent,
    DeviceType,
    Link,
    Settings,
    Source,
    ratelimit_day_key,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PUBLIC_HOST = "link-shrink.org"
PUBLIC_IP = "93.184.216.34"  # a public address the fake resolver returns
PRIVATE_IP = "10.0.0.1"


# --- Container + schema fixtures (mirror tests/test_migrations.py & test_cache.py) ---


@pytest.fixture(scope="module")
def database_url() -> str:
    """Start a throwaway Postgres and yield an asyncpg URL; skip if Docker is absent."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError as error:  # pragma: no cover - dev dependency missing
        pytest.skip(f"testcontainers not installed: {error}")

    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as error:  # pragma: no cover - Docker unavailable
        pytest.skip(f"Docker/Postgres container unavailable: {error}")

    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield (
            f"postgresql+asyncpg://{container.username}:{container.password}"
            f"@{host}:{port}/{container.dbname}"
        )
    finally:
        container.stop()


@pytest.fixture(scope="module")
def redis_url() -> str:
    """Start a throwaway Redis and yield its URL; skip if Docker is absent."""
    try:
        from testcontainers.redis import RedisContainer
    except ImportError as error:  # pragma: no cover - dev dependency missing
        pytest.skip(f"testcontainers not installed: {error}")

    try:
        container = RedisContainer("redis:7-alpine")
        container.start()
    except Exception as error:  # pragma: no cover - Docker unavailable
        pytest.skip(f"Docker/Redis container unavailable: {error}")

    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}"
    finally:
        container.stop()


@pytest.fixture(scope="module")
def alembic_config(database_url: str):
    """An Alembic Config pointed at the throwaway container."""
    from alembic.config import Config

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def schema_at_head(alembic_config, database_url: str) -> str:
    """Reset to an empty DB then migrate to head, so each test starts clean."""
    from alembic import command

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    return database_url


# --- App + client fixtures ---------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory(schema_at_head: str):
    """A session factory bound to a fresh engine over the migrated container DB."""
    engine = create_async_engine(schema_at_head)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> Redis:
    """A decoded async client against a freshly-flushed DB, closed after each test."""
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def resolver_holder() -> dict:
    """Mutable DNS resolver seam; defaults to resolving everything to a public IP.

    A test that needs the SSRF path swaps in a resolver returning a private address.
    """
    return {"resolver": lambda hostname: [PUBLIC_IP]}


@pytest.fixture
def test_settings() -> Settings:
    """Settings isolated from any local ``.env`` with a fixed salt and public host."""
    return Settings(
        _env_file=None, hashids_salt="integration-test-salt", public_host=PUBLIC_HOST
    )


@pytest_asyncio.fixture
async def client(session_factory, redis_client, test_settings, resolver_holder):
    """An async HTTP client driving the app with container-backed dependencies."""
    app = create_app()

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_settings_dependency] = lambda: test_settings
    app.dependency_overrides[get_host_resolver] = lambda: resolver_holder["resolver"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def _create(client: AsyncClient, ip: str = "203.0.113.1", **body) -> object:
    """POST /api/links as a given client IP (via the trusted X-Real-IP header)."""
    return await client.post("/api/links", json=body, headers={"X-Real-IP": ip})


# --- Tests -------------------------------------------------------------------------


async def test_create_returns_201_with_expected_shape(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com/some/page")
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {
        "short_code",
        "short_url",
        "original_url",
        "created_at",
        "expires_at",
        "qr_url",
    }
    code = data["short_code"]
    assert len(code) >= 6
    assert data["original_url"] == "https://example.com/some/page"
    assert data["short_url"] == f"https://{PUBLIC_HOST}/{code}"
    assert data["qr_url"] == f"https://{PUBLIC_HOST}/api/links/{code}/qr"


async def test_create_with_custom_alias(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="My-Custom-Link")
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "my-custom-link"  # normalized to lowercase
    assert data["short_url"] == f"https://{PUBLIC_HOST}/my-custom-link"


async def test_invalid_scheme_returns_400(client: AsyncClient) -> None:
    response = await _create(client, url="javascript:alert(1)")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_scheme"


async def test_over_length_url_returns_400(client: AsyncClient) -> None:
    long_url = "https://example.com/" + "a" * 2048
    response = await _create(client, url=long_url)
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_length"


async def test_private_address_returns_400(
    client: AsyncClient, resolver_holder: dict
) -> None:
    resolver_holder["resolver"] = lambda hostname: [PRIVATE_IP]
    response = await _create(client, url="http://internal.example.com")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "url_private_address"


async def test_reserved_alias_returns_409(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="api")
    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "alias_reserved"


async def test_bad_grammar_alias_returns_400(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", alias="bad_alias!")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "alias_grammar"


async def test_taken_alias_returns_409(client: AsyncClient) -> None:
    first = await _create(client, url="https://example.com", alias="taken-alias")
    assert first.status_code == 201
    second = await _create(client, url="https://example.org", alias="taken-alias")
    assert second.status_code == 409
    assert second.json()["detail"]["reason"] == "alias_taken"


async def test_ttl_clamped_to_minimum(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", ttl_seconds=1)
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 3600


async def test_ttl_clamped_to_maximum(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com", ttl_seconds=99_999_999)
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 2_592_000


async def test_ttl_defaults_to_thirty_days(client: AsyncClient) -> None:
    response = await _create(client, url="https://example.com")
    assert response.status_code == 201
    assert _lifetime_seconds(response.json()) == 2_592_000


async def test_minute_window_rate_limit_returns_429(client: AsyncClient) -> None:
    ip = "203.0.113.10"
    for _ in range(10):
        ok = await _create(client, ip=ip, url="https://example.com")
        assert ok.status_code == 201
    blocked = await _create(client, ip=ip, url="https://example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_day_window_rate_limit_returns_429(
    client: AsyncClient, redis_client: Redis
) -> None:
    ip = "203.0.113.20"
    await redis_client.set(ratelimit_day_key(ip), RATE_LIMIT_PER_DAY)
    blocked = await _create(client, ip=ip, url="https://example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def _lifetime_seconds(data: dict) -> int:
    """Whole seconds between created_at and expires_at in a create response."""
    created_at = datetime.fromisoformat(data["created_at"])
    expires_at = datetime.fromisoformat(data["expires_at"])
    return round((expires_at - created_at).total_seconds())


# --- Epic 7: read endpoints (listing + detail) -------------------------------------

#: A fixed base time so seeded ``created_at`` values (and thus ordering) are
#: deterministic. Link ``i`` is created at ``base + i seconds``, so higher ``i`` = newer.
_SEED_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

LINK_VIEW_FIELDS = {
    "short_code",
    "short_url",
    "original_url",
    "created_at",
    "expires_at",
    "qr_url",
    "is_custom",
}


async def _seed_links(
    session_factory, count: int, *, is_custom: bool = False, start: int = 0
) -> list[str]:
    """Insert ``count`` links straight into the DB and return their codes oldest→newest.

    Seeding via the ORM (not the API) deliberately departs from the create tests: it
    sidesteps the 10/min create rate limit when more than ten rows are needed and lets
    each ``created_at`` be pinned so newest-first ordering is exact and repeatable.
    """
    codes = []
    async with session_factory() as session:
        for offset in range(count):
            index = start + offset
            created_at = _SEED_BASE_TIME + timedelta(seconds=index)
            code = f"seed-{index:04d}"
            session.add(
                Link(
                    short_code=code,
                    original_url=f"https://example.com/{index}",
                    is_custom=is_custom,
                    created_at=created_at,
                    expires_at=created_at + timedelta(days=30),
                )
            )
            codes.append(code)
        await session.commit()
    return codes


async def _list(client: AsyncClient, **params) -> Response:
    """GET /api/links with optional cursor/limit query params."""
    return await client.get("/api/links", params=params)


async def test_list_returns_newest_first_with_expected_shape(
    client: AsyncClient, session_factory
) -> None:
    codes = await _seed_links(session_factory, 3)  # seed-0000 (oldest) .. seed-0002 (newest)
    response = await _list(client)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "next_cursor"}
    assert data["next_cursor"] is None  # all three fit on one page
    returned = [item["short_code"] for item in data["items"]]
    assert returned == list(reversed(codes))  # newest first
    assert set(data["items"][0]) == LINK_VIEW_FIELDS


async def test_list_defaults_to_twenty_per_page(
    client: AsyncClient, session_factory
) -> None:
    await _seed_links(session_factory, 25)
    data = (await _list(client)).json()
    assert len(data["items"]) == 20
    assert data["next_cursor"] is not None


async def test_list_limit_clamped_to_one_hundred(
    client: AsyncClient, session_factory
) -> None:
    await _seed_links(session_factory, 101)
    data = (await _list(client, limit=500)).json()
    assert len(data["items"]) == 100  # clamped despite asking for 500
    assert data["next_cursor"] is not None  # the 101st row is on the next page


async def test_cursor_paging_is_stable_under_inserts(
    client: AsyncClient, session_factory
) -> None:
    codes = await _seed_links(session_factory, 5)  # seed-0000 .. seed-0004 (newest)

    first = (await _list(client, limit=2)).json()
    assert [item["short_code"] for item in first["items"]] == ["seed-0004", "seed-0003"]
    assert first["next_cursor"] is not None

    # A newer link arrives between page requests; it sorts above the held cursor and
    # must not shift or duplicate the in-progress paging.
    await _seed_links(session_factory, 1, start=99)  # seed-0099 is the newest row now

    second = (await _list(client, limit=2, cursor=first["next_cursor"])).json()
    assert [item["short_code"] for item in second["items"]] == ["seed-0002", "seed-0001"]
    assert second["next_cursor"] is not None

    third = (await _list(client, limit=2, cursor=second["next_cursor"])).json()
    assert [item["short_code"] for item in third["items"]] == ["seed-0000"]
    assert third["next_cursor"] is None  # last page

    seen = [item["short_code"] for page in (first, second, third) for item in page["items"]]
    assert seen == codes[::-1]  # every original row once, newest→oldest, no dupes/gaps
    assert "seed-0099" not in seen  # the mid-paging insert never leaked into the run


async def test_malformed_cursor_returns_400(client: AsyncClient) -> None:
    response = await _list(client, cursor="not-a-valid-cursor!!!")
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "invalid_cursor"


async def test_cursor_with_naive_timestamp_returns_400(client: AsyncClient) -> None:
    # A crafted-but-decodable cursor whose timestamp lacks a timezone must be rejected
    # rather than slipping a naive datetime into the timestamptz comparison.
    naive_cursor = base64.urlsafe_b64encode(b"2026-01-01T00:00:00|5").decode("ascii")
    response = await _list(client, cursor=naive_cursor)
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "invalid_cursor"


async def test_get_link_detail_returns_200_with_shape(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1, is_custom=True)
    response = await client.get(f"/api/links/{code}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == LINK_VIEW_FIELDS
    assert data["short_code"] == code
    assert data["is_custom"] is True
    assert data["short_url"] == f"https://{PUBLIC_HOST}/{code}"
    assert data["qr_url"] == f"https://{PUBLIC_HOST}/api/links/{code}/qr"


async def test_get_link_detail_is_case_insensitive(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1)
    response = await client.get(f"/api/links/{code.upper()}")
    assert response.status_code == 200
    assert response.json()["short_code"] == code


async def test_get_unknown_code_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/links/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["reason"] == "not_found"


# --- Epic 8: per-link analytics aggregation ----------------------------------------

ANALYTICS_FIELDS = {
    "short_code",
    "total_clicks",
    "daily",
    "by_device_type",
    "by_browser_family",
    "by_os_family",
    "by_referrer_domain",
    "by_source",
}

#: A fixed click time used by clicks that don't care about the daily bucketing.
_CLICK_TIME = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _click(**overrides) -> dict:
    """Build a ClickEvent field dict with sane defaults; override only what a test cares about."""
    fields = {
        "clicked_at": _CLICK_TIME,
        "device_type": DeviceType.desktop,
        "source": Source.direct,
        "referrer_domain": "example.com",
        "browser_family": "Chrome",
        "os_family": "Windows",
    }
    fields.update(overrides)
    return fields


async def _seed_clicks(session_factory, code: str, clicks: list[dict]) -> None:
    """Insert ClickEvent rows for the link with ``code`` (looked up by short code)."""
    async with session_factory() as session:
        link = await session.scalar(select(Link).where(Link.short_code == code))
        for click in clicks:
            session.add(ClickEvent(link_id=link.id, **click))
        await session.commit()


async def _analytics(client: AsyncClient, code: str) -> Response:
    """GET /api/links/{code}/analytics."""
    return await client.get(f"/api/links/{code}/analytics")


async def test_analytics_unknown_code_returns_404(client: AsyncClient) -> None:
    response = await _analytics(client, "does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["reason"] == "not_found"


async def test_analytics_empty_link_returns_zeroed_structure(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1)
    response = await _analytics(client, code)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == ANALYTICS_FIELDS
    assert data["short_code"] == code
    assert data["total_clicks"] == 0
    assert data["daily"] == []
    for dimension in ("by_device_type", "by_browser_family", "by_os_family",
                      "by_referrer_domain", "by_source"):
        assert data[dimension] == []


async def test_analytics_reports_total_clicks(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [_click() for _ in range(7)])
    data = (await _analytics(client, code)).json()
    assert data["total_clicks"] == 7


async def test_analytics_daily_buckets_use_utc(
    client: AsyncClient, session_factory
) -> None:
    # Three clicks: two on the UTC day 2026-03-01 (one of them at 23:30, just before
    # UTC midnight) and one at 00:30 on 2026-03-02. UTC bucketing must split them into
    # two days; DB-local-day bucketing would group them differently.
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [
        _click(clicked_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC)),
        _click(clicked_at=datetime(2026, 3, 1, 23, 30, tzinfo=UTC)),
        _click(clicked_at=datetime(2026, 3, 2, 0, 30, tzinfo=UTC)),
    ])
    daily = (await _analytics(client, code)).json()["daily"]
    assert daily == [
        {"day": "2026-03-01", "count": 2},
        {"day": "2026-03-02", "count": 1},
    ]


async def test_analytics_breakdown_by_enum_dimensions(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [
        _click(device_type=DeviceType.mobile, source=Source.qr),
        _click(device_type=DeviceType.mobile, source=Source.direct),
        _click(device_type=DeviceType.desktop, source=Source.direct),
    ])
    data = (await _analytics(client, code)).json()
    # Ordered most-clicks-first.
    assert data["by_device_type"] == [
        {"value": "mobile", "count": 2},
        {"value": "desktop", "count": 1},
    ]
    assert data["by_source"] == [
        {"value": "direct", "count": 2},
        {"value": "qr", "count": 1},
    ]


async def test_analytics_null_dimensions_coalesce_to_unknown(
    client: AsyncClient, session_factory
) -> None:
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [
        _click(referrer_domain="example.com", browser_family="Chrome", os_family="Windows"),
        _click(referrer_domain=None, browser_family=None, os_family=None),
        _click(referrer_domain=None, browser_family=None, os_family=None),
    ])
    data = (await _analytics(client, code)).json()
    # NULLs become an "unknown" bucket, so each breakdown still sums to total_clicks (3).
    assert data["by_referrer_domain"] == [
        {"value": "unknown", "count": 2},
        {"value": "example.com", "count": 1},
    ]
    assert data["by_browser_family"] == [
        {"value": "unknown", "count": 2},
        {"value": "Chrome", "count": 1},
    ]
    assert data["by_os_family"] == [
        {"value": "unknown", "count": 2},
        {"value": "Windows", "count": 1},
    ]


async def test_analytics_breakdown_tiebreak_is_deterministic(
    client: AsyncClient, session_factory
) -> None:
    # Equal counts must order by value ascending so the response is stable.
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [
        _click(referrer_domain="zebra.example"),
        _click(referrer_domain="alpha.example"),
    ])
    by_referrer = (await _analytics(client, code)).json()["by_referrer_domain"]
    assert by_referrer == [
        {"value": "alpha.example", "count": 1},
        {"value": "zebra.example", "count": 1},
    ]


async def test_analytics_enum_breakdown_tiebreak_is_alphabetical(
    client: AsyncClient, session_factory
) -> None:
    # Enum dimensions tie-break by string value ascending too — not by the enum's
    # declaration order. "desktop" sorts before "mobile" on an equal count.
    [code] = await _seed_links(session_factory, 1)
    await _seed_clicks(session_factory, code, [
        _click(device_type=DeviceType.mobile),
        _click(device_type=DeviceType.desktop),
    ])
    by_device_type = (await _analytics(client, code)).json()["by_device_type"]
    assert by_device_type == [
        {"value": "desktop", "count": 1},
        {"value": "mobile", "count": 1},
    ]

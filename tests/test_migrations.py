"""Epic 2 — schema & migration integration tests against a real Postgres.

Uses Testcontainers to spin up a throwaway Postgres, runs the Alembic migration
against it, and verifies the acceptance criteria from the epic plan:

* `alembic upgrade head` creates the tables, the link_code_seq sequence, and all
  four indexes.
* `alembic downgrade base` then `alembic upgrade head` round-trips cleanly.
* a model insert/select sanity check passes, including the ON DELETE CASCADE FK.

If Docker is unavailable the whole module is skipped (so `pytest` still exits 0
on a Docker-less machine), matching Epic 1's clean-run expectation.

Alembic is driven from synchronous fixtures/tests because env.py runs migrations
via `asyncio.run(...)`, which cannot be called from inside a running event loop.
The data-level assertions use a fresh async engine.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from linkshrink_shared.models import ClickEvent, DeviceType, Link, Source

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_INDEXES = {
    "uq_links_lower_short_code",
    "ix_links_created_at_id_desc",
    "ix_links_expires_at",
    "ix_click_events_link_id_clicked_at",
}


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
        url = (
            f"postgresql+asyncpg://{container.username}:{container.password}"
            f"@{host}:{port}/{container.dbname}"
        )
        yield url
    finally:
        container.stop()


@pytest.fixture(scope="module")
def alembic_config(database_url: str) -> Config:
    """An Alembic Config pointed at the throwaway container."""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def schema_at_head(alembic_config: Config, database_url: str) -> str:
    """Reset to an empty DB then migrate to head, so each test starts clean."""
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    return database_url


async def _fetch_names(url: str, query: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(sa.text(query))
            return {row[0] for row in result}
    finally:
        await engine.dispose()


def test_downgrade_upgrade_roundtrip(alembic_config: Config, database_url: str) -> None:
    """upgrade head creates the schema; downgrade base clears it; upgrade head restores it."""
    import asyncio

    tables_query = (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    )

    command.upgrade(alembic_config, "head")
    tables = asyncio.run(_fetch_names(database_url, tables_query))
    assert {"links", "click_events"} <= tables

    command.downgrade(alembic_config, "base")
    tables = asyncio.run(_fetch_names(database_url, tables_query))
    assert "links" not in tables
    assert "click_events" not in tables

    command.upgrade(alembic_config, "head")
    tables = asyncio.run(_fetch_names(database_url, tables_query))
    assert {"links", "click_events"} <= tables


async def test_schema_objects_present(schema_at_head: str) -> None:
    """Tables, the sequence, and all four indexes exist after upgrade head."""
    tables = await _fetch_names(
        schema_at_head,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
    )
    assert {"links", "click_events"} <= tables

    sequences = await _fetch_names(
        schema_at_head,
        "SELECT sequence_name FROM information_schema.sequences "
        "WHERE sequence_schema = 'public'",
    )
    assert "link_code_seq" in sequences

    indexes = await _fetch_names(
        schema_at_head,
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'",
    )
    assert EXPECTED_INDEXES <= indexes


async def test_insert_select_and_cascade(schema_at_head: str) -> None:
    """A link + click round-trips, the sequence is usable, and the FK cascades on delete."""
    engine = create_async_engine(schema_at_head)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            link = Link(
                short_code="abc123",
                original_url="https://example.com/some/page",
                is_custom=False,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add(link)
            await session.commit()
            assert link.id is not None
            assert link.created_at is not None  # server default applied

            session.add(
                ClickEvent(
                    link_id=link.id,
                    referrer_domain="news.ycombinator.com",
                    device_type=DeviceType.mobile,
                    browser_family="Safari",
                    os_family="iOS",
                    source=Source.qr,
                )
            )
            await session.commit()

            stored = await session.get(Link, link.id)
            assert stored is not None
            assert stored.short_code == "abc123"

            click_count = await session.scalar(
                sa.select(sa.func.count()).select_from(ClickEvent)
            )
            assert click_count == 1

            # The standalone sequence is usable (feeds hashids in Epic 3).
            next_value = await session.scalar(sa.text("SELECT nextval('link_code_seq')"))
            assert next_value >= 1

            # Core DELETE bypasses ORM cascade, so this exercises the DB-level
            # ON DELETE CASCADE created by the migration.
            await session.execute(sa.delete(Link).where(Link.id == link.id))
            await session.commit()

            click_count = await session.scalar(
                sa.select(sa.func.count()).select_from(ClickEvent)
            )
            assert click_count == 0
    finally:
        await engine.dispose()

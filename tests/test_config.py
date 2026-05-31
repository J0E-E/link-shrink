"""Unit tests for the shared env-driven config (Epic 5). No Docker required.

Constructs :class:`Settings` with explicit init kwargs / ``_env_file=None`` so the
dev ``.env`` and the ambient environment can't make these assertions flaky.
"""

from __future__ import annotations

from redis.asyncio import Redis

from linkshrink_shared.config import Settings, get_redis_client, get_settings


def _settings(**overrides) -> Settings:
    """Build Settings isolated from the dev `.env` and ambient env (kwargs win)."""
    return Settings(_env_file=None, **overrides)


def test_database_url_is_async_postgres_url() -> None:
    settings = _settings(
        postgres_user="alice",
        postgres_password="secret",
        postgres_host="db.internal",
        postgres_port=6543,
        postgres_db="links",
    )
    assert settings.database_url == "postgresql+asyncpg://alice:secret@db.internal:6543/links"


def test_redis_url_without_password_omits_auth_segment() -> None:
    settings = _settings(redis_host="cache", redis_port=6380, redis_password="")
    assert settings.redis_url == "redis://cache:6380"


def test_redis_url_with_password_includes_auth_segment() -> None:
    settings = _settings(redis_host="cache", redis_port=6379, redis_password="hunter2")
    assert settings.redis_url == "redis://:hunter2@cache:6379"


def test_settings_read_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("HASHIDS_SALT", "from-env")
    monkeypatch.setenv("PUBLIC_HOST", "example.test")
    monkeypatch.setenv("REDIS_HOST", "redis-host")
    monkeypatch.setenv("POSTGRES_PORT", "5599")
    settings = _settings()
    assert settings.hashids_salt == "from-env"
    assert settings.public_host == "example.test"
    assert settings.redis_host == "redis-host"
    assert settings.postgres_port == 5599


def test_get_settings_returns_a_settings_instance() -> None:
    assert isinstance(get_settings(), Settings)


async def test_get_redis_client_builds_from_settings() -> None:
    settings = _settings(redis_host="cache", redis_port=6379, redis_password="")
    client = get_redis_client(settings)
    try:
        assert isinstance(client, Redis)
    finally:
        await client.aclose()

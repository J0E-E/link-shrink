"""Env-driven application config (pydantic-settings).

The one place every service reads its settings, so the API, redirect, and worker
agree on the hashids salt, Postgres/Redis connection details, and the public host
(TDD §5.1). Values come from the process environment, falling back to a repo-root
``.env`` file for local development (``.env`` is gitignored; ``.env.example`` is the
committed template). In containers, docker-compose supplies the environment directly.

Every field has a default mirroring ``.env.example`` so :class:`Settings` always
constructs — required-ness is enforced where a value is consumed (e.g.
:func:`linkshrink_shared.shortcode.default_short_code_generator` raises if the salt is
empty). Secrets default to ``""`` so a missing secret reads as empty, not as a real value.
"""

from __future__ import annotations

from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis


class Settings(BaseSettings):
    """Centralized, env-driven settings shared by all LinkShrink services.

    Field names map case-insensitively to the env vars in ``.env.example``
    (``hashids_salt`` ← ``HASHIDS_SALT``, ``postgres_user`` ← ``POSTGRES_USER``, …).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hashids_salt: str = ""
    postgres_user: str = "linkshrink"
    postgres_password: str = ""
    postgres_db: str = "linkshrink"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    public_host: str = ""

    @property
    def database_url(self) -> str:
        """The async SQLAlchemy URL (``postgresql+asyncpg://``) built from the PG fields.

        The user and password are percent-encoded so a credential containing a
        URL-reserved character (``@``, ``:``, ``/``, ``#`` …) can never produce a
        malformed DSN.
        """
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """The Redis URL; the ``:password@`` segment is omitted when no password is set.

        The password is percent-encoded so a URL-reserved character cannot produce a
        malformed URL.
        """
        auth = f":{quote(self.redis_password, safe='')}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"


def get_settings() -> Settings:
    """Build a fresh :class:`Settings` from the current environment + ``.env``.

    Deliberately uncached so it re-reads the environment each call (matching the
    direct ``os.environ`` reads it replaces). Services typically call it once at
    startup and hold the result.
    """
    return Settings()


def get_redis_client(settings: Settings | None = None) -> Redis:
    """Build an async Redis client from config, decoding responses to ``str``.

    ``decode_responses=True`` so the cache/queue helpers in this package deal in
    ``str`` rather than ``bytes``. Pass an explicit ``settings`` to reuse one already
    loaded; otherwise it is read via :func:`get_settings`.
    """
    settings = settings or get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)

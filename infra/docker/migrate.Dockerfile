# One-shot migration image (Epic 18a).
#
# Builds on the Epic 1 base image (linkshrink-base) — it already has
# linkshrink_shared (models + config) and asyncpg, which migrations/env.py needs.
# Alembic is a dev/tooling dependency, not a service runtime dependency, so it is
# installed only here. The container runs `alembic upgrade head` once and exits;
# the api/redirect/worker services wait on its successful completion before they
# start, so the schema is always applied before anything serves traffic.
#
# Build from the repo root so `COPY migrations` / `COPY alembic.ini` resolve:
#   docker build -f infra/docker/migrate.Dockerfile -t linkshrink-migrate .
FROM linkshrink-base

RUN pip install --no-cache-dir alembic

COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

CMD ["alembic", "upgrade", "head"]

# Worker service image (Epic 18a).
#
# Builds on the Epic 1 base image (linkshrink-base), which already has the
# editable linkshrink_shared package installed. We install the worker service on
# top. The worker has no HTTP surface — it runs the asyncio consumer loop until
# SIGTERM, and Docker reads liveness from the heartbeat healthcheck script.
#
# Build from the repo root so `COPY services/worker` resolves:
#   docker build -f infra/docker/worker.Dockerfile -t linkshrink-worker .
FROM linkshrink-base

COPY services/worker /app/services/worker
RUN pip install --no-cache-dir -e /app/services/worker

CMD ["python", "-m", "linkshrink_worker.main"]

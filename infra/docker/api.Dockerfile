# API service image (Epic 18a).
#
# Builds on the Epic 1 base image (linkshrink-base), which already has the
# editable linkshrink_shared package installed. We install the API service on
# top, then serve it with uvicorn.
#
# Build from the repo root so `COPY services/api` resolves:
#   docker build -f infra/docker/api.Dockerfile -t linkshrink-api .
FROM linkshrink-base

COPY services/api /app/services/api
RUN pip install --no-cache-dir -e /app/services/api

EXPOSE 8000

CMD ["uvicorn", "linkshrink_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

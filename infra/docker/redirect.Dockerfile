# Redirect service image (Epic 18a).
#
# Builds on the Epic 1 base image (linkshrink-base), which already has the
# editable linkshrink_shared package installed. We install the redirect service
# on top, then serve it with uvicorn on port 8001.
#
# Build from the repo root so `COPY services/redirect` resolves:
#   docker build -f infra/docker/redirect.Dockerfile -t linkshrink-redirect .
FROM linkshrink-base

COPY services/redirect /app/services/redirect
RUN pip install --no-cache-dir -e /app/services/redirect

EXPOSE 8001

CMD ["uvicorn", "linkshrink_redirect.main:app", "--host", "0.0.0.0", "--port", "8001"]

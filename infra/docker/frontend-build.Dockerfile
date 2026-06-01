# One-shot SPA build (Epic 18b).
#
# Compiles the React/Vite frontend and publishes the static dist/ into the
# shared frontend-dist volume the nginx service serves. Mirrors the migrate
# service: it builds at image-build time, then the CMD copies the result into
# the mounted volume at run time and exits.
#
# node_modules/ and dist/ are .dockerignored, so dependencies are installed
# inside the image (we cannot COPY the host's node_modules). This image is
# Node-based and does NOT extend linkshrink-base (that base is Python-only).
#
# Build from the repo root so `COPY frontend` resolves:
#   docker build -f infra/docker/frontend-build.Dockerfile -t linkshrink-frontend-build .
#
# ECR Public mirror of the Docker official image — avoids Docker Hub's anonymous
# pull rate limit in CI.
FROM public.ecr.aws/docker/library/node:20-slim

WORKDIR /app/frontend

# Manifests first for layer caching, then a reproducible install.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Source, then the production build (tsc -b && vite build -> /app/frontend/dist).
COPY frontend/ ./
RUN npm run build

# The build already ran above; the CMD only PUBLISHES dist/ into the mounted
# /out volume so a fresh build replaces any stale assets from a previous run.
CMD ["sh", "-c", "rm -rf /out/* && cp -r /app/frontend/dist/. /out/"]

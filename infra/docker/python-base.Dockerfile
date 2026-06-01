# Common Python base image for the api/redirect/worker services.
# The api/redirect/worker Dockerfiles (Epic 18a) build FROM this image so the
# editable linkshrink_shared package is already installed in a shared layer.
#
# Build from the repo root so `COPY packages/shared` resolves:
#   docker build -f infra/docker/python-base.Dockerfile -t linkshrink-base .
#
# Pulled from the ECR Public mirror of the Docker official image to avoid Docker
# Hub's anonymous pull rate limit in CI (CodeBuild's shared IPs hit 429s).
FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

# LinkShrink — developer bring-up targets (Epics 18a + 18b).
#
# The api/redirect/worker/migrate Dockerfiles build `FROM linkshrink-base`, so
# that shared base image must exist before the stack builds. These targets build
# it first, then drive `docker compose` against infra/docker-compose.yml. (The
# Epic 18b nginx + frontend-build services need no base image — nginx:alpine and
# a Node build image.) Run them from the repo root.

COMPOSE := docker compose -f infra/docker-compose.yml
BASE_IMAGE := linkshrink-base
BASE_DOCKERFILE := infra/docker/python-base.Dockerfile

.PHONY: base build up down logs migrate ps frontend nginx-reload certs-clean

# Build the shared Epic 1 base image the service Dockerfiles extend.
base:
	docker build -f $(BASE_DOCKERFILE) -t $(BASE_IMAGE) .

# Build the base image, then all service images.
build: base
	$(COMPOSE) build

# Build everything and start the stack in the background.
up: base
	$(COMPOSE) up --build -d

# Stop and remove the stack (keeps named volumes).
down:
	$(COMPOSE) down

# Follow logs for all services.
logs:
	$(COMPOSE) logs -f

# Run the one-shot migration on its own (normally runs automatically on `up`).
migrate: base
	$(COMPOSE) run --rm migrate

# Show service/health status.
ps:
	$(COMPOSE) ps

# Rebuild the SPA and republish it into the frontend-dist volume nginx serves.
frontend:
	$(COMPOSE) run --rm --build frontend-build

# Hot-reload nginx after editing the proxy config (no restart needed).
nginx-reload:
	$(COMPOSE) exec nginx nginx -s reload

# Drop the self-signed cert; it regenerates on the next `up`.
certs-clean:
	docker volume rm linkshrink_nginx-certs

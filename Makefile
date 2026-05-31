# LinkShrink — developer bring-up targets (Epic 18a).
#
# The service Dockerfiles build `FROM linkshrink-base`, so that shared base image
# must exist before the stack builds. These targets build it first, then drive
# `docker compose` against infra/docker-compose.yml. Run them from the repo root.

COMPOSE := docker compose -f infra/docker-compose.yml
BASE_IMAGE := linkshrink-base
BASE_DOCKERFILE := infra/docker/python-base.Dockerfile

.PHONY: base build up down logs migrate ps

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

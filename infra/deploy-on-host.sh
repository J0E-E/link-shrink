#!/usr/bin/env bash
#
# Deploy LinkShrink on the host. Run by the pipeline's Deploy stage via SSM Run
# Command (as root), or by hand in an SSM session:
#
#   bash infra/deploy-on-host.sh <commit-sha>
#
# It pins the repo to the exact deployed commit so the compose files match the
# images, renders .env from Parameter Store, then pulls and starts the stack.

set -euo pipefail

IMAGE_TAG="${1:-${IMAGE_TAG:?IMAGE_TAG (commit sha) required}}"
export IMAGE_TAG
export ECR_REGISTRY="${ECR_REGISTRY:-310199963650.dkr.ecr.us-east-1.amazonaws.com}"
AWS_REGION="us-east-1"               # root's shell has no default region — be explicit
REPO_DIR="/opt/linkshrink"
REPO_URL="https://github.com/J0E-E/link-shrink.git"

# 1. Repo is auto-managed at a fixed, root-owned path: clone if missing.
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Cloning $REPO_URL -> $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"

# Check out the EXACT deployed commit so compose files and images agree.
git fetch --all --prune
git checkout --force "$IMAGE_TAG"
git reset --hard "$IMAGE_TAG"

# 2. Render .env from Parameter Store (matches manual-deploy.md 2.3).
get() {
  aws ssm get-parameter --region "$AWS_REGION" --with-decryption \
    --name "/linkshrink/$1" --query Parameter.Value --output text
}
cat > .env <<EOF
HASHIDS_SALT=$(get HASHIDS_SALT)
POSTGRES_USER=$(get POSTGRES_USER)
POSTGRES_PASSWORD=$(get POSTGRES_PASSWORD)
POSTGRES_DB=$(get POSTGRES_DB)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
PUBLIC_HOST=link-shrink.org
WORKER_NUMBER=1
EOF
chmod 600 .env

# 3. Log in to ECR (the instance role has pull permission).
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# 4. Pull the tagged images and (re)start the stack via the prod overlay.
COMPOSE="docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml"
$COMPOSE pull
$COMPOSE up -d --remove-orphans

# 4b. Ensure a real TLS cert (issues on a fresh box, no-op once valid).
bash infra/cert.sh issue

# 5. Wait for health; fail the deploy if anything stays unhealthy.
deadline=$(( $(date +%s) + 180 ))
while :; do
  pending=$($COMPOSE ps --format '{{.Service}} {{.Health}}' | grep -E 'starting|unhealthy' || true)
  [ -z "$pending" ] && break
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "Services not healthy in time:"
    echo "$pending"
    $COMPOSE ps
    exit 1
  fi
  sleep 5
done

echo "Deploy OK at $IMAGE_TAG"

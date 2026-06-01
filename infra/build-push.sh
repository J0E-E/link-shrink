#!/usr/bin/env bash
#
# Build the LinkShrink images and push them to ECR, tagged by commit SHA.
#
# Run from the repo root with Docker running and AWS credentials available:
#   ./infra/build-push.sh                 # tag = short commit SHA
#   IMAGE_TAG=v1 ./infra/build-push.sh    # explicit tag
#
# The host then pulls these via infra/docker-compose.prod.yml. Epic 8's CodeBuild
# buildspec reuses this same script.

set -euo pipefail

ECR_REGISTRY="${ECR_REGISTRY:-310199963650.dkr.ecr.us-east-1.amazonaws.com}"
AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

# Built FROM linkshrink-base, so the base image must exist locally before them.
SERVICES=(api redirect worker migrate nginx frontend-build)

echo "Registry: $ECR_REGISTRY"
echo "Tag:      $IMAGE_TAG"

# Repos are IMMUTABLE, so re-pushing an existing tag fails. If every image for
# this tag already exists (e.g. a same-commit pipeline re-run), skip straight to
# the deploy instead of erroring.
already_pushed() {
  for service in "${SERVICES[@]}"; do
    aws ecr describe-images --region "$AWS_REGION" \
      --repository-name "linkshrink-$service" \
      --image-ids "imageTag=$IMAGE_TAG" >/dev/null 2>&1 || return 1
  done
  return 0
}

if already_pushed; then
  echo "All six images already exist at tag $IMAGE_TAG — skipping build/push."
  exit 0
fi

echo "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "Building base image (linkshrink-base)..."
docker build -f infra/docker/python-base.Dockerfile -t linkshrink-base .

for service in "${SERVICES[@]}"; do
  image="$ECR_REGISTRY/linkshrink-$service:$IMAGE_TAG"
  echo "Building and pushing $image ..."
  docker build -f "infra/docker/$service.Dockerfile" -t "$image" .
  docker push "$image"
done

echo "Done. Pushed tag: $IMAGE_TAG"
echo "Deploy on the host with:"
echo "  export ECR_REGISTRY=$ECR_REGISTRY IMAGE_TAG=$IMAGE_TAG"
echo "  docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml pull"
echo "  docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d"

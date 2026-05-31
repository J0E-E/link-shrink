# LinkShrink — Windows bring-up helper (Epic 18a).
#
# PowerShell equivalent of `make up` for hosts without `make`. Builds the shared
# Epic 1 base image the service Dockerfiles extend, then builds and starts the
# Compose core stack. Run from the repo root:  ./infra/up.ps1

$ErrorActionPreference = "Stop"

# Resolve the repo root (parent of this script's infra/ directory) and run there
# so the build contexts and repo-root .env resolve regardless of caller's cwd.
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    Write-Host "Building base image (linkshrink-base)..."
    docker build -f infra/docker/python-base.Dockerfile -t linkshrink-base .
    if ($LASTEXITCODE -ne 0) { throw "base image build failed" }

    Write-Host "Building and starting the Compose core stack..."
    docker compose -f infra/docker-compose.yml up --build -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    docker compose -f infra/docker-compose.yml ps
}
finally {
    Pop-Location
}

# LinkShrink — Windows load-test helper (Epic 20, TDD §9.10).
#
# PowerShell equivalent of `make loadtest` for hosts without `make`. Generates redirect
# cache-hit traffic, then measures the server-side p95 from Nginx's $request_time. The
# stack must already be up (./infra/up.ps1). See infra/loadtest/README.md for details.
#
# Run from the repo root:
#   ./infra/loadtest.ps1                         # creates + tests a fresh link
#   ./infra/loadtest.ps1 -Code abc123            # reuse an existing short code
#   ./infra/loadtest.ps1 -Requests 5000 -Concurrency 100

param(
    [string]$Code = "",
    [int]$Requests = 2000,
    [int]$Concurrency = 50
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $generatorArgs = @(
        "infra/loadtest/run_load_test.py",
        "--requests", $Requests,
        "--concurrency", $Concurrency
    )
    if ($Code -ne "") { $generatorArgs += @("--code", $Code) }

    python @generatorArgs
    if ($LASTEXITCODE -ne 0) { throw "load generator failed" }

    if ($Code -eq "") {
        Write-Host ""
        Write-Host "No -Code given, so a fresh link was created above. Re-run the parse step with"
        Write-Host "that printed code to measure its p95, e.g.:"
        Write-Host "  docker compose -f infra/docker-compose.yml exec -T nginx cat /var/log/nginx/access.log | python infra/loadtest/parse_nginx_p95.py --code <code>"
        return
    }

    Write-Host ""
    Write-Host "Measuring server-side p95 at Nginx for /$Code ..."
    docker compose -f infra/docker-compose.yml exec -T nginx cat /var/log/nginx/access.log | python infra/loadtest/parse_nginx_p95.py --code $Code
    if ($LASTEXITCODE -ne 0) { throw "p95 budget check failed (or no matching log lines)" }
}
finally {
    Pop-Location
}

param(
    [ValidateSet("start", "stop", "status", "logs")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dataRoot = "E:\DockerData\gpu-saas"

if ($Action -eq "start") {
    if (-not (Test-Path E:\)) { throw "E: drive is unavailable; stopping to avoid writing Docker data to C:." }
    New-Item -ItemType Directory -Force -Path "$dataRoot\postgres", "$dataRoot\redis" | Out-Null
    if (-not (Test-Path "$root\.env")) {
        $postgresPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
        $jwtSecret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
        $loginPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(12))
        @"
POSTGRES_PASSWORD=$postgresPassword
LOCAL_JWT_SECRET=$jwtSecret
LOCAL_DEV_EMAIL=student@example.com
LOCAL_DEV_PASSWORD=$loginPassword
DOCKER_DATA_ROOT=E:/DockerData/gpu-saas
"@ | Set-Content -LiteralPath "$root\.env" -Encoding utf8
        Write-Host "First local login: student@example.com / $loginPassword"
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker engine is unavailable. Start Docker Desktop and retry." }
    docker compose --project-directory $root up -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed. Run .\scripts\local-stack.ps1 logs for details." }
    Write-Host "App: http://localhost:3000"
    Write-Host "API health: http://localhost:8000/healthz"
    exit
}

if ($Action -eq "stop") {
    docker compose --project-directory $root down
} elseif ($Action -eq "status") {
    docker compose --project-directory $root ps
} else {
    docker compose --project-directory $root logs --tail 200
}

param(
    [ValidateSet("start", "stop", "status", "logs")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dataRoot = "E:\DockerData\gpu-saas"

if ($Action -eq "start") {
    if (-not (Test-Path E:\)) { throw "E: 盘不可用，已停止以避免把 Docker 数据写入 C 盘。" }
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
        Write-Host "首次本地登录：student@example.com / $loginPassword"
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker 引擎不可用。请启动 Docker Desktop 后重试。" }
    docker compose --project-directory $root up --build -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose 启动失败，请运行 .\scripts\local-stack.ps1 logs 查看证据。" }
    Write-Host "统一入口：http://localhost:3000"
    Write-Host "API 健康：http://localhost:8000/healthz"
    exit
}

if ($Action -eq "stop") {
    docker compose --project-directory $root down
} elseif ($Action -eq "status") {
    docker compose --project-directory $root ps
} else {
    docker compose --project-directory $root logs --tail 200
}

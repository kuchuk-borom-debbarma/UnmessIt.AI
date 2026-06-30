$ErrorActionPreference = "Stop"

# Change to the root directory of the project
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path "$ScriptDir\.."

Write-Host -ForegroundColor Blue "Building and starting UnmessIt.AI locally from source..."

# We use the default docker-compose.yml, which uses the local build context
docker compose up -d --build

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "    UnmessIt.AI is now running from source!   " -ForegroundColor Green
Write-Host "==============================================`n" -ForegroundColor Green

Write-Host -NoNewline "Web UI: " -ForegroundColor Blue
Write-Host "http://localhost:2831"
Write-Host -NoNewline "API:    " -ForegroundColor Blue
Write-Host "http://localhost:2317`n"

Write-Host "To stop, run: docker compose down"

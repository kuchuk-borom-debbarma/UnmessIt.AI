$ErrorActionPreference = "Stop"

# Change to the root directory of the project
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path "$ScriptDir\.."

Write-Host -ForegroundColor Blue "Building and starting UnmessIt.AI locally from source..."

# If the user previously used the installer, grab their existing .env
$EnvArgs = ""
if (Test-Path "unmessit-ai/.env") {
    Write-Host -ForegroundColor Yellow "Detected existing staging installation. Linking to existing database and config..."
    $EnvArgs = "--env-file unmessit-ai/.env"
}

# We force the project name to 'unmessit-ai' so it seamlessly shares the database volume
# and replaces the staging containers without port conflicts.
if ($EnvArgs) {
    docker compose --env-file unmessit-ai/.env -p unmessit-ai up -d --build
} else {
    docker compose -p unmessit-ai up -d --build
}

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "    UnmessIt.AI is now running from source!   " -ForegroundColor Green
Write-Host "==============================================`n" -ForegroundColor Green

Write-Host -NoNewline "Web UI: " -ForegroundColor Blue
Write-Host "http://localhost:2831"
Write-Host -NoNewline "API:    " -ForegroundColor Blue
Write-Host "http://localhost:2317`n"

Write-Host "To stop, run: docker compose down"

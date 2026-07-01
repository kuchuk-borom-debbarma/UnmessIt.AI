# Requires -Version 3.0
$ErrorActionPreference = "Stop"

Write-Host -ForegroundColor Blue @"
  _   _                                ___ _   _  _   ___ 
 | | | |                              |_ _| | | |/ | |_ _|
 | | | |_ __  _ __ ___   ___  ___ ___  | || |_| |/| |  | | 
 | |_| | '_ \| '_ ` _ \ / _ \/ __/ __| | ||  _  | | |  | | 
 |  _  | | | | | | | | |  __/\__ \__ \ | || | | | | |  | | 
 |_| |_|_| |_|_| |_| |_|\___||___/___/|___|_| |_| |_| |___|
                                                           
"@
Write-Host -ForegroundColor Green "Welcome to the UnmessIt.AI interactive installer!`n"

# Dependency checks
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host -ForegroundColor Red "Error: Docker is not installed. Please install Docker Desktop first: https://docs.docker.com/desktop/install/windows/"
    exit 1
}

# Directory setup
$INSTALL_DIR = "unmessit-ai"
if (Test-Path $INSTALL_DIR) {
    Write-Host -ForegroundColor Yellow "Directory '$INSTALL_DIR' already exists. The installer will use it."
} else {
    Write-Host "Creating installation directory '$INSTALL_DIR'..."
    New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
}
Set-Location $INSTALL_DIR
New-Item -ItemType Directory -Force -Path "data" | Out-Null

# Interaction
$SERVER_PORT = "2317"
$WEB_PORT = "2831"
$JWT_SECRET = ""

Write-Host "This installer will set up UnmessIt.AI with standard defaults."
$MODE = Read-Host "Press [Enter] to continue with defaults, or type 'advanced' to customize ports and secrets"

if ($MODE -eq "advanced") {
    Write-Host ""
    $input_sp = Read-Host "Enter Server Port (default: 2317)"
    if ($input_sp) { $SERVER_PORT = $input_sp }

    $input_wp = Read-Host "Enter Web Port (default: 2831)"
    if ($input_wp) { $WEB_PORT = $input_wp }

    $input_jwt = Read-Host "Enter a secure JWT Secret (leave blank to auto-generate)"
    if ($input_jwt) { $JWT_SECRET = $input_jwt }
}

if (-not $JWT_SECRET) {
    # Generate random 32 character hex string
    $bytes = New-Object Byte[] 32
    $rand = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rand.GetBytes($bytes)
    $JWT_SECRET = -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

Write-Host "`nDownloading docker-compose.prod.yml..." -ForegroundColor Blue
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/docker-compose.prod.yml" -OutFile "docker-compose.prod.yml"

Write-Host "Generating .env file..."
@"
SERVER_PORT=$SERVER_PORT
WEB_PORT=$WEB_PORT
JWT_SECRET=$JWT_SECRET
UNMESSIT_DATA_DIR=./data
"@ | Out-File -Encoding UTF8 -FilePath ".env"

Write-Host "`nStarting UnmessIt.AI in the background..." -ForegroundColor Blue
docker compose -f docker-compose.prod.yml up -d

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "    UnmessIt.AI is now running successfully!   " -ForegroundColor Green
Write-Host "==============================================`n" -ForegroundColor Green

Write-Host -NoNewline "Access the web app at:  "
Write-Host "http://localhost:$WEB_PORT" -ForegroundColor Blue
Write-Host -NoNewline "Access the API at:      "
Write-Host "http://localhost:$SERVER_PORT`n" -ForegroundColor Blue

$currentPath = (Get-Location).Path
Write-Host -NoNewline "Your configuration is saved in "
Write-Host "$currentPath\.env" -ForegroundColor Yellow
Write-Host -NoNewline "Your UnmessIt.AI data is stored in "
Write-Host "$currentPath\data" -ForegroundColor Yellow

Write-Host -NoNewline "To stop the app, run: "
Write-Host "cd `"$currentPath`"; docker compose -f docker-compose.prod.yml down" -ForegroundColor Yellow

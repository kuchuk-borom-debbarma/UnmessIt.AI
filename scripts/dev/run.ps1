$ErrorActionPreference = "Stop"

# Change to the root directory of the project
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path "$ScriptDir\..\.."

Write-Host -ForegroundColor Blue "Starting UnmessIt.AI Development Environment..."

# Define script block to run web client
$webJob = Start-Job -ScriptBlock {
    Set-Location -Path "$using:PWD\web"
    npm run dev
}

Write-Host "Starting web client on http://localhost:2831 (logs hidden)"

# Setup cleanup on exit
$cleanup = {
    Write-Host "`nStopping services..." -ForegroundColor Red
    Stop-Job $webJob -ErrorAction SilentlyContinue
    Remove-Job $webJob -ErrorAction SilentlyContinue
}

# Register cleanup event for Ctrl+C
[console]::TreatControlCAsInput = $true
$host.ui.rawui.FlushInputBuffer()
Register-EngineEvent -SourceIdentifier ([System.Management.Automation.PsEngineEvent]::Exiting) -Action $cleanup | Out-Null

Write-Host "Starting backend server on http://localhost:2317"
Write-Host "Server logs will appear below:"
Write-Host "----------------------------------------"

# Run the server in foreground
Set-Location -Path "server"
if (Test-Path ".venv\Scripts\activate.ps1") {
    . .\.venv\Scripts\activate.ps1
}
uvicorn src.main:create_app --reload --port 2317

# If uvicorn exits, run cleanup
& $cleanup

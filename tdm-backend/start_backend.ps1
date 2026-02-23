# TDM Backend Startup Script
# This script starts the backend server with proper logging
# If WinError 10013 occurs, set: $env:API_PORT=8004

$port = if ($env:API_PORT) { $env:API_PORT } else { 8003 }
$env:API_PORT = $port  # So config.py picks it up

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Starting TDM Backend Server" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server will start on: http://localhost:$port" -ForegroundColor Green
Write-Host "API Documentation: http://localhost:$port/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host "If WinError 10013 occurs, run: `$env:API_PORT=8004; .\start_backend.ps1" -ForegroundColor DarkGray
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Blue
    & .\venv\Scripts\Activate.ps1
}

# Start uvicorn with file logging
Write-Host "[INFO] Starting uvicorn server with file logging..." -ForegroundColor Blue
Write-Host "[INFO] Log files will be created in current directory:" -ForegroundColor Yellow
Write-Host "  - tdm_backend.log (Application logs)" -ForegroundColor Yellow
Write-Host "  - uvicorn_default.log (Server logs)" -ForegroundColor Yellow
Write-Host "  - uvicorn_access.log (Request logs)" -ForegroundColor Yellow
Write-Host ""
python -m uvicorn main:app --host 0.0.0.0 --port $port --reload --log-config logging_config.json

# View TDM Backend Logs in Real-Time

param(
    [string]$LogType = "all"
)

function Show-LogHelp {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  TDM Backend Log Viewer" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\view_logs.ps1 [LogType]" -ForegroundColor White
    Write-Host ""
    Write-Host "Log Types:" -ForegroundColor Yellow
    Write-Host "  all        - Show all logs combined (default)" -ForegroundColor White
    Write-Host "  app        - Application logs (workflow, database operations)" -ForegroundColor White
    Write-Host "  access     - HTTP request/response logs" -ForegroundColor White
    Write-Host "  server     - Uvicorn server logs" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\view_logs.ps1            # View all logs" -ForegroundColor White
    Write-Host "  .\view_logs.ps1 app        # View only application logs" -ForegroundColor White
    Write-Host "  .\view_logs.ps1 access     # View only request logs" -ForegroundColor White
    Write-Host ""
}

Clear-Host

switch ($LogType.ToLower()) {
    "app" {
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "  Viewing Application Logs (tdm_backend.log)" -ForegroundColor Cyan
        Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
        if (Test-Path "tdm_backend.log") {
            Get-Content tdm_backend.log -Wait -Tail 30
        } else {
            Write-Host "Log file not found. Start the backend server first." -ForegroundColor Red
        }
    }
    "access" {
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "  Viewing HTTP Access Logs (uvicorn_access.log)" -ForegroundColor Cyan
        Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
        if (Test-Path "uvicorn_access.log") {
            Get-Content uvicorn_access.log -Wait -Tail 30
        } else {
            Write-Host "Log file not found. Start the backend server first." -ForegroundColor Red
        }
    }
    "server" {
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "  Viewing Server Logs (uvicorn_default.log)" -ForegroundColor Cyan
        Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
        if (Test-Path "uvicorn_default.log") {
            Get-Content uvicorn_default.log -Wait -Tail 30
        } else {
            Write-Host "Log file not found. Start the backend server first." -ForegroundColor Red
        }
    }
    "all" {
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "  Viewing All Recent Logs" -ForegroundColor Cyan
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host ""
        
        if (Test-Path "tdm_backend.log") {
            Write-Host "[APPLICATION LOGS - Last 20 lines]" -ForegroundColor Green
            Get-Content tdm_backend.log -Tail 20
            Write-Host ""
        }
        
        if (Test-Path "uvicorn_access.log") {
            Write-Host "[ACCESS LOGS - Last 15 lines]" -ForegroundColor Yellow
            Get-Content uvicorn_access.log -Tail 15
            Write-Host ""
        }
        
        if (Test-Path "uvicorn_default.log") {
            Write-Host "[SERVER LOGS - Last 10 lines]" -ForegroundColor Cyan
            Get-Content uvicorn_default.log -Tail 10
            Write-Host ""
        }
        
        Write-Host "================================================================================" -ForegroundColor Cyan
        Write-Host "To follow logs in real-time, use:" -ForegroundColor Yellow
        Write-Host "  .\view_logs.ps1 app      # Follow application logs" -ForegroundColor White
        Write-Host "  .\view_logs.ps1 access   # Follow request logs" -ForegroundColor White
        Write-Host "================================================================================" -ForegroundColor Cyan
    }
    "help" {
        Show-LogHelp
    }
    default {
        Write-Host "Unknown log type: $LogType" -ForegroundColor Red
        Show-LogHelp
    }
}

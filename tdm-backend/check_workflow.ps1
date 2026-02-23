# Check Workflow Execution and Database Status

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  TDM Workflow Status Checker" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "Checking backend server..." -ForegroundColor Yellow
$connection = Test-NetConnection localhost -Port 8002 -WarningAction SilentlyContinue
if ($connection.TcpTestSucceeded) {
    Write-Host "[OK] Backend server is running on port 8002" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Backend server is NOT running!" -ForegroundColor Red
    Write-Host "Start it with: .\start_backend.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check database records
Write-Host "Checking database records..." -ForegroundColor Yellow
$dbCheck = python -c @"
from database import SessionLocal
from models import Job, JobLog, Schema, PIIClassification, DatasetVersion

db = SessionLocal()
try:
    jobs = db.query(Job).count()
    logs = db.query(JobLog).count()
    schemas = db.query(Schema).count()
    pii = db.query(PIIClassification).count()
    datasets = db.query(DatasetVersion).count()
    
    print(f'Jobs: {jobs}')
    print(f'Job Logs: {logs}')
    print(f'Schemas: {schemas}')
    print(f'PII Classifications: {pii}')
    print(f'Dataset Versions: {datasets}')
    
    if jobs > 0:
        print('---')
        latest = db.query(Job).order_by(Job.created_at.desc()).first()
        print(f'Latest Job: {latest.job_id}')
        print(f'Type: {latest.job_type}')
        print(f'Status: {latest.status}')
        if latest.error:
            print(f'Error: {latest.error}')
finally:
    db.close()
"@

Write-Host $dbCheck -ForegroundColor White
Write-Host ""

# Check recent application logs
if (Test-Path "tdm_backend.log") {
    Write-Host "Recent application activity (last 10 lines):" -ForegroundColor Yellow
    Get-Content tdm_backend.log -Tail 10 | ForEach-Object {
        if ($_ -match "ERROR|FAILED") {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "SUCCESS|Completed") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "WARNING") {
            Write-Host $_ -ForegroundColor Yellow
        } else {
            Write-Host $_ -ForegroundColor White
        }
    }
    Write-Host ""
}

# Check recent access logs
if (Test-Path "uvicorn_access.log") {
    Write-Host "Recent API requests (last 5):" -ForegroundColor Yellow
    Get-Content uvicorn_access.log -Tail 5
    Write-Host ""
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "To view logs in real-time: .\view_logs.ps1" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan

# Backend Logging Guide

## Quick Start - View Logs from Files

The backend now writes all logs to files automatically! No need to watch console output.

### 1. Start Backend (creates log files automatically)

```powershell
cd "C:\Users\gparavasthu\Workspace\Gen AI QE\TDM\tdm-backend"
.\start_backend.ps1
```

### 2. View Logs in Real-Time

```powershell
# View all recent logs
.\view_logs.ps1

# Follow application logs (workflows, database, operations)
.\view_logs.ps1 app

# Follow HTTP request logs
.\view_logs.ps1 access

# Follow server logs
.\view_logs.ps1 server
```

### 3. Check Workflow Status & Database

```powershell
.\check_workflow.ps1
```

## Log Files Created

When backend starts, these files are automatically created:

| File | Contains |
|------|----------|
| `tdm_backend.log` | Application logs: workflow steps, database operations, errors |
| `uvicorn_access.log` | HTTP requests/responses with timestamps |
| `uvicorn_default.log` | Server startup, shutdown, reload events |

## Example Workflow

**Terminal 1 - Start Backend:**
```powershell
cd tdm-backend
.\start_backend.ps1
```

**Terminal 2 - Watch Logs:**
```powershell
cd tdm-backend
.\view_logs.ps1 app
```

**Terminal 3 - Execute workflow from UI, then check status:**
```powershell
cd tdm-backend
.\check_workflow.ps1
```

## What You'll See in Logs
```
================================================================================
[STARTUP] TDM Backend Starting Up
================================================================================
[CONFIG] Configuring CORS middleware
[CONFIG] Adding request logging middleware
...
[READY] Application startup complete
```

When you make requests (e.g., execute a workflow from UI):
```
[REQUEST] POST /api/v1/workflow/execute
[OK] POST /api/v1/workflow/execute -> 200 (5ms)
[WORKFLOW] Queued: workflow_id=xxx, job_id=xxx
[WORKFLOW] Starting background execution: workflow_id=xxx, job_id=xxx
[DATABASE] Created Job record: job_id=xxx, type=workflow
[DISCOVER] running: Starting schema discovery...
[PII] running: Starting PII detection...
[SYNTHETIC] running: Generating synthetic data...
[DATABASE] Updated Job status: job_id=xxx, status=completed
================================================================================
[SUCCESS] Workflow Completed: xxx
   Duration: 45.23s
   Operations Executed: 6
================================================================================
```

## Checking Log Files

All logs are also written to `tdm_backend.log`:

```powershell
# View last 50 lines
Get-Content tdm_backend.log -Tail 50

# Follow logs in real-time
Get-Content tdm_backend.log -Wait -Tail 20
```

## Verifying Database Inserts

Check if data is being saved:

```powershell
python -c "from database import SessionLocal; from models import Job, JobLog; db = SessionLocal(); print(f'Jobs: {db.query(Job).count()}'); print(f'Logs: {db.query(JobLog).count()}')"
```

## Troubleshooting

If you still don't see logs:

1. **Check if backend is running:**
   ```powershell
   Test-NetConnection localhost -Port 8002
   ```

2. **Check for Python errors:**
   - Look for error messages when starting
   - Check if virtual environment is activated

3. **Check log file:**
   ```powershell
   Get-Content tdm_backend.log -Tail 100
   ```

4. **Restart with verbose output:**
   ```powershell
   python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload --log-level debug
   ```

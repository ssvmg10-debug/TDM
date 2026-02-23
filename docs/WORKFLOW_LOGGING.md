# Real-Time Workflow Logging

## Overview
The TDM Workflow Orchestrator now includes real-time logging capabilities that display backend execution logs directly in the UI.

## Features

### 1. Backend Logging
All workflow operations automatically log their progress to the database:
- **Step-level logs**: Each operation (discover, pii, subset, mask, synthetic, provision) logs its steps
- **Timestamp tracking**: Every log entry includes a precise timestamp
- **Log levels**: info, warning, error, success
- **Detailed context**: Each log can include additional details in JSON format

### 2. Real-Time Log Viewer Component
A dedicated LogViewer component displays logs with:
- **Auto-refresh**: Logs refresh every 2 seconds by default
- **Auto-scroll**: Automatically scrolls to the latest log entry
- **Color-coded steps**: Each operation type has a distinct color
- **Level indicators**: Visual icons for error, warning, success, info
- **Expandable details**: Click to view full JSON details of each log entry
- **Responsive design**: Scrollable area with fixed height

### 3. UI Integration
The LogViewer is integrated into the Workflow Orchestrator page:
- **Click to view logs**: Click any job in the execution history to view its logs
- **Highlighted selection**: The selected job is highlighted with a blue ring
- **Automatic display**: When a workflow is executed, logs appear immediately

## API Endpoints

### GET /api/v1/workflow/logs/{job_id}
Get all logs for a specific workflow job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs": [
    {
      "timestamp": "2026-02-23T10:30:45.123456",
      "step": "synthetic",
      "level": "info",
      "message": "Starting synthetic data generation",
      "details": {
        "mode": "test_case_content",
        "entities": ["user", "order"]
      }
    }
  ]
}
```

## Log Levels

| Level | Icon | Color | Usage |
|-------|------|-------|-------|
| info | ℹ️ | Blue | General information messages |
| warning | ⚠️ | Yellow | Warnings that don't stop execution |
| error | ❌ | Red | Errors that cause operation failure |
| success/completed | ✅ | Green | Successful completion messages |

## Step Colors

Each workflow operation has a distinct color in the logs:

| Step | Color | Description |
|------|-------|-------------|
| discover | Blue | Schema discovery from database |
| pii | Purple | PII classification |
| subset | Green | Data subsetting |
| mask | Orange | Data masking |
| synthetic | Cyan | Synthetic data generation |
| provision | Pink | Data provisioning to target |

## Usage Example

1. **Start a workflow**:
   - Fill in test case content or connection string
   - Click "Generate Synthetic Data" or "Execute Workflow"

2. **View logs**:
   - The workflow job appears in "Execution History"
   - Click on the job to view its logs
   - Logs update automatically every 2 seconds

3. **Monitor progress**:
   - Watch step-by-step execution
   - See which operation is currently running
   - Check for any errors or warnings

4. **Debug issues**:
   - Click "View details" on any log entry
   - See full context including parameters and results
   - Use timestamps to identify bottlenecks

## Configuration

### Auto-refresh Settings
You can customize the LogViewer refresh behavior:

```typescript
<LogViewer 
  jobId={currentJobId} 
  autoRefresh={true}        // Enable/disable auto-refresh
  refreshInterval={2000}    // Refresh interval in milliseconds
/>
```

### Log Viewer Height
The log viewer has a fixed height of 400px and auto-scrolls. To change:

```typescript
<ScrollArea className="h-[400px]">  {/* Change height here */}
```

## Backend Implementation

### Logging in Services
All service modules use the same logging pattern:

```python
from models import JobLog
from database import get_db

def log_step(db, job_id, step, status, message, details=None):
    log_entry = JobLog(
        job_id=job_id,
        step=step,
        level=status,
        message=message,
        details=details or {}
    )
    db.add(log_entry)
    db.commit()
```

### Example Usage
```python
# Start of operation
log_step(db, job_id, "synthetic", "info", "Starting synthetic data generation")

# Progress update
log_step(db, job_id, "synthetic", "info", f"Generated {entity_name}: {n} rows")

# Success
log_step(db, job_id, "synthetic", "success", "Synthetic generation completed", 
         {"dataset_version_id": version_id})

# Error
log_step(db, job_id, "synthetic", "error", f"Generation failed: {str(e)}")
```

## Database Schema

The `job_logs` table stores all log entries:

```sql
CREATE TABLE job_logs (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL,
    step VARCHAR,
    level VARCHAR,
    message TEXT,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

## Benefits

1. **Real-time visibility**: See exactly what's happening during workflow execution
2. **Better debugging**: Detailed logs help identify issues quickly
3. **Progress tracking**: Know which step is running and how long it takes
4. **Historical analysis**: Review logs from past executions
5. **User confidence**: Users can see the system is working, not frozen

## Future Enhancements

- **Log filtering**: Filter by level, step, or time range
- **Log export**: Download logs as CSV or JSON
- **Log search**: Search through log messages
- **Performance metrics**: Show execution time for each step
- **Log aggregation**: Summary view showing counts by level
- **WebSocket streaming**: Real-time log streaming without polling

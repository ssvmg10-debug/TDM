# TDM Platform Fixes Summary

## 1. Notifications

**Problem**: Notification bell did not show any job completion/failure alerts.

**Fix**:
- Added `useJobNotifications` hook that polls jobs every 5 seconds
- When a job transitions from `running`/`pending` to `completed` or `failed`, shows a **Sonner toast**
- Respects user preferences from Settings (jobComplete, jobFailed)
- Invalidates datasets and target-tables queries on completion so UI refreshes
- Integrated in `Layout.tsx`

## 2. Quality Indicator

**Problem**: Quality dashboard showed static "85" when no jobs had quality data.

**Fix**:
- Removed hardcoded fallback of 85 when `completedWithContext.length === 0`
- Now shows "—" (dash) when no quality data exists
- Radial chart shows gray when no data
- Metrics display real values only when available

## 3. Dataset Catalog

**Problem**: Dataset catalog did not show latest data after workflows completed.

**Fix**:
- Added `refetchInterval: 15000` (15 seconds) to datasets query
- Added `staleTime: 5000` so data is considered fresh for 5 seconds
- Job completion notifications trigger `invalidateQueries(["datasets"])` so catalog refreshes immediately when a workflow finishes

## 4. TDM Target Refresh Button

**Problem**: Refresh button on tdm_target card did not work.

**Fix**:
- Replaced `Badge` (which had `onClick`) with a proper `Button`
- Added `isFetching` state to show "Refreshing..." and disable during refetch
- Added spin animation on RefreshCw icon during fetch

## 5. UI Crawler

**Problem**: Crawler could fail on slow SPAs or when elements threw during extraction.

**Fix**:
- Changed `wait_until` to `domcontentloaded` for faster initial load
- Increased `networkidle` timeout to 15 seconds, with fallback to `load` if it fails
- Wrapped `element.evaluate` in try/except for `_extract_field_info` to avoid crashes on malformed elements

## 6. Workflow Response Display

**Problem**: User could not see what the workflow did.

**Fix**:
- Added "What the workflow did" summary panel in `JobTracePanel`
- Shows: operations executed, dataset created, tables provisioned, quality score
- Shows step log (last 8 log entries)
- Backend `get_job_trace` now returns `operations_executed` (actual steps run)
- Displayed in Data Lineage tab when a job is selected

## 7. Test Suite

**Added**:
- `tests/test_decision_engine.py` – 7 unit tests for classify_intent and generate_pipeline_plan
- `tests/test_synthetic_enhanced.py` – 6 unit tests for test_case_needs_synthetic_data and _parse_test_case_content
- `tests/test_api.py` – 6 API integration tests (docs, classify-intent, analyze-test-case, datasets, quality)
- `pytest.ini` – pytest configuration
- `requirements.txt` – added pytest, httpx

**Run tests**:
```powershell
cd tdm-backend
python -m pytest tests -v
```

## Files Changed

| File | Changes |
|------|---------|
| `tdm-ui/src/hooks/useJobNotifications.ts` | **NEW** – Job polling and toast notifications |
| `tdm-ui/src/components/Layout.tsx` | Integrated useJobNotifications |
| `tdm-ui/src/pages/QualityDashboard.tsx` | Removed static 85, show — when no data |
| `tdm-ui/src/pages/DatasetCatalog.tsx` | refetchInterval, staleTime |
| `tdm-ui/src/components/TargetTablesCard.tsx` | Button instead of Badge, loading state |
| `tdm-ui/src/components/JobTracePanel.tsx` | "What the workflow did" summary, step log |
| `tdm-backend/routers/jobs.py` | Added operations_executed to trace response |
| `tdm-backend/services/crawler.py` | Timeout and error handling improvements |
| `tdm-backend/tests/*` | **NEW** – Unit and API tests |
| `tdm-backend/pytest.ini` | **NEW** – Pytest config |
| `tdm-backend/requirements.txt` | Added pytest, httpx |

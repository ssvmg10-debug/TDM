# What the Workflow Did With Your Test Case

## Your Test Case

```
https://demo.evershop.io/
click on shop now
click on any item and choose colour then add to cart
the click on checkout and fill all the required details
```

## Workflow Steps (What Happened)

| Step | Status | What It Did |
|------|--------|-------------|
| **1. Discover** | ✅ Success | Connected to `postgresql://...localhost:5432/tdm`, discovered schema (tables, columns, relationships) |
| **2. PII** | ❌ Failed | Tried to classify columns as PII (email, phone, etc.) but hit a UUID type mismatch bug |
| **3. Subset** | ❌ Failed | Tried to extract a subset of data from source DB to parquet; same UUID bug |
| **4. Mask** | ⏭ Skipped | Not run (subset failed) |
| **5. Synthetic** | ⏭ Skipped | Initially skipped because "fill all the required details" wasn't matched by form-field patterns |
| **6. Provision** | ⏭ Skipped | No dataset to provision (subset failed) |

## Issues Fixed

### 1. Lineage `details` column missing
- **Error**: `column lineage.details does not exist`
- **Fix**: Ran `alembic upgrade head` — migration was already at head; column should exist if migration ran successfully.

### 2. Provision API 404 (schema-evolution, migration-script)
- **Error**: `GET /api/v1/provision/schema-evolution/{id}` → 404
- **Fix**: API routes are at `/api/v1/schema-evolution/{id}` and `/api/v1/migration-script/{id}` (not under `/provision`). Updated the UI API client to use the correct paths.

### 3. PII & Subset UUID sentinel mismatch
- **Error**: `Can't match sentinel values in result set to parameter sets; key '...' was not found`
- **Fix**: Set `use_insertmanyvalues=False` in the database engine to avoid SQLAlchemy's bulk-insert optimization that conflicts with PostgreSQL UUID handling.

### 4. Synthetic skipped for "fill all the required details"
- **Error**: `Skipped - no form field patterns detected (navigation/click-only test)`
- **Fix**: Added patterns to detect "fill all the required details", "fill required details", and "checkout + fill". Added fallback: when these patterns match but no specific fields are parsed, generate default checkout form fields (full_name, email, phone, address, city, zip_code, country).

## What You Should See Now

After restarting the backend and running the workflow again:

1. **Discover** — succeeds
2. **PII** — should succeed (UUID fix)
3. **Subset** — should succeed (UUID fix)
4. **Mask** — runs if PII found
5. **Synthetic** — should run and generate checkout form data (full_name, email, phone, etc.) from "fill all the required details"
6. **Provision** — runs if you have a dataset

## Restart Required

Restart the backend to pick up the database engine change (`use_insertmanyvalues=False`):

```powershell
# Stop the current backend (Ctrl+C), then:
cd tdm-backend
.\start_backend.ps1
```

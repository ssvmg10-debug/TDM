# TDM E2E Test Scenarios

Use this to verify DB, backend, and UI with real data.

## Prerequisites

1. **PostgreSQL** running with database `tdm` (e.g. `postgresql://postgres:12345@localhost:5432/tdm`).
2. **Root `.env`** at `TDM/.env` with `DATABASE_URL`, `API_PORT=8002`, and optionally Azure keys for PII LLM.
3. **UI** `.env` at `tdm-ui/.env` with `VITE_API_URL=http://localhost:8002`.

## 1. Backend setup

```bash
cd tdm-backend
pip install -r requirements.txt
python init_db.py
python seed_env.py
python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

Or from project root:

```bash
cd tdm-backend && pip install -r requirements.txt && python init_db.py && python seed_env.py
# In another terminal:
cd tdm-backend && python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

## 2. UI

```bash
cd tdm-ui
npm install
npm run dev
```

Open http://localhost:8080 (or the port Vite shows).

## 3. Scenario A: Schema Discovery → Dashboard / Schema Explorer

1. **Schema Discovery**
   - Go to **Schema Discovery**.
   - Enter your DB connection string (e.g. same as `DATABASE_URL`: `postgresql://postgres:12345@localhost:5432/tdm`).
   - Click **Run Discovery**.
   - You should see a new schema card under "Discovered Schemas" (e.g. `source_public`).
   - Click it; **Tables** list and **Column Details** should load from the API (real tables from your DB).

2. **Dashboard**
   - Go to **Dashboard**.
   - "Schemas" count should be ≥ 1.
   - "Recent Datasets" may be empty until you run subset/synthetic.
   - "Job Timeline" shows jobs (e.g. after PII or subset).

3. **Dataset Catalog**
   - Go to **Dataset Catalog**.
   - Initially empty; after subset/synthetic, datasets appear from API.

## 4. Scenario B: PII Classification

1. Run **Schema Discovery** first (so a schema version exists).
2. Go to **PII Classification**.
3. Select the schema (version) in the dropdown.
4. Click **Scan All**.
5. Table should show real PII classifications from the backend (regex + optional Azure OpenAI).
6. Summary cards show High/Medium/Total counts from API.

## 5. Scenario C: Subset → Datasets / Jobs

1. Ensure at least one **Schema Discovery** has been run (so `schema_version_id` exists).
2. Go to **Subsetting Engine**.
3. Select schema and root table; set max rows (e.g. 1000).
4. Optionally set connection string (empty = use default `DATABASE_URL`).
5. Click **Run Subset**.
6. Go to **Jobs** (or Workflows): new job with status `running` then `completed`.
7. Go to **Dataset Catalog**: new dataset with type `subset` and row counts from API.

## 6. Scenario D: Synthetic Data

1. Ensure at least one schema version exists.
2. Go to **Synthetic Data Factory**.
3. Select schema version, set row count, click **Generate**.
4. Check **Jobs** and **Dataset Catalog** for new synthetic dataset.

## 7. Scenario E: Masking

1. You need a **subset** (or synthetic) dataset first.
2. Go to **Masking Engine**.
3. Select that dataset; add rules JSON e.g. `{"public.users.email": "mask.email_deterministic"}` (adjust table/column to your schema).
4. Click **Apply Mask**.
5. **Dataset Catalog** should show a new `masked` dataset.

## 8. Scenario F: Provisioning

1. Create **QA** environment (already done by `seed_env.py`).
2. Have at least one dataset (subset or synthetic).
3. Go to **Environment Provisioning**.
4. Select dataset and **QA**, click **Run Provision** (or Provision on QA card).
5. Check job logs on the same page (from API); job should complete and data load into the target DB (same as metadata DB if using default).

## 9. Scenario G: Audit & Governance

1. **Audit Logs**: After running any jobs, open **Audit Logs**; list should come from API (job-based audit).
2. **Governance & Lineage**: Lineage steps and recent events (from audit) should display.

## Automated E2E test script

From project root (with backend already running on port 8002):

```bash
pip install requests
python tests/e2e_tdm_scenarios.py
```

This runs: health → discover-schema → list schemas → get schema/tables → PII classify → subset job → synthetic job → list datasets/jobs → mask (if dataset exists) → provision (if dataset + env) → audit logs. Pass/fail/skip is printed per step. Fixes applied in code:

- **Subset**: Flush `dataset_versions` before inserting `dataset_metadata` (FK); convert UUID/object columns to string before writing Parquet.
- **Synthetic**: Flush `dataset_versions` before `dataset_metadata`; rollback on exception before updating job status.

**Restart the backend** after pulling these fixes so the test sees them.

## Quick health check

- **Backend**: `curl http://localhost:8002/health` → `{"status":"ok"}`.
- **API**: `curl http://localhost:8002/api/v1/schemas` → `[]` or list of schemas.
- **UI**: Dashboard loads and shows 0 or more schemas/datasets/jobs without errors.

## Troubleshooting

- **CORS**: Backend allows all origins; if UI is on another port, it should still work.
- **Empty schemas**: Run **Schema Discovery** with a valid connection string first.
- **Subset fails**: Ensure connection string reaches the same DB that was discovered and that the root table exists.
- **Provision fails**: Ensure QA environment exists (`python seed_env.py`) and target tables can be created/dropped (e.g. same DB as metadata).

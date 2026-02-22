# TDM UI Testing Guide — Inputs for Each Feature

Use this guide to test the full application from the UI. **Ensure the backend is running and the UI points to it** so you see request logs in the backend terminal when you navigate and click.

---

## 1. See Backend Logs When Using the UI

- **Backend** must log every request. Restart the backend so it uses the request-logging middleware (each `GET/POST` to `/api/v1/...` is logged with method, path, status, and duration).
- **UI** must call the same host/port as the backend:
  - Backend default port: **8002** (from root `.env`: `API_PORT=8002`).
  - In `tdm-ui/.env` set: **`VITE_API_URL=http://localhost:8002`** (or the port you actually start the backend on).
- If you start the backend on a different port (e.g. `--port 8003`), set `VITE_API_URL=http://localhost:8003` and restart the UI (`npm run dev`). Otherwise the UI will call the wrong port and you will see no logs.

**Quick check:** Open Dashboard in the UI — the backend terminal should show lines like:
```text
GET /api/v1/schemas -> 200 (45 ms)
GET /api/v1/datasets -> 200 (12 ms)
GET /api/v1/jobs -> 200 (8 ms)
```

---

## 2. Prerequisites

- PostgreSQL with database `tdm` (e.g. `postgresql://postgres:12345@localhost:5432/tdm`).
- Root `.env` with `DATABASE_URL`, `API_PORT=8002`, and optionally Azure keys for PII.
- Backend: `cd tdm-backend && python init_db.py && python seed_env.py` (once), then `python -m uvicorn main:app --host 0.0.0.0 --port 8002`.
- UI: `cd tdm-ui && npm run dev`; ensure `tdm-ui/.env` has `VITE_API_URL=http://localhost:8002`.

---

## 3. Test Inputs by Feature

### Dashboard (Command Center)

| What to do | Inputs |
|------------|--------|
| Load overview | None. Just open the page. |
| Expected | Backend logs: `GET /api/v1/schemas`, `GET /api/v1/datasets`, `GET /api/v1/jobs`. UI shows schema count, recent datasets, job timeline. |

---

### Schema Discovery

| What to do | Inputs |
|------------|--------|
| Run discovery | **Connection string:** same as your metadata DB, e.g. `postgresql://postgres:12345@localhost:5432/tdm` |
| Expected | Backend: `POST /api/v1/discover-schema` → 200. A new schema card appears (e.g. `public` or `source_public`). Click it to load tables and columns (`GET /api/v1/schema/{id}`, `GET /api/v1/schema/version/{versionId}/tables`, `GET .../tables/{table}/columns`). |

**Example connection string (match your `.env`):**
```text
postgresql://postgres:12345@localhost:5432/tdm
```

---

### PII Classification

| What to do | Inputs |
|------------|--------|
| Scan for PII | Run **Schema Discovery** first so a schema exists. Then open PII Classification, **select the schema** from the dropdown (e.g. "public"), click **Scan All**. |
| Expected | Backend: `POST /api/v1/pii/classify` and `GET /api/v1/pii/{schema_version_id}`. Table shows columns classified as PII (e.g. email, name). |

No manual text input; only schema selection and "Scan All".

---

### Subsetting Engine

| What to do | Inputs |
|------------|--------|
| Create subset | 1. **Schema:** Select the discovered schema (dropdown). 2. **Root table:** Pick a table that exists in that schema (e.g. `users` or the first table listed). 3. **Max rows:** e.g. `1000` or `10000`. 4. **Connection string:** Leave empty to use backend default `DATABASE_URL`, or set same as discovery, e.g. `postgresql://postgres:12345@localhost:5432/tdm`. |
| Expected | Backend: `POST /api/v1/subset` → job_id. Then **Jobs** and **Dataset Catalog** show the new subset job and dataset. |

**Example:** Root table = `users`, Max rows = `5000`, Connection string = empty or `postgresql://postgres:12345@localhost:5432/tdm`.

---

### Synthetic Data Factory

| What to do | Inputs |
|------------|--------|
| Generate synthetic data | 1. **Schema version:** Select the discovered schema from dropdown. 2. **Rows:** e.g. `1000`. 3. Click **Generate**. |
| Expected | Backend: `POST /api/v1/synthetic`. New job and dataset (source_type = synthetic) in Jobs and Dataset Catalog. |

---

### Masking Engine

| What to do | Inputs |
|------------|--------|
| Apply masking | 1. Have at least one **subset** or **synthetic** dataset. 2. **Dataset:** Select that dataset from dropdown. 3. **Rules:** JSON mapping `table.column` → rule type. Example (adjust table/column to your schema): `{"public.users.email": "mask.email_deterministic", "public.users.name": "mask.hash"}`. 4. Click **Apply Mask**. |
| Expected | Backend: `POST /api/v1/mask`. New masked dataset in Dataset Catalog. |

**Example rules (if you have `public.users` with `email` and `name`):**
```json
{"public.users.email": "mask.email_deterministic", "public.users.name": "mask.hash"}
```

---

### Dataset Catalog

| What to do | Inputs |
|------------|--------|
| View datasets | None. Open the page. |
| Expected | Backend: `GET /api/v1/datasets`. List of subset/synthetic/masked datasets. |

---

### Environment Provisioning

| What to do | Inputs |
|------------|--------|
| Provision to QA | 1. **QA** environment must exist (created by `python seed_env.py`). 2. **Dataset:** Select any dataset (subset or synthetic). 3. **Target env:** Select **QA**. 4. Click **Run Provision** (or the Provision button on the QA card). |
| Expected | Backend: `POST /api/v1/provision`. Job runs; logs appear on the same page. Data is loaded into the target DB (default QA uses same DB as metadata). |

---

### Workflow / Jobs

| What to do | Inputs |
|------------|--------|
| View jobs | None. Open Workflows or Jobs. |
| Expected | Backend: `GET /api/v1/jobs`. List of subset, synthetic, mask, provision jobs. Click a job for details: `GET /api/v1/job/{id}`. |

---

### Governance & Lineage

| What to do | Inputs |
|------------|--------|
| View lineage | Select a **dataset** (if the UI has a dropdown). |
| Expected | Backend: `GET /api/v1/lineage/dataset/{id}`. Lineage steps for that dataset. |

---

### Audit Logs

| What to do | Inputs |
|------------|--------|
| View audit | None. Open Audit Logs. |
| Expected | Backend: `GET /api/v1/audit-logs`. List of actions (e.g. job runs). |

---

### Environments

| What to do | Inputs |
|------------|--------|
| List / create | None to list. To create: use API or ensure `seed_env.py` has run (creates QA). |
| Expected | Backend: `GET /api/v1/environments`. QA (and others) listed. |

---

## 4. Recommended Test Order

1. **Schema Discovery** — connection string: `postgresql://postgres:12345@localhost:5432/tdm` (or your `DATABASE_URL`).
2. **Dashboard** — confirm schema count and empty/partial datasets and jobs.
3. **PII Classification** — select schema, click Scan All.
4. **Subsetting Engine** — select schema, pick root table (e.g. first table), max rows 1000, Run Subset.
5. **Synthetic Data Factory** — select schema, rows 500, Generate.
6. **Dataset Catalog** — confirm subset and synthetic datasets.
7. **Masking Engine** — select a subset or synthetic dataset, add one rule (e.g. `{"public.<table>.<column>": "mask.hash"}`), Apply Mask.
8. **Environment Provisioning** — select a dataset, target QA, Run Provision.
9. **Jobs / Workflow** — confirm all jobs and statuses.
10. **Audit Logs** — confirm entries.
11. **Governance & Lineage** — select a dataset and check lineage.

---

## 5. Troubleshooting

- **No backend logs when clicking in UI:** Ensure `VITE_API_URL` in `tdm-ui/.env` matches the port the backend is running on. Restart UI after changing `.env`.
- **Empty schemas:** Run Schema Discovery with a valid connection string first.
- **Subset fails:** Use the same DB (and schema) as discovery; root table must exist.
- **Mask rules:** Use keys like `schema_name.table_name.column_name` (e.g. `public.users.email`). Rule values: `mask.hash`, `mask.email_deterministic`, `mask.redact`, etc.
- **Provision fails:** Run `python tdm-backend/seed_env.py` so QA environment exists; ensure target DB is reachable with the same credentials as in the environment config.

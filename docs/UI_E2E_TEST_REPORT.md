# TDM UI — End-to-End Test Report

This report documents **every button and dynamic behavior** in the UI, how to test it, and the expected outcome. The app runs in **single-user mode** (no RBAC; no login).

---

## Prerequisites

- **Backend** running (e.g. `cd tdm-backend && python -m uvicorn main:app --host 0.0.0.0 --port 8002`).
- **UI** `VITE_API_URL` in `tdm-ui/.env` must match backend port (e.g. `http://localhost:8002`).
- **PostgreSQL** with DB `tdm`; run `python init_db.py` and `python seed_env.py` once from `tdm-backend`.
- Open UI (e.g. `cd tdm-ui && npm run dev`) and use **http://localhost:5173** (or the port Vite prints).

---

## 1. Dashboard (Command Center) — `/`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches schemas, datasets, jobs | Open `/` | 3 API calls: `GET /api/v1/schemas`, `GET /api/v1/datasets`, `GET /api/v1/jobs`. Cards show counts; Job Timeline and Recent Datasets from API. |
| "Run Schema Discovery" card | Link | Navigate to Schema Discovery | Click card | Goes to `/schema-discovery`. |
| "Create Subset" card | Link | Navigate to Subsetting | Click card | Goes to `/subsetting`. |
| "Generate Synthetic Data" card | Link | Navigate to Synthetic | Click card | Goes to `/synthetic-data`. |
| "Mask Dataset" card | Link | Navigate to Masking | Click card | Goes to `/masking`. |
| "View All" (jobs) | Link | Navigate to Workflows | Click | Goes to `/workflows`. |
| "View Catalog" | Link | Navigate to Dataset Catalog | Click | Goes to `/datasets`. |

**Pass criteria:** All links navigate; numbers and lists match backend (schemas count, datasets, jobs). No console/network errors.

---

## 2. Schema Discovery — `/schema-discovery`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches schemas list | Open page | `GET /api/v1/schemas`. Discovered schemas grid (or "No schemas yet"). |
| Connection string input | Input | User types connection string | Type e.g. `postgresql://postgres:12345@localhost:5432/tdm` | Value stored. |
| **Run Discovery** button | Button | POST discover-schema, invalidate schemas | Enter connection string, click | `POST /api/v1/discover-schema`. Success toast; schema card appears; connection string cleared. On failure: error toast. |
| Schema card | Clickable | Select schema, load tables/columns | Click a schema card | `GET /api/v1/schema/{schema_id}`. Tables list loads. |
| Table row | Clickable | Select table, load columns | Click a table | `GET /api/v1/schema/version/{id}/tables/{table}/columns`. Column details panel updates. |

**Pass criteria:** Discovery runs and new schema appears; selecting schema/table loads tables and columns from API. Toasts on success/error.

---

## 3. PII Classification — `/pii-classification`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches schemas, then PII for selected schema | Open page | `GET /api/v1/schemas`. If schemas exist, `GET /api/v1/pii/{schema_version_id}` for first. |
| Schema dropdown | Select | Select schema version | Change option | PII table refetches: `GET /api/v1/pii/{version_id}`. |
| **Scan All** button | Button | POST classify PII, refetch PII | Select schema, click | `POST /api/v1/pii/classify`. Success toast; table and summary cards update. On failure: error toast. |

**Pass criteria:** Dropdown shows schemas; Scan All runs and PII table/cards show API data. Toasts on success/error.

---

## 4. Subsetting Engine — `/subsetting`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches schemas, then schema detail (tables) | Open page | `GET /api/v1/schemas`, then `GET /api/v1/schema/{id}` when schema selected. |
| Step buttons (1–4) | Buttons | Change current step (visual only) | Click steps | Step highlight changes; no API. |
| Schema dropdown | Select | Select schema | Change option | Schema detail refetches; root table dropdown populates. |
| Root table dropdown | Select | Select root table | Change option | Value stored for subset request. |
| Max rows input | Input | Set max rows | Enter number | Value used in subset request. |
| Connection string input | Input | Optional override | Enter or leave empty | Sent if non-empty; else backend uses default. |
| **Run Subset** button | Button | POST subset, invalidate jobs/datasets | Select schema + table, set max rows, click | `POST /api/v1/subset`. Success toast; Jobs/Datasets refresh. On failure: error toast. Button disabled when no schema. |

**Pass criteria:** Schema and root table dropdowns populate from API; Run Subset starts job and shows toast. Button disabled when no schemas.

---

## 5. Masking Engine — `/masking`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches datasets | Open page | `GET /api/v1/datasets`. Dataset dropdown shows only non-masked (subset/synthetic). |
| Dataset dropdown | Select | Select source dataset | Select item | Required for Apply; no API until Apply. |
| Rules textarea | Textarea | JSON rules (table.column → rule) | Enter e.g. `{"public.users.email": "mask.email_deterministic"}` | Parsed to object; invalid JSON leaves previous state. |
| **Apply Mask** button | Button | POST mask, invalidate jobs/datasets | Select dataset, add rules, click | `POST /api/v1/mask`. Success toast; new masked dataset in catalog. On failure: error toast. Disabled when no dataset or no rules. |

**Pass criteria:** Only subset/synthetic datasets in dropdown; Apply Mask runs and creates masked dataset; toasts on success/error. Message when no source datasets.

---

## 6. Synthetic Data Factory — `/synthetic-data`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches schemas | Open page | `GET /api/v1/schemas`. |
| Schema dropdown | Select | Select schema version | Change option | Value used for generation (or first if none selected). |
| Rows input | Number | Default row count per table | Enter number | Sent as `row_counts: { "*": N }`. |
| **Generate** button | Button | POST synthetic, invalidate jobs/datasets | Select schema, set rows, click | `POST /api/v1/synthetic`. Success toast; job/datasets refresh. On failure: error toast. Disabled when no schema. |

**Pass criteria:** Generate starts job and shows toast; Dataset Catalog shows new synthetic dataset. Toasts on success/error.

---

## 7. Workflow Orchestrator (Jobs) — `/workflows`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches jobs | Open page | `GET /api/v1/jobs`. Execution history list from API. |

**Pass criteria:** Job list shows operations and status from backend. No action buttons; read-only.

---

## 8. Dataset Catalog — `/datasets`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches datasets; static lineage steps | Open page | `GET /api/v1/datasets`. Table shows name, type, rows, tables, created. Lineage strip is static. |
| Download icon (per row) | Button | Placeholder (no backend) | Click | No API call; UI only. |

**Pass criteria:** Table populated from API; types and row counts correct.

---

## 9. Environment Provisioning — `/environments`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches environments and datasets | Open page | `GET /api/v1/environments`, `GET /api/v1/datasets`. |
| QA/SIT/UAT/PERF/DEV cards | Cards | Each has "Provision" button | Click Provision on a card | Sets target env and first dataset, calls provision mutation. |
| Dataset dropdown | Select | Select dataset to provision | Change option | Value used for provision. |
| Target env dropdown | Select | QA / SIT / UAT / DEV | Change option | Value sent as `target_env`. |
| **Run Provision** button | Button | POST provision, invalidate jobs | Select dataset + env, click | `POST /api/v1/provision`. Success toast; job logs section can poll `GET /api/v1/job/{id}`. On failure: error toast. |

**Pass criteria:** Provision starts job; toasts on success/error. Job logs (if shown) from API.

---

## 10. Governance & Lineage — `/governance`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches datasets, audit logs | Open page | `GET /api/v1/datasets`, `GET /api/v1/audit-logs`. |
| Dataset dropdown | Select | Select dataset for lineage | Change option | `GET /api/v1/lineage/dataset/{id}`. Lineage steps update from API. |
| "Access (Single User)" block | Static | Message only | Read | "No RBAC — single user mode." |
| Recent Events | — | From audit logs | — | Shows last 5 audit entries from API. |

**Pass criteria:** Selecting a dataset loads lineage from API; Access section shows single-user message; events from audit API.

---

## 11. Audit Logs — `/audit-logs`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Page load | — | Fetches audit logs | Open page | `GET /api/v1/audit-logs`. Table shows ID, Action, Target, User, Role, Time, Severity. |
| Filter button | Button | Placeholder | Click | No API; UI only. |
| Export button | Button | Placeholder | Click | No API; UI only. |

**Pass criteria:** Table from API; no errors. Role column shows backend value (single user).

---

## 12. Settings — `/settings`

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Tabs | Buttons | API Keys, Environment, Access, Notifications | Click each tab | Content switches. No API for these tabs. |
| Access tab | Static | Single-user message | Open Access tab | "Single user mode — no RBAC. No login required for testing." |
| + New Key (API Keys) | Button | Placeholder | Click | No backend; UI only. |

**Pass criteria:** All tabs switch; Access tab shows single-user text.

---

## 13. Sidebar & Layout

| Element | Type | Behavior | How to test | Expected |
|--------|------|----------|-------------|----------|
| Nav links | Links | Route to each page | Click each | Correct route; no auth. |
| Collapse sidebar | Button | Toggle sidebar width | Click chevron at bottom | Sidebar collapses/expands. |
| Bell icon, avatar "TF" | Static | No backend | — | No API; single user. |

**Pass criteria:** All routes work; sidebar toggles.

---

## Recommended E2E Test Order (Single User, Full Flow)

1. **Dashboard** — Open `/`; confirm schemas/datasets/jobs load.
2. **Schema Discovery** — Run discovery with `postgresql://postgres:12345@localhost:5432/tdm`; confirm schema card and tables/columns.
3. **PII** — Select schema; click Scan All; confirm table and toasts.
4. **Subsetting** — Select schema and root table; set max rows; Run Subset; confirm toast and job/dataset.
5. **Synthetic** — Select schema; set rows; Generate; confirm toast and dataset.
6. **Dataset Catalog** — Confirm subset and synthetic datasets listed.
7. **Masking** — Select a dataset; add rules JSON; Apply Mask; confirm toast and new masked dataset.
8. **Environments** — Select dataset and QA; Run Provision; confirm toast.
9. **Workflows** — Confirm all jobs listed.
10. **Governance** — Select a dataset; confirm lineage from API; confirm single-user message.
11. **Audit Logs** — Confirm entries from API.
12. **Settings** — Open Access tab; confirm single-user message.

---

## Summary: Buttons and Dynamic Behavior

| Page | Buttons / actions that call API | Buttons / actions that are UI-only |
|------|----------------------------------|------------------------------------|
| Dashboard | — (load: schemas, datasets, jobs) | All cards are links. |
| Schema Discovery | Run Discovery | Schema/table click (trigger GET). |
| PII | Scan All | Schema dropdown (trigger GET). |
| Subsetting | Run Subset | Step buttons, dropdowns. |
| Masking | Apply Mask | Dataset dropdown, rules textarea. |
| Synthetic | Generate | Schema dropdown, rows input. |
| Workflows | — (load: jobs) | — |
| Dataset Catalog | — (load: datasets) | Download (placeholder). |
| Environments | Run Provision, card Provision | Dataset/env dropdowns; job logs poll. |
| Governance | — (load: datasets, audit; lineage on select) | Dataset dropdown. |
| Audit Logs | — (load: audit-logs) | Filter, Export (placeholder). |
| Settings | — | Tab switch, New Key (placeholder). |

All mutation buttons (Run Discovery, Scan All, Run Subset, Apply Mask, Generate, Run Provision) now show **success** and **error toasts** from the backend response. Single-user mode: **no RBAC**, no login; Access/Governance sections state this clearly.

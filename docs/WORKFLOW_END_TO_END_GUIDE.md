# TDM Workflow: End-to-End Flow Guide

> Complete documentation of the Test Data Management (TDM) workflow with real-time examples.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Workflow Steps (Pipeline)](#3-workflow-steps-pipeline)
4. [Input Sources](#4-input-sources)
5. [End-to-End Flow Diagrams](#5-end-to-end-flow-diagrams)
6. [Real-Time Examples](#6-real-time-examples)
7. [API Reference](#7-api-reference)
8. [UI Flow](#8-ui-flow)
9. [Traceability & Lineage](#9-traceability--lineage)

---

## 1. Overview

The TDM platform orchestrates a **6-step pipeline** that transforms test case inputs into provisioned test data:

```
Test Case Input → Schema Discovery → PII Detection → Subsetting → Masking → Synthetic Generation → Provisioning → tdm_target
```

**Key capabilities:**
- **Multiple input modes**: Test case content, test case URLs, domain packs, or existing schema
- **Four synthetic generation modes**: Schema-based, domain-based, URL-crawled, or test case content-based
- **Full traceability**: Test case → Job → Dataset → Provisioned tables
- **Live logs**: Real-time step-by-step logs in the UI

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TDM Platform                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌──────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐  │
│   │  React UI    │────▶│  FastAPI Backend │────▶│  PostgreSQL (Metadata)      │  │
│   │  (Vite)      │     │  (Port 8003)     │     │  - schemas, jobs, datasets  │  │
│   └──────────────┘     └────────┬─────────┘     └─────────────────────────────┘  │
│                                │                                                  │
│                                │  Services                                        │
│                                ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  Workflow Orchestrator                                                   │   │
│   │  ├── Schema Discovery (PostgreSQL inspect)                               │   │
│   │  ├── PII Detection (rule-based / LLM)                                    │   │
│   │  ├── Subsetting (FK-aware extract)                                       │   │
│   │  ├── Masking (hash, redact, tokenize)                                    │   │
│   │  ├── Synthetic (Faker, domain packs, crawler)                             │   │
│   │  └── Provisioning (Parquet → PostgreSQL)                                 │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                │                                                  │
│                                ▼                                                  │
│   ┌─────────────────────┐     ┌─────────────────────────────────────────────┐   │
│   │  Source DB          │     │  tdm_target (PostgreSQL)                     │   │
│   │  (Discovery/Subset) │     │  - Provisioned tables for testing           │   │
│   └─────────────────────┘     └─────────────────────────────────────────────┘   │
│                                                                                   │
│   ┌─────────────────────┐                                                        │
│   │  Dataset Store      │  Parquet files per dataset_version_id                   │
│   │  (Local / MinIO)    │                                                        │
│   └─────────────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Workflow Steps (Pipeline)

### Step 1: Schema Discovery

**Purpose:** Connect to a source database and extract table/column structure, primary keys, and foreign keys.

**Input:** `connection_string`, optional `schemas` (default: `["public"]`)

**Output:** `schema_id`, `schema_version_id`

**What happens:**
- Connects to PostgreSQL via SQLAlchemy
- Inspects tables, columns, data types
- Detects PK/FK relationships
- Stores metadata in `SchemaVersion`, `TableMeta`, `ColumnMeta`, `Relationship`

**Example:**
```json
{
  "connection_string": "postgresql://postgres:12345@localhost:5432/tdm",
  "schemas": ["public"]
}
```

---

### Step 2: PII Detection

**Purpose:** Classify columns that contain PII (email, phone, SSN, etc.) for masking.

**Input:** `schema_version_id`

**Output:** PII map stored in `PIIClassification` table

**What happens:**
- Rule-based classification (column name patterns, data types)
- Optional LLM-based classification (Azure OpenAI)
- Stores `table`, `column`, `pii_type`, `confidence`, `technique`

---

### Step 3: Subsetting

**Purpose:** Extract a subset of data from the source DB while preserving referential integrity.

**Input:** `schema_version_id`, `connection_string`, `root_table`, `max_rows_per_table`

**Output:** `dataset_version_id` (Parquet files in dataset store)

**What happens:**
- Infers root table (e.g., `users`, `customers`) if not specified
- Extracts data respecting FK order
- Writes Parquet files per table
- Stores metadata in `DatasetVersion`, `DatasetMetadata`

**Example:**
```json
{
  "root_table": "users",
  "max_rows_per_table": {"*": 10000, "orders": 50000}
}
```

---

### Step 4: Masking

**Purpose:** Transform PII fields (hash, redact, tokenize) in a dataset.

**Input:** `dataset_version_id`, optional `rules`

**Output:** `masked_dataset_version_id` (new Parquet files)

**What happens:**
- Reads Parquet from source dataset
- Applies masking rules per column
- Writes new dataset version
- Creates lineage record

---

### Step 5: Synthetic Data Generation

**Purpose:** Generate synthetic test data. Supports **four modes**:

| Mode | Trigger | Use Case |
|------|---------|----------|
| **Schema-based** | `schema_version_id` | Clone structure from DB |
| **Domain-based** | `domain` + `scenario` | E-commerce, banking, etc. |
| **URL-crawled** | `test_case_urls` | Crawl form pages, extract fields |
| **Test case content** | `test_case_content` | Parse Cucumber/Selenium steps |

**Input:** `test_case_content`, `test_case_urls`, `domain`, or `schema_version_id` + `row_counts`

**Output:** `dataset_version_id` (Parquet files)

**What happens:**
- **Test case content:** Parses "Enter X as Y" patterns → extracts entities
- **URLs:** Playwright crawls pages → extracts form fields
- **Domain:** Uses pre-configured domain packs (ecommerce, banking, etc.)
- **Schema:** Uses Faker to generate values per column type
- Writes Parquet files, stores metadata

**Example (test case content):**
```
navigate to https://example.com
Enter email as test@example.com
Enter firstname as John
Enter lastname as Doe
click on submit
```
→ Extracts entities: `email`, `firstname`, `lastname` → generates `users` table with rows

---

### Step 6: Provisioning

**Purpose:** Load dataset Parquet files into the target database (`tdm_target`).

**Input:** `dataset_version_id`, `target_env`, `reset_env`, `run_smoke_tests`

**Output:** Tables created in `tdm_target`, row counts per table

**What happens:**
- Reads Parquet from dataset store
- Creates tables in target DB (drop if `reset_env`)
- Loads data
- Runs smoke tests (optional)
- Records lineage

---

## 4. Input Sources

| Source | Required For | Example |
|--------|--------------|---------|
| **Connection string** | discover, pii, subset | `postgresql://user:pass@host:5432/db` |
| **Test case content** | synthetic (content mode) | Cucumber steps, Selenium scripts |
| **Test case URLs** | synthetic (crawl mode) | `["https://app.example.com/register"]` |
| **Domain** | synthetic (domain mode) | `ecommerce`, `banking`, `telecom` |
| **Schema version ID** | pii, subset, synthetic (schema mode) | From discovery |
| **Dataset version ID** | mask, provision | From subset or synthetic |

---

## 5. End-to-End Flow Diagrams

### Flow A: Full Workflow (Database → Provisioned)

```
[Source DB] → discover → [Schema] → pii → [PII Map]
                              ↓
                         subset → [Dataset Parquet]
                              ↓
                         mask  → [Masked Parquet]
                              ↓
                         synthetic (optional, from schema)
                              ↓
                         provision → [tdm_target]
```

### Flow B: Test Case Content → Synthetic → Provision

```
[Test Case Content] → synthetic (content mode) → [Dataset Parquet] → provision → [tdm_target]
```

### Flow C: Test Case URLs → Synthetic → Provision

```
[Test Case URLs] → crawl → synthetic (crawl mode) → [Dataset Parquet] → provision → [tdm_target]
```

### Flow D: Domain Only → Synthetic → Provision

```
[Domain + Scenario] → synthetic (domain mode) → [Dataset Parquet] → provision → [tdm_target]
```

---

## 6. Real-Time Examples

### Example 1: Full Workflow from Database

**Scenario:** Clone production schema, subset, mask PII, generate synthetic data, provision to QA.

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "postgresql://postgres:12345@localhost:5432/tdm",
    "operations": ["discover", "pii", "subset", "mask", "synthetic", "provision"],
    "config": {
      "subset": {"root_table": "users", "max_rows_per_table": {"*": 5000}},
      "synthetic": {"row_counts": {"*": 1000}},
      "provision": {"target_env": "default", "reset_env": true, "run_smoke_tests": true}
    }
  }'
```

**Response:**
```json
{
  "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "job_id": "f1e2d3c4-b5a6-9870-fedc-ba0987654321",
  "operations": {},
  "overall_status": "queued",
  "start_time": "2025-02-23T14:30:00.000Z"
}
```

**Poll logs:**
```bash
curl http://localhost:8003/api/v1/workflow/logs/f1e2d3c4-b5a6-9870-fedc-ba0987654321
```

**Output:**
```json
{
  "job_id": "f1e2d3c4-b5a6-9870-fedc-ba0987654321",
  "job_status": "completed",
  "logs": [
    {"step": "discover", "level": "started", "message": "Starting schema discovery"},
    {"step": "discover", "level": "completed", "message": "Schema discovered: source_public"},
    {"step": "pii", "level": "started", "message": "Starting PII classification"},
    {"step": "pii", "level": "completed", "message": "PII classification completed"},
    {"step": "subset", "level": "started", "message": "Starting subsetting"},
    {"step": "subset", "level": "completed", "message": "Subsetting completed. Dataset: abc123..."},
    {"step": "mask", "level": "started", "message": "Starting masking"},
    {"step": "mask", "level": "completed", "message": "Masking completed."},
    {"step": "synthetic", "level": "started", "message": "Starting synthetic data generation"},
    {"step": "synthetic", "level": "completed", "message": "Synthetic data generated using schema mode."},
    {"step": "provision", "level": "started", "message": "Starting provisioning"},
    {"step": "provision", "level": "completed", "message": "Provisioning completed."}
  ]
}
```

---

### Example 2: Test Case Content → Synthetic → Provision

**Scenario:** User pastes Cucumber test steps. System extracts form fields and generates matching data.

**Test case content:**
```
Feature: User Registration
  Scenario: New user signs up
    Given I navigate to https://app.example.com/register
    When I enter "email" as "user@test.com"
    And I enter "firstname" as "John"
    And I enter "lastname" as "Doe"
    And I enter "password" as "Secret123"
    And I click on "Submit"
    Then I should see "Welcome"
```

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_content": "When I enter \"email\" as \"user@test.com\"\nAnd I enter \"firstname\" as \"John\"\nAnd I enter \"lastname\" as \"Doe\"",
    "domain": "generic",
    "operations": ["synthetic", "provision"],
    "config": {
      "synthetic": {"row_counts": {"*": 500}},
      "provision": {"target_env": "default", "run_smoke_tests": true}
    }
  }'
```

**Result:** Entities `email`, `firstname`, `lastname` → generates `users` table with 500 rows → provisions to `tdm_target`.

---

### Example 3: Domain-Based E-Commerce Data

**Scenario:** Generate e-commerce test data without any database or test case.

**Request:**
```bash
curl -X POST http://localhost:8003/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "ecommerce",
    "operations": ["synthetic", "provision"],
    "config": {
      "synthetic": {"row_counts": {"*": 1000}, "scenario": "b2c"},
      "provision": {"target_env": "default"}
    }
  }'
```

**Result:** Generates `customer`, `order`, `order_item`, `product`, `payment` tables with realistic data → provisions to `tdm_target`.

---

### Example 4: UI Flow (Workflow Page)

1. Go to **Workflows** → `/workflows`
2. Paste test case content in the text area
3. Select operations: `discover`, `pii`, `subset`, `mask`, `synthetic`, `provision`
4. Set **Row Count** (e.g., 1000)
5. Click **Execute Workflow**
6. Job appears in **Execution History**; click to view logs
7. **Logs** tab shows live step-by-step output
8. **Data Lineage** tab shows test case → job → dataset → provisioned tables

---

## 7. API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/workflow/execute` | POST | Execute full workflow |
| `/api/v1/workflow/logs/{job_id}` | GET | Get workflow logs (live) |
| `/api/v1/workflow/status/{workflow_id}` | GET | Get workflow status |
| `/api/v1/workflow/templates` | GET | Get workflow templates |
| `/api/v1/workflow/analyze-test-case` | POST | Analyze if test case needs synthetic data |
| `/api/v1/discover-schema` | POST | Schema discovery only |
| `/api/v1/pii/classify` | POST | PII classification only |
| `/api/v1/subset` | POST | Subsetting only |
| `/api/v1/mask` | POST | Masking only |
| `/api/v1/synthetic` | POST | Synthetic generation only |
| `/api/v1/provision` | POST | Provisioning only |
| `/api/v1/schemas` | GET | List schemas |
| `/api/v1/datasets` | GET | List datasets |
| `/api/v1/jobs` | GET | List jobs |
| `/api/v1/target-tables` | GET | List provisioned tables in tdm_target |
| `/api/v1/workflow/classify-intent` | POST | Dynamic Decision Engine — get recommended operations |
| `/api/v1/quality/dataset/{id}` | GET | Synthetic quality score and report |
| `/api/v1/schema-fusion/fuse` | POST | Fuse UI + API + DB + Domain schemas |
| `/api/v1/provision/schema-evolution/{id}` | GET | Schema evolution detection |
| `/api/v1/provision/migration-script/{id}` | GET | Generate migration SQL script |
| `/api/v1/lineage/job/{id}/full` | GET | Full lineage with fallbacks, quality score |

---

## 8. UI Flow

### Dashboard (Command Center)
- **Metrics:** Datasets Ready, Rows Generated, Workflows Completed, Failed Jobs, Running Jobs
- **Quick Actions:** Execute Workflow, Browse Datasets
- **Job Timeline:** Recent jobs with status
- **Recent Datasets:** Latest datasets with links to catalog

### Workflows Page
- **Test case content:** Textarea for Cucumber/Selenium steps
- **Test case URLs:** Optional URLs to crawl
- **Operations:** Toggle discover, pii, subset, mask, synthetic, provision
- **Row count:** Number of rows per entity (default 1000)
- **Execute:** Starts workflow; job appears in history
- **Logs:** Live view when job selected
- **Lineage:** Test case → job → dataset → tables

### Dataset Catalog
- Lists all datasets with type, rows, tables
- Export per dataset or Export All (CSV)

### Audit Logs
- Filter by severity, action
- Export to CSV

---

## 9. Traceability & Lineage

```
Test Case (content/URLs) 
    → test_case_id (hash)
    → Job (workflow_id, job_id)
    → Dataset (dataset_version_id)
    → Provisioned Tables (tdm_target)
```

**Traceability:**
- `Job.request_json` stores `test_case_id`, `test_case_summary` for audit
- `Job.result_json` stores `operations` with `schema_version_id`, `dataset_version_id`
- `Lineage` table links source → target per operation

**Job Trace API:**
```bash
curl http://localhost:8003/api/v1/job/{job_id}/trace
```

Returns: workflow_id, test_case_id, operations, dataset_version_id, provisioned_tables, row_counts.

---

## Appendix: Quick Reference

### Environment Variables
```bash
DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm
TARGET_DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm_target
API_PORT=8003
```

### Start Services
```powershell
# Backend
cd tdm-backend
.\start_backend.ps1

# UI
cd tdm-ui
npm run dev
```

### Access
- **UI:** http://localhost:5173
- **API:** http://localhost:8003
- **API Docs:** http://localhost:8003/docs

---

---

## 10. TDM Platform v2.0 Enhancements (New)

### 10.1 Dynamic Decision Engine
- **Intent Classifier**: Analyzes test case content, URLs, connection string, domain to determine operations
- **Rules**: connection_string → discover+subset; URLs → crawl; domain → domain-pack; PII → masking
- **API**: `POST /workflow/classify-intent` returns recommended operations and preferred_synthetic_mode

### 10.2 Global TDM Context (JobContext)
Every job maintains:
- `test_case_id`, `ui_schemas`, `api_schemas`, `db_schemas`, `unified_schema`
- `domain_pack`, `scenario`, `operations`, `fallbacks_used`, `quality_score`
- Stored in `Job.request_json.job_context` and `Job.result_json.job_context`

### 10.3 Modular LangGraph Subgraphs
- `decision_graph`: parse_user_input → classify_intent → generate_pipeline_plan
- `discover_graph`, `pii_graph`, `subset_graph`, `mask_graph`, `synthetic_graph`, `provisioning_graph`
- `schema_fusion_graph`, `quality_graph` (foundation)

### 10.4 Schema Fusion Engine (Phase 2 Foundation)
- Schema Normalizer, Field Matcher, Weighted Fusion (DB > API > UI > Test case > Domain)
- `UnifiedSchemaVersion` model for fused schemas

### 10.5 UI Enhancements
- **Quality Dashboard** (`/quality`): Radial score, quality metrics, dataset selector
- **Schema Fusion Viewer** (`/schema-fusion`): Run fusion, domain + test case entities
- **Governance & Lineage**: Full lineage graph, Job lineage with fallbacks, quality score
- **Environment Provisioning**: Schema evolution, migration script, table-by-table
- **Workflow**: "Classify Intent" button for Dynamic Decision Engine

### 10.6 Phase 3–7 Implemented
- **Phase 3**: Rule-based synthetic (country→currency), domain pack, flow templates
- **Phase 4**: Self-healing fallbacks (crawl, synthetic, provision retry)
- **Phase 5**: Full quality engine (null ratio, type consistency, drift)
- **Phase 6**: Schema evolution detection, migration script generator
- **Phase 7**: Lineage details (field-level, fallbacks_used, quality_score)

---

*Document version: 2.0 | Last updated: February 2025*

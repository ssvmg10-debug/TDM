# Enterprise TDM Platform — End-to-End Implementation Document

**Stack:** PostgreSQL | Azure OpenAI | LangGraph | FastAPI | MinIO/S3 | Redis  
**Version:** 1.0  
**Last Updated:** February 2025

---

## Table of Contents

1. [Technology Choices & Prerequisites](#1-technology-choices--prerequisites)
2. [Core System Architecture](#2-core-system-architecture)
3. [LangGraph Orchestration Design](#3-langgraph-orchestration-design)
4. [Module 1 — Schema Discovery Agent](#4-module-1--schema-discovery-agent)
5. [Module 2 — PII Classification Agent](#5-module-2--pii-classification-agent)
6. [Module 3 — Subsetting Agent](#6-module-3--subsetting-agent)
7. [Module 4 — Masking Agent](#7-module-4--masking-agent)
8. [Module 5 — Synthetic Data Agent](#8-module-5--synthetic-data-agent)
9. [Module 6 — Provisioning Agent](#9-module-6--provisioning-agent)
10. [Governance & Lineage Engine](#10-governance--lineage-engine)
11. [Data Layer — Metadata Store (PostgreSQL)](#11-data-layer--metadata-store-postgresql)
12. [Data Layer — Dataset Store & Cache](#12-data-layer--dataset-store--cache)
13. [API Design (FastAPI)](#13-api-design-fastapi)
14. [UI Design (Self-Service Portal)](#14-ui-design-self-service-portal)
15. [LangGraph Supergraph Design](#15-langgraph-supergraph-design)
16. [Infrastructure & Deployment](#16-infrastructure--deployment)
17. [Testing Strategy](#17-testing-strategy)
18. [90-Day Execution Plan](#18-90-day-execution-plan)
19. [Azure OpenAI Integration](#19-azure-openai-integration)
20. [Environment & Configuration](#20-environment--configuration)

---

## 1. Technology Choices & Prerequisites

| Component | Choice | Notes |
|-----------|--------|--------|
| **Database (Metadata + Source/Target)** | PostgreSQL 15+ | Single DB tech for metadata store; can also be source/target for subset/provision |
| **LLM** | Azure OpenAI | GPT-4o / gpt-4o-mini for PII classification, synthetic hints; API key required |
| **Orchestration** | LangGraph | Stateful workflows, branching, retries, subgraphs |
| **API** | FastAPI | Async, OpenAPI, Pydantic |
| **Dataset Storage** | MinIO (S3-compatible) | Parquet/CSV for dataset versions |
| **Cache / State** | Redis 7+ | Job state, TTL datasets, session cache |
| **Optional Message Bus** | Kafka | Event-driven flows; optional for Phase 1 |

**Prerequisites**

- Python 3.11+
- Docker & Docker Compose (for local stack)
- Azure OpenAI resource + API key + deployment names (e.g. `gpt-4o`, `gpt-4o-mini`)
- PostgreSQL 15+ (local or managed)
- MinIO server (or AWS S3)
- Redis 7+

---

## 2. Core System Architecture

### 2.1 High-Level Microservice Layout

```
tdm/
├── tdm-orchestrator/          # LangGraph orchestrator
│   ├── graphs/
│   │   ├── master.py          # Supergraph: parse_request → decide_operation → execute_subgraph → finalize
│   │   ├── schema_discovery.py
│   │   ├── pii_classification.py
│   │   ├── subsetting.py
│   │   ├── masking.py
│   │   ├── synthetic.py
│   │   └── provisioning.py
│   ├── state.py
│   └── nodes/
├── agents/
│   ├── schema_discovery/
│   ├── pii_detection/
│   ├── subsetting/
│   ├── masking/
│   ├── synthetic/
│   └── provisioning/
├── tdm-api/                   # FastAPI application
│   ├── main.py
│   ├── routers/
│   ├── services/
│   └── models/
├── tdm-ui/                    # Web portal (React/Vue/Next.js)
├── tdm-dataset-store/         # MinIO/S3 client + paths
├── tdm-metadata-store/        # PostgreSQL models, migrations, repos
├── tdm-cache/                 # Redis client, key patterns
└── tdm-message-bus/           # Optional Kafka producers/consumers
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **tdm-orchestrator** | Runs LangGraph workflows; invokes agents; persists state to Redis/DB |
| **agents/** | Domain logic: discovery, PII, subset, mask, synthetic, provision |
| **tdm-api** | REST API; auth; calls orchestrator or agents directly for sync paths |
| **tdm-metadata-store** | All metadata: schemas, tables, columns, PII, datasets, lineage, jobs |
| **tdm-dataset-store** | Object storage for parquet/csv per dataset version |
| **tdm-cache** | Job state, lock keys, TTL for temp datasets |

### 2.3 Data Flow (High Level)

- **Metadata:** Source DB → Schema Discovery → Metadata Store (PostgreSQL).  
- **PII:** Metadata + optional sampling → PII Agent (Regex + Azure OpenAI) → `pii_classification` table.  
- **Subset:** Metadata + request → Subsetting Agent → Parquet in Dataset Store + `dataset_versions` row.  
- **Mask:** Dataset + rules → Masking Agent → New version in Dataset Store.  
- **Synthetic:** UI/API/DB schemas → Synthetic Agent → Relational SDV → Dataset Store.  
- **Provision:** Dataset version → Provisioning Agent → Target PostgreSQL (or other) + smoke tests.

---

## 3. LangGraph Orchestration Design

### 3.1 Why LangGraph for TDM

- **Multiple workflows:** Prod→Subset→Mask→QA; UI→Schema→Synthetic→Provision; API schema→Merge→Synthetic→Perf.
- **Stateful nodes:** Shared state (e.g. `TDMState`) across nodes.
- **Retries & branching:** Conditional edges, human-in-the-loop, failure handling.
- **Subgraphs:** Each agent = subgraph; master graph invokes by operation type.
- **Long-running:** Checkpointing to Redis/DB; resume by job_id.

### 3.2 Shared State Contract (Pydantic)

```python
# tdm-orchestrator/state.py
from typing import TypedDict, Any, Optional
from pydantic import BaseModel

class TDMState(TypedDict, total=False):
    job_id: str
    operation: str  # TDM_SYNTHETIC_RUN | TDM_SUBSET_MASK_PROVISION | ...
    request: dict
    # Schema discovery
    connection_config: dict
    tables: list
    columns: list
    relationships: list
    stats: dict
    schema_version_id: str
    # PII
    pii_map: list
    # Subset
    subset_spec: dict
    subset_dataset_path: str
    # Mask
    masking_rules: dict
    masked_dataset_path: str
    # Synthetic
    merged_schema: dict
    synthetic_dataset_path: str
    # Provision
    target_env: str
    provisioning_result: dict
    # Common
    errors: list
    current_node: str
```

### 3.3 Node Naming Convention

- **Orchestrator:** `parse_request`, `decide_operation`, `execute_subgraph`, `finalize`.
- **Subgraphs:** `connect_db`, `fetch_tables`, `fetch_columns`, … (see each module).

---

## 4. Module 1 — Schema Discovery Agent

**Purpose:** Discover table structures, column types, statistics, PKs/FKs, and feed metadata store.

### 4.1 Nodes (LangGraph Subgraph)

| Node | Input | Output | Description |
|------|--------|--------|-------------|
| `connect_db` | `connection_config` | `engine` / connection | SQLAlchemy engine for PostgreSQL |
| `fetch_tables` | `engine` | `tables[]` | List tables (include schema name) |
| `fetch_columns` | `engine`, `tables` | `columns[]` | Name, type, nullable, default |
| `infer_column_types` | `columns` | `columns` (enriched) | Refine types (e.g. varchar → email) |
| `profile_statistics` | `engine`, `tables` | `stats` | Row counts, min/max, distinct (optional sampling) |
| `infer_primary_keys` | `engine`, `tables` | `pk_map` | PK columns per table |
| `infer_foreign_keys` | `engine`, `tables` | `relationships[]` | FK pairs (parent, child, columns) |
| `save_metadata` | all above | `schema_version_id` | Insert into metadata store |

### 4.2 Tools / Libraries

- **SQLAlchemy** 2.x + `inspect(engine)` for tables, columns, PKs, FKs.
- **PostgreSQL:** Use `pg_catalog` / `information_schema` if needed for extras.
- **Profiler:** Custom or **Great Expectations** / **Pandas** for row counts and basic stats (with sampling for large tables).
- **Type inference:** Regex + optional Azure OpenAI for semantic types (e.g. “email”, “phone”) — can be shared with PII agent.

### 4.3 Input/Output Contracts

**Input (API / Orchestrator):**

```json
{
  "connection_string": "postgresql://user:pass@host:5432/dbname",
  "schemas": ["public"],
  "include_stats": true,
  "sample_size": 10000
}
```

**Output (stored in metadata DB, returned in response):**

```json
{
  "schema_version_id": "uuid",
  "tables": [
    { "name": "customers", "schema": "public", "row_count": 100000 }
  ],
  "columns": [
    { "table": "customers", "name": "email", "data_type": "varchar", "inferred_type": "email", "nullable": true }
  ],
  "relationships": [
    { "parent_table": "customers", "child_table": "orders", "parent_column": "id", "child_column": "customer_id" }
  ],
  "stats": { "customers": { "row_count": 100000, "email_distinct": 95000 } }
}
```

### 4.4 Database Impact

- Insert/update: `schemas`, `schema_versions`, `tables`, `columns`, `relationships`.
- Optional: `stats` in `dataset_metadata` or dedicated `table_stats` table.

### 4.5 Implementation Tasks

1. Implement PostgreSQL connector (SQLAlchemy, connection pooling, optional SSL).
2. Implement profiler (row count, optional min/max/distinct with sampling).
3. Implement relationship inference (PK/FK from SQLAlchemy inspector).
4. Implement metadata storage (repos for schemas, tables, columns, relationships).
5. Build LangGraph subgraph (`schema_discovery.py`) with the nodes above.
6. Add REST: `POST /discover-schema` calling the subgraph or sync discovery service.

### 4.6 File Structure

```
agents/schema_discovery/
├── __init__.py
├── connector.py      # PostgreSQL connection, inspector
├── profiler.py       # Statistics with sampling
├── type_inference.py # Regex + optional LLM
├── relationship_inference.py
└── metadata_writer.py
tdm-metadata-store/repositories/schema_repository.py
graphs/schema_discovery.py
```

---

## 5. Module 2 — PII Classification Agent

**Purpose:** Identify columns that contain PII (email, phone, SSN, name, address, etc.) using regex + LLM.

### 5.1 Nodes

| Node | Description |
|------|-------------|
| `load_schema_metadata` | Load tables/columns from metadata store for given schema_version_id |
| `detect_pii_regex` | Apply regex patterns (email, phone, SSN, credit card, etc.) on sample or full column |
| `detect_pii_llm` | Use Azure OpenAI to classify semantic PII (e.g. “customer name”, “billing address”) |
| `validate_pii` | Merge regex + LLM results; resolve conflicts; confidence score |
| `store_pii_metadata` | Persist to `pii_classification` table |

### 5.2 Techniques

- **Regex:** Predefined patterns for email, phone (E.164), SSN, credit card (masked), address snippets.
- **LLM (Azure OpenAI):** Send column name + sample values (anonymized or hashed) + schema context; use structured output (e.g. Instructor / JSON mode) to get PII type and confidence.
- **Storage:** One row per (schema_version_id, table_name, column_name) with pii_type, technique (regex/llm), confidence.

### 5.3 Input/Output

**Input:**

```json
{
  "schema_version_id": "uuid",
  "use_llm": true,
  "sample_size_per_column": 100
}
```

**Output (stored and returned):**

```json
{
  "pii_map": [
    { "table": "customers", "column": "email", "pii_type": "email", "confidence": 1.0, "technique": "regex" },
    { "table": "customers", "column": "full_name", "pii_type": "person_name", "confidence": 0.95, "technique": "llm" }
  ]
}
```

### 5.4 Implementation Tasks

1. Define regex patterns (module or config file).
2. Implement Azure OpenAI client (see [§19](#19-azure-openai-integration)); structured output for PII labels.
3. Implement `detect_pii_regex` and `detect_pii_llm` nodes.
4. Implement merge/validation and persistence to `pii_classification`.
5. Build LangGraph subgraph and expose via `POST /pii/classify` or as part of discovery.

### 5.5 File Structure

```
agents/pii_detection/
├── __init__.py
├── regex_patterns.py
├── llm_classifier.py   # Azure OpenAI
├── merger.py
└── repository.py       # pii_classification CRUD
graphs/pii_classification.py
```

---

## 6. Module 3 — Subsetting Agent

**Purpose:** Extract a consistent, referentially intact subset from production (PostgreSQL) with FK-aware traversal.

### 6.1 Nodes

| Node | Description |
|------|-------------|
| `load_profiled_metadata` | Load tables, columns, relationships, stats from metadata store |
| `parse_subset_request` | Parse filters, date range, row limits, % sampling |
| `build_fk_graph` | Build directed graph of FK relationships (parent → child) |
| `evaluate_conditions` | Resolve which tables have filters and in what order to traverse |
| `recursive_row_extract` | Start from root table(s); follow FKs; extract IDs then dependent rows (breadth/depth) |
| `merge_results` | Assemble per-table DataFrames/files |
| `store_subset_dataset` | Write parquet per table to Dataset Store; create `dataset_versions` and lineage |

### 6.2 Features

- **Root table + filter:** e.g. “customers where region = 'US'” then all related orders, order_items, etc.
- **Time-based:** e.g. “orders where created_at between X and Y”.
- **Row limits / % sampling:** Max rows per table or N% random sample with referential integrity (include all referenced parents).
- **Recursive FK traversal:** Respect FK direction; optional cycle detection.

### 6.3 Input/Output

**Input:**

```json
{
  "schema_version_id": "uuid",
  "connection_string": "postgresql://...",
  "root_table": "customers",
  "filters": { "customers": { "region": "US" } },
  "max_rows_per_table": { "customers": 10000, "orders": 50000 },
  "date_range": { "table": "orders", "column": "created_at", "start": "2024-01-01", "end": "2024-12-31" }
}
```

**Output:**

- Dataset version ID.
- Paths in Dataset Store: `/datasets/<version_id>/<table>.parquet`.

### 6.4 Implementation Tasks

1. FK graph builder from metadata `relationships`.
2. Recursive extraction: query root with filters → get PKs → query children by FK → repeat.
3. Apply max_rows and sampling in a consistent way (e.g. limit on root, then proportional on children).
4. Export to Parquet (PyArrow/Pandas); upload to MinIO.
5. Create `dataset_versions` and `lineage` records.
6. LangGraph subgraph + `POST /subset`.

### 6.5 File Structure

```
agents/subsetting/
├── __init__.py
├── fk_graph.py
├── extractor.py
├── exporter.py
└── subset_parser.py
graphs/subsetting.py
```

---

## 7. Module 4 — Masking Agent

**Purpose:** Apply deterministic masking to PII and sensitive columns (format-preserving, repeatable across environments).

### 7.1 Nodes

| Node | Description |
|------|-------------|
| `load_dataset` | Load dataset version from Dataset Store (parquet per table) |
| `load_masking_rules` | From `masking_rules` table or request body (table.column → rule type) |
| `apply_mask_transformers` | Apply FPE, deterministic hash, tokenization, nulling, redaction per rule |
| `validate_integrity` | Check FK consistency (same FK value masked to same value); row counts unchanged |
| `store_masked_dataset` | Write new version to Dataset Store; lineage link (source_version → masked_version) |

### 7.2 Mask Types

| Type | Description | Use Case |
|------|-------------|----------|
| `mask.email_deterministic` | Same email → same masked email | Joins, lookups |
| `mask.fpe_pan` | Format-preserving encryption for card numbers | PCI |
| `mask.tokenize` | Replace with token; reversible via vault (optional) | PCI, reversible |
| `mask.null` | Set to NULL | Drop PII |
| `mask.redact` | Replace with fixed string (e.g. REDACTED) | Simple hide |
| `mask.hash` | Deterministic hash (e.g. SHA256 with salt) | Non-reversible identifier |

### 7.3 Masking Rules JSON

```json
{
  "customers.email": "mask.email_deterministic",
  "customers.pan": "mask.fpe_pan",
  "orders.card_last4": "mask.redact",
  "customers.ssn": "mask.hash"
}
```

### 7.4 Implementation Tasks

1. Implement transformers for each mask type (use e.g. `cryptography` for FPE, hashlib for hash).
2. Load rules by dataset/schema; apply per column.
3. Validate referential integrity (deterministic masking keeps FKs aligned).
4. Store new version and lineage.
5. LangGraph subgraph + `POST /mask`.

### 7.5 File Structure

```
agents/masking/
├── __init__.py
├── transformers/
│   ├── fpe.py
│   ├── deterministic_hash.py
│   ├── tokenize.py
│   ├── null_redact.py
│   └── email_mask.py
├── rule_loader.py
└── validator.py
graphs/masking.py
```

---

## 8. Module 5 — Synthetic Data Agent

**Purpose:** Generate multi-table, realistic synthetic data from UI + API + DB schema fusion, with relational consistency.

### 8.1 Nodes

| Node | Description |
|------|-------------|
| `parse_request` | Parse request (UI URLs, API spec URLs, schema_version_id, domain pack, row counts) |
| `crawl_ui` (optional) | 3-phase DOM walk: discover forms/inputs, tables, key elements; extract field names and types |
| `extract_html_schema` | Normalize crawled fields into a schema (entity + attributes) |
| `collect_api_schema` | Fetch OpenAPI/Swagger; map to entities and attributes |
| `fetch_db_schema` (optional) | Load from metadata store (tables/columns/relationships) |
| `merge_all_schemas` | Unify UI, API, DB into one normalized schema (Pydantic models); resolve conflicts |
| `normalize_schema` | Final entity list, attributes, types, FKs |
| `train_sdv_relational_model` | Use SDV (Synthetic Data Vault) relational models (e.g. HMA, PAR) on structure |
| `generate_multi_table_data` | Generate data for each table with FK consistency |
| `validate_distribution` | Optional: compare distributions to sample; check constraints |
| `store_dataset` | Save parquet to Dataset Store; create dataset version and lineage |

### 8.2 Improvements Over Naive Approach

- **Crawling:** 3-phase DOM walk (forms → tables → other); robust selectors; headless browser (Playwright) optional.
- **Schema merge:** Deterministic merge with Pydantic; priority order (e.g. DB > API > UI).
- **Multi-table:** SDV relational (parent-child); domain packs for common shapes.
- **Domain packs (examples):**

```yaml
ecommerce:
  entities: [customer, order, order_item, payment]
  relationships: [customer.id -> order.customer_id, order.id -> order_item.order_id, ...]
banking:
  entities: [account, transaction, ledger, beneficiary]
telecom:
  entities: [customer, sims, recharge_history]
```

### 8.3 Input/Output

**Input:**

```json
{
  "ui_urls": ["https://app.example.com/registration"],
  "api_spec_url": "https://api.example.com/openapi.json",
  "schema_version_id": "optional-uuid",
  "domain_pack": "ecommerce",
  "row_counts": { "customer": 1000, "order": 5000 },
  "scenario_template": "default"
}
```

**Output:** Dataset version ID; parquet files in Dataset Store under `/datasets/<version_id>/`.

### 8.4 Implementation Tasks

1. Implement UI crawler (3-phase); optional Playwright.
2. Implement API schema collector (OpenAPI parser).
3. Implement schema merge (Pydantic); handle naming and type mapping.
4. Integrate SDV relational (install `sdv`, define metadata from normalized schema).
5. Domain packs as YAML/JSON configs.
6. Generate → validate → store; LangGraph subgraph + `POST /synthetic`.

### 8.5 File Structure

```
agents/synthetic/
├── __init__.py
├── crawler/
│   ├── dom_walk.py
│   └── schema_extractor.py
├── api_schema.py
├── schema_merger.py
├── sdv_runner.py
├── domain_packs/
│   ├── ecommerce.yaml
│   ├── banking.yaml
│   └── telecom.yaml
└── validator.py
graphs/synthetic.py
```

---

## 9. Module 6 — Provisioning Agent

**Purpose:** Push a dataset version into a target environment (QA, SIT, UAT, Perf, Dev); optional reset and smoke tests.

### 9.1 Nodes

| Node | Description |
|------|-------------|
| `validate_dataset_version` | Check version exists in Dataset Store and metadata; check format |
| `connect_env` | Connect to target PostgreSQL using env-specific connection config |
| `reset_env` (optional) | Truncate target tables (in FK-safe order) or drop/recreate |
| `apply_schema` | Create tables if not exist (from metadata store schema for that version) |
| `load_data` | Read parquet from Dataset Store; bulk insert (COPY or batch INSERT) |
| `run_smoke_tests` | Row counts, optional FK checks, optional sample queries |
| `complete_provisioning` | Update job status; write lineage (dataset_version → target_env) |

### 9.2 Supported Environments

- QA, SIT, UAT, Perf, Dev (config-driven connection strings per env).

### 9.3 Input/Output

**Input:**

```json
{
  "dataset_version_id": "uuid",
  "target_env": "QA",
  "reset_env": true,
  "run_smoke_tests": true
}
```

**Output:**

```json
{
  "job_id": "uuid",
  "status": "completed",
  "tables_loaded": ["customers", "orders"],
  "row_counts": { "customers": 10000, "orders": 50000 },
  "smoke_test_results": { "passed": true, "checks": [...] }
}
```

### 9.4 Implementation Tasks

1. Target connection manager (per env from config/DB).
2. Safe truncate order (reverse FK dependency).
3. Schema apply (CREATE TABLE IF NOT EXISTS from metadata).
4. Bulk load (PostgreSQL COPY or batched inserts).
5. Smoke tests (counts, FK checks).
6. LangGraph subgraph + `POST /provision`.

### 9.5 File Structure

```
agents/provisioning/
├── __init__.py
├── target_connector.py
├── schema_applier.py
├── data_loader.py
├── smoke_tests.py
└── env_config.py
graphs/provisioning.py
```

---

## 10. Governance & Lineage Engine

**Purpose:** Track provenance of datasets (discovery → subset → mask → synthetic → provision) and support governance.

### 10.1 Lineage Model

- **Nodes:** `schema_version`, `dataset_version`, `environment`, `job`.
- **Edges:** `discovered_from` (schema ← source DB), `derived_from` (dataset B ← dataset A), `provisioned_to` (dataset → env).
- Stored in `lineage` table: `source_type`, `source_id`, `target_type`, `target_id`, `operation`, `job_id`, `created_at`.

### 10.2 Governance

- **PII metadata:** All PII columns tagged; masking rules versioned.
- **Audit:** Job logs (who, when, what operation, which resources).
- **RBAC:** Roles (Admin, Operator, Viewer) applied in API and UI (see §13, §14).

### 10.3 Implementation

- Write lineage rows from each agent (subset, mask, synthetic, provision).
- Optional: graph API for lineage visualization (e.g. `GET /lineage/dataset/{id}`).

---

## 11. Data Layer — Metadata Store (PostgreSQL)

All metadata lives in PostgreSQL. Use migrations (e.g. Alembic) for versioned schema.

### 11.1 Tables

| Table | Purpose |
|-------|---------|
| `schemas` | Logical schema (name, description, source_connection_id) |
| `schema_versions` | Immutable snapshot per discovery run (schema_id, version_number, discovered_at, status) |
| `tables` | schema_version_id, name, schema (namespace), row_count (optional) |
| `columns` | table_id, name, data_type, inferred_type, nullable, ordinal_position |
| `relationships` | parent_table_id, child_table_id, parent_column_id, child_column_id, name (optional) |
| `pii_classification` | schema_version_id, table_name, column_name, pii_type, technique, confidence, created_at |
| `dataset_versions` | id (UUID), name, schema_version_id (optional), source_type (subset|synthetic|masked), status, path_prefix, created_at |
| `dataset_metadata` | dataset_version_id, key-value for stats, row_counts, params |
| `lineage` | source_type, source_id, target_type, target_id, operation, job_id, created_at |
| `masking_rules` | id, name, schema_version_id or dataset_version_id, rules_json, created_at |
| `jobs` | id, operation, status, request_json, result_json, started_at, finished_at, user_id |
| `job_logs` | job_id, level, message, created_at |
| `environments` | id, name (QA|SIT|UAT|Perf|Dev), connection_string_encrypted, config_json |
| `connections` | id, name, connection_string_encrypted, type (postgres), created_at |

### 11.2 Example DDL (Core Tables)

```sql
-- schemas
CREATE TABLE schemas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  source_connection_id UUID REFERENCES connections(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- schema_versions
CREATE TABLE schema_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_id UUID NOT NULL REFERENCES schemas(id),
  version_number INT NOT NULL,
  discovered_at TIMESTAMPTZ DEFAULT NOW(),
  status VARCHAR(50) DEFAULT 'active',
  UNIQUE(schema_id, version_number)
);

-- tables
CREATE TABLE tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version_id UUID NOT NULL REFERENCES schema_versions(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  schema_name VARCHAR(255) DEFAULT 'public',
  row_count BIGINT,
  UNIQUE(schema_version_id, schema_name, name)
);

-- columns
CREATE TABLE columns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id UUID NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  data_type VARCHAR(100),
  inferred_type VARCHAR(100),
  nullable BOOLEAN DEFAULT TRUE,
  ordinal_position INT,
  UNIQUE(table_id, name)
);

-- relationships
CREATE TABLE relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_table_id UUID NOT NULL REFERENCES tables(id),
  child_table_id UUID NOT NULL REFERENCES tables(id),
  parent_column_id UUID NOT NULL REFERENCES columns(id),
  child_column_id UUID NOT NULL REFERENCES columns(id)
);

-- pii_classification
CREATE TABLE pii_classification (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version_id UUID NOT NULL REFERENCES schema_versions(id) ON DELETE CASCADE,
  table_name VARCHAR(255) NOT NULL,
  column_name VARCHAR(255) NOT NULL,
  pii_type VARCHAR(100) NOT NULL,
  technique VARCHAR(50),
  confidence DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(schema_version_id, table_name, column_name)
);

-- dataset_versions
CREATE TABLE dataset_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255),
  schema_version_id UUID REFERENCES schema_versions(id),
  source_type VARCHAR(50) NOT NULL,
  status VARCHAR(50) DEFAULT 'active',
  path_prefix VARCHAR(500) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- dataset_metadata (key-value stats and params per dataset version)
CREATE TABLE dataset_metadata (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_version_id UUID NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
  meta_key VARCHAR(255) NOT NULL,
  meta_value JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(dataset_version_id, meta_key)
);

-- lineage
CREATE TABLE lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type VARCHAR(50) NOT NULL,
  source_id VARCHAR(255) NOT NULL,
  target_type VARCHAR(50) NOT NULL,
  target_id VARCHAR(255) NOT NULL,
  operation VARCHAR(100),
  job_id UUID REFERENCES jobs(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- masking_rules
CREATE TABLE masking_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255),
  schema_version_id UUID REFERENCES schema_versions(id),
  rules_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- jobs
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  operation VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  request_json JSONB,
  result_json JSONB,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  user_id VARCHAR(255)
);

-- job_logs
CREATE TABLE job_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  level VARCHAR(20),
  message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- environments
CREATE TABLE environments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) UNIQUE NOT NULL,
  connection_string_encrypted TEXT,
  config_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- connections (source DBs)
CREATE TABLE connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  connection_string_encrypted TEXT,
  type VARCHAR(50) DEFAULT 'postgres',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 12. Data Layer — Dataset Store & Cache

### 12.1 Dataset Store (MinIO/S3)

- **Path pattern:** `/<bucket>/datasets/<dataset_version_id>/<table_name>.parquet`
- **Formats:** Parquet (primary), optional CSV for small exports.
- **Client:** `boto3` (S3-compatible); MinIO endpoint and credentials in env.
- **Operations:** upload (multipart for large files), download, list, delete (on dataset version purge).

### 12.2 Cache (Redis)

- **Job state:** `tdm:job:{job_id}` → LangGraph checkpoint or status JSON; TTL e.g. 7 days.
- **Locks:** `tdm:lock:subset:{schema_version_id}` to avoid concurrent subset on same schema.
- **Temp datasets:** Optional short-lived keys for intermediate artifacts; TTL 24h.
- **Session:** Optional session cache for UI (e.g. selected schema, filters).

---

## 13. API Design (FastAPI)

Base URL: `/api/v1` (or `/v1`). All request/response bodies as JSON; use Pydantic models.

### 13.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/discover-schema` | Trigger schema discovery; body: connection_id or connection_string, options. Returns job_id and/or schema_version_id. |
| GET | `/schemas` | List schemas. |
| GET | `/schema/{id}` | Schema detail with latest or specified version. |
| GET | `/schema/{id}/versions` | List schema_versions. |
| POST | `/pii/classify` | Run PII classification for a schema_version_id. |
| GET | `/pii/{schema_version_id}` | Get PII map for a schema version. |
| POST | `/subset` | Start subset job; body: schema_version_id, connection, filters, limits. |
| POST | `/mask` | Start mask job; body: dataset_version_id, rules or rule_set_id. |
| POST | `/synthetic` | Start synthetic generation; body: ui_urls, api_spec_url, schema_version_id, domain_pack, row_counts. |
| POST | `/provision` | Start provisioning; body: dataset_version_id, target_env, reset_env, run_smoke_tests. |
| GET | `/datasets` | List dataset versions (filter by source_type, schema_version_id). |
| GET | `/dataset/{id}` | Dataset version metadata and lineage. |
| GET | `/dataset/{id}/download` | Optional: signed URL or stream for download. |
| POST | `/rules/masking` | Create/update masking rule set (schema_version_id, rules_json). |
| GET | `/jobs` | List jobs (filter by operation, status). |
| GET | `/job/{id}` | Job detail and logs. |
| GET | `/lineage/dataset/{id}` | Lineage graph for a dataset version. |
| GET | `/environments` | List target environments. |

### 13.2 Auth & RBAC

- **Auth:** API key header (`X-API-Key`) or OAuth2/JWT (optional). Validate in FastAPI dependency.
- **RBAC:** Admin (all), Operator (run jobs, no env/connection change), Viewer (read-only). Store roles in DB or integrate with Azure AD.

### 13.3 File Structure

```
tdm-api/
├── main.py
├── config.py
├── dependencies.py     # DB session, auth, Redis
├── routers/
│   ├── discover.py
│   ├── pii.py
│   ├── subset.py
│   ├── mask.py
│   ├── synthetic.py
│   ├── provision.py
│   ├── datasets.py
│   ├── schemas.py
│   ├── jobs.py
│   ├── lineage.py
│   └── rules.py
├── services/
│   ├── orchestrator_client.py
│   └── ...
└── models/
    ├── request.py
    └── response.py
```

---

## 14. UI Design (Self-Service Portal)

**Stack suggestion:** React + TypeScript + Vite (or Next.js); Tailwind CSS; state (React Query or Zustand).

### 14.1 Modules

| Module | Description |
|--------|-------------|
| **Dataset Catalog** | List dataset versions; filters; view metadata and lineage; trigger download/provision. |
| **Schema Explorer** | List schemas and versions; drill into tables/columns/relationships; view PII tags. |
| **Masking Rule Builder** | Select schema/version; table.column → rule type; save rule set. |
| **Subset Builder** | Select schema and connection; root table + filters; row limits; submit subset job. |
| **Synthetic Data Generator** | Input UI URLs, API spec, domain pack; row counts; submit synthetic job. |
| **Provisioning Console** | Select dataset version and target env; reset/smoke options; run provision. |
| **Job Monitor** | List jobs; status; logs; cancel (if supported). |

### 14.2 Wireframes (Concept)

- **Dashboard:** Cards for recent jobs, dataset count, schema count; quick links to Subset, Synthetic, Provision.
- **Schema Explorer:** Tree (schema → version → tables → columns); PII badges on columns; relationship diagram (optional).
- **Subset Builder:** Form: connection, schema version, root table, filters (key-value), max rows, date range; “Run subset” button.
- **Job Monitor:** Table: job_id, operation, status, started_at; expand row for logs.

---

## 15. LangGraph Supergraph Design

### 15.1 Master Graph Flow

```
User Request
    → parse_request
    → decide_operation
    → execute_subgraph (branch by operation)
    → finalize (update job, lineage, response)
```

### 15.2 Supported Operations (decide_operation output)

| Operation | Subgraph |
|-----------|----------|
| `TDM_SYNTHETIC_RUN` | synthetic |
| `TDM_SUBSET_MASK_PROVISION` | subset → mask → provision |
| `TDM_SUBSET_ONLY` | subset |
| `TDM_MASK_ONLY` | mask |
| `TDM_PROVISION_ONLY` | provision |
| `UI_BASED_SYNTHETIC_GENERATION` | synthetic (with UI crawl) |
| `API_BASED_SYNTHETIC_GENERATION` | synthetic (API schema only) |
| `FULL_TDM_PIPELINE` | discover_schema (if needed) → subset → mask → synthetic (optional) → provision |

### 15.3 Routing Logic (Pseudocode)

```python
def decide_operation(state: TDMState) -> str:
    req = state["request"]
    if req.get("full_pipeline"):
        return "FULL_TDM_PIPELINE"
    if req.get("synthetic_only"):
        return "TDM_SYNTHETIC_RUN"
    if req.get("subset") and req.get("mask") and req.get("provision"):
        return "TDM_SUBSET_MASK_PROVISION"
    # ... etc
```

### 15.4 Subgraph Invocation

- Each operation maps to one subgraph or a composed chain (e.g. subset → mask → provision as three sequential subgraphs).
- State passed in/out; `execute_subgraph` runs the appropriate graph and merges result back into `TDMState`.

### 15.5 File Structure

```
tdm-orchestrator/
├── graphs/
│   ├── master.py           # Supergraph
│   ├── schema_discovery.py
│   ├── pii_classification.py
│   ├── subsetting.py
│   ├── masking.py
│   ├── synthetic.py
│   └── provisioning.py
├── state.py
└── nodes/
    ├── parse_request.py
    ├── decide_operation.py
    ├── execute_subgraph.py
    └── finalize.py
```

---

## 16. Infrastructure & Deployment

### 16.1 Recommended Setup

- **API + Orchestrator:** Docker containers; same repo or split; orchestrator can be a worker that consumes jobs from Redis/DB.
- **Dataset Store:** MinIO (Docker or K8s) or AWS S3.
- **Metadata DB:** PostgreSQL 15+ (local, RDS, or Azure Database for PostgreSQL).
- **Cache/State:** Redis 7+ (ElastiCache or Azure Cache for Redis).
- **Optional:** Kafka for event-driven triggers (e.g. “on subset complete → trigger mask”).

### 16.2 Docker Compose (Minimal)

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: tdm
      POSTGRES_PASSWORD: tdm_secret
      POSTGRES_DB: tdm_metadata
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
  tdm-api:
    build: ./tdm-api
    environment:
      DATABASE_URL: postgresql://tdm:tdm_secret@postgres:5432/tdm_metadata
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - minio
  tdm-orchestrator:
    build: ./tdm-orchestrator
    environment:
      DATABASE_URL: postgresql://tdm:tdm_secret@postgres:5432/tdm_metadata
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
    depends_on:
      - postgres
      - redis
      - minio
volumes:
  pgdata:
  minio_data:
```

### 16.3 CI/CD (GitHub Actions)

- **On PR:** Lint (ruff/black), unit tests (pytest), type check (mypy).
- **On push to main:** Run integration tests (test DB + MinIO + Redis); build Docker images; push to registry; optional deploy to staging.
- **Secrets:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, DB credentials, MinIO credentials in GitHub Secrets.

---

## 17. Testing Strategy

| Level | Scope | Tools |
|-------|--------|------|
| **Unit** | Masking transformers, subset FK graph, schema parser, PII regex | pytest |
| **Integration** | SDV multi-table generation, DB discovery, MinIO upload/download, Redis state | pytest + testcontainers or fixtures |
| **API** | All FastAPI endpoints (mock orchestrator or in-process) | pytest + TestClient |
| **UI** | Critical flows: login, create subset job, view job status | Playwright or Cypress |
| **Load** | Synthetic generation under concurrency; subset with large row counts | locust or pytest-xdist |
| **E2E** | Full pipeline: discover → subset → mask → provision (test env) | pytest + real DB + MinIO |

### 17.1 Test Data

- Seed PostgreSQL with a small schema (e.g. customers, orders, order_items); use for discovery, subset, mask, provision tests.
- Mock Azure OpenAI in unit tests (responses fixed); use real Azure OpenAI in integration/E2E if budget allows or use a dedicated test deployment.

---

## 18. 90-Day Execution Plan

| Phase | Days | Focus |
|-------|------|--------|
| **Phase 1 — Base** | 1–15 | Metadata DB (migrations); Dataset Store (MinIO client); Redis; LangGraph base; FastAPI skeleton; Docker Compose. |
| **Phase 2 — Schema + PII** | 16–30 | Schema discovery agent (connector, profiler, FK inference); metadata storage; PII agent (regex + Azure OpenAI); schema + PII API and basic UI (Schema Explorer, PII view). |
| **Phase 3 — Subsetting** | 31–45 | FK graph; recursive extractor; Parquet export; Dataset Store upload; subset API and Subset Builder UI. |
| **Phase 4 — Masking** | 46–60 | Mask transformers (FPE, hash, email, null, redact); rule loader; integrity check; mask API and Rule Builder UI. |
| **Phase 5 — Synthetic** | 61–75 | UI crawler (3-phase); API schema merge; schema merger (Pydantic); SDV relational; domain packs; synthetic API and Synthetic Generator UI. |
| **Phase 6 — Provision + E2E** | 76–90 | Provisioning agent (connect, reset, schema apply, load, smoke tests); master orchestrator; Dataset Catalog, Provisioning Console, Job Monitor; RBAC and security; production hardening and docs. |

---

## 19. Azure OpenAI Integration

### 19.1 Configuration

- **Endpoint:** `https://<your-resource>.openai.azure.com/`
- **API Key:** Stored in env `AZURE_OPENAI_API_KEY` (never in code).
- **Deployments:** One for chat/completion (e.g. `gpt-4o` or `gpt-4o-mini`). Use same deployment for PII classification and any synthetic “hints” if needed.

### 19.2 Client Setup (Python)

```python
# Use openai package with Azure endpoint
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-02-15-preview",  # or latest stable
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)

# For chat (PII classification, etc.)
response = client.chat.completions.create(
    model="gpt-4o",  # deployment name in Azure
    messages=[{"role": "user", "content": "..."}],
    response_format={"type": "json_object"},
)
```

### 19.3 PII Classification Prompt (Structured Output)

- Send: column name, sample values (masked/hashed if needed), optional table name.
- Ask: classify as one of [email, phone, person_name, address, ssn, credit_card, date_of_birth, other, none].
- Use `response_format={"type": "json_object"}` and parse JSON; map to `pii_type` and confidence.

### 19.4 Security

- No PII in logs; optionally hash sample values before sending to Azure OpenAI.
- Prefer `gpt-4o-mini` for high volume; use `gpt-4o` where accuracy is critical.
- Rate limits: respect Azure quotas; implement backoff in client.

---

## 20. Environment & Configuration

### 20.1 Required Environment Variables

```bash
# PostgreSQL (metadata store)
DATABASE_URL=postgresql://user:password@host:5432/tdm_metadata

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO / S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=tdm-datasets
# Or for AWS S3:
# S3_BUCKET=tdm-datasets
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1

# Azure OpenAI
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional
LOG_LEVEL=INFO
API_SECRET_KEY=<for X-API-Key auth>
```

### 20.2 Config Module (Pydantic Settings)

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "tdm-datasets"
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment_chat: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
```

---

## Summary Checklist

- [x] **Architecture:** Microservices (orchestrator, agents, API, metadata store, dataset store, cache).
- [x] **LangGraph:** State, nodes, subgraphs, master supergraph with operation routing.
- [x] **Modules 1–6:** Schema Discovery, PII, Subsetting, Masking, Synthetic, Provisioning — nodes, contracts, tasks, file layout.
- [x] **Data layer:** PostgreSQL DDL for metadata; MinIO path convention; Redis usage.
- [x] **API:** FastAPI endpoints, auth/RBAC.
- [x] **UI:** Module list and wireframe concepts.
- [x] **Supergraph:** Operations and subgraph mapping.
- [x] **Infrastructure:** Docker Compose, CI/CD.
- [x] **Testing:** Unit, integration, API, UI, load, E2E.
- [x] **90-day plan:** Phased execution.
- [x] **Azure OpenAI:** Config, client, PII usage, security.
- [x] **PostgreSQL:** Used for metadata and as source/target DB throughout.

This document is the single reference for implementing the Enterprise TDM platform end-to-end with **PostgreSQL** and **Azure OpenAI**, with no gaps from the original plan.

---

## Appendix A — Request/Response Validation (Pydantic)

All API request bodies should be validated with Pydantic v2 models. Example for subset and masking:

```python
# Subset request
class SubsetRequest(BaseModel):
    schema_version_id: UUID
    connection_string: Optional[str] = None
    connection_id: Optional[UUID] = None
    root_table: str
    filters: Optional[dict[str, dict]] = None
    max_rows_per_table: Optional[dict[str, int]] = None
    date_range: Optional[dict] = None  # { "table": str, "column": str, "start": str, "end": str }
    sampling_pct: Optional[float] = None  # 0-100

# Mask request
class MaskRequest(BaseModel):
    dataset_version_id: UUID
    rules: Optional[dict[str, str]] = None  # "table.column": "mask.rule_type"
    rule_set_id: Optional[UUID] = None
```

Validation rules: `schema_version_id` must exist in DB; `dataset_version_id` must exist; `connection_string` or `connection_id` required for subset; at least one of `rules` or `rule_set_id` for mask.

---

## Appendix B — Sequence Diagrams (Text)

**Schema Discovery:**
```
Client → API: POST /discover-schema
API → Orchestrator: create job, invoke schema_discovery subgraph
Orchestrator → Schema Agent: connect_db → fetch_tables → fetch_columns → profile → infer PK/FK → save_metadata
Schema Agent → Metadata DB: INSERT schemas, tables, columns, relationships
Orchestrator → API: job_id, schema_version_id
API → Client: 202 + job_id
```

**Subset → Mask → Provision:**
```
Client → API: POST /subset then POST /mask then POST /provision
Orchestrator: subset subgraph → Dataset Store (parquet); mask subgraph → Dataset Store (new version); provision subgraph → Target PostgreSQL
Each step writes lineage and job_logs.
```

---

## Appendix C — Alembic Migrations

Use Alembic for metadata store schema changes:

```bash
cd tdm-metadata-store
alembic init alembic
# Edit alembic.ini: sqlalchemy.url from env
# Create revision: alembic revision -m "initial_schema"
# Apply: alembic upgrade head
```

Keep migrations in `tdm-metadata-store/alembic/versions/`; never edit existing revisions in production.

---

## Appendix D — Optional Kafka Events

If using Kafka for event-driven flows, suggested topic and payload:

- **Topic:** `tdm.job.completed`
- **Payload:** `{ "job_id": "uuid", "operation": "subset", "status": "completed", "dataset_version_id": "uuid", "timestamp": "ISO8601" }`
- **Consumer:** Optional service that triggers downstream (e.g. auto-mask after subset, or notify UI).

# TDM Implementation — Quick Reference

Companion to `TDM_IMPLEMENTATION_END_TO_END.md`. Use this for copy-paste file structure, env template, and sample API calls.

---

## 1. Full Directory Structure

```
tdm/
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── docs/
│   ├── TDM_IMPLEMENTATION_END_TO_END.md
│   └── IMPLEMENTATION_QUICK_REFERENCE.md
├── tdm-orchestrator/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── state.py
│   ├── graphs/
│   │   ├── __init__.py
│   │   ├── master.py
│   │   ├── schema_discovery.py
│   │   ├── pii_classification.py
│   │   ├── subsetting.py
│   │   ├── masking.py
│   │   ├── synthetic.py
│   │   └── provisioning.py
│   └── nodes/
│       ├── __init__.py
│       ├── parse_request.py
│       ├── decide_operation.py
│       ├── execute_subgraph.py
│       └── finalize.py
├── agents/
│   ├── __init__.py
│   ├── schema_discovery/
│   │   ├── __init__.py
│   │   ├── connector.py
│   │   ├── profiler.py
│   │   ├── type_inference.py
│   │   ├── relationship_inference.py
│   │   └── metadata_writer.py
│   ├── pii_detection/
│   │   ├── __init__.py
│   │   ├── regex_patterns.py
│   │   ├── llm_classifier.py
│   │   ├── merger.py
│   │   └── repository.py
│   ├── subsetting/
│   │   ├── __init__.py
│   │   ├── fk_graph.py
│   │   ├── extractor.py
│   │   ├── exporter.py
│   │   └── subset_parser.py
│   ├── masking/
│   │   ├── __init__.py
│   │   ├── transformers/
│   │   │   ├── __init__.py
│   │   │   ├── fpe.py
│   │   │   ├── deterministic_hash.py
│   │   │   ├── tokenize.py
│   │   │   ├── null_redact.py
│   │   │   └── email_mask.py
│   │   ├── rule_loader.py
│   │   └── validator.py
│   ├── synthetic/
│   │   ├── __init__.py
│   │   ├── crawler/
│   │   │   ├── dom_walk.py
│   │   │   └── schema_extractor.py
│   │   ├── api_schema.py
│   │   ├── schema_merger.py
│   │   ├── sdv_runner.py
│   │   ├── domain_packs/
│   │   │   ├── ecommerce.yaml
│   │   │   ├── banking.yaml
│   │   │   └── telecom.yaml
│   │   └── validator.py
│   └── provisioning/
│       ├── __init__.py
│       ├── target_connector.py
│       ├── schema_applier.py
│       ├── data_loader.py
│       ├── smoke_tests.py
│       └── env_config.py
├── tdm-api/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── discover.py
│   │   ├── pii.py
│   │   ├── subset.py
│   │   ├── mask.py
│   │   ├── synthetic.py
│   │   ├── provision.py
│   │   ├── datasets.py
│   │   ├── schemas.py
│   │   ├── jobs.py
│   │   ├── lineage.py
│   │   └── rules.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── orchestrator_client.py
│   └── models/
│       ├── __init__.py
│       ├── request.py
│       └── response.py
├── tdm-metadata-store/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── dataset.py
│   │   ├── job.py
│   │   └── lineage.py
│   └── repositories/
│       ├── __init__.py
│       ├── schema_repository.py
│       ├── dataset_repository.py
│       ├── job_repository.py
│       └── pii_repository.py
├── tdm-dataset-store/
│   ├── __init__.py
│   ├── client.py
│   └── paths.py
├── tdm-cache/
│   ├── __init__.py
│   └── client.py
└── tdm-ui/
    ├── package.json
    ├── src/
    │   ├── App.tsx
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   ├── SchemaExplorer.tsx
    │   │   ├── SubsetBuilder.tsx
    │   │   ├── MaskingRuleBuilder.tsx
    │   │   ├── SyntheticGenerator.tsx
    │   │   ├── ProvisioningConsole.tsx
    │   │   ├── DatasetCatalog.tsx
    │   │   └── JobMonitor.tsx
    │   └── api/
    │       └── client.ts
    └── ...
```

---

## 2. Environment Template (`.env.example`)

```bash
# PostgreSQL — metadata store
DATABASE_URL=postgresql://tdm:tdm_secret@localhost:5432/tdm_metadata

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (S3-compatible)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=tdm-datasets
MINIO_SECURE=false

# Azure OpenAI (required for PII LLM and optional synthetic hints)
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_CHAT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# API
LOG_LEVEL=INFO
API_SECRET_KEY=your-api-secret-for-x-api-key-auth
```

---

## 3. Sample API Requests (cURL)

**Discover schema**
```bash
curl -X POST http://localhost:8000/api/v1/discover-schema \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "connection_string": "postgresql://user:pass@host:5432/sourcedb",
    "schemas": ["public"],
    "include_stats": true,
    "sample_size": 10000
  }'
```

**Classify PII**
```bash
curl -X POST http://localhost:8000/api/v1/pii/classify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "schema_version_id": "SCHEMA_VERSION_UUID",
    "use_llm": true,
    "sample_size_per_column": 100
  }'
```

**Subset**
```bash
curl -X POST http://localhost:8000/api/v1/subset \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "schema_version_id": "SCHEMA_VERSION_UUID",
    "connection_string": "postgresql://user:pass@host:5432/sourcedb",
    "root_table": "customers",
    "filters": { "customers": { "region": "US" } },
    "max_rows_per_table": { "customers": 10000, "orders": 50000 }
  }'
```

**Mask**
```bash
curl -X POST http://localhost:8000/api/v1/mask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "dataset_version_id": "DATASET_VERSION_UUID",
    "rules": {
      "customers.email": "mask.email_deterministic",
      "customers.pan": "mask.fpe_pan"
    }
  }'
```

**Synthetic**
```bash
curl -X POST http://localhost:8000/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "schema_version_id": "SCHEMA_VERSION_UUID",
    "domain_pack": "ecommerce",
    "row_counts": { "customer": 1000, "order": 5000 }
  }'
```

**Provision**
```bash
curl -X POST http://localhost:8000/api/v1/provision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_SECRET_KEY" \
  -d '{
    "dataset_version_id": "DATASET_VERSION_UUID",
    "target_env": "QA",
    "reset_env": true,
    "run_smoke_tests": true
  }'
```

---

## 4. Core Dependencies (Python)

**tdm-orchestrator / tdm-api (shared):**
- `langgraph`
- `langchain-core`
- `fastapi`
- `uvicorn`
- `sqlalchemy[asyncio]`
- `asyncpg` or `psycopg2-binary`
- `redis`
- `boto3`
- `openai` (Azure OpenAI compatible)
- `pydantic`
- `pydantic-settings`
- `alembic`

**agents (per-agent):**
- schema_discovery: `sqlalchemy`, `pandas` (optional)
- pii_detection: `openai`, `instructor` (optional)
- subsetting: `pandas`, `pyarrow`
- masking: `cryptography`
- synthetic: `sdv`, `pandas`, `pyarrow`, `playwright` (optional)
- provisioning: `sqlalchemy`, `pandas`, `pyarrow`

---

## 5. Key Implementation Notes

- **PostgreSQL:** All metadata in one DB; source/target DBs can be the same or different instances; use connection strings from `connections` or request body.
- **Azure OpenAI:** Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`; use deployment name as `model` in client. No other LLM provider is required for this doc.
- **Idempotency:** Subset/mask/provision create new dataset versions or job records; same request can be run again with new IDs.
- **Secrets:** Store `connection_string` and `connection_string_encrypted` in DB encrypted (e.g. Fernet or KMS); never log or return raw credentials.

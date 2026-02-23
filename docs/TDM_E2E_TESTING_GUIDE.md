# TDM End-to-End Testing Guide

## Overview

This guide provides a comprehensive end-to-end testing flow for the Test Data Management (TDM) platform. The TDM system now supports **dynamic test data generation** through three modes:

1. **Schema-based**: Generate from existing discovered database schemas
2. **Domain-based**: Generate from predefined domain packs (e-commerce, banking, telecom, healthcare)
3. **Test Case-based**: Crawl test case URLs to dynamically extract schema and generate data

## System Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌────────────────┐
│   PostgreSQL    │◄─────┤  TDM Backend     │◄─────┤   TDM UI       │
│   (Metadata +   │      │  (FastAPI)       │      │   (React)      │
│    Test Data)   │      │  Port: 8002      │      │  Port: 5173    │
└─────────────────┘      └──────────────────┘      └────────────────┘
                                 │
                                 ▼
                         ┌──────────────────┐
                         │  Services:       │
                         │  - Schema Disc.  │
                         │  - PII Detection │
                         │  - Subsetting    │
                         │  - Masking       │
                         │  - Synthetic Gen │
                         │  - Provisioning  │
                         │  - Test Crawler  │
                         └──────────────────┘
```

## Prerequisites

### 1. Database Setup
- PostgreSQL 15+ running
- Database: `tdm`
- Connection string in `.env`: `DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm`

### 2. Backend Setup
```bash
cd tdm-backend
pip install -r requirements.txt
python reset_db.py  # Creates all tables
python seed_env.py  # Seeds test environments
```

### 3. UI Setup
```bash
cd tdm-ui
npm install --ignore-scripts  # Avoid esbuild issues on Windows
npm run dev
```

### 4. Optional: Playwright for Test Case Crawling
```bash
pip install playwright
playwright install chromium
```

## Features and Relationships

### Feature Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     TDM Feature Flow                              │
└──────────────────────────────────────────────────────────────────┘

1. SCHEMA DISCOVERY (Entry Point)
   ├─► Connects to source database
   ├─► Discovers tables, columns, relationships
   ├─► Profiles data (row counts, types)
   └─► Creates: schema_version
           │
           ├──► 2. PII CLASSIFICATION
           │    ├─► Scans columns for PII (email, phone, SSN, etc.)
           │    ├─► Uses regex + Azure OpenAI
           │    └─► Marks sensitive columns
           │
           └──► 3. SUBSETTING
                ├─► Extracts related data subset
                ├─► Follows FK relationships
                ├─► Creates: dataset_version (type: subset)
                │
                ├──► 4. MASKING
                │    ├─► Applies masking rules to PII columns
                │    ├─► Transformations: email, hash, redact, tokenize
                │    └─► Creates: dataset_version (type: masked)
                │
                └──► 5. PROVISIONING
                     ├─► Loads data into target environment
                     ├─► Environments: QA, SIT, UAT, Perf, Dev
                     └─► Runs smoke tests

ALTERNATIVE PATH (No Source Database):

A. SYNTHETIC DATA GENERATION (Three Modes)
   │
   ├──► Mode 1: FROM DOMAIN PACK
   │    ├─► Select: ecommerce, banking, telecom, healthcare
   │    ├─► Choose scenario within domain
   │    ├─► Uses predefined entity relationships
   │    └─► Creates: dataset_version (type: synthetic)
   │
   ├──► Mode 2: FROM TEST CASE URLS
   │    ├─► Provide URLs of test pages/forms
   │    ├─► Crawls pages using Playwright
   │    ├─► Extracts schema from:
   │    │   • Form fields (input, select, textarea)
   │    │   • HTML tables
   │    │   • Data attributes
   │    ├─► Infers data types (email, phone, date, etc.)
   │    ├─► Generates realistic data
   │    └─► Creates: dataset_version (type: synthetic_crawled)
   │
   └──► Mode 3: FROM EXISTING SCHEMA
        ├─► Uses previously discovered schema
        └─► Creates: dataset_version (type: synthetic)

   ALL SYNTHETIC DATASETS CAN BE:
   ├──► Masked (if needed)
   └──► Provisioned to target environments
```

## End-to-End Testing Scenarios

### Scenario 1: Full Database-Driven Flow (Traditional TDM)

**Use Case**: You have a production database and want to create test data for QA

**Steps**:

1. **Schema Discovery**
   ```bash
   # Via UI
   - Navigate to Schema Discovery page
   - Enter connection string: postgresql://postgres:12345@localhost:5432/tdm
   - Click "Run Discovery"
   - Verify: New schema appears with tables
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/discover-schema \
     -H "Content-Type: application/json" \
     -d '{
       "connection_string": "postgresql://postgres:12345@localhost:5432/tdm",
       "schemas": ["public"],
       "include_stats": true
     }'
   ```
   **Expected**: `schema_version_id` returned, tables discovered

2. **PII Classification**
   ```bash
   # Via UI
   - Go to PII Classification
   - Select discovered schema
   - Click "Scan All"
   - Verify: PII columns identified (email, phone, etc.)
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/pii/classify \
     -H "Content-Type: application/json" \
     -d '{
       "schema_version_id": "<schema_version_id>",
       "use_llm": true
     }'
   ```
   **Expected**: PII map with confidence scores

3. **Subsetting**
   ```bash
   # Via UI
   - Go to Subsetting Engine
   - Select schema and root table (e.g., "customers")
   - Set max rows: 1000
   - Click "Run Subset"
   - Check Jobs page for status
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/subset \
     -H "Content-Type: application/json" \
     -d '{
       "schema_version_id": "<schema_version_id>",
       "root_table": "customers",
       "max_rows_per_table": {"*": 1000}
     }'
   ```
   **Expected**: `job_id` returned, dataset created with related data

4. **Masking**
   ```bash
   # Via UI
   - Go to Masking Engine
   - Select subset dataset
   - Add rules (or use auto-detect from PII)
   - Click "Apply Mask"
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/mask \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_version_id": "<dataset_version_id>",
       "rules": {
         "public.customers.email": "mask.email_deterministic",
         "public.customers.phone": "mask.redact"
       }
     }'
   ```
   **Expected**: Masked dataset created

5. **Provisioning**
   ```bash
   # Via UI
   - Go to Environment Provisioning
   - Select masked dataset
   - Choose environment: QA
   - Enable "Reset Environment"
   - Enable "Run Smoke Tests"
   - Click "Provision"
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/provision \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_version_id": "<masked_dataset_id>",
       "target_env": "QA",
       "reset_env": true,
       "run_smoke_tests": true
     }'
   ```
   **Expected**: Data loaded to QA environment

---

### Scenario 2: Domain-Based Synthetic Generation (No Source Database)

**Use Case**: You need test data but don't have access to production database

**Steps**:

1. **Select Domain Pack**
   ```bash
   # Via UI
   - Go to Synthetic Data Factory
   - Select "Domain Pack" mode
   - Choose domain: "E-Commerce" or "Banking" or "Telecom" or "Healthcare"
   - Select scenario: "default" or specific (e.g., "b2c", "retail")
   - Set rows: 1000
   - Click "Generate Synthetic Data"
   
   # Via API - Get available domains
   curl http://localhost:8002/api/v1/synthetic/domains
   
   # Via API - Generate
   curl -X POST http://localhost:8002/api/v1/synthetic \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "ecommerce",
       "scenario": "b2c",
       "row_counts": {"*": 1000}
     }'
   ```
   
   **Expected**:
   - Job created and runs in background
   - Dataset generated with entities:
     - E-commerce: customer, order, order_item, product, payment
     - Banking: account, transaction, customer, loan
     - Telecom: customer, sim, recharge, plan
     - Healthcare: patient, appointment, prescription, doctor

2. **View Generated Data**
   ```bash
   # Via UI
   - Go to Dataset Catalog
   - Find dataset with source_type: "synthetic"
   - View metadata (row counts, domain, scenario)
   
   # Via API
   curl http://localhost:8002/api/v1/datasets?source_type=synthetic
   ```

3. **Optional: Mask and Provision**
   - Follow steps 4-5 from Scenario 1

---

### Scenario 3: Test Case-Based Dynamic Generation (NEW!)

**Use Case**: You have test cases/UI pages and want to generate data that matches those forms

**Steps**:

1. **Provide Test Case URLs**
   ```bash
   # Via UI
   - Go to Synthetic Data Factory
   - Select "Test Case URLs" mode
   - Add URL(s):
     * https://example.com/register
     * https://example.com/checkout
     * https://example.com/profile
   - Select domain hint: "E-Commerce" (helps with context)
   - Set rows: 500
   - Click "Generate Synthetic Data"
   
   # Via API
   curl -X POST http://localhost:8002/api/v1/synthetic \
     -H "Content-Type: application/json" \
     -d '{
       "test_case_urls": [
         "https://example.com/register",
         "https://example.com/checkout"
       ],
       "domain": "ecommerce",
       "scenario": "default",
       "row_counts": {"*": 500}
     }'
   ```

2. **System Behavior**:
   - Playwright launches headless browser
   - Crawls each URL:
     - **Phase 1**: Extracts all form fields (input, select, textarea)
     - **Phase 2**: Extracts table structures
     - **Phase 3**: Extracts other data-bearing elements
   - Infers data types:
     - Email fields → generates valid emails
     - Phone fields → generates valid phone numbers
     - Name fields → generates realistic names
     - Date fields → generates dates
     - Select fields → uses options as enum values
   - Merges schemas from multiple URLs
   - Normalizes field names (snake_case)
   - Groups fields into entities
   - Generates realistic data using Faker library

3. **Result**:
   ```json
   {
     "job_id": "uuid",
     "dataset_version_id": "uuid",
     "entities": ["registration_form", "checkout_form", "user_profile"],
     "message": "Synthetic job started in test_cases mode"
   }
   ```

4. **View Results**:
   ```bash
   # Check job status
   curl http://localhost:8002/api/v1/job/<job_id>
   
   # View dataset
   curl http://localhost:8002/api/v1/dataset/<dataset_version_id>
   ```
   
   **Expected Metadata**:
   ```json
   {
     "id": "uuid",
     "source_type": "synthetic_crawled",
     "metadata": {
       "test_case_urls": ["..."],
       "domain": "ecommerce",
       "crawled_entities": ["registration", "checkout"],
       "row_counts": {"registration": 500, "checkout": 500}
     }
   }
   ```

---

## Testing Each Feature

### Test 1: Health Check
```bash
curl http://localhost:8002/health
# Expected: {"status": "ok"}
```

### Test 2: List Schemas
```bash
curl http://localhost:8002/api/v1/schemas
# Expected: [] or list of schemas
```

### Test 3: List Datasets
```bash
curl http://localhost:8002/api/v1/datasets
# Expected: [] or list of datasets
```

### Test 4: List Jobs
```bash
curl http://localhost:8002/api/v1/jobs
# Expected: [] or list of jobs
```

### Test 5: Get Available Domains (NEW!)
```bash
curl http://localhost:8002/api/v1/synthetic/domains
# Expected: List of domains with scenarios and entities
```

### Test 6: List Environments
```bash
curl http://localhost:8002/api/v1/environments
# Expected: [{"name": "QA", ...}, {"name": "SIT", ...}, ...]
```

---

## UI Testing Flow

### Dashboard Flow
1. Open http://localhost:5173
2. Verify Dashboard shows:
   - Schemas count
   - Datasets count
   - Jobs count
   - Recent activity
3. Click each card to navigate

### Schema Discovery Flow
1. Navigate to "Schema Discovery"
2. Enter connection string
3. Click "Run Discovery"
4. Wait for completion
5. Verify schema card appears
6. Click schema to view tables/columns

### Synthetic Data Flow (Dynamic - Three Ways)

#### Option A: Domain Pack
1. Navigate to "Synthetic Data Factory"
2. Select "Domain Pack" mode tab
3. Click a domain card (e.g., "E-Commerce")
4. (Optional) Select scenario
5. Set row count
6. Click "Generate Synthetic Data"
7. Toast notification appears
8. Navigate to "Jobs" - see running/completed job
9. Navigate to "Dataset Catalog" - see new synthetic dataset

#### Option B: Test Case URLs
1. Navigate to "Synthetic Data Factory"
2. Select "Test Case URLs" mode tab
3. Enter test case URL(s)
4. Add more URLs with "+ Add URL" button
5. Select domain hint
6. Set row count
7. Click "Generate Synthetic Data"
8. Check Jobs for crawling status
9. Check Dataset Catalog for generated data

#### Option C: Existing Schema
1. Navigate to "Synthetic Data Factory"
2. Select "Existing Schema" mode tab
3. Choose discovered schema from dropdown
4. Set row count
5. Click "Generate Synthetic Data"
6. Verify dataset created

### Complete Workflow Test
1. Schema Discovery → Creates schema
2. PII Classification → Identifies sensitive data
3. Subsetting → Creates data subset
4. Masking → Masks sensitive columns
5. Dataset Catalog → View all datasets
6. Provisioning → Load to QA
7. Audit Logs → View all operations
8. Governance & Lineage → View data flow

---

## Key Improvements Made

### 1. Dynamic Domain Handling
- ✅ Domains fetched from backend API (`/synthetic/domains`)
- ✅ UI displays available domains dynamically
- ✅ Each domain has:
  - Name (technical)
  - Label (display)
  - Description
  - Scenarios
  - Entity list

### 2. Test Case Crawler Integration
- ✅ New crawler service (`services/crawler.py`)
- ✅ Three-phase extraction:
  - Forms
  - Tables
  - Orphan fields
- ✅ Type inference:
  - Email, phone, date, address, name patterns
  - Number/integer detection
  - Boolean from checkboxes
- ✅ Schema merging from multiple URLs
- ✅ Fallback to domain pack if crawling unavailable

### 3. Enhanced Synthetic Generation
- ✅ New service (`services/synthetic_enhanced.py`)
- ✅ Three generation modes:
  - `generate_from_schema_version()` - From discovered schemas
  - `generate_from_domain_scenario()` - From domain packs
  - `generate_from_test_cases()` - From crawled test cases
- ✅ Backward compatible with existing API

### 4. Dynamic UI
- ✅ Mode selection tabs (Domain / Test Case / Schema)
- ✅ Domain cards with descriptions
- ✅ Test case URL input (multiple URLs)
- ✅ Scenario selector (when applicable)
- ✅ Clear visual feedback

### 5. API Enhancements
- ✅ `GET /synthetic/domains` - List available domains
- ✅ `POST /synthetic` - Enhanced with three modes
- ✅ Request supports:
  - `schema_version_id` (Mode 1)
  - `test_case_urls` + `domain` + `scenario` (Mode 2)
  - `domain` + `scenario` (Mode 3)

---

## Troubleshooting

### Backend Issues

**Issue**: Tables not created
```bash
cd tdm-backend
python reset_db.py  # Drops and recreates all tables
```

**Issue**: Port 8002 already in use
```bash
# Find and kill process
netstat -ano | findstr :8002
taskkill /PID <pid> /F
```

**Issue**: Playwright not installed
```bash
pip install playwright
playwright install chromium
```

### UI Issues

**Issue**: Cannot connect to backend
- Verify backend is running on port 8002
- Check `.env` file: `VITE_API_URL=http://localhost:8002`

**Issue**: npm install fails with esbuild error
```bash
npm install --ignore-scripts
```

### Data Issues

**Issue**: No datasets appearing
- Run schema discovery first OR
- Use domain-based synthetic generation

**Issue**: Subset fails
- Ensure connection string is valid
- Ensure root table exists
- Check job logs in UI or via API

---

## Performance Tips

1. **Synthetic Generation**: Start with small row counts (100-1000) for testing
2. **Test Case Crawling**: Limit to 3-5 URLs at a time
3. **Subsetting**: Set appropriate max_rows_per_table
4. **Provisioning**: Use reset_env=false for incremental loads

---

## Next Steps

1. **Add More Domains**: Extend domain packs in crawler fallback
2. **API Schema Extraction**: Implement OpenAPI/Swagger parsing
3. **Advanced Crawling**: Add JavaScript interaction support
4. **Relationship Inference**: Auto-detect FKs from crawled entities
5. **SDV Integration**: Use Synthetic Data Vault for better multi-table generation
6. **Caching**: Cache crawled schemas to avoid repeated crawling

---

## Summary

The TDM platform now provides **three flexible ways** to generate test data:

| Mode | Use When | Input | Output |
|------|----------|-------|--------|
| **Schema-based** | You have a source database | Connection string | Dataset from real structure |
| **Domain-based** | You know the business domain | Domain + scenario | Predefined entity relationships |
| **Test Case-based** | You have test pages/forms | URL(s) | Dynamically extracted schema |

All generated datasets can be:
- Masked (to protect PII)
- Provisioned (to target environments)
- Tracked (via lineage and audit logs)

This makes TDM suitable for:
- Traditional database cloning/subsetting
- Green field projects (no prod data)
- UI/API testing (test case-driven)
- Continuous testing in CI/CD pipelines

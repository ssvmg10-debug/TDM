# TDM Database Migration - Summary

## What Was Done

### 1. ✅ Alembic Setup and Configuration
- Installed Alembic for database migrations
- Initialized Alembic directory structure in `tdm-backend/alembic/`
- Configured `alembic.ini` with PostgreSQL connection string
- Updated `alembic/env.py` to import all models for autogeneration

### 2. ✅ Created Initial Migration
- Generated migration file: `alembic/versions/aec55a121109_initial_migration_with_all_tdm_models.py`
- Migration includes all 14 models:
  - connections
  - schemas
  - schema_versions  
  - tables
  - columns
  - relationships
  - pii_classification
  - dataset_versions
  - dataset_metadata
  - jobs
  - job_logs
  - lineage
  - masking_rules
  - environments

### 3. ✅ Applied Migration to TDM Database
- Ran `alembic upgrade head` to create all tables
- Created `alembic_version` table to track migrations
- All 14 model tables + 1 alembic_version table = 15 total tables

### 4. ✅ Created Separate Target Database
- Created `tdm_target` database for provisioned/synthetic data
- This separates metadata (tdm) from actual test data (tdm_target)

### 5. ✅ Updated Configuration
- Added `target_database_url` to `config.py`
- Updated `.env` file with both database URLs:
  - `DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm`
  - `TARGET_DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm_target`

### 6. ✅ Updated Provisioning Service
- Modified `services/provisioning.py` to use `tdm_target` database by default
- Falls back to environment-specific connections if configured

### 7. ✅ Created Documentation and Verification Tools
- `DATABASE_SETUP.md` - Complete database architecture guide
- `verify_db_setup.py` - Verification script that checks:
  - Metadata database connectivity
  - Target database connectivity
  - Alembic migration status

## Database Architecture

```
┌─────────────────────────────────────────┐
│  TDM System                             │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────────────────────────┐   │
│  │  tdm (Metadata Database)       │   │
│  │  - Schema definitions          │   │
│  │  - PII classifications         │   │
│  │  - Job tracking                │   │
│  │  - Lineage information         │   │
│  │  - Masking rules               │   │
│  └────────────────────────────────┘   │
│                                         │
│  ┌────────────────────────────────┐   │
│  │  tdm_target (Data Database)    │   │
│  │  - Subsetted data              │   │
│  │  - Masked data                 │   │
│  │  - Synthetic data              │   │
│  │  - Ready for provisioning      │   │
│  └────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Files Created/Modified

### Created:
- `tdm-backend/alembic/` - Alembic migration directory
- `tdm-backend/alembic.ini` - Alembic configuration
- `tdm-backend/alembic/versions/aec55a121109_*.py` - Initial migration
- `tdm-backend/DATABASE_SETUP.md` - Database setup documentation
- `tdm-backend/verify_db_setup.py` - Verification script

### Modified:
- `tdm-backend/config.py` - Added target_database_url
- `tdm-backend/services/provisioning.py` - Use target database
- `.env` - Added TARGET_DATABASE_URL

## Verification Results

```
✅ Metadata (tdm) Database Connected
   - 15 tables (14 models + alembic_version)
   
✅ Target (tdm_target) Database Connected  
   - 0 tables (will be created dynamically when data is provisioned)
   
✅ Alembic Migrations Up to Date
   - Current: aec55a121109
   - Latest:  aec55a121109
```

## How to Use

### Running Migrations
```bash
cd tdm-backend

# Create new migration after model changes
python -m alembic revision --autogenerate -m "Description"

# Apply migrations
python -m alembic upgrade head

# Check current version
python -m alembic current
```

### Verifying Setup
```bash
cd tdm-backend
python verify_db_setup.py
```

### Starting the Backend
```bash
cd tdm-backend
python -m uvicorn main:app --reload --port 8002
```

## Data Flow Example

1. **User executes workflow** → Creates job in `tdm.jobs`
2. **Schema discovery** → Stores metadata in `tdm.schemas`, `tdm.tables`, `tdm.columns`
3. **PII detection** → Stores results in `tdm.pii_classification`
4. **Synthetic data generation** → Creates data in `tdm_target`
5. **Provisioning** → Reads from `tdm_target`, deploys to target environment
6. **Lineage tracking** → Records relationships in `tdm.lineage`

## Important Notes

- **Metadata vs Data**: `tdm` stores metadata, `tdm_target` stores actual test data
- **Hardcoded Connections**: Using `postgresql://postgres:12345@localhost:5432/*`
- **Migration Tracking**: Alembic tracks version in `alembic_version` table
- **Future Changes**: Any model changes require creating new Alembic migration

## Next Steps

1. ✅ Database setup complete
2. ✅ All tables created
3. ✅ Migrations configured
4. Ready to start backend and execute workflows
5. Data will be stored in correct databases automatically

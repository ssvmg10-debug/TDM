# TDM Database Setup Guide

This document explains the database architecture and migration setup for the TDM (Test Data Management) system.

## Database Architecture

The TDM system uses **two separate PostgreSQL databases**:

### 1. TDM Metadata Database (`tdm`)
**Connection:** `postgresql://postgres:12345@localhost:5432/tdm`

This database stores all metadata and operational information:

- **connections** - Source database connections
- **schemas** - Schema definitions and versions
- **schema_versions** - Versioned schema snapshots
- **tables** - Table metadata
- **columns** - Column metadata and types
- **relationships** - Foreign key relationships
- **pii_classification** - PII detection results
- **dataset_versions** - Generated dataset versions
- **dataset_metadata** - Dataset metadata key-value pairs
- **jobs** - Job execution tracking
- **job_logs** - Detailed job logs
- **lineage** - Data lineage tracking
- **masking_rules** - Data masking rule definitions
- **environments** - Target environment configurations

### 2. Target Data Database (`tdm_target`)
**Connection:** `postgresql://postgres:12345@localhost:5432/tdm_target`

This database stores the actual provisioned/synthetic data:
- Subsetted data from source databases
- Masked data (PII removed/obfuscated)
- Synthetic data generated from test cases
- Data ready for environment provisioning

## Migration Management with Alembic

### Setup Already Complete ✅

The following has been set up:

1. **Alembic initialized** - Migration directory created at `tdm-backend/alembic/`
2. **Initial migration created** - All 14 models migrated
3. **Tables created** - All metadata tables exist in `tdm` database
4. **Target database created** - `tdm_target` database ready for data

### Migration Commands

To work with migrations:

```bash
# Navigate to backend directory
cd tdm-backend

# Create a new migration after model changes
python -m alembic revision --autogenerate -m "Description of changes"

# Apply migrations (upgrade to latest)
python -m alembic upgrade head

# Rollback one migration
python -m alembic downgrade -1

# View migration history
python -m alembic history

# View current migration version
python -m alembic current
```

### Verify Database Setup

```python
# Check metadata database tables
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('\n'.join(sorted(inspector.get_table_names())))"

# Check Alembic migration version
python -m alembic current
```

## Data Flow

1. **Schema Discovery** → Stores metadata in `tdm.schemas`, `tdm.tables`, `tdm.columns`
2. **PII Classification** → Stores results in `tdm.pii_classification`
3. **Data Subsetting/Masking** → Processes source data, stores in `tdm_target`
4. **Synthetic Data Generation** → Generates from test cases, stores in `tdm_target`
5. **Provisioning** → Reads from `tdm_target`, deploys to target environments

## Configuration

Database URLs are configured in `config.py`:

```python
database_url = "postgresql://postgres:12345@localhost:5432/tdm"  # Metadata
target_database_url = "postgresql://postgres:12345@localhost:5432/tdm_target"  # Target data
```

These can be overridden via environment variables:
- `DATABASE_URL` - Metadata database
- `TARGET_DATABASE_URL` - Target data database

## Maintenance

### Reset Databases (Development Only)

```bash
# Reset metadata database
python reset_db.py

# Recreate target database
python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:12345@localhost:5432/postgres'); conn.autocommit = True; cur = conn.cursor(); cur.execute('DROP DATABASE IF EXISTS tdm_target'); cur.execute('CREATE DATABASE tdm_target'); cur.close(); conn.close()"
```

### Backup/Restore

```bash
# Backup metadata
pg_dump -h localhost -U postgres -d tdm > tdm_backup.sql

# Backup target data
pg_dump -h localhost -U postgres -d tdm_target > tdm_target_backup.sql

# Restore
psql -h localhost -U postgres -d tdm < tdm_backup.sql
psql -h localhost -U postgres -d tdm_target < tdm_target_backup.sql
```

## Troubleshooting

### Migration conflicts
```bash
# View pending migrations
python -m alembic heads

# Merge branches if multiple heads exist
python -m alembic merge -m "Merge migrations" <revision1> <revision2>
```

### Database connection issues
- Verify PostgreSQL is running: `psql -h localhost -U postgres -l`
- Check credentials in `config.py`
- Ensure databases exist: `tdm` and `tdm_target`

### Table not found errors
```bash
# Ensure migrations are up to date
python -m alembic upgrade head

# Verify tables exist
python -c "from database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

## Next Steps

With the database setup complete, you can now:

1. ✅ Run the backend server: `python -m uvicorn main:app --reload --port 8002`
2. ✅ Execute workflows that will store metadata in `tdm` database
3. ✅ Generated data will be stored in `tdm_target` database
4. ✅ Use provisioning operations to deploy data to target environments

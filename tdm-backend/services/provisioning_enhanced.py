"""
Phase 6: Provisioning Enhancements.
Schema evolution detection, migration script generator, table-by-table control, incremental updates.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text, inspect

from config import settings
from dataset_store import get_dataset_dir

logger = logging.getLogger("tdm.provisioning")


def detect_schema_evolution(
    target_connection: str,
    dataset_version_id: str,
) -> Dict[str, Any]:
    """
    Compare dataset schema with target DB schema.
    Returns: new_tables, modified_tables, dropped_tables, column_diffs.
    """
    base_dir = get_dataset_dir(dataset_version_id)
    if not base_dir.exists():
        return {"error": "Dataset not found"}
    parquet_files = list(base_dir.glob("*.parquet"))
    dataset_tables = {f.stem: pd.read_parquet(f, columns=[]).columns.tolist() for f in parquet_files}

    engine = create_engine(target_connection, pool_pre_ping=True)
    inspector = inspect(engine)
    target_tables = inspector.get_table_names()
    target_schema = {}
    for t in target_tables:
        cols = [c["name"] for c in inspector.get_columns(t)]
        target_schema[t] = cols

    new_tables = [t for t in dataset_tables if t not in target_schema]
    dropped_tables = [t for t in target_schema if t not in dataset_tables]
    modified_tables = []
    column_diffs = {}
    for t in dataset_tables:
        if t in target_schema:
            ds_cols = set(dataset_tables[t])
            tg_cols = set(target_schema[t])
            added = ds_cols - tg_cols
            removed = tg_cols - ds_cols
            if added or removed:
                modified_tables.append(t)
                column_diffs[t] = {"added": list(added), "removed": list(removed)}
    engine.dispose()
    return {
        "new_tables": new_tables,
        "modified_tables": modified_tables,
        "dropped_tables": dropped_tables,
        "column_diffs": column_diffs,
    }


def generate_migration_script(evolution: Dict[str, Any]) -> str:
    """Generate SQL migration script from schema evolution."""
    lines = ["-- TDM Schema Migration Script", ""]
    for t in evolution.get("new_tables", []):
        lines.append(f"-- Table {t} will be created by provision (CREATE from Parquet)")
    for t, diffs in evolution.get("column_diffs", {}).items():
        for col in diffs.get("added", []):
            lines.append(f"ALTER TABLE \"{t}\" ADD COLUMN \"{col}\" TEXT;")
        for col in diffs.get("removed", []):
            lines.append(f"ALTER TABLE \"{t}\" DROP COLUMN IF EXISTS \"{col}\";")
    return "\n".join(lines)


def provision_table_by_table(
    dataset_version_id: str,
    target_connection: str,
    tables_to_provision: Optional[List[str]] = None,
    reset_env: bool = True,
) -> Dict[str, Any]:
    """Provision only specified tables (table-by-table control)."""
    base_dir = get_dataset_dir(dataset_version_id)
    if not base_dir.exists():
        return {"error": "Dataset not found", "tables_loaded": []}
    parquet_files = sorted(base_dir.glob("*.parquet"))
    if tables_to_provision:
        parquet_files = [f for f in parquet_files if f.stem in tables_to_provision]
    tables_loaded = []
    row_counts = {}
    engine = create_engine(target_connection, pool_pre_ping=True)
    try:
        for pf in parquet_files:
            tname = pf.stem
            df = pd.read_parquet(pf)
            with engine.connect() as conn:
                if reset_env:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{tname}" CASCADE'))
                    conn.commit()
            df.to_sql(tname, engine, if_exists="replace", index=False, method="multi", chunksize=1000)
            tables_loaded.append(tname)
            row_counts[tname] = len(df)
        engine.dispose()
        return {"tables_loaded": tables_loaded, "row_counts": row_counts}
    except Exception as e:
        engine.dispose()
        raise e

"""Subset: FK-aware extract from source DB to parquet in dataset store."""
import logging
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path

from config import settings
from database import SessionLocal
from models import (
    SchemaVersion, TableMeta, ColumnMeta, Relationship,
    DatasetVersion, DatasetMetadata, Job, JobLog, Lineage,
)
from dataset_store import ensure_dataset_dir

logger = logging.getLogger(__name__)


def _build_fk_map(db: Session, schema_version_id: str) -> dict[str, list[tuple[str, str, str, str]]]:
    """child_table -> [(parent_table, parent_col, child_col), ...]"""
    sv = db.query(SchemaVersion).filter(SchemaVersion.id == schema_version_id).first()
    if not sv:
        return {}
    table_by_id = {t.id: t for t in sv.tables_rel}
    out = {}
    for rel in db.query(Relationship).filter(
        Relationship.parent_table_id.in_([t.id for t in sv.tables_rel]),
        Relationship.child_table_id.in_([t.id for t in sv.tables_rel]),
    ).all():
        pt = table_by_id.get(rel.parent_table_id)
        ct = table_by_id.get(rel.child_table_id)
        if not pt or not ct:
            continue
        pc = next((c for c in pt.columns if c.id == rel.parent_column_id), None)
        cc = next((c for c in ct.columns if c.id == rel.child_column_id), None)
        if pc and cc:
            out.setdefault(ct.name, []).append((pt.name, pc.name, cc.name))
    return out


def run_subset(
    schema_version_id: str,
    connection_string: str,
    root_table: str,
    filters: dict | None = None,
    max_rows_per_table: dict | None = None,
    job_id: str | None = None,
) -> dict:
    db = SessionLocal()
    try:
        if not job_id:
            job = Job(operation="subset", status="running", request_json={"schema_version_id": schema_version_id})
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        else:
            job = db.query(Job).get(job_id)
            if not job:
                raise ValueError("Job not found")

        def log(msg: str, level: str = "info"):
            db.add(JobLog(job_id=job_id, level=level, message=msg))
            db.commit()

        log("Starting subset extraction")
        sv = db.query(SchemaVersion).filter(SchemaVersion.id == schema_version_id).first()
        if not sv:
            log("Schema version not found", "error")
            job.status = "failed"
            db.commit()
            return {"job_id": job_id, "dataset_version_id": None}

        engine = create_engine(connection_string, pool_pre_ping=True)
        fk_map = _build_fk_map(db, schema_version_id)
        table_names = [t.name for t in sv.tables_rel]
        schema_ns = sv.tables_rel[0].schema_name if sv.tables_rel else "public"

        max_rows = max_rows_per_table or {}
        default_max = max_rows.get("*", 100_000)

        extracted = {}
        if root_table not in table_names:
            root_table = table_names[0] if table_names else root_table
        try:
            filter_clause = ""
            params = None
            if filters and filters.get(root_table):
                parts = [f'"{k}" = :{k}' for k in filters[root_table]]
                filter_clause = " WHERE " + " AND ".join(parts) if parts else ""
                params = filters[root_table]
            limit = max_rows.get(root_table, default_max)
            q = f'SELECT * FROM "{schema_ns}"."{root_table}"{filter_clause} LIMIT {limit}'
            with engine.connect() as conn:
                df = pd.read_sql(text(q), conn, params=params)
            limit = max_rows.get(root_table, default_max)
            if len(df) > limit:
                df = df.head(limit)
            extracted[root_table] = df
            log(f"Root table {root_table}: {len(df)} rows")

            for child_t in table_names:
                if child_t == root_table:
                    continue
                deps = fk_map.get(child_t, [])
                if not deps:
                    try:
                        with engine.connect() as conn:
                            edf = pd.read_sql(f'SELECT * FROM "{schema_ns}"."{child_t}"', conn)
                        if len(edf) > max_rows.get(child_t, default_max):
                            edf = edf.head(max_rows.get(child_t, default_max))
                        extracted[child_t] = edf
                        log(f"Table {child_t}: {len(edf)} rows (no FK)")
                    except Exception as e:
                        log(f"Table {child_t} failed: {e}", "warning")
                    continue
                parent_t, pcol, ccol = deps[0]
                if parent_t not in extracted:
                    continue
                parent_ids = extracted[parent_t][pcol].dropna().unique()
                if len(parent_ids) == 0:
                    extracted[child_t] = pd.DataFrame()
                    continue
                placeholders = ",".join([str(int(x)) if isinstance(x, (int, float)) else f"'{x}'" for x in parent_ids[:10000]])
                with engine.connect() as conn:
                    edf = pd.read_sql(
                        f'SELECT * FROM "{schema_ns}"."{child_t}" WHERE "{ccol}" IN ({placeholders})',
                        conn,
                    )
                limit = max_rows.get(child_t, default_max)
                if len(edf) > limit:
                    edf = edf.head(limit)
                extracted[child_t] = edf
                log(f"Table {child_t}: {len(edf)} rows")
        finally:
            engine.dispose()

        version_id = str(uuid4())
        path_prefix = str(Path(settings.dataset_store_path) / version_id)
        ensure_dataset_dir(version_id)
        for tname, df in extracted.items():
            # Convert object columns (e.g. UUID) to string so Arrow/Parquet can write them
            for c in df.columns:
                if df[c].dtype == object or str(df[c].dtype) == "object":
                    df[c] = df[c].apply(lambda x: str(x) if x is not None else None)
            fp = Path(settings.dataset_store_path) / version_id / f"{tname}.parquet"
            df.to_parquet(fp, index=False)

        dv = DatasetVersion(
            id=version_id,
            name=f"subset_{root_table}",
            schema_version_id=schema_version_id,
            source_type="subset",
            status="active",
            path_prefix=path_prefix,
        )
        db.add(dv)
        db.flush()  # ensure dataset_versions row exists before dataset_metadata (FK)
        row_counts = {t: int(len(df)) for t, df in extracted.items()}
        for k, v in row_counts.items():
            dm = DatasetMetadata(dataset_version_id=version_id, meta_key=f"row_count_{k}", meta_value=v)
            db.add(dm)
        db.add(DatasetMetadata(dataset_version_id=version_id, meta_key="row_counts", meta_value=row_counts))
        db.add(Lineage(source_type="schema_version", source_id=schema_version_id, target_type="dataset_version", target_id=version_id, operation="subset", job_id=job_id))
        from datetime import datetime
        job.status = "completed"
        job.result_json = {"dataset_version_id": version_id, "row_counts": row_counts}
        job.finished_at = datetime.utcnow()
        log("Subset completed")
        db.commit()
        return {"job_id": job_id, "dataset_version_id": version_id, "row_counts": row_counts}
    except Exception as e:
        logger.exception("Subset failed")
        if job_id:
            try:
                db.rollback()
                job = db.query(Job).get(job_id)
                if job:
                    job.status = "failed"
                    job.result_json = {"error": str(e)}
                    db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                    db.commit()
            except Exception:
                pass
        raise
    finally:
        db.close()

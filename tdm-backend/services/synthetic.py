"""Generate synthetic dataset from schema version (Faker + pandas)."""
import logging
from uuid import uuid4
from pathlib import Path
from datetime import datetime
import pandas as pd

from database import SessionLocal
from models import SchemaVersion, TableMeta, DatasetVersion, DatasetMetadata, Job, JobLog, Lineage
from config import settings
from dataset_store import ensure_dataset_dir

logger = logging.getLogger(__name__)

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None


def _fake_value(col_name: str, data_type: str, inferred: str):
    if inferred:
        inferred = inferred.lower()
        if "email" in inferred or col_name.lower() == "email":
            return fake.email() if fake else "user@example.com"
        if "phone" in inferred or "phone" in col_name.lower():
            return fake.phone_number() if fake else "+1555000000"
        if "name" in inferred or "name" in col_name.lower():
            return fake.name() if fake else "Unknown"
        if "address" in inferred or "address" in col_name.lower():
            return fake.address() if fake else "123 Main St"
        if "date" in inferred or "date" in col_name.lower():
            return fake.date_isoformat() if fake else "2024-01-01"
    if data_type:
        dt = str(data_type).upper()
        if "UUID" in dt:
            return str(uuid4()) if fake else "00000000-0000-0000-0000-000000000000"
        if "INT" in dt or "SERIAL" in dt or "BIGINT" in dt:
            return fake.random_int(1, 1000000) if fake else 1
        if "BOOL" in dt:
            return fake.boolean() if fake else False
        if "DATE" in dt or "TIME" in dt:
            return fake.iso8601() if fake else "2024-01-01T00:00:00"
        if "CHAR" in dt or "TEXT" in dt or "VARCHAR" in dt:
            return fake.word() if fake else "value"
    return fake.word() if fake else "value"


def run_synthetic(
    schema_version_id: str,
    row_counts: dict[str, int] | None = None,
    job_id: str | None = None,
) -> dict:
    db = SessionLocal()
    try:
        if not job_id:
            job = Job(operation="synthetic", status="running", request_json={"schema_version_id": schema_version_id})
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        else:
            job = db.query(Job).get(job_id)

        def log(msg: str, level: str = "info"):
            db.add(JobLog(job_id=job_id, level=level, message=msg))
            db.commit()

        log("Starting synthetic generation")
        sv = db.query(SchemaVersion).filter(SchemaVersion.id == schema_version_id).first()
        if not sv:
            log("Schema version not found", "error")
            job.status = "failed"
            db.commit()
            return {"job_id": job_id, "dataset_version_id": None}

        row_counts = row_counts or {}
        default_rows = row_counts.get("*", 1000)
        version_id = str(uuid4())
        ensure_dataset_dir(version_id)
        out_path = Path(settings.dataset_store_path) / version_id
        generated = {}
        pk_columns = {}  # table -> pk col name for FK refs
        for table in sv.tables_rel:
            n = row_counts.get(table.name, default_rows)
            cols = [(c.name, c.data_type, c.inferred_type) for c in table.columns]
            if not cols:
                continue
            data = {}
            pk_col = None
            for cname, dtype, inferred in cols:
                dstr = str(dtype or "").lower()
                if ("int" in dstr or "serial" in dstr) and ("id" in cname.lower() or "pk" in cname.lower()):
                    pk_col = cname
                try:
                    data[cname] = [_fake_value(cname, str(dtype or ""), str(inferred or "")) for _ in range(n)]
                except Exception as e:
                    logger.warning("Column %s: %s", cname, e)
                    data[cname] = ["value"] * n
            if pk_col and pk_col not in data:
                pk_col = None
            if not pk_col and cols:
                pk_col = cols[0][0]
            if pk_col:
                data[pk_col] = list(range(1, n + 1))
            pk_columns[table.name] = pk_col
            df = pd.DataFrame(data)
            df.to_parquet(out_path / f"{table.name}.parquet", index=False)
            generated[table.name] = n
            log(f"Generated {table.name}: {n} rows")

        path_prefix = str(out_path)
        dv = DatasetVersion(
            id=version_id,
            name=f"synthetic_{schema_version_id[:8]}",
            schema_version_id=schema_version_id,
            source_type="synthetic",
            status="active",
            path_prefix=path_prefix,
        )
        db.add(dv)
        db.flush()  # ensure dataset_versions row exists before dataset_metadata (FK)
        db.add(DatasetMetadata(dataset_version_id=version_id, meta_key="row_counts", meta_value=generated))
        db.add(Lineage(source_type="schema_version", source_id=schema_version_id, target_type="dataset_version", target_id=version_id, operation="synthetic", job_id=job_id))
        job.status = "completed"
        job.result_json = {"dataset_version_id": version_id, "row_counts": generated}
        job.finished_at = datetime.utcnow()
        log("Synthetic generation completed")
        db.commit()
        return {"job_id": job_id, "dataset_version_id": version_id}
    except Exception as e:
        logger.exception("Synthetic failed")
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

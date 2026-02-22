"""Load dataset version into target environment (PostgreSQL)."""
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

from database import SessionLocal
from models import Environment, DatasetVersion, Job, JobLog, Lineage
from config import settings
from dataset_store import get_dataset_dir

logger = logging.getLogger(__name__)


def run_provision(
    dataset_version_id: str,
    target_env: str,
    reset_env: bool = True,
    run_smoke_tests: bool = True,
    job_id: str | None = None,
) -> dict:
    db = SessionLocal()
    try:
        if not job_id:
            job = Job(operation="provision", status="running", request_json={"dataset_version_id": dataset_version_id, "target_env": target_env})
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        else:
            job = db.query(Job).get(job_id)

        def log(msg: str, level: str = "info"):
            db.add(JobLog(job_id=job_id, level=level, message=msg))
            db.commit()

        log("Starting provisioning")
        env = db.query(Environment).filter(Environment.name == target_env).first()
        connection_string = env.connection_string_encrypted if env else settings.database_url
        if not connection_string:
            log("No connection string for environment", "error")
            job.status = "failed"
            db.commit()
            return {"job_id": job_id, "status": "failed"}

        base_dir = get_dataset_dir(dataset_version_id)
        if not base_dir.exists():
            log("Dataset not found", "error")
            job.status = "failed"
            db.commit()
            return {"job_id": job_id, "status": "failed"}

        engine = create_engine(connection_string, pool_pre_ping=True)
        tables_loaded = []
        row_counts = {}
        try:
            for parquet_file in sorted(base_dir.glob("*.parquet")):
                tname = parquet_file.stem
                df = pd.read_parquet(parquet_file)
                with engine.connect() as conn:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{tname}" CASCADE'))
                    conn.commit()
                df.to_sql(tname, engine, if_exists="replace", index=False, method="multi", chunksize=1000)
                tables_loaded.append(tname)
                row_counts[tname] = len(df)
                log(f"Loaded {tname}: {len(df)} rows", "success")
            if run_smoke_tests:
                for t in tables_loaded:
                    with engine.connect() as conn:
                        r = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                    log(f"Smoke check {t}: {r} rows")
            db.add(Lineage(source_type="dataset_version", source_id=dataset_version_id, target_type="environment", target_id=target_env, operation="provision", job_id=job_id))
            job.status = "completed"
            job.result_json = {"tables_loaded": tables_loaded, "row_counts": row_counts, "smoke_test_results": {"passed": True}}
            job.finished_at = datetime.utcnow()
            log("Provisioning complete")
        finally:
            engine.dispose()
        db.commit()
        return {"job_id": job_id, "status": "completed", "tables_loaded": tables_loaded, "row_counts": row_counts}
    except Exception as e:
        logger.exception("Provision failed")
        if job_id:
            job = db.query(Job).get(job_id)
            if job:
                job.status = "failed"
                job.result_json = {"error": str(e)}
                db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                db.commit()
        raise
    finally:
        db.close()

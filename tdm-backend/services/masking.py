"""Apply masking rules to a dataset version; write new version."""
import hashlib
import re
import logging
from uuid import uuid4
from pathlib import Path
import pandas as pd
from datetime import datetime

from config import settings
from database import SessionLocal
from models import DatasetVersion, DatasetMetadata, Job, JobLog, Lineage
from dataset_store import get_dataset_dir, ensure_dataset_dir

logger = logging.getLogger(__name__)
SALT = b"tdm-mask-v1"


def _mask_email_deterministic(val):
    if pd.isna(val) or val == "":
        return val
    s = str(val).strip()
    parts = s.split("@")
    if len(parts) != 2:
        return "***@***.***"
    h = hashlib.sha256((SALT + s.encode()).hex().encode()).hexdigest()[:8]
    return f"{h}@masked.local"


def _mask_hash(val):
    if pd.isna(val) or val == "":
        return val
    return hashlib.sha256(SALT + str(val).encode()).hexdigest()[:16]


def _mask_redact(val):
    if pd.isna(val) or val == "":
        return val
    return "REDACTED"


def _mask_null(val):
    return None


def _mask_fpe_pan(val):
    if pd.isna(val) or val == "":
        return val
    s = re.sub(r"\D", "", str(val))
    if len(s) < 4:
        return "****"
    return s[:4] + "-****-****-" + s[-4:]


TRANSFORMERS = {
    "mask.email_deterministic": _mask_email_deterministic,
    "mask.hash": _mask_hash,
    "mask.redact": _mask_redact,
    "mask.null": _mask_null,
    "mask.fpe_pan": _mask_fpe_pan,
}


def run_mask(
    dataset_version_id: str,
    rules: dict[str, str],
    job_id: str | None = None,
) -> dict:
    db = SessionLocal()
    try:
        if not job_id:
            job = Job(operation="mask", status="running", request_json={"dataset_version_id": dataset_version_id, "rules": rules})
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        else:
            job = db.query(Job).get(job_id)

        def log(msg: str, level: str = "info"):
            db.add(JobLog(job_id=job_id, level=level, message=msg))
            db.commit()

        log("Starting masking")
        base_dir = get_dataset_dir(dataset_version_id)
        if not base_dir.exists():
            log("Dataset not found", "error")
            job.status = "failed"
            db.commit()
            return {"job_id": job_id, "masked_dataset_version_id": None}

        new_version_id = str(uuid4())
        ensure_dataset_dir(new_version_id)
        out_path = Path(settings.dataset_store_path) / new_version_id
        row_counts = {}
        for parquet_file in base_dir.glob("*.parquet"):
            tname = parquet_file.stem
            df = pd.read_parquet(parquet_file)
            for key, rule_type in rules.items():
                if "." in key:
                    tbl, col = key.split(".", 1)
                    if tbl != tname:
                        continue
                    if col not in df.columns:
                        continue
                    fn = TRANSFORMERS.get(rule_type, _mask_redact)
                    df[col] = df[col].apply(fn)
            df.to_parquet(out_path / f"{tname}.parquet", index=False)
            row_counts[tname] = len(df)
            log(f"Masked table {tname}: {len(df)} rows")

        path_prefix = str(out_path)
        dv = DatasetVersion(
            id=new_version_id,
            name=f"masked_{dataset_version_id[:8]}",
            schema_version_id=db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first().schema_version_id if db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first() else None,
            source_type="masked",
            status="active",
            path_prefix=path_prefix,
        )
        db.add(dv)
        db.add(DatasetMetadata(dataset_version_id=new_version_id, meta_key="row_counts", meta_value=row_counts))
        db.add(Lineage(source_type="dataset_version", source_id=dataset_version_id, target_type="dataset_version", target_id=new_version_id, operation="mask", job_id=job_id))
        job.status = "completed"
        job.result_json = {"masked_dataset_version_id": new_version_id, "row_counts": row_counts}
        job.finished_at = datetime.utcnow()
        log("Masking completed")
        db.commit()
        return {"job_id": job_id, "masked_dataset_version_id": new_version_id}
    except Exception as e:
        logger.exception("Mask failed")
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

from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import Lineage, Job
from schemas_pydantic import LineageItem

router = APIRouter()


@router.get("/lineage/dataset/{dataset_id}", response_model=list[LineageItem])
def get_lineage_dataset(dataset_id: str):
    db = SessionLocal()
    try:
        rows = db.query(Lineage).filter(
            (Lineage.source_id == dataset_id) | (Lineage.target_id == dataset_id)
        ).order_by(Lineage.created_at).all()
        return [
            LineageItem(source_type=r.source_type, source_id=r.source_id, target_type=r.target_type, target_id=r.target_id, operation=r.operation, created_at=r.created_at)
            for r in rows
        ]
    finally:
        db.close()


@router.get("/lineage/job/{job_id}/full")
def get_job_lineage_full(job_id: str):
    """Phase 7: Full lineage for a job including field-level, fallbacks, schema sources."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404, "Job not found")
        rows = db.query(Lineage).filter(Lineage.job_id == job_id).order_by(Lineage.created_at).all()
        req = job.request_json or {}
        res = job.result_json or {}
        job_context = res.get("job_context") or req.get("job_context") or {}
        lineage_items = [
            {
                "source_type": r.source_type,
                "source_id": r.source_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "operation": r.operation,
                "details": getattr(r, "details", None),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return {
            "job_id": job_id,
            "job_context": job_context,
            "lineage": lineage_items,
            "fallbacks_used": job_context.get("fallbacks_used", []),
            "quality_score": job_context.get("quality_score"),
        }
    finally:
        db.close()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Job, JobLog
from schemas_pydantic import JobItem, JobDetail

router = APIRouter()


@router.get("/jobs", response_model=list[JobItem])
def list_jobs(
    db: Session = Depends(get_db),
    operation: str | None = None,
    status: str | None = None,
    limit: int = 50,
):
    q = db.query(Job)
    if operation:
        q = q.filter(Job.operation == operation)
    if status:
        q = q.filter(Job.status == status)
    q = q.order_by(Job.started_at.desc()).limit(limit)
    jobs = q.all()
    return [
        JobItem(
            id=j.id,
            operation=j.operation,
            status=j.status,
            started_at=j.started_at,
            finished_at=j.finished_at,
            result_json=j.result_json,
            request_json=j.request_json if j.operation == "workflow" else None,
        )
        for j in jobs
    ]


@router.get("/job/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    logs = db.query(JobLog).filter(JobLog.job_id == job_id).order_by(JobLog.created_at).all()
    return JobDetail(
        id=job.id,
        operation=job.operation,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result_json=job.result_json,
        request_json=job.request_json,
        logs=[{"level": l.level, "message": l.message, "created_at": l.created_at, "step": getattr(l, "step", None), "details": getattr(l, "details", None)} for l in logs],
    )


@router.get("/job/{job_id}/trace")
def get_job_trace(job_id: str, db: Session = Depends(get_db)):
    """
    Return full traceability: test case -> job -> dataset -> tdm_target tables.
    Links which test case produced which data for production-grade auditing.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    req = job.request_json or {}
    res = job.result_json or {}
    ops = res.get("operations") or {}
    dataset_version_id = (
        ops.get("synthetic", {}).get("dataset_version_id") or
        ops.get("mask", {}).get("dataset_version_id") or
        ops.get("subset", {}).get("dataset_version_id")
    )
    provision_result = ops.get("provision", {})
    tables_loaded = provision_result.get("tables_loaded") or []
    row_counts = provision_result.get("row_counts") or {}
    job_context = res.get("job_context") or req.get("job_context")
    ops_executed = list(ops.keys()) if isinstance(ops, dict) else (req.get("operations") or [])
    result = {
        "job_id": job.id,
        "workflow_id": req.get("workflow_id"),
        "test_case_id": req.get("test_case_id"),
        "test_case_summary": req.get("test_case_summary"),
        "operations": req.get("operations"),
        "operations_executed": ops_executed,
        "dataset_version_id": dataset_version_id,
        "provisioned_tables": tables_loaded,
        "row_counts": row_counts,
        "status": job.status,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
    if job_context:
        result["job_context"] = job_context
        result["quality_score"] = job_context.get("quality_score")
    return result

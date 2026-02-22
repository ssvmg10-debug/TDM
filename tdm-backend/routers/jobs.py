from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import Job, JobLog
from schemas_pydantic import JobItem, JobDetail

router = APIRouter()


@router.get("/jobs", response_model=list[JobItem])
def list_jobs(operation: str | None = None, status: str | None = None, limit: int = 50):
    db = SessionLocal()
    try:
        q = db.query(Job).order_by(Job.started_at.desc()).limit(limit)
        if operation:
            q = q.filter(Job.operation == operation)
        if status:
            q = q.filter(Job.status == status)
        jobs = q.all()
        return [
            JobItem(
                id=j.id,
                operation=j.operation,
                status=j.status,
                started_at=j.started_at,
                finished_at=j.finished_at,
                result_json=j.result_json,
            )
            for j in jobs
        ]
    finally:
        db.close()


@router.get("/job/{job_id}", response_model=JobDetail)
def get_job(job_id: str):
    db = SessionLocal()
    try:
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
            logs=[{"level": l.level, "message": l.message, "created_at": l.created_at} for l in logs],
        )
    finally:
        db.close()

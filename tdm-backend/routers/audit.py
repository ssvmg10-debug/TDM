"""Audit logs from job_logs and jobs."""
from fastapi import APIRouter
from database import SessionLocal
from models import Job, JobLog
from schemas_pydantic import AuditLogItem

router = APIRouter()


@router.get("/audit-logs", response_model=list[AuditLogItem])
def list_audit_logs(limit: int = 100):
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.started_at.desc()).limit(limit).all()
        out = []
        for j in jobs:
            out.append(AuditLogItem(
                id=j.id[:8].upper(),
                action=f"{j.operation} job",
                target=j.operation,
                user=j.user_id or "system",
                role="System",
                time=j.started_at.strftime("%H:%M:%S") if j.started_at else "",
                severity="error" if j.status == "failed" else "info",
            ))
        return out
    finally:
        db.close()

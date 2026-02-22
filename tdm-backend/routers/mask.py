from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas_pydantic import MaskRequest, MaskResponse
from services.masking import run_mask
from database import SessionLocal
from models import Job

router = APIRouter()


def _run_mask_task(job_id: str, dataset_version_id: str, rules: dict):
    run_mask(dataset_version_id=dataset_version_id, rules=rules, job_id=job_id)


@router.post("/mask", response_model=MaskResponse)
def post_mask(body: MaskRequest, background_tasks: BackgroundTasks):
    rules = body.rules
    if not rules:
        from database import SessionLocal
        from models import MaskingRule
        db = SessionLocal()
        rset = db.query(MaskingRule).filter(MaskingRule.id == body.rule_set_id).first() if body.rule_set_id else None
        if rset:
            rules = rset.rules_json or {}
        db.close()
        if not rules:
            raise HTTPException(status_code=400, detail="rules or rule_set_id required")
    job = Job(operation="mask", status="running", request_json=body.model_dump())
    db = SessionLocal()
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    background_tasks.add_task(_run_mask_task, job_id, body.dataset_version_id, rules)
    return MaskResponse(job_id=job_id, message="Mask job started")

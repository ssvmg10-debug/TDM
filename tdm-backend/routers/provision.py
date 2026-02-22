from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas_pydantic import ProvisionRequest, ProvisionResponse
from services.provisioning import run_provision
from database import SessionLocal
from models import Job

router = APIRouter()


def _run_provision_task(job_id: str, dataset_version_id: str, target_env: str, reset_env: bool, run_smoke_tests: bool):
    run_provision(dataset_version_id=dataset_version_id, target_env=target_env, reset_env=reset_env, run_smoke_tests=run_smoke_tests, job_id=job_id)


@router.post("/provision", response_model=ProvisionResponse)
def post_provision(body: ProvisionRequest, background_tasks: BackgroundTasks):
    job = Job(operation="provision", status="running", request_json=body.model_dump())
    db = SessionLocal()
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    background_tasks.add_task(
        _run_provision_task,
        job_id,
        body.dataset_version_id,
        body.target_env,
        body.reset_env,
        body.run_smoke_tests,
    )
    return ProvisionResponse(job_id=job_id, status="pending", message="Provision job started")

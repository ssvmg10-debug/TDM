from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas_pydantic import SubsetRequest, SubsetResponse
from services.subsetting import run_subset
from database import SessionLocal
from models import Job

router = APIRouter()


def _run_subset_task(job_id: str, schema_version_id: str, connection_string: str, root_table: str, filters: dict | None, max_rows: dict | None):
    run_subset(schema_version_id=schema_version_id, connection_string=connection_string, root_table=root_table, filters=filters, max_rows_per_table=max_rows, job_id=job_id)


@router.post("/subset", response_model=SubsetResponse)
def post_subset(body: SubsetRequest, background_tasks: BackgroundTasks):
    from config import settings
    connection_string = body.connection_string or settings.database_url
    if not connection_string:
        raise HTTPException(status_code=400, detail="connection_string required")
    job = Job(operation="subset", status="running", request_json=body.model_dump())
    db = SessionLocal()
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    background_tasks.add_task(
        _run_subset_task,
        job_id,
        body.schema_version_id,
        connection_string,
        body.root_table,
        body.filters,
        body.max_rows_per_table,
    )
    return SubsetResponse(job_id=job_id, message="Subset job started")


from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas_pydantic import SyntheticRequest, SyntheticResponse
from services.synthetic import run_synthetic
from database import SessionLocal
from models import Job

router = APIRouter()


def _run_synthetic_task(job_id: str, schema_version_id: str, row_counts: dict | None):
    run_synthetic(schema_version_id=schema_version_id, row_counts=row_counts, job_id=job_id)


@router.post("/synthetic", response_model=SyntheticResponse)
def post_synthetic(body: SyntheticRequest, background_tasks: BackgroundTasks):
    try:
        schema_version_id = body.schema_version_id
        if not schema_version_id:
            from models import SchemaVersion
            db = SessionLocal()
            latest = db.query(SchemaVersion).order_by(SchemaVersion.discovered_at.desc()).first()
            if not latest:
                db.close()
                raise HTTPException(status_code=400, detail="No schema version found. Run discover-schema first.")
            schema_version_id = latest.id
            db.close()
        req_json = body.model_dump()
        # Ensure JSON-serializable (e.g. no Pydantic models)
        if isinstance(req_json.get("row_counts"), dict):
            req_json["row_counts"] = {str(k): int(v) for k, v in req_json["row_counts"].items()}
        job = Job(operation="synthetic", status="running", request_json=req_json)
        db = SessionLocal()
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
        db.close()
        background_tasks.add_task(_run_synthetic_task, job_id, schema_version_id, body.row_counts)
        return SyntheticResponse(job_id=job_id, message="Synthetic job started")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

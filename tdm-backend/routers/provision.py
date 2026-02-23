from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import text, create_engine
from schemas_pydantic import ProvisionRequest, ProvisionResponse
from services.provisioning import run_provision
from database import SessionLocal
from models import Job
from config import settings

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


@router.get("/target-tables")
def get_target_tables():
    """List tables in the target database (tdm_target). Used to verify provision created tables."""
    try:
        engine = create_engine(settings.target_database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            ))
            tables = [row[0] for row in r]
        engine.dispose()
        return {"database": "tdm_target", "tables": tables, "count": len(tables)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Target database unreachable: {str(e)}")


@router.get("/schema-evolution/{dataset_version_id}")
def get_schema_evolution(dataset_version_id: str):
    """Phase 6: Detect schema evolution between dataset and target DB."""
    from services.provisioning_enhanced import detect_schema_evolution
    conn = settings.target_database_url
    if not conn:
        raise HTTPException(503, "Target database URL not configured")
    try:
        return detect_schema_evolution(conn, dataset_version_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/migration-script/{dataset_version_id}")
def get_migration_script(dataset_version_id: str):
    """Phase 6: Generate migration script from schema evolution."""
    from services.provisioning_enhanced import detect_schema_evolution, generate_migration_script
    conn = settings.target_database_url
    if not conn:
        raise HTTPException(503, "Target database URL not configured")
    try:
        evolution = detect_schema_evolution(conn, dataset_version_id)
        script = generate_migration_script(evolution)
        return {"evolution": evolution, "script": script}
    except Exception as e:
        raise HTTPException(500, str(e))

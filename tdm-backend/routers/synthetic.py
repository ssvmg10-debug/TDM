from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas_pydantic import SyntheticRequest, SyntheticResponse
from services.synthetic_enhanced import SyntheticDataGenerator
from database import SessionLocal
from models import Job, SchemaVersion

router = APIRouter()


@router.get("/synthetic/domains")
def get_domains():
    """Get available domain packs and scenarios."""
    return {
        "domains": [
            {
                "name": "ecommerce",
                "label": "E-Commerce",
                "description": "Online shopping, orders, customers, products",
                "scenarios": ["default", "b2c", "b2b", "marketplace"],
                "entities": ["customer", "order", "order_item", "product", "payment"]
            },
            {
                "name": "banking",
                "label": "Banking & Finance",
                "description": "Accounts, transactions, customers, loans",
                "scenarios": ["default", "retail", "corporate", "investment"],
                "entities": ["account", "transaction", "customer", "loan", "beneficiary"]
            },
            {
                "name": "telecom",
                "label": "Telecommunications",
                "description": "Customers, SIMs, recharges, plans",
                "scenarios": ["default", "prepaid", "postpaid", "enterprise"],
                "entities": ["customer", "sim", "recharge", "plan", "usage"]
            },
            {
                "name": "healthcare",
                "label": "Healthcare",
                "description": "Patients, appointments, prescriptions, doctors",
                "scenarios": ["default", "hospital", "clinic", "pharmacy"],
                "entities": ["patient", "appointment", "prescription", "doctor", "diagnosis"]
            },
            {
                "name": "generic",
                "label": "Generic",
                "description": "Basic test data structure",
                "scenarios": ["default"],
                "entities": ["test_entity"]
            }
        ]
    }


def _run_synthetic_task(job_id: str, mode: str, **kwargs):
    """Background task to run synthetic data generation."""
    generator = SyntheticDataGenerator()
    
    if mode == "schema_version":
        generator.generate_from_schema_version(
            schema_version_id=kwargs["schema_version_id"],
            row_counts=kwargs.get("row_counts"),
            job_id=job_id
        )
    elif mode == "test_cases":
        generator.generate_from_test_cases(
            test_case_urls=kwargs["test_case_urls"],
            domain=kwargs.get("domain", "generic"),
            scenario=kwargs.get("scenario", "default"),
            row_counts=kwargs.get("row_counts"),
            job_id=job_id
        )
    elif mode == "domain_scenario":
        generator.generate_from_domain_scenario(
            domain=kwargs["domain"],
            scenario=kwargs.get("scenario", "default"),
            row_counts=kwargs.get("row_counts"),
            job_id=job_id
        )


@router.post("/synthetic", response_model=SyntheticResponse)
def post_synthetic(body: SyntheticRequest, background_tasks: BackgroundTasks):
    """
    Generate synthetic data using one of three modes:
    
    1. From existing schema version: Provide schema_version_id
    2. From test case URLs: Provide test_case_urls (and optionally domain/scenario)
    3. From domain/scenario: Provide domain and optionally scenario
    
    The system will automatically determine the mode based on provided parameters.
    """
    try:
        # Determine mode and validate
        mode = None
        kwargs = {"row_counts": body.row_counts}
        
        # Legacy support: map old fields to new ones
        if body.ui_urls:
            body.test_case_urls = body.ui_urls
        if body.domain_pack and not body.domain:
            body.domain = body.domain_pack
            
        # Mode 1: From schema version
        if body.schema_version_id:
            mode = "schema_version"
            kwargs["schema_version_id"] = body.schema_version_id
            
        # Mode 2: From test cases (crawl)
        elif body.test_case_urls:
            mode = "test_cases"
            kwargs["test_case_urls"] = body.test_case_urls
            kwargs["domain"] = body.domain or "generic"
            kwargs["scenario"] = body.scenario or "default"
            
        # Mode 3: From domain/scenario
        elif body.domain:
            mode = "domain_scenario"
            kwargs["domain"] = body.domain
            kwargs["scenario"] = body.scenario or "default"
            
        # Fallback: try to get latest schema version
        else:
            db = SessionLocal()
            latest = db.query(SchemaVersion).order_by(SchemaVersion.discovered_at.desc()).first()
            db.close()
            
            if latest:
                mode = "schema_version"
                kwargs["schema_version_id"] = latest.id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No schema version found and no test_case_urls or domain provided. Please run schema discovery first or provide test_case_urls/domain."
                )
        
        # Create job
        req_json = body.model_dump()
        if isinstance(req_json.get("row_counts"), dict):
            req_json["row_counts"] = {str(k): int(v) for k, v in req_json["row_counts"].items()}
            
        job = Job(
            operation="synthetic",
            status="running",
            request_json=req_json
        )
        db = SessionLocal()
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
        db.close()
        
        # Start background task
        background_tasks.add_task(_run_synthetic_task, job_id, mode, **kwargs)
        
        return SyntheticResponse(
            job_id=job_id,
            message=f"Synthetic job started in {mode} mode"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



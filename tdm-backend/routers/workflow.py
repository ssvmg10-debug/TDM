"""
Workflow API Router
Unified workflow endpoint that orchestrates all TDM operations
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

from database import get_db, SessionLocal
from services.workflow_orchestrator import execute_workflow

logger = logging.getLogger("tdm.api")
router = APIRouter(prefix="/workflow", tags=["Workflow Orchestration"])


class WorkflowRequest(BaseModel):
    """
    Generic workflow request accepting test cases and configuration
    """
    # Input sources
    test_case_content: Optional[str] = Field(
        None,
        description="Raw test case content (Cucumber scenarios, Selenium scripts, manual steps, etc.)"
    )
    test_case_urls: Optional[List[str]] = Field(
        None, 
        description="List of test case URLs to crawl (web UI test cases)"
    )
    test_case_files: Optional[List[str]] = Field(
        None, 
        description="List of test case files (Cucumber, Selenium, Playwright, etc.)"
    )
    connection_string: Optional[str] = Field(
        None, 
        description="Database connection string for schema discovery"
    )
    domain: Optional[str] = Field(
        None, 
        description="Domain pack to use (ecommerce, banking, telecom, healthcare, insurance, generic)"
    )
    
    # Operations to run (default: all)
    operations: Optional[List[str]] = Field(
        None,
        description="Operations to run. Options: discover, pii, subset, mask, synthetic, provision. If not specified, runs all."
    )
    
    # Operation-specific configuration
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="""
        Configuration for each operation:
        {
            "discover": {},
            "pii": {"use_llm": false},
            "subset": {"root_table": "users", "filters": {}, "max_rows_per_table": 10000},
            "mask": {"rules": []},
            "synthetic": {"row_counts": {"*": 100}, "scenario": "default"},
            "provision": {"environment_id": "...", "target_connection": "...", "mode": "copy"}
        }
        """
    )
    
    # Common configuration
    schema_version_id: Optional[str] = Field(
        None,
        description="Existing schema version ID to use (skip discovery)"
    )
    dataset_version_id: Optional[str] = Field(
        None,
        description="Existing dataset version ID to use (skip generation)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_case_urls": [
                    "https://example.com/login",
                    "https://example.com/checkout"
                ],
                "domain": "ecommerce",
                "operations": ["synthetic", "provision"],
                "config": {
                    "synthetic": {
                        "row_counts": {"*": 500}
                    },
                    "provision": {
                        "target_connection": "postgresql://user:pass@host:5432/db",
                        "mode": "copy"
                    }
                }
            }
        }


class WorkflowResponse(BaseModel):
    """Workflow execution response"""
    workflow_id: str
    job_id: str
    operations: Dict[str, Any]
    overall_status: str
    start_time: str
    end_time: Optional[str] = None
    error: Optional[str] = None


@router.post("/execute", response_model=WorkflowResponse)
async def execute_tdm_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Execute complete TDM workflow
    
    This unified endpoint orchestrates all TDM operations based on test case input:
    1. Schema Discovery (from DB or crawled test cases)
    2. PII Detection & Classification
    3. Data Subsetting
    4. Data Masking
    5. Synthetic Data Generation
    6. Environment Provisioning
    
    **Example 1: Full workflow from database**
    ```json
    {
        "connection_string": "postgresql://user:pass@host:5432/db",
        "operations": ["discover", "pii", "synthetic", "provision"],
        "config": {
            "pii": {"use_llm": true},
            "synthetic": {"row_counts": {"*": 1000}},
            "provision": {"target_connection": "...", "mode": "copy"}
        }
    }
    ```
    
    **Example 2: Synthetic from test cases only**
    ```json
    {
        "test_case_urls": [
            "https://app.example.com/login",
            "https://app.example.com/checkout"
        ],
        "domain": "ecommerce",
        "operations": ["synthetic"],
        "config": {
            "synthetic": {"row_counts": {"*": 500}}
        }
    }
    ```
    
    **Example 3: Complete e-commerce workflow**
    ```json
    {
        "test_case_urls": ["https://shop.example.com/products"],
        "connection_string": "postgresql://localhost:5432/prod",
        "domain": "ecommerce",
        "operations": ["discover", "pii", "subset", "mask", "synthetic", "provision"],
        "config": {
            "subset": {"root_table": "customers", "max_rows_per_table": 5000},
            "mask": {"rules": [{"column": "email", "method": "hash"}]},
            "synthetic": {"row_counts": {"customers": 1000, "orders": 5000}},
            "provision": {"environment_id": "uat-env", "mode": "replace"}
        }
    }
    ```
    
    **Returns:**
    - workflow_id: Unique workflow execution ID
    - job_id: Job ID for tracking
    - operations: Status and results for each operation
    - overall_status: Overall workflow status (running, completed, failed)
    """
    
    logger.info(f"Starting workflow execution: {request.dict()}")
    
    # Merge schema_version_id and dataset_version_id into config
    if request.schema_version_id:
        request.config["schema_version_id"] = request.schema_version_id
    if request.dataset_version_id:
        request.config["dataset_version_id"] = request.dataset_version_id
    
    # Generate IDs for tracking
    import uuid
    from datetime import datetime
    workflow_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    # Execute workflow in background with its own DB session so logs are persisted
    def run_workflow_with_error_handling():
        db = SessionLocal()
        try:
            print(f"[WORKFLOW] Starting background execution: workflow_id={workflow_id}, job_id={job_id}", flush=True)
            logger.info(f"[WORKFLOW] Starting background execution: workflow_id={workflow_id}, job_id={job_id}")
            result = execute_workflow(
                test_case_content=request.test_case_content,
                test_case_urls=request.test_case_urls,
                test_case_files=request.test_case_files,
                connection_string=request.connection_string,
                domain=request.domain,
                operations=request.operations,
                config=request.config,
                db=db,
                workflow_id=workflow_id,
                job_id=job_id,
            )
            print(f"[WORKFLOW] Completed: workflow_id={workflow_id}, status={result.get('overall_status')}", flush=True)
            logger.info(f"[WORKFLOW] Completed: workflow_id={workflow_id}, status={result.get('overall_status')}")
        except Exception as e:
            print(f"[WORKFLOW ERROR] {workflow_id}: {str(e)}", flush=True)
            logger.error(f"[WORKFLOW ERROR] {workflow_id}: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    background_tasks.add_task(run_workflow_with_error_handling)
    
    print(f"[WORKFLOW] Queued: workflow_id={workflow_id}, job_id={job_id}", flush=True)
    logger.info(f"[WORKFLOW] Queued: workflow_id={workflow_id}, job_id={job_id}")
    
    # Return immediately with job_id for tracking
    return {
        "workflow_id": workflow_id,
        "job_id": job_id,
        "operations": {},
        "overall_status": "queued",
        "start_time": datetime.utcnow().isoformat()
    }


@router.get("/logs/{job_id}")
async def get_workflow_logs(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get logs for a specific workflow job. Logs are written by the orchestrator
    and polled by the UI so they appear while the workflow is running.
    Includes job_status so the UI can stop polling when the job completes.
    """
    from models import JobLog, Job
    job_id_str = str(job_id)
    job = db.query(Job).filter(Job.id == job_id_str).first()
    job_status = job.status if job else None
    logs = db.query(JobLog).filter(JobLog.job_id == job_id_str).order_by(JobLog.created_at).all()
    return {
        "job_id": job_id_str,
        "job_status": job_status,
        "logs": [
            {
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "step": getattr(log, "step", None) or "",
                "level": (log.level or "info"),
                "message": (log.message or ""),
                "details": (getattr(log, "details", None) or {}) if isinstance(getattr(log, "details", None), dict) else {},
            }
            for log in logs
        ],
    }


class ClassifyIntentRequest(BaseModel):
    """Request for intent classification (Dynamic Decision Engine)."""
    test_case_content: Optional[str] = None
    test_case_urls: Optional[List[str]] = None
    connection_string: Optional[str] = None
    domain: Optional[str] = None
    schema_version_id: Optional[str] = None
    config_flags: Optional[Dict[str, Any]] = None


@router.post("/classify-intent")
async def classify_workflow_intent(body: ClassifyIntentRequest):
    """
    Classify intent and get recommended operations (Dynamic Decision Engine).
    Returns: intent, operations, preferred_synthetic_mode, plan.
    """
    from services.decision_engine import classify_intent, generate_pipeline_plan
    intent = classify_intent(
        test_case_content=body.test_case_content,
        test_case_urls=body.test_case_urls,
        connection_string=body.connection_string,
        domain=body.domain,
        schema_version_id=body.schema_version_id,
        config_flags=body.config_flags or {},
    )
    plan = generate_pipeline_plan(intent)
    return {
        "intent": intent,
        "plan": plan,
        "operations": plan.get("operations", []),
        "preferred_synthetic_mode": intent.get("preferred_synthetic_mode", "schema"),
    }


class AnalyzeTestCaseRequest(BaseModel):
    test_case_content: Optional[str] = None


@router.post("/analyze-test-case")
async def analyze_test_case_content(body: AnalyzeTestCaseRequest):
    """
    Analyze test case content to determine if synthetic data generation is needed.
    Returns whether the test case has form fields (Enter/fill patterns) that require data.
    """
    from services.synthetic_enhanced import SyntheticDataGenerator
    generator = SyntheticDataGenerator()
    needs_synthetic, reason = generator.test_case_needs_synthetic_data(body.test_case_content or "")
    return {
        "needs_synthetic_data": needs_synthetic,
        "reason": reason,
        "hint": "Synthetic data will be generated" if needs_synthetic else "No form fields - synthetic step will be skipped (faster)"
    }


@router.get("/templates")
async def get_workflow_templates():
    """
    Get predefined workflow templates for common scenarios
    
    Returns templates for:
    - Full TDM workflow (all operations)
    - Quick synthetic generation (test cases only)
    - DB migration (subset + provision)
    - Secure masking (discover + pii + mask + provision)
    - Test data generation (synthetic + provision)
    """
    return {
        "templates": [
            {
                "name": "full_workflow",
                "description": "Complete TDM workflow with all operations",
                "operations": ["discover", "pii", "subset", "mask", "synthetic", "provision"],
                "requires": ["connection_string"],
                "optional": ["test_case_urls", "domain"],
                "example": {
                    "connection_string": "postgresql://localhost:5432/prod",
                    "operations": ["discover", "pii", "subset", "mask", "synthetic", "provision"],
                    "config": {
                        "pii": {"use_llm": True},
                        "subset": {"root_table": "users", "max_rows_per_table": 10000},
                        "mask": {"rules": []},
                        "synthetic": {"row_counts": {"*": 1000}},
                        "provision": {"environment_id": "uat", "mode": "copy"}
                    }
                }
            },
            {
                "name": "quick_synthetic",
                "description": "Quick synthetic data generation from test cases",
                "operations": ["synthetic"],
                "requires": ["test_case_urls", "domain"],
                "example": {
                    "test_case_urls": ["https://app.example.com/login"],
                    "domain": "ecommerce",
                    "operations": ["synthetic"],
                    "config": {
                        "synthetic": {"row_counts": {"*": 500}}
                    }
                }
            },
            {
                "name": "db_migration",
                "description": "Subset and provision data for migration",
                "operations": ["discover", "subset", "provision"],
                "requires": ["connection_string"],
                "example": {
                    "connection_string": "postgresql://localhost:5432/prod",
                    "operations": ["discover", "subset", "provision"],
                    "config": {
                        "subset": {"root_table": "users", "max_rows_per_table": 5000},
                        "provision": {"target_connection": "postgresql://localhost:5432/uat", "mode": "copy"}
                    }
                }
            },
            {
                "name": "secure_masking",
                "description": "Discover PII, mask sensitive data, and provision",
                "operations": ["discover", "pii", "mask", "provision"],
                "requires": ["connection_string"],
                "example": {
                    "connection_string": "postgresql://localhost:5432/prod",
                    "operations": ["discover", "pii", "mask", "provision"],
                    "config": {
                        "pii": {"use_llm": True},
                        "mask": {"rules": []},
                        "provision": {"target_connection": "postgresql://localhost:5432/dev", "mode": "copy"}
                    }
                }
            },
            {
                "name": "test_data_generation",
                "description": "Generate synthetic test data and provision",
                "operations": ["synthetic", "provision"],
                "requires": [],
                "optional": ["test_case_urls", "domain", "schema_version_id"],
                "example": {
                    "domain": "ecommerce",
                    "operations": ["synthetic", "provision"],
                    "config": {
                        "synthetic": {"row_counts": {"*": 1000}},
                        "provision": {"environment_id": "qa", "mode": "replace"}
                    }
                }
            }
        ]
    }


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str, db: Session = Depends(get_db)):
    """
    Get status of a running or completed workflow
    """
    from models import Job, JobLog

    # Find workflow job by workflow_id stored in request_json
    job = db.query(Job).filter(
        Job.operation == "workflow",
        Job.request_json["workflow_id"].astext == workflow_id,
    ).first()

    if not job:
        return {"error": "Workflow not found"}

    logs = db.query(JobLog).filter(JobLog.job_id == job.id).order_by(JobLog.created_at).all()
    error = None
    if job.result_json and isinstance(job.result_json, dict):
        error = job.result_json.get("error")

    return {
        "workflow_id": workflow_id,
        "job_id": job.id,
        "status": job.status,
        "start_time": job.started_at.isoformat() if job.started_at else None,
        "end_time": job.finished_at.isoformat() if job.finished_at else None,
        "details": job.result_json or job.request_json or {},
        "error": error,
        "logs": [
            {
                "step": getattr(log, "step", None),
                "status": log.level,
                "message": log.message,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "details": getattr(log, "details", None) or {},
            }
            for log in logs
        ],
    }

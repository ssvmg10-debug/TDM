"""
Workflow Orchestrator Service
Unified workflow that takes test cases as input and runs all TDM operations:
1. Schema Discovery
2. PII Detection  
3. Subsetting
4. Masking
5. Synthetic Data Generation
6. Provisioning
7. Schema Fusion (optional)
8. Quality (optional)

Uses Dynamic Decision Engine for intent-aware pipeline planning.
Maintains Global TDM Context (JobContext) for lineage.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json
from sqlalchemy.orm import Session

from database import get_db
from models import Job, JobLog, Schema, SchemaVersion, DatasetVersion
from services.schema_discovery import run_discovery
from services.pii_detection import run_pii_classification
from services.subsetting import run_subset
from services.masking import run_mask
from services.synthetic_enhanced import SyntheticDataGenerator
from services.provisioning import run_provision
from services.crawler import TestCaseCrawler
from services.decision_engine import classify_intent, generate_pipeline_plan
from context.job_context import JobContext, create_initial_context

logger = logging.getLogger("tdm.workflow")


class WorkflowOrchestrator:
    """
    Orchestrates the complete TDM workflow from test cases to provisioned data
    """
    
    def __init__(self, db: Session, workflow_id: Optional[str] = None, job_id: Optional[str] = None):
        self.db = db
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.job_id = job_id or str(uuid.uuid4())
        
    def _log_step(self, step: str, status: str, message: str, details: Optional[Dict] = None):
        """Log workflow step to DB and stdout so logs are visible in UI and console."""
        log_entry = JobLog(
            job_id=self.job_id,
            level=status,
            message=message,
            step=step,
            details=details or {}
        )
        self.db.add(log_entry)
        self.db.commit()
        print(f"[{step.upper()}] {status}: {message}", flush=True)
        logger.info(f"[{step}] {status}: {message}")
        
    def execute_workflow(
        self,
        test_case_content: Optional[str] = None,
        test_case_urls: Optional[List[str]] = None,
        test_case_files: Optional[List[str]] = None,
        connection_string: Optional[str] = None,
        domain: Optional[str] = None,
        operations: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete TDM workflow
        
        Args:
            test_case_content: Raw test case content (Cucumber scenarios, Selenium scripts, etc.)
            test_case_urls: List of test case URLs to crawl
            test_case_files: List of test case files (Cucumber, Selenium, etc.)
            connection_string: Database connection string for schema discovery
            domain: Domain pack to use (ecommerce, banking, etc.)
            operations: List of operations to run. If None, runs all operations:
                       ['discover', 'pii', 'subset', 'mask', 'synthetic', 'provision']
            config: Configuration for each operation
                {
                    'discover': {...},
                    'pii': {...},
                    'subset': {...},
                    'mask': {...},
                    'synthetic': {...},
                    'provision': {...}
                }
        
        Returns:
            Workflow execution result with job IDs, dataset IDs, and status for each step
        """
        
        logger.info("=" * 80)
        logger.info(f"[WORKFLOW] Starting Workflow Execution: {self.workflow_id}")
        logger.info(f"   Job ID: {self.job_id}")
        logger.info(f"   Operations: {operations or 'ALL'}")
        logger.info(f"   Domain: {domain or 'N/A'}")
        logger.info(f"   Test Case Content: {'YES' if test_case_content else 'NO'}")
        logger.info(f"   Test Case URLs: {len(test_case_urls) if test_case_urls else 0}")
        logger.info(f"   Connection String: {'YES' if connection_string else 'NO'}")
        logger.info("=" * 80)
        
        config = config or {}

        # Dynamic Decision Engine: classify intent and get operations when not specified
        if operations is None:
            intent = classify_intent(
                test_case_content=test_case_content,
                test_case_urls=test_case_urls,
                connection_string=connection_string,
                domain=domain,
                schema_version_id=config.get("schema_version_id"),
                config_flags={"operations": config.get("operations", [])},
            )
            plan = generate_pipeline_plan(intent)
            operations = plan.get("operations", [])
            if not operations:
                operations = ['discover', 'pii', 'subset', 'mask', 'synthetic', 'provision']

        # Global TDM Context
        job_context = create_initial_context(
            test_case_content=test_case_content,
            test_case_urls=test_case_urls,
            connection_string=connection_string,
            domain=domain,
            job_id=self.job_id,
            workflow_id=self.workflow_id,
        )
        job_context.operations = operations
        job_context.domain_pack = domain
        job_context.scenario = config.get("synthetic", {}).get("scenario", "default")

        # Build test case reference for traceability
        import hashlib
        test_case_id = job_context.test_case_id
        test_case_summary = None
        if test_case_content:
            test_case_summary = (test_case_content[:100] + "…") if len(test_case_content) > 100 else test_case_content
        elif test_case_urls:
            test_case_summary = f"URLs: {', '.join((u[:50] + '…') if len(u) > 50 else u for u in test_case_urls[:3])}"

        # Create workflow job (id = job_id so UI can fetch logs by same id)
        job = Job(
            id=self.job_id,
            operation="workflow",
            status="running",
            request_json={
                "workflow_id": self.workflow_id,
                "operations": operations,
                "test_case_urls": test_case_urls,
                "test_case_id": test_case_id,
                "test_case_summary": test_case_summary,
                "domain": domain,
                "job_context": job_context.to_dict(),
            },
        )
        self.db.add(job)
        self.db.commit()
        print(f"[DATABASE] Created Job record: job_id={self.job_id}, type=workflow", flush=True)
        logger.info(f"[DATABASE] Created Job record: job_id={self.job_id}")
        
        result = {
            "workflow_id": self.workflow_id,
            "job_id": self.job_id,
            "operations": {},
            "overall_status": "running",
            "start_time": datetime.utcnow().isoformat()
        }
        
        try:
            # Step 1: Schema Discovery
            if 'discover' in operations:
                result["operations"]["discover"] = self._run_discovery(
                    connection_string, 
                    test_case_urls,
                    config.get('discover', {})
                )
            
            # Get schema_version_id from discovery or config
            schema_version_id = (
                result["operations"].get("discover", {}).get("schema_version_id") or
                config.get("schema_version_id")
            )
            
            # Step 2: PII Detection
            if 'pii' in operations and schema_version_id:
                result["operations"]["pii"] = self._run_pii_detection(
                    schema_version_id,
                    config.get('pii', {})
                )
            
            # Step 3: Subsetting
            if 'subset' in operations and schema_version_id:
                result["operations"]["subset"] = self._run_subsetting(
                    schema_version_id,
                    connection_string,
                    config.get('subset', {})
                )
            
            # Get dataset_version_id from subsetting or config
            dataset_version_id_for_mask = (
                result["operations"].get("subset", {}).get("dataset_version_id") or
                config.get("dataset_version_id")
            )
            
            # Step 4: Masking
            if 'mask' in operations and dataset_version_id_for_mask:
                result["operations"]["mask"] = self._run_masking(
                    dataset_version_id_for_mask,
                    config.get('mask', {})
                )
            
            # Step 5: Synthetic Data Generation
            if 'synthetic' in operations:
                result["operations"]["synthetic"] = self._run_synthetic(
                    schema_version_id,
                    test_case_content,
                    test_case_urls,
                    domain,
                    config.get('synthetic', {})
                )
            
            # Get dataset_version_id from synthetic, masking, subsetting, or config
            dataset_version_id = (
                result["operations"].get("synthetic", {}).get("dataset_version_id") or
                result["operations"].get("mask", {}).get("dataset_version_id") or
                result["operations"].get("subset", {}).get("dataset_version_id") or
                config.get("dataset_version_id")
            )
            
            # Step 6: Provisioning
            if 'provision' in operations and dataset_version_id:
                result["operations"]["provision"] = self._run_provisioning(
                    dataset_version_id,
                    config.get('provision', {})
                )
            
            # Update job context with results
            job_context.schema_version_id = schema_version_id
            job_context.dataset_version_id = dataset_version_id
            job_context.operations = list(result.get("operations", {}).keys())
            # Phase 5: Compute quality score for synthetic datasets
            if dataset_version_id:
                try:
                    from services.quality_engine import compute_dataset_quality
                    q = compute_dataset_quality(dataset_version_id)
                    job_context.quality_score = q.get("quality_score")
                    job_context.quality_report = q.get("quality_report")
                except Exception as qe:
                    logger.warning(f"Quality computation skipped: {qe}")
            result["job_context"] = job_context.to_dict()

            # Update job status
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            job.result_json = result
            self.db.commit()
            print(f"[DATABASE] Updated Job status: job_id={self.job_id}, status=completed", flush=True)
            
            result["overall_status"] = "completed"
            result["end_time"] = datetime.utcnow().isoformat()
            
            print("=" * 80, flush=True)
            print(f"[SUCCESS] Workflow Completed: {self.workflow_id}", flush=True)
            logger.info("=" * 80)
            logger.info(f"[SUCCESS] Workflow Completed: {self.workflow_id}")
            duration = (datetime.utcnow() - datetime.fromisoformat(result['start_time'])).total_seconds()
            print(f"   Duration: {duration:.2f}s", flush=True)
            print(f"   Operations Executed: {len(result['operations'])}", flush=True)
            print("=" * 80, flush=True)
            logger.info(f"   Duration: {duration:.2f}s")
            logger.info(f"   Operations Executed: {len(result['operations'])}")
            logger.info("=" * 80)
            
        except Exception as e:
            print(f"[ERROR] Workflow failed: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            logger.error(f"[ERROR] Workflow failed: {str(e)}", exc_info=True)
            print("=" * 80, flush=True)
            print(f"[FAILED] Workflow Failed: {self.workflow_id}", flush=True)
            print(f"   Error: {str(e)}", flush=True)
            print("=" * 80, flush=True)
            logger.info("=" * 80)
            logger.error(f"[FAILED] Workflow Failed: {self.workflow_id}")
            logger.error(f"   Error: {str(e)}")
            logger.info("=" * 80)
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            job.result_json = {"error": str(e), "overall_status": "failed"}
            self.db.commit()
            
            result["overall_status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = datetime.utcnow().isoformat()
        
        return result
    
    def _run_discovery(
        self, 
        connection_string: Optional[str], 
        test_case_urls: Optional[List[str]],
        config: Dict
    ) -> Dict[str, Any]:
        """Run schema discovery"""
        try:
            logger.info("[1/6] Starting Schema Discovery...")
            self._log_step("discover", "started", "Starting schema discovery")
            
            if not connection_string:
                raise ValueError("connection_string is required for schema discovery")
            
            schemas = config.get("schemas", ["public"])
            result = run_discovery(
                connection_string=connection_string,
                schemas=schemas,
                include_stats=config.get("include_stats", True),
                sample_size=config.get("sample_size", 10000),
            )
            schema_id = result.get("schema_id")
            schema_version_id = result.get("schema_version_id")
            
            logger.info(f"[SUCCESS] Schema Discovery Complete - Schema: {schema_id}")
            self._log_step(
                "discover", 
                "completed", 
                f"Schema discovered: {schema_id}",
                {"schema_id": schema_id, "schema_version_id": schema_version_id}
            )
            
            return {
                "status": "completed",
                "schema_id": schema_id,
                "schema_version_id": schema_version_id
            }
            
        except Exception as e:
            self._log_step("discover", "failed", f"Discovery failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def _run_pii_detection(self, schema_version_id: str, config: Dict) -> Dict[str, Any]:
        """Run PII detection and classification"""
        try:
            self._log_step("pii", "started", f"Starting PII classification for schema: {schema_version_id}")
            
            # Run PII classification (service uses its own DB session)
            run_pii_classification(
                schema_version_id=schema_version_id,
                use_llm=config.get('use_llm', False),
                sample_size_per_column=config.get('sample_size_per_column', 100),
            )
            
            self._log_step(
                "pii", 
                "completed", 
                f"PII classification completed for schema: {schema_version_id}"
            )
            
            return {
                "status": "completed",
                "schema_version_id": schema_version_id
            }
            
        except Exception as e:
            self._log_step("pii", "failed", f"PII classification failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def _infer_root_table(self, schema_version_id: str, config: Dict) -> str:
        """Infer root table from schema - use first table or prefer common entity names."""
        sv = self.db.query(SchemaVersion).filter(SchemaVersion.id == str(schema_version_id)).first()
        if not sv or not sv.tables_rel:
            return config.get('root_table', 'users')
        table_names = [t.name for t in sv.tables_rel]
        preferred = config.get('root_table')
        if preferred and preferred in table_names:
            return preferred
        # Prefer common root entity tables (user-like, customer, product)
        for name in ('users', 'user', 'customers', 'customer', 'accounts', 'account', 'products', 'product'):
            if name in table_names:
                return name
        return table_names[0]

    def _run_subsetting(
        self, 
        schema_version_id: str, 
        connection_string: str,
        config: Dict
    ) -> Dict[str, Any]:
        """Run data subsetting"""
        try:
            root_table = self._infer_root_table(schema_version_id, config)
            self._log_step("subset", "started", f"Starting subsetting for schema: {schema_version_id} (root_table={root_table})")
            
            # Run subsetting (service uses its own DB session)
            max_rows_cfg = config.get('max_rows_per_table', 10000)
            max_rows = max_rows_cfg if isinstance(max_rows_cfg, dict) else {"*": max_rows_cfg}
            result = run_subset(
                schema_version_id=schema_version_id,
                connection_string=connection_string,
                root_table=root_table,
                filters=config.get('filters', {}),
                max_rows_per_table=max_rows,
                job_id=self.job_id,
            )
            dataset_version_id = result.get("dataset_version_id")
            
            self._log_step(
                "subset", 
                "completed", 
                f"Subsetting completed. Dataset: {dataset_version_id}",
                {"dataset_version_id": dataset_version_id}
            )
            
            return {
                "status": "completed",
                "dataset_version_id": dataset_version_id
            }
            
        except Exception as e:
            self._log_step("subset", "failed", f"Subsetting failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def _run_masking(self, dataset_version_id: str, config: Dict) -> Dict[str, Any]:
        """Run data masking"""
        try:
            self._log_step("mask", "started", f"Starting masking for dataset: {dataset_version_id}")
            
            # Get rules from config (dict of column: mask_type)
            rules = config.get('rules', {})
            
            # Run masking
            result = run_mask(
                dataset_version_id=dataset_version_id,
                rules=rules,
                job_id=self.job_id
            )
            
            masked_dataset_id = result.get('masked_dataset_version_id')
            
            self._log_step(
                "mask", 
                "completed", 
                f"Masking completed. Dataset: {masked_dataset_id}",
                {"dataset_version_id": masked_dataset_id}
            )
            
            return {
                "status": "completed",
                "dataset_version_id": masked_dataset_id
            }
            
        except Exception as e:
            self._log_step("mask", "failed", f"Masking failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def _run_synthetic(
        self,
        schema_version_id: Optional[str],
        test_case_content: Optional[str],
        test_case_urls: Optional[List[str]],
        domain: Optional[str],
        config: Dict
    ) -> Dict[str, Any]:
        """Run synthetic data generation"""
        try:
            logger.info("[5/6] Starting Synthetic Data Generation...")
            self._log_step("synthetic", "started", "Starting synthetic data generation")
            
            generator = SyntheticDataGenerator()
            
            # Determine generation mode
            if test_case_content:
                # Mode 4: Test case content-based generation (preferred)
                # Only generate if test case has form fields (Enter/fill patterns)
                logger.info("[INFO] Using test case content for generation")
                dataset_version_id = generator.generate_from_test_case_content(
                    test_case_content=test_case_content,
                    row_counts=config.get('row_counts', {'*': 1000}),
                    job_id=self.job_id
                )
                if dataset_version_id is None:
                    self._log_step("synthetic", "completed", "Skipped - no form fields in test case (navigation/click-only)")
                    return {"status": "skipped", "dataset_version_id": None, "mode": "skipped", "reason": "No form fields"}
                mode = "test_case_content"
                
            elif test_case_urls:
                # Mode 3: Test case URL-based generation
                dataset_version_id = generator.generate_from_test_cases(
                    test_case_urls=test_case_urls,
                    row_counts=config.get('row_counts', {'*': 1000}),
                    job_id=self.job_id
                )
                mode = "test_cases"
                
            elif domain:
                # Mode 2: Domain-based generation
                dataset_version_id = generator.generate_from_domain_scenario(
                    domain=domain,
                    scenario=config.get('scenario', 'default'),
                    row_counts=config.get('row_counts', {'*': 1000}),
                    job_id=self.job_id
                )
                mode = "domain"
                
            elif schema_version_id:
                # Mode 1: Schema-based generation
                dataset_version_id = generator.generate_from_schema_version(
                    schema_version_id=schema_version_id,
                    row_counts=config.get('row_counts', {'*': 1000}),
                    job_id=self.job_id
                )
                mode = "schema"
                
            else:
                raise ValueError("Must provide either schema_version_id, domain, test_case_content, or test_case_urls")
            
            logger.info(f"[SUCCESS] Synthetic Data Generated - Mode: {mode}, Dataset: {dataset_version_id}")
            self._log_step(
                "synthetic", 
                "completed", 
                f"Synthetic data generated using {mode} mode. Dataset: {dataset_version_id}",
                {"dataset_version_id": dataset_version_id, "mode": mode}
            )
            
            return {
                "status": "completed",
                "dataset_version_id": dataset_version_id,
                "mode": mode
            }
            
        except Exception as e:
            self._log_step("synthetic", "failed", f"Synthetic generation failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def _run_provisioning(self, dataset_version_id: str, config: Dict) -> Dict[str, Any]:
        """Run data provisioning to target environment"""
        try:
            self._log_step("provision", "started", f"Starting provisioning for dataset: {dataset_version_id}")
            
            # Run provisioning
            result = run_provision(
                dataset_version_id=dataset_version_id,
                target_env=config.get('target_env', 'default'),
                reset_env=config.get('reset_env', True),
                run_smoke_tests=config.get('run_smoke_tests', True),
                job_id=self.job_id
            )
            
            provision_job_id = result.get('job_id')
            tables_loaded = result.get('tables_loaded', [])
            row_counts = result.get('row_counts', {})
            
            self._log_step(
                "provision", 
                "completed", 
                f"Provisioning completed. Job: {provision_job_id}",
                {"provision_job_id": provision_job_id, "tables_loaded": tables_loaded}
            )
            
            return {
                "status": "completed",
                "provision_job_id": provision_job_id,
                "tables_loaded": tables_loaded,
                "row_counts": row_counts
            }
            
        except Exception as e:
            self._log_step("provision", "failed", f"Provisioning failed: {str(e)}")
            return {"status": "failed", "error": str(e)}


def execute_workflow(
    test_case_content: Optional[str] = None,
    test_case_urls: Optional[List[str]] = None,
    test_case_files: Optional[List[str]] = None,
    connection_string: Optional[str] = None,
    domain: Optional[str] = None,
    operations: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    workflow_id: Optional[str] = None,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to execute workflow
    """
    if db is None:
        db = next(get_db())
    
    orchestrator = WorkflowOrchestrator(db, workflow_id=workflow_id, job_id=job_id)
    return orchestrator.execute_workflow(
        test_case_content=test_case_content,
        test_case_urls=test_case_urls,
        test_case_files=test_case_files,
        connection_string=connection_string,
        domain=domain,
        operations=operations,
        config=config
    )

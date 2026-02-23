"""
Workflow Orchestrator Service
Unified workflow that takes test cases as input and runs all TDM operations:
1. Schema Discovery
2. PII Detection  
3. Subsetting
4. Masking
5. Synthetic Data Generation
6. Provisioning
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
        """Log workflow step"""
        log_entry = JobLog(
            job_id=self.job_id,
            step=step,
            status=status,
            message=message,
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
        
        # Default to all operations
        if operations is None:
            operations = ['discover', 'pii', 'subset', 'mask', 'synthetic', 'provision']
            
        config = config or {}
        
        # Create workflow job
        job = Job(
            job_id=self.job_id,
            job_type="workflow",
            status="running",
            details={
                "workflow_id": self.workflow_id,
                "operations": operations,
                "test_case_urls": test_case_urls,
                "domain": domain
            }
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
            
            # Update job status
            job.status = "completed"
            job.end_time = datetime.utcnow()
            job.details["result"] = result
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
            job.end_time = datetime.utcnow()
            job.error = str(e)
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
            
            # Run discovery
            schema_id, schema_version_id = run_discovery(
                connection_string=connection_string,
                db=self.db,
                job_id=self.job_id
            )
            
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
            
            # Run PII classification
            run_pii_classification(
                schema_version_id=schema_version_id,
                db=self.db,
                job_id=self.job_id,
                use_llm=config.get('use_llm', False)
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
    
    def _run_subsetting(
        self, 
        schema_version_id: str, 
        connection_string: str,
        config: Dict
    ) -> Dict[str, Any]:
        """Run data subsetting"""
        try:
            self._log_step("subset", "started", f"Starting subsetting for schema: {schema_version_id}")
            
            # Run subsetting
            dataset_version_id = run_subset(
                schema_version_id=schema_version_id,
                connection_string=connection_string,
                root_table=config.get('root_table', 'users'),
                filters=config.get('filters', {}),
                max_rows_per_table=config.get('max_rows_per_table', 10000),
                db=self.db,
                job_id=self.job_id
            )
            
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
                # Parse test case content to extract field information
                logger.info("[INFO] Using test case content for generation")
                dataset_version_id = generator.generate_from_test_case_content(
                    test_case_content=test_case_content,
                    row_counts=config.get('row_counts', {'*': 100}),
                    job_id=self.job_id
                )
                mode = "test_case_content"
                
            elif test_case_urls:
                # Mode 3: Test case URL-based generation
                dataset_version_id = generator.generate_from_test_cases(
                    test_case_urls=test_case_urls,
                    row_counts=config.get('row_counts', {'*': 100}),
                    job_id=self.job_id
                )
                mode = "test_cases"
                
            elif domain:
                # Mode 2: Domain-based generation
                dataset_version_id = generator.generate_from_domain_scenario(
                    domain=domain,
                    scenario=config.get('scenario', 'default'),
                    row_counts=config.get('row_counts', {'*': 100}),
                    job_id=self.job_id
                )
                mode = "domain"
                
            elif schema_version_id:
                # Mode 1: Schema-based generation
                dataset_version_id = generator.generate_from_schema_version(
                    schema_version_id=schema_version_id,
                    row_counts=config.get('row_counts', {'*': 100}),
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
            
            self._log_step(
                "provision", 
                "completed", 
                f"Provisioning completed. Job: {provision_job_id}",
                {"provision_job_id": provision_job_id}
            )
            
            return {
                "status": "completed",
                "provision_job_id": provision_job_id
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

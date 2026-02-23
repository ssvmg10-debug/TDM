"""Enhanced synthetic data generation with crawler support and dynamic scenarios."""
import logging
import re
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Any, Optional
import random

from database import SessionLocal
from models import SchemaVersion, TableMeta, DatasetVersion, DatasetMetadata, Job, JobLog, Lineage
from config import settings
from dataset_store import ensure_dataset_dir
from services.crawler import TestCaseCrawler

logger = logging.getLogger(__name__)

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None


class SyntheticDataGenerator:
    """Enhanced synthetic data generator with crawler and dynamic scenarios."""
    
    def __init__(self):
        self.fake = fake
        
    def generate_from_schema_version(
        self,
        schema_version_id: str,
        row_counts: Optional[Dict[str, int]] = None,
        job_id: Optional[str] = None
    ) -> Dict:
        """Generate synthetic data from existing schema version (original method)."""
        db = SessionLocal()
        try:
            if not job_id:
                job = Job(operation="synthetic", status="running", request_json={"schema_version_id": schema_version_id})
                db.add(job)
                db.commit()
                db.refresh(job)
                job_id = job.id
            else:
                job = db.query(Job).get(job_id)

            def log(msg: str, level: str = "info"):
                db.add(JobLog(job_id=job_id, level=level, message=msg))
                db.commit()

            log("Starting synthetic generation from schema version")
            sv = db.query(SchemaVersion).filter(SchemaVersion.id == schema_version_id).first()
            if not sv:
                log("Schema version not found", "error")
                job.status = "failed"
                db.commit()
                return {"job_id": job_id, "dataset_version_id": None}

            row_counts = row_counts or {}
            default_rows = row_counts.get("*", 1000)
            version_id = str(uuid4())
            ensure_dataset_dir(version_id)
            out_path = Path(settings.dataset_store_path) / version_id
            generated = {}
            
            for table in sv.tables_rel:
                n = row_counts.get(table.name, default_rows)
                cols = [(c.name, c.data_type, c.inferred_type) for c in table.columns]
                if not cols:
                    continue
                    
                data = {}
                for cname, dtype, inferred in cols:
                    try:
                        data[cname] = [self._generate_value(cname, str(dtype or ""), str(inferred or "")) for _ in range(n)]
                    except Exception as e:
                        logger.warning("Column %s: %s", cname, e)
                        data[cname] = ["value"] * n
                        
                df = pd.DataFrame(data)
                df.to_parquet(out_path / f"{table.name}.parquet", index=False)
                generated[table.name] = n
                log(f"Generated {table.name}: {n} rows")

            # Save metadata
            self._save_dataset_metadata(db, version_id, schema_version_id, generated, job_id, job, "schema_version")
            log("Synthetic generation completed")
            db.commit()
            return {"job_id": job_id, "dataset_version_id": version_id}
            
        except Exception as e:
            logger.exception("Synthetic failed")
            if job_id:
                try:
                    db.rollback()
                    job = db.query(Job).get(job_id)
                    if job:
                        job.status = "failed"
                        job.result_json = {"error": str(e)}
                        db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                        db.commit()
                except Exception:
                    pass
            raise
        finally:
            db.close()
            
    def generate_from_test_cases(
        self,
        test_case_urls: List[str],
        domain: str = "generic",
        scenario: str = "default",
        row_counts: Optional[Dict[str, int]] = None,
        job_id: Optional[str] = None
    ) -> Dict:
        """Generate synthetic data by crawling test case URLs."""
        db = SessionLocal()
        try:
            if not job_id:
                job = Job(
                    operation="synthetic",
                    status="running",
                    request_json={
                        "test_case_urls": test_case_urls,
                        "domain": domain,
                        "scenario": scenario
                    }
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                job_id = job.id
            else:
                job = db.query(Job).get(job_id)

            def log(msg: str, level: str = "info"):
                db.add(JobLog(job_id=job_id, level=level, message=msg))
                db.commit()

            log(f"Starting synthetic generation from test cases: {test_case_urls}")
            
            # Crawl test cases
            with TestCaseCrawler() as crawler:
                scenario_hints = {"domain": domain, "scenario": scenario}
                schema = crawler.crawl_test_cases(test_case_urls, scenario_hints)
                
            log(f"Crawled schema with {len(schema.get('entities', {}))} entities")
            
            if not schema.get("entities"):
                log("No entities found in crawled schema", "warning")
                # Fall back to domain-based schema
                log(f"Using fallback schema for domain: {domain}")
                
            # Generate data based on crawled schema
            row_counts = row_counts or {}
            default_rows = row_counts.get("*", 1000)
            version_id = str(uuid4())
            ensure_dataset_dir(version_id)
            out_path = Path(settings.dataset_store_path) / version_id
            generated = {}
            
            for entity_name, entity_info in schema.get("entities", {}).items():
                n = row_counts.get(entity_name, default_rows)
                fields = entity_info.get("fields", {})
                
                if not fields:
                    continue
                    
                data = {}
                for field_name, field_info in fields.items():
                    field_type = field_info.get("type", "string")
                    try:
                        data[field_name] = [self._generate_value_by_type(field_name, field_type) for _ in range(n)]
                    except Exception as e:
                        logger.warning(f"Field {field_name}: {e}")
                        data[field_name] = ["value"] * n
                        
                df = pd.DataFrame(data)
                df.to_parquet(out_path / f"{entity_name}.parquet", index=False)
                generated[entity_name] = n
                log(f"Generated {entity_name}: {n} rows")
                
            # Save metadata with crawler info
            metadata_extra = {
                "source": "test_cases",
                "test_case_urls": test_case_urls,
                "domain": domain,
                "scenario": scenario,
                "crawled_entities": list(schema.get("entities", {}).keys())
            }
            
            self._save_dataset_metadata(
                db, version_id, None, generated, job_id, job,
                source_type="synthetic_crawled",
                extra_metadata=metadata_extra
            )
            
            log("Synthetic generation from test cases completed")
            db.commit()
            return {"job_id": job_id, "dataset_version_id": version_id, "entities": list(schema.get("entities", {}).keys())}
            
        except Exception as e:
            logger.exception("Synthetic from test cases failed")
            if job_id:
                try:
                    db.rollback()
                    job = db.query(Job).get(job_id)
                    if job:
                        job.status = "failed"
                        job.result_json = {"error": str(e)}
                        db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                        db.commit()
                except Exception:
                    pass
            raise
        finally:
            db.close()
    
    def generate_from_test_case_content(
        self,
        test_case_content: str,
        row_counts: Optional[Dict[str, int]] = None,
        job_id: Optional[str] = None
    ) -> str:
        """Generate synthetic data from raw test case content (Cucumber, Selenium, manual steps)."""
        logger.info("📄 Generating from test case content...")
        db = SessionLocal()
        try:
            if not job_id:
                job = Job(
                    operation="synthetic",
                    status="running",
                    request_json={"source": "test_case_content"}
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                job_id = job.id
            else:
                job = db.query(Job).get(job_id)

            def log(msg: str, level: str = "info"):
                db.add(JobLog(job_id=job_id, level=level, message=msg))
                db.commit()
                logger.info(f"   {msg}")

            log("Starting synthetic generation from test case content")
            logger.info(f"   Content length: {len(test_case_content)} characters")
            
            # Parse test case content to extract fields
            schema = self._parse_test_case_content(test_case_content)
            
            entities_count = len(schema.get('entities', {}))
            logger.info(f"   ✅ Parsed {entities_count} entities from test case")
            for entity_name, entity_info in schema.get('entities', {}).items():
                fields_count = len(entity_info.get('fields', {}))
                logger.info(f"      • {entity_name}: {fields_count} fields")
            
            log(f"Parsed schema with {entities_count} entities from test case content")
            
            # Generate data based on parsed schema
            row_counts = row_counts or {}
            default_rows = row_counts.get("*", 100)
            version_id = str(uuid4())
            ensure_dataset_dir(version_id)
            out_path = Path(settings.dataset_store_path) / version_id
            generated = {}
            
            for entity_name, entity_info in schema.get("entities", {}).items():
                n = row_counts.get(entity_name, default_rows)
                fields = entity_info.get("fields", {})
                
                if not fields:
                    continue
                    
                data = {}
                for field_name, field_info in fields.items():
                    field_type = field_info.get("type", "string")
                    try:
                        data[field_name] = [self._generate_value_by_type(field_name, field_type) for _ in range(n)]
                    except Exception as e:
                        logger.warning(f"Field {field_name}: {e}")
                        data[field_name] = ["value"] * n
                        
                df = pd.DataFrame(data)
                df.to_parquet(out_path / f"{entity_name}.parquet", index=False)
                generated[entity_name] = n
                log(f"Generated {entity_name}: {n} rows")
                
            # Save metadata
            metadata_extra = {
                "source": "test_case_content",
                "parsed_entities": list(schema.get("entities", {}).keys())
            }
            
            self._save_dataset_metadata(
                db, version_id, None, generated, job_id, job,
                source_type="synthetic_test_content",
                extra_metadata=metadata_extra
            )
            
            log("Synthetic generation from test case content completed")
            job.status = "completed"
            job.result_json = {"dataset_version_id": version_id, "entities": list(schema.get("entities", {}).keys())}
            db.commit()
            return version_id
            
        except Exception as e:
            logger.exception("Synthetic from test case content failed")
            if job_id:
                try:
                    db.rollback()
                    job = db.query(Job).get(job_id)
                    if job:
                        job.status = "failed"
                        job.result_json = {"error": str(e)}
                        db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                        db.commit()
                except Exception:
                    pass
            raise
        finally:
            db.close()
            
    def generate_from_domain_scenario(
        self,
        domain: str,
        scenario: str = "default",
        row_counts: Optional[Dict[str, int]] = None,
        job_id: Optional[str] = None
    ) -> Dict:
        """Generate synthetic data from predefined domain scenarios."""
        db = SessionLocal()
        try:
            if not job_id:
                job = Job(
                    operation="synthetic",
                    status="running",
                    request_json={"domain": domain, "scenario": scenario}
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                job_id = job.id
            else:
                job = db.query(Job).get(job_id)

            def log(msg: str, level: str = "info"):
                db.add(JobLog(job_id=job_id, level=level, message=msg))
                db.commit()

            log(f"Starting synthetic generation for domain: {domain}, scenario: {scenario}")
            
            # Get schema from domain/scenario
            schema = self._get_domain_schema(domain, scenario)
            
            log(f"Using {domain} schema with {len(schema.get('entities', {}))} entities")
            
            # Generate data
            row_counts = row_counts or {}
            default_rows = row_counts.get("*", 1000)
            version_id = str(uuid4())
            ensure_dataset_dir(version_id)
            out_path = Path(settings.dataset_store_path) / version_id
            generated = {}
            
            for entity_name, entity_info in schema.get("entities", {}).items():
                n = row_counts.get(entity_name, default_rows)
                fields = entity_info.get("fields", {})
                
                if not fields:
                    continue
                    
                data = {}
                for field_name, field_info in fields.items():
                    field_type = field_info.get("type", "string")
                    try:
                        data[field_name] = [self._generate_value_by_type(field_name, field_type) for _ in range(n)]
                    except Exception as e:
                        logger.warning(f"Field {field_name}: {e}")
                        data[field_name] = ["value"] * n
                        
                df = pd.DataFrame(data)
                df.to_parquet(out_path / f"{entity_name}.parquet", index=False)
                generated[entity_name] = n
                log(f"Generated {entity_name}: {n} rows")
                
            # Save metadata
            metadata_extra = {
                "source": "domain_scenario",
                "domain": domain,
                "scenario": scenario
            }
            
            self._save_dataset_metadata(
                db, version_id, None, generated, job_id, job,
                source_type="synthetic",
                extra_metadata=metadata_extra
            )
            
            log("Synthetic generation from domain scenario completed")
            db.commit()
            return {"job_id": job_id, "dataset_version_id": version_id}
            
        except Exception as e:
            logger.exception("Synthetic from domain scenario failed")
            if job_id:
                try:
                    db.rollback()
                    job = db.query(Job).get(job_id)
                    if job:
                        job.status = "failed"
                        job.result_json = {"error": str(e)}
                        db.add(JobLog(job_id=job_id, level="error", message=str(e)))
                        db.commit()
                except Exception:
                    pass
            raise
        finally:
            db.close()
    
    def _parse_test_case_content(self, content: str) -> Dict[str, Any]:
        """Parse test case content to extract entity and field information."""
        import re
        
        entities = {}
        
        # Parse Cucumber-style "Given/When/Then" steps
        cucumber_pattern = r'(?:Given|When|And|Then)\s+I\s+enter\s+"([^"]+)"\s+in\s+the\s+"?([^"\n]+)"?\s+field'
        matches = re.findall(cucumber_pattern, content, re.IGNORECASE)
        
        # Parse Selenium-style findElement calls
        selenium_pattern = r'findElement\(By\.(?:id|name|xpath|css)\("([^"]+)"\)\)'
        selenium_matches = re.findall(selenium_pattern, content, re.IGNORECASE)
        
        # Parse manual test step patterns like "Enter X in Y field"
        manual_pattern = r'(?:enter|input|type|fill)\s+["\']?([^"\']+)["\']?\s+(?:in|into|to|for)\s+(?:the\s+)?["\']?([^"\']+)["\']?\s+field'
        manual_matches = re.findall(manual_pattern, content, re.IGNORECASE)
        
        # Combine all matches
        all_fields = []
        
        # Cucumber matches (value, field_name)
        for value, field_name in matches:
            all_fields.append((field_name.strip(), value))
            
        # Selenium matches (field_name)
        for field_name in selenium_matches:
            # Clean up common prefixes/suffixes
            field_name = field_name.replace("_field", "").replace("Field", "").replace("-", "_")
            all_fields.append((field_name, None))
            
        # Manual test matches (value, field_name)
        for value, field_name in manual_matches:
            all_fields.append((field_name.strip(), value))
        
        # Create a default entity if fields found
        if all_fields:
            entity_name = "user"  # Default entity name
            entities[entity_name] = {"fields": {}}
            
            for field_name, sample_value in all_fields:
                # Normalize field name
                field_name_normalized = field_name.lower().replace(" ", "_").replace("-", "_")
                
                # Infer type from field name or sample value
                field_type = self._infer_field_type(field_name_normalized, sample_value)
                
                entities[entity_name]["fields"][field_name_normalized] = {
                    "type": field_type,
                    "sample_value": sample_value
                }
        
        # If no fields found, create a minimal default schema
        if not entities:
            logger.warning("No fields found in test case content, using default schema")
            entities = {
                "user": {
                    "fields": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "email"},
                        "created_at": {"type": "datetime"}
                    }
                }
            }
        
        return {"entities": entities}
    
    def _infer_field_type(self, field_name: str, sample_value: Optional[str] = None) -> str:
        """Infer field type from field name and optional sample value."""
        field_name_lower = field_name.lower()
        
        # Check field name patterns
        if "email" in field_name_lower:
            return "email"
        elif "phone" in field_name_lower or "mobile" in field_name_lower:
            return "phone"
        elif "password" in field_name_lower:
            return "password"
        elif "address" in field_name_lower:
            return "address"
        elif "name" in field_name_lower and "user" in field_name_lower:
            return "name"
        elif "first_name" in field_name_lower or "firstname" in field_name_lower:
            return "first_name"
        elif "last_name" in field_name_lower or "lastname" in field_name_lower:
            return "last_name"
        elif "date" in field_name_lower or "dob" in field_name_lower or "birth" in field_name_lower:
            return "date"
        elif "time" in field_name_lower or "timestamp" in field_name_lower:
            return "datetime"
        elif "age" in field_name_lower or "quantity" in field_name_lower or "count" in field_name_lower:
            return "integer"
        elif "price" in field_name_lower or "amount" in field_name_lower or "salary" in field_name_lower:
            return "decimal"
        elif "url" in field_name_lower or "link" in field_name_lower:
            return "url"
        elif "zip" in field_name_lower or "postal" in field_name_lower:
            return "zipcode"
        elif "city" in field_name_lower:
            return "city"
        elif "state" in field_name_lower:
            return "state"
        elif "country" in field_name_lower:
            return "country"
        elif "card" in field_name_lower and "number" in field_name_lower:
            return "credit_card"
        elif "ssn" in field_name_lower or "social_security" in field_name_lower:
            return "ssn"
        
        # Check sample value if provided
        if sample_value:
            if "@" in sample_value:
                return "email"
            elif re.match(r'^\d{3}-\d{3}-\d{4}$', sample_value):
                return "phone"
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', sample_value):
                return "date"
        
        # Default to string
        return "string"
            
    def _generate_value(self, col_name: str, data_type: str, inferred: str):
        """Original value generator (for backward compatibility)."""
        if inferred:
            inferred = inferred.lower()
            if "email" in inferred or col_name.lower() == "email":
                return self.fake.email() if self.fake else "user@example.com"
            if "phone" in inferred or "phone" in col_name.lower():
                return self.fake.phone_number() if self.fake else "+1555000000"
            if "name" in inferred or "name" in col_name.lower():
                return self.fake.name() if self.fake else "Unknown"
            if "address" in inferred or "address" in col_name.lower():
                return self.fake.address() if self.fake else "123 Main St"
            if "date" in inferred or "date" in col_name.lower():
                return self.fake.date_isoformat() if self.fake else "2024-01-01"
                
        if data_type:
            dt = str(data_type).upper()
            if "UUID" in dt:
                return str(uuid4())
            if "INT" in dt or "SERIAL" in dt or "BIGINT" in dt:
                return self.fake.random_int(1, 1000000) if self.fake else 1
            if "BOOL" in dt:
                return self.fake.boolean() if self.fake else False
            if "DATE" in dt or "TIME" in dt:
                return self.fake.iso8601() if self.fake else "2024-01-01T00:00:00"
            if "CHAR" in dt or "TEXT" in dt or "VARCHAR" in dt:
                return self.fake.word() if self.fake else "value"
                
        return self.fake.word() if self.fake else "value"
        
    def _generate_value_by_type(self, field_name: str, field_type: str):
        """Generate value based on semantic type."""
        if not self.fake:
            return "value"
            
        field_type = field_type.lower()
        field_name_lower = field_name.lower()
        
        if field_type == "email" or "email" in field_name_lower:
            return self.fake.email()
        elif field_type == "phone" or "phone" in field_name_lower:
            return self.fake.phone_number()
        elif field_type == "person_name" or "name" in field_name_lower:
            return self.fake.name()
        elif field_type == "address" or "address" in field_name_lower:
            return self.fake.address().replace('\n', ', ')
        elif field_type == "date" or "date" in field_name_lower:
            return self.fake.date_between(start_date='-2y', end_date='today').isoformat()
        elif field_type == "datetime":
            return self.fake.date_time_between(start_date='-2y', end_date='now').isoformat()
        elif field_type == "integer" or field_type == "number":
            if "price" in field_name_lower or "amount" in field_name_lower:
                return round(random.uniform(10, 1000), 2)
            elif "id" in field_name_lower:
                return random.randint(1, 100000)
            else:
                return random.randint(1, 1000)
        elif field_type == "boolean":
            return random.choice([True, False])
        elif field_type == "password":
            return self.fake.password()
        else:
            return self.fake.word()
            
    def _get_domain_schema(self, domain: str, scenario: str) -> Dict:
        """Get predefined schema for a domain and scenario."""
        # Use crawler's fallback schema which has domain templates
        crawler = TestCaseCrawler()
        return crawler._fallback_schema({"domain": domain, "scenario": scenario})
        
    def _save_dataset_metadata(
        self,
        db,
        version_id: str,
        schema_version_id: Optional[str],
        generated: Dict[str, int],
        job_id: str,
        job,
        source_type: str = "synthetic",
        extra_metadata: Optional[Dict] = None
    ):
        """Save dataset metadata to database."""
        path_prefix = str(Path(settings.dataset_store_path) / version_id)
        
        dv = DatasetVersion(
            id=version_id,
            name=f"{source_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            schema_version_id=schema_version_id,
            source_type=source_type,
            status="active",
            path_prefix=path_prefix,
        )
        db.add(dv)
        db.flush()  # Ensure dataset_versions row exists before dataset_metadata (FK)
        
        # Add row counts metadata
        db.add(DatasetMetadata(
            dataset_version_id=version_id,
            meta_key="row_counts",
            meta_value=generated
        ))
        
        # Add extra metadata if provided
        if extra_metadata:
            for key, value in extra_metadata.items():
                db.add(DatasetMetadata(
                    dataset_version_id=version_id,
                    meta_key=key,
                    meta_value=value if isinstance(value, (dict, list)) else {"value": value}
                ))
                
        # Add lineage
        source_id = schema_version_id or "none"
        source_type_lineage = "schema_version" if schema_version_id else "test_cases"
        db.add(Lineage(
            source_type=source_type_lineage,
            source_id=source_id,
            target_type="dataset_version",
            target_id=version_id,
            operation=source_type,
            job_id=job_id
        ))
        
        # Update job
        job.status = "completed"
        job.result_json = {"dataset_version_id": version_id, "row_counts": generated}
        job.finished_at = datetime.utcnow()
        

# Backward compatibility function
def run_synthetic(
    schema_version_id: str,
    row_counts: Dict[str, int] | None = None,
    job_id: str | None = None,
) -> dict:
    """Original run_synthetic function for backward compatibility."""
    generator = SyntheticDataGenerator()
    return generator.generate_from_schema_version(schema_version_id, row_counts, job_id)

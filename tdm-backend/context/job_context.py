"""
Global TDM Job Context
Every job maintains this context for decision-making and lineage.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class JobContext:
    """
    Global context maintained across all workflow steps.
    Powers decision-making, lineage, and traceability.
    """
    # Identifiers
    test_case_id: Optional[str] = None
    job_id: Optional[str] = None
    workflow_id: Optional[str] = None

    # Schema sources (populated by discovery/crawl/fusion)
    ui_schemas: Dict[str, Any] = field(default_factory=dict)
    api_schemas: Dict[str, Any] = field(default_factory=dict)
    db_schemas: Dict[str, Any] = field(default_factory=dict)
    unified_schema: Optional[Dict[str, Any]] = None

    # Domain & scenario
    domain_pack: Optional[str] = None
    scenario: Optional[str] = None

    # Operations executed
    operations: List[str] = field(default_factory=list)

    # Fallbacks triggered (for lineage)
    fallbacks_used: List[Dict[str, Any]] = field(default_factory=list)

    # Quality metrics (from quality_graph)
    quality_score: Optional[float] = None
    quality_report: Optional[Dict[str, Any]] = None

    # IDs from each step (for chaining)
    schema_version_id: Optional[str] = None
    dataset_version_id: Optional[str] = None
    unified_schema_version_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage in Job.request_json or result_json."""
        return {
            "test_case_id": self.test_case_id,
            "job_id": self.job_id,
            "workflow_id": self.workflow_id,
            "ui_schemas": self.ui_schemas,
            "api_schemas": self.api_schemas,
            "db_schemas": self.db_schemas,
            "unified_schema": self.unified_schema,
            "domain_pack": self.domain_pack,
            "scenario": self.scenario,
            "operations": self.operations,
            "fallbacks_used": self.fallbacks_used,
            "quality_score": self.quality_score,
            "quality_report": self.quality_report,
            "schema_version_id": self.schema_version_id,
            "dataset_version_id": self.dataset_version_id,
            "unified_schema_version_id": self.unified_schema_version_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobContext":
        """Deserialize from stored dict."""
        return cls(
            test_case_id=data.get("test_case_id"),
            job_id=data.get("job_id"),
            workflow_id=data.get("workflow_id"),
            ui_schemas=data.get("ui_schemas", {}),
            api_schemas=data.get("api_schemas", {}),
            db_schemas=data.get("db_schemas", {}),
            unified_schema=data.get("unified_schema"),
            domain_pack=data.get("domain_pack"),
            scenario=data.get("scenario"),
            operations=data.get("operations", []),
            fallbacks_used=data.get("fallbacks_used", []),
            quality_score=data.get("quality_score"),
            quality_report=data.get("quality_report"),
            schema_version_id=data.get("schema_version_id"),
            dataset_version_id=data.get("dataset_version_id"),
            unified_schema_version_id=data.get("unified_schema_version_id"),
        )


def create_initial_context(
    test_case_content: Optional[str] = None,
    test_case_urls: Optional[List[str]] = None,
    connection_string: Optional[str] = None,
    domain: Optional[str] = None,
    job_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> JobContext:
    """Create initial JobContext from workflow input."""
    import hashlib
    test_case_id = None
    if test_case_content:
        test_case_id = hashlib.sha256(test_case_content.encode()).hexdigest()[:16]
    elif test_case_urls:
        test_case_id = hashlib.sha256(";".join(test_case_urls).encode()).hexdigest()[:16]

    return JobContext(
        test_case_id=test_case_id,
        job_id=job_id,
        workflow_id=workflow_id,
        domain_pack=domain,
        scenario="default",
    )

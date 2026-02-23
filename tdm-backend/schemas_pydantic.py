"""Pydantic request/response schemas for API."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---- Discover ----
class DiscoverSchemaRequest(BaseModel):
    connection_string: str
    schemas: list[str] = Field(default_factory=lambda: ["public"])
    include_stats: bool = True
    sample_size: Optional[int] = 10000


class DiscoverSchemaResponse(BaseModel):
    job_id: Optional[str] = None
    schema_version_id: Optional[str] = None
    message: str = "ok"


# ---- PII ----
class PIIClassifyRequest(BaseModel):
    schema_version_id: str
    use_llm: bool = True
    sample_size_per_column: int = 100


class PIIEntry(BaseModel):
    table: str
    column: str
    pii_type: str
    confidence: float
    technique: str


class PIIClassifyResponse(BaseModel):
    job_id: Optional[str] = None
    pii_map: list[PIIEntry] = []


# ---- Subset ----
class SubsetRequest(BaseModel):
    schema_version_id: str
    connection_string: Optional[str] = None
    connection_id: Optional[str] = None
    root_table: str
    filters: Optional[dict[str, dict]] = None
    max_rows_per_table: Optional[dict[str, int]] = None
    date_range: Optional[dict] = None
    sampling_pct: Optional[float] = None


class SubsetResponse(BaseModel):
    job_id: str
    dataset_version_id: Optional[str] = None
    message: str = "ok"


# ---- Mask ----
class MaskRequest(BaseModel):
    dataset_version_id: str
    rules: Optional[dict[str, str]] = None
    rule_set_id: Optional[str] = None


class MaskResponse(BaseModel):
    job_id: str
    masked_dataset_version_id: Optional[str] = None
    message: str = "ok"


# ---- Synthetic ----
class SyntheticRequest(BaseModel):
    # Mode 1: From existing schema version
    schema_version_id: Optional[str] = None
    
    # Mode 2: From test case URLs (crawl)
    test_case_urls: Optional[list[str]] = None
    
    # Mode 3: From domain/scenario
    domain: Optional[str] = None  # e.g., "ecommerce", "banking", "telecom", "healthcare"
    scenario: Optional[str] = "default"  # scenario name within domain
    
    # Common parameters
    row_counts: Optional[dict[str, int]] = None
    
    # Legacy support
    domain_pack: Optional[str] = None  # Deprecated, use 'domain' instead
    ui_urls: Optional[list[str]] = None  # Deprecated, use 'test_case_urls' instead
    api_spec_url: Optional[str] = None  # Future: API schema extraction


class SyntheticResponse(BaseModel):
    job_id: str
    dataset_version_id: Optional[str] = None
    message: str = "ok"
    entities: Optional[list[str]] = None  # List of generated entities (for crawled schemas)


# ---- Provision ----
class ProvisionRequest(BaseModel):
    dataset_version_id: str
    target_env: str
    reset_env: bool = True
    run_smoke_tests: bool = True


class ProvisionResponse(BaseModel):
    job_id: str
    status: str = "pending"
    message: str = "ok"


# ---- Common list/detail ----
class TableInfo(BaseModel):
    id: str
    name: str
    schema_name: str
    row_count: Optional[int] = None


class ColumnInfo(BaseModel):
    id: str
    name: str
    data_type: Optional[str] = None
    inferred_type: Optional[str] = None
    nullable: bool = True
    ordinal_position: Optional[int] = None


class RelationshipInfo(BaseModel):
    parent_table: str
    child_table: str
    parent_column: str
    child_column: str


class SchemaVersionDetail(BaseModel):
    id: str
    schema_id: str
    version_number: int
    discovered_at: Optional[datetime] = None
    status: str
    tables: list[TableInfo] = []
    columns_count: int = 0
    relationships_count: int = 0


class SchemaListItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    latest_version_id: Optional[str] = None
    tables_count: int = 0


class DatasetVersionItem(BaseModel):
    id: str
    name: Optional[str] = None
    source_type: str
    status: str
    path_prefix: str
    created_at: Optional[datetime] = None
    row_counts: Optional[dict[str, int]] = None
    tables_count: int = 0
    schema_version_id: Optional[str] = None


class JobItem(BaseModel):
    id: str
    operation: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_json: Optional[dict] = None
    request_json: Optional[dict] = None  # For workflow jobs: test_case_id, test_case_summary, etc.


class JobDetail(JobItem):
    request_json: Optional[dict] = None
    logs: list[dict] = []


class EnvironmentItem(BaseModel):
    id: str
    name: str
    config_json: Optional[dict] = None


class LineageItem(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    operation: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogItem(BaseModel):
    id: str
    action: str
    target: str
    user: str
    role: str
    time: str
    severity: str

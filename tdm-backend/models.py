"""SQLAlchemy models for TDM metadata store."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Connection(Base):
    __tablename__ = "connections"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    connection_string_encrypted = Column(Text)
    type = Column(String(50), default="postgres")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Schema(Base):
    __tablename__ = "schemas"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    source_connection_id = Column(UUID(as_uuid=False), ForeignKey("connections.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    versions = relationship("SchemaVersion", back_populates="schema")


class SchemaVersion(Base):
    __tablename__ = "schema_versions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    schema_id = Column(UUID(as_uuid=False), ForeignKey("schemas.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="active")
    schema = relationship("Schema", back_populates="versions")
    tables_rel = relationship("TableMeta", back_populates="schema_version")
    __table_args__ = (UniqueConstraint("schema_id", "version_number", name="uq_schema_version"),)


class TableMeta(Base):
    __tablename__ = "tables"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    schema_version_id = Column(UUID(as_uuid=False), ForeignKey("schema_versions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    schema_name = Column(String(255), default="public")
    row_count = Column(BigInteger)
    schema_version = relationship("SchemaVersion", back_populates="tables_rel")
    columns = relationship("ColumnMeta", back_populates="table")
    __table_args__ = (UniqueConstraint("schema_version_id", "schema_name", "name", name="uq_tables_sv_schema_name"),)


class ColumnMeta(Base):
    __tablename__ = "columns"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    table_id = Column(UUID(as_uuid=False), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    data_type = Column(String(100))
    inferred_type = Column(String(100))
    nullable = Column(Boolean, default=True)
    ordinal_position = Column(Integer)
    table = relationship("TableMeta", back_populates="columns")
    __table_args__ = (UniqueConstraint("table_id", "name", name="uq_columns_table_name"),)


class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    parent_table_id = Column(UUID(as_uuid=False), ForeignKey("tables.id"), nullable=False)
    child_table_id = Column(UUID(as_uuid=False), ForeignKey("tables.id"), nullable=False)
    parent_column_id = Column(UUID(as_uuid=False), ForeignKey("columns.id"), nullable=False)
    child_column_id = Column(UUID(as_uuid=False), ForeignKey("columns.id"), nullable=False)


class PIIClassification(Base):
    __tablename__ = "pii_classification"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    schema_version_id = Column(UUID(as_uuid=False), ForeignKey("schema_versions.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False)
    column_name = Column(String(255), nullable=False)
    pii_type = Column(String(100), nullable=False)
    technique = Column(String(50))
    confidence = Column(Numeric(3, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("schema_version_id", "table_name", "column_name", name="uq_pii_sv_table_column"),)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255))
    schema_version_id = Column(UUID(as_uuid=False), ForeignKey("schema_versions.id"))
    source_type = Column(String(50), nullable=False)  # subset | synthetic | masked
    status = Column(String(50), default="active")
    path_prefix = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    dataset_version_id = Column(UUID(as_uuid=False), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    meta_key = Column(String(255), nullable=False)
    meta_value = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("dataset_version_id", "meta_key", name="uq_dataset_metadata_dv_key"),)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    operation = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # pending | running | completed | failed
    request_json = Column(JSONB)
    result_json = Column(JSONB)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    user_id = Column(String(255))
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")


class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20))
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    job = relationship("Job", back_populates="logs")


class Lineage(Base):
    __tablename__ = "lineage"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=False)
    operation = Column(String(100))
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MaskingRule(Base):
    __tablename__ = "masking_rules"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255))
    schema_version_id = Column(UUID(as_uuid=False), ForeignKey("schema_versions.id"))
    rules_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Environment(Base):
    __tablename__ = "environments"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(50), unique=True, nullable=False)
    connection_string_encrypted = Column(Text)
    config_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

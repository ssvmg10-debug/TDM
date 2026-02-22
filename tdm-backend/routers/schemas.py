from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import Schema, SchemaVersion, TableMeta, ColumnMeta, Relationship
from schemas_pydantic import SchemaListItem, SchemaVersionDetail, TableInfo, ColumnInfo, RelationshipInfo

router = APIRouter()


@router.get("/schemas", response_model=list[SchemaListItem])
def list_schemas():
    db = SessionLocal()
    try:
        schemas = db.query(Schema).all()
        out = []
        for s in schemas:
            latest = db.query(SchemaVersion).filter(SchemaVersion.schema_id == s.id).order_by(SchemaVersion.version_number.desc()).first()
            tables_count = db.query(TableMeta).filter(TableMeta.schema_version_id == latest.id).count() if latest else 0
            out.append(SchemaListItem(
                id=s.id,
                name=s.name,
                description=s.description,
                latest_version_id=latest.id if latest else None,
                tables_count=tables_count,
            ))
        return out
    finally:
        db.close()


@router.get("/schema/{schema_id}", response_model=SchemaVersionDetail)
def get_schema(schema_id: str, version: int | None = None):
    db = SessionLocal()
    try:
        schema = db.query(Schema).filter(Schema.id == schema_id).first()
        if not schema:
            raise HTTPException(404, "Schema not found")
        if version is not None:
            sv = db.query(SchemaVersion).filter(SchemaVersion.schema_id == schema_id, SchemaVersion.version_number == version).first()
        else:
            sv = db.query(SchemaVersion).filter(SchemaVersion.schema_id == schema_id).order_by(SchemaVersion.version_number.desc()).first()
        if not sv:
            raise HTTPException(404, "Schema version not found")
        tables = db.query(TableMeta).filter(TableMeta.schema_version_id == sv.id).all()
        rel_count = db.query(Relationship).filter(
            Relationship.parent_table_id.in_([t.id for t in tables]),
        ).count()
        cols_count = sum(len(t.columns) for t in tables)
        return SchemaVersionDetail(
            id=sv.id,
            schema_id=sv.schema_id,
            version_number=sv.version_number,
            discovered_at=sv.discovered_at,
            status=sv.status,
            tables=[TableInfo(id=t.id, name=t.name, schema_name=t.schema_name, row_count=t.row_count) for t in tables],
            columns_count=cols_count,
            relationships_count=rel_count,
        )
    finally:
        db.close()


@router.get("/schema/{schema_id}/versions", response_model=list[dict])
def list_schema_versions(schema_id: str):
    db = SessionLocal()
    try:
        versions = db.query(SchemaVersion).filter(SchemaVersion.schema_id == schema_id).order_by(SchemaVersion.version_number.desc()).all()
        return [{"id": v.id, "version_number": v.version_number, "discovered_at": v.discovered_at, "status": v.status} for v in versions]
    finally:
        db.close()


@router.get("/schema/version/{schema_version_id}/tables", response_model=list[TableInfo])
def get_tables(schema_version_id: str):
    db = SessionLocal()
    try:
        tables = db.query(TableMeta).filter(TableMeta.schema_version_id == schema_version_id).all()
        return [TableInfo(id=t.id, name=t.name, schema_name=t.schema_name, row_count=t.row_count) for t in tables]
    finally:
        db.close()


@router.get("/schema/version/{schema_version_id}/tables/{table_name}/columns", response_model=list[ColumnInfo])
def get_columns(schema_version_id: str, table_name: str):
    db = SessionLocal()
    try:
        t = db.query(TableMeta).filter(TableMeta.schema_version_id == schema_version_id, TableMeta.name == table_name).first()
        if not t:
            raise HTTPException(404, "Table not found")
        return [ColumnInfo(id=c.id, name=c.name, data_type=c.data_type, inferred_type=c.inferred_type, nullable=c.nullable, ordinal_position=c.ordinal_position) for c in t.columns]
    finally:
        db.close()

"""Schema discovery: connect to PostgreSQL, inspect tables/columns/PK/FK, save to metadata."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import logging
from typing import Any

from models import (
    Schema, SchemaVersion, TableMeta, ColumnMeta, Relationship,
    Connection,
)
from database import SessionLocal

logger = logging.getLogger(__name__)


def _get_connection_id_or_create(db: Session, name: str, connection_string: str) -> str:
    conn = db.query(Connection).filter(Connection.name == name).first()
    if conn:
        return conn.id
    conn = Connection(name=name, connection_string_encrypted=connection_string, type="postgres")
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn.id


def run_discovery(
    connection_string: str,
    schemas: list[str],
    include_stats: bool = True,
    sample_size: int = 10000,
) -> dict[str, Any]:
    engine = create_engine(connection_string, pool_pre_ping=True)
    inspector = inspect(engine)
    db = SessionLocal()
    try:
        schema_name_for_list = schemas[0] if schemas else "public"
        conn_name = f"source_{schema_name_for_list}"
        conn_id = _get_connection_id_or_create(db, conn_name, connection_string)
        schema_obj = db.query(Schema).filter(Schema.source_connection_id == conn_id).first()
        if not schema_obj:
            schema_obj = Schema(name=conn_name, source_connection_id=conn_id)
            db.add(schema_obj)
            db.commit()
            db.refresh(schema_obj)
        next_ver = 1
        latest = db.query(SchemaVersion).filter(SchemaVersion.schema_id == schema_obj.id).order_by(SchemaVersion.version_number.desc()).first()
        if latest:
            next_ver = latest.version_number + 1
        sv = SchemaVersion(schema_id=schema_obj.id, version_number=next_ver, status="active")
        db.add(sv)
        db.commit()
        db.refresh(sv)
        schema_version_id = sv.id

        tables_list = []
        for schema in schemas:
            for tname in inspector.get_table_names(schema=schema):
                tables_list.append((schema, tname))

        table_id_by_key = {}
        for schema_ns, tname in tables_list:
            row_count = None
            if include_stats:
                try:
                    with engine.connect() as conn:
                        r = conn.execute(text(f'SELECT COUNT(*) FROM "{schema_ns}"."{tname}"')).scalar()
                    if r and r > sample_size:
                        row_count = r
                    else:
                        row_count = r
                except Exception as e:
                    logger.warning("Count failed for %s.%s: %s", schema_ns, tname, e)
            t = TableMeta(schema_version_id=str(schema_version_id), name=tname, schema_name=schema_ns, row_count=row_count)
            db.add(t)
            db.flush()
            table_id_by_key[(schema_ns, tname)] = str(t.id)

        for (schema_ns, tname), table_id in table_id_by_key.items():
            for col in inspector.get_columns(tname, schema=schema_ns):
                c = ColumnMeta(
                    table_id=str(table_id),
                    name=col["name"],
                    data_type=str(col.get("type", "")) if col.get("type") else None,
                    nullable=col.get("nullable", True),
                    ordinal_position=col.get("ordinal_position"),
                )
                db.add(c)
            db.flush()
        db.commit()

        # Refresh to get column ids
        for (schema_ns, tname), table_id in table_id_by_key.items():
            tbl = db.query(TableMeta).filter(TableMeta.id == table_id).first()
            if not tbl:
                continue
            col_ids = {c.name: str(c.id) for c in tbl.columns}
            for fk in inspector.get_foreign_keys(tname, schema=schema_ns):
                parent_schema = fk.get("referred_schema") or schema_ns
                parent_table = fk["referred_table"]
                parent_key = (parent_schema, parent_table)
                if parent_key not in table_id_by_key:
                    continue
                for uc, rc in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                    child_col_id = col_ids.get(uc)
                    parent_tid = table_id_by_key[parent_key]
                    parent_tbl = db.query(TableMeta).filter(TableMeta.id == parent_tid).first()
                    parent_col_id = {c.name: str(c.id) for c in parent_tbl.columns}.get(rc) if parent_tbl else None
                    if child_col_id and parent_col_id:
                        rel = Relationship(
                            parent_table_id=str(parent_tid),
                            child_table_id=str(table_id),
                            parent_column_id=str(parent_col_id),
                            child_column_id=str(child_col_id),
                        )
                        db.add(rel)
        db.commit()

        return {
            "schema_version_id": schema_version_id,
            "schema_id": schema_obj.id,
            "version_number": next_ver,
            "tables_count": len(tables_list),
        }
    finally:
        db.close()
        engine.dispose()

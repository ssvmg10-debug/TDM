from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import DatasetVersion, DatasetMetadata
from dataset_store import list_tables
from schemas_pydantic import DatasetVersionItem

router = APIRouter()


@router.get("/datasets", response_model=list[DatasetVersionItem])
def list_datasets(source_type: str | None = None, schema_version_id: str | None = None):
    db = SessionLocal()
    try:
        q = db.query(DatasetVersion)
        if source_type:
            q = q.filter(DatasetVersion.source_type == source_type)
        if schema_version_id:
            q = q.filter(DatasetVersion.schema_version_id == schema_version_id)
        versions = q.order_by(DatasetVersion.created_at.desc()).all()
        out = []
        for dv in versions:
            row_counts = None
            for dm in db.query(DatasetMetadata).filter(DatasetMetadata.dataset_version_id == dv.id).all():
                if dm.meta_key == "row_counts" and dm.meta_value:
                    row_counts = dm.meta_value
                    break
            tables_list = list_tables(dv.id)
            out.append(DatasetVersionItem(
                id=dv.id,
                name=dv.name,
                source_type=dv.source_type,
                status=dv.status,
                path_prefix=dv.path_prefix,
                created_at=dv.created_at,
                row_counts=row_counts,
                tables_count=len(tables_list),
                schema_version_id=dv.schema_version_id,
            ))
        return out
    finally:
        db.close()


@router.get("/dataset/{dataset_id}", response_model=DatasetVersionItem)
def get_dataset(dataset_id: str):
    db = SessionLocal()
    try:
        dv = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_id).first()
        if not dv:
            raise HTTPException(404, "Dataset not found")
        row_counts = None
        for dm in db.query(DatasetMetadata).filter(DatasetMetadata.dataset_version_id == dv.id).all():
            if dm.meta_key == "row_counts" and dm.meta_value:
                row_counts = dm.meta_value
                break
        tables_list = list_tables(dv.id)
        return DatasetVersionItem(
            id=dv.id,
            name=dv.name,
            source_type=dv.source_type,
            status=dv.status,
            path_prefix=dv.path_prefix,
            created_at=dv.created_at,
            row_counts=row_counts,
            tables_count=len(tables_list),
            schema_version_id=dv.schema_version_id,
        )
    finally:
        db.close()

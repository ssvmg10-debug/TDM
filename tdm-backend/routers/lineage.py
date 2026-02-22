from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import Lineage
from schemas_pydantic import LineageItem

router = APIRouter()


@router.get("/lineage/dataset/{dataset_id}", response_model=list[LineageItem])
def get_lineage_dataset(dataset_id: str):
    db = SessionLocal()
    try:
        rows = db.query(Lineage).filter(
            (Lineage.source_id == dataset_id) | (Lineage.target_id == dataset_id)
        ).order_by(Lineage.created_at).all()
        return [
            LineageItem(source_type=r.source_type, source_id=r.source_id, target_type=r.target_type, target_id=r.target_id, operation=r.operation, created_at=r.created_at)
            for r in rows
        ]
    finally:
        db.close()

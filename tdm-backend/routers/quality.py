"""Phase 5: Synthetic Quality Engine API."""
from fastapi import APIRouter, HTTPException

from services.quality_engine import compute_dataset_quality

router = APIRouter(prefix="/quality", tags=["Quality"])


@router.get("/dataset/{dataset_version_id}")
def get_dataset_quality(dataset_version_id: str):
    """Compute quality score and report for a dataset."""
    try:
        return compute_dataset_quality(dataset_version_id)
    except Exception as e:
        raise HTTPException(500, str(e))

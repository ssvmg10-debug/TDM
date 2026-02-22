from fastapi import APIRouter, HTTPException
from schemas_pydantic import PIIClassifyRequest, PIIClassifyResponse, PIIEntry
from services.pii_detection import run_pii_classification

router = APIRouter()


@router.post("/pii/classify", response_model=PIIClassifyResponse)
def post_pii_classify(body: PIIClassifyRequest):
    try:
        entries = run_pii_classification(
            schema_version_id=body.schema_version_id,
            use_llm=body.use_llm,
            sample_size_per_column=body.sample_size_per_column,
        )
        return PIIClassifyResponse(
            pii_map=[PIIEntry(table=e["table"], column=e["column"], pii_type=e["pii_type"], confidence=e["confidence"], technique=e["technique"]) for e in entries],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pii/{schema_version_id}", response_model=PIIClassifyResponse)
def get_pii(schema_version_id: str):
    from database import SessionLocal
    from models import PIIClassification
    db = SessionLocal()
    try:
        rows = db.query(PIIClassification).filter(PIIClassification.schema_version_id == schema_version_id).all()
        return PIIClassifyResponse(
            pii_map=[PIIEntry(table=r.table_name, column=r.column_name, pii_type=r.pii_type, confidence=float(r.confidence or 0), technique=r.technique or "") for r in rows],
        )
    finally:
        db.close()

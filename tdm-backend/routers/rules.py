from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import SessionLocal
from models import MaskingRule

router = APIRouter()


class MaskingRuleCreate(BaseModel):
    name: str | None = None
    schema_version_id: str | None = None
    rules_json: dict


@router.post("/rules/masking")
def create_masking_rule(body: MaskingRuleCreate):
    db = SessionLocal()
    try:
        r = MaskingRule(name=body.name, schema_version_id=body.schema_version_id, rules_json=body.rules_json)
        db.add(r)
        db.commit()
        db.refresh(r)
        return {"id": r.id, "message": "created"}
    finally:
        db.close()

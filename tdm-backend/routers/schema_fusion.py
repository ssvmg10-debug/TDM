"""Phase 2: Schema Fusion API."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from services.schema_fusion import run_schema_fusion

router = APIRouter(prefix="/schema-fusion", tags=["Schema Fusion"])


class SchemaFusionRequest(BaseModel):
    ui_schemas: Optional[Dict[str, Any]] = None
    api_schemas: Optional[Dict[str, Any]] = None
    db_schemas: Optional[Dict[str, Any]] = None
    test_case_entities: Optional[Dict[str, Any]] = None
    domain_pack: Optional[str] = None


@router.post("/fuse")
def fuse_schemas(body: SchemaFusionRequest):
    """Fuse UI + API + DB + Test Case + Domain schemas into unified schema."""
    return run_schema_fusion(
        ui_schemas=body.ui_schemas,
        api_schemas=body.api_schemas,
        db_schemas=body.db_schemas,
        test_case_entities=body.test_case_entities,
        domain_pack=body.domain_pack,
    )

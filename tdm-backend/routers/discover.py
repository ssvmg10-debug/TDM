from fastapi import APIRouter, HTTPException
from schemas_pydantic import DiscoverSchemaRequest, DiscoverSchemaResponse
from services.schema_discovery import run_discovery

router = APIRouter()


@router.post("/discover-schema", response_model=DiscoverSchemaResponse)
def post_discover_schema(body: DiscoverSchemaRequest):
    try:
        result = run_discovery(
            connection_string=body.connection_string,
            schemas=body.schemas,
            include_stats=body.include_stats,
            sample_size=body.sample_size or 10000,
        )
        return DiscoverSchemaResponse(
            schema_version_id=result.get("schema_version_id"),
            message="Discovery completed",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

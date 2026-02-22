from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import SessionLocal
from models import Environment
from schemas_pydantic import EnvironmentItem

router = APIRouter()


class EnvironmentCreate(BaseModel):
    name: str
    connection_string: str | None = None
    config_json: dict | None = None


@router.get("/environments", response_model=list[EnvironmentItem])
def list_environments():
    db = SessionLocal()
    try:
        envs = db.query(Environment).all()
        return [EnvironmentItem(id=e.id, name=e.name, config_json=e.config_json) for e in envs]
    finally:
        db.close()


@router.post("/environments", response_model=EnvironmentItem)
def create_environment(body: EnvironmentCreate):
    db = SessionLocal()
    try:
        existing = db.query(Environment).filter(Environment.name == body.name).first()
        if existing:
            raise HTTPException(400, "Environment name exists")
        e = Environment(name=body.name, connection_string_encrypted=body.connection_string, config_json=body.config_json)
        db.add(e)
        db.commit()
        db.refresh(e)
        return EnvironmentItem(id=e.id, name=e.name, config_json=e.config_json)
    finally:
        db.close()

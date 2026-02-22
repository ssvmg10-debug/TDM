"""Local filesystem dataset store. Path: {dataset_store_path}/{version_id}/{table_name}.parquet"""
import os
from pathlib import Path
from config import settings


def get_dataset_dir(version_id: str) -> Path:
    base = Path(settings.dataset_store_path)
    base.mkdir(parents=True, exist_ok=True)
    return base / version_id


def get_table_path(version_id: str, table_name: str) -> Path:
    return get_dataset_dir(version_id) / f"{table_name}.parquet"


def ensure_dataset_dir(version_id: str) -> Path:
    d = get_dataset_dir(version_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_tables(version_id: str) -> list[str]:
    d = get_dataset_dir(version_id)
    if not d.exists():
        return []
    return [f.stem for f in d.glob("*.parquet")]

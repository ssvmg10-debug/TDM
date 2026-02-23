"""Load from project root .env or tdm-backend/.env."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Prefer parent .env (TDM root) so one file holds all config
_root = Path(__file__).resolve().parent.parent
_env_file = _root / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    # DB (metadata store) - support both DATABASE_URL and your .env names
    database_url: str = "postgresql://postgres:12345@localhost:5432/tdm"
    
    # Target DB (where provisioned/synthetic data is stored)
    target_database_url: str = "postgresql://postgres:12345@localhost:5432/tdm_target"

    # Azure OpenAI - support AZURE_* from your .env
    azure_api_key: str = ""
    azure_endpoint: str = ""
    azure_deployment: str = "gpt-4.1"
    azure_api_version: str = "2024-02-01"
    azure_openai_temperature: float = 0.1

    # API (8003 avoids WinError 10013 on some Windows systems; use API_PORT=8002 if preferred)
    api_port: int = 8003
    log_level: str = "INFO"

    # Dataset store: local path when MinIO not used
    dataset_store_path: str = ""

    class Config:
        env_file = _env_file
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Alias common .env names
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.target_database_url = os.getenv("TARGET_DATABASE_URL", self.target_database_url)
        self.azure_api_key = os.getenv("AZURE_API_KEY", self.azure_api_key)
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT", self.azure_endpoint)
        self.azure_deployment = os.getenv("AZURE_DEPLOYMENT", self.azure_deployment)
        self.azure_api_version = os.getenv("AZURE_API_VERSION", self.azure_api_version)
        self.api_port = int(os.getenv("API_PORT", str(self.api_port)))
        if not self.dataset_store_path:
            base = Path(__file__).resolve().parent
            self.dataset_store_path = str(base / "data" / "datasets")


settings = Settings()

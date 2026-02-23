"""
TDM Backend API — Test Data Management.
Base URL: /api/v1
"""
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load parent .env (TDM root)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Configure comprehensive logging with UTF-8 encoding
file_handler = logging.FileHandler("tdm_backend.log", encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[stream_handler, file_handler]
)

# Set log levels for different modules
logger = logging.getLogger("tdm.api")
logger.setLevel(logging.INFO)

# Set log levels for service modules
for module in ["tdm.workflow", "tdm.synthetic", "tdm.masking", "tdm.subsetting", 
               "tdm.pii", "tdm.discovery", "tdm.provision", "tdm.crawler"]:
    logging.getLogger(module).setLevel(logging.INFO)

# Reduce noise from libraries
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger.info("=" * 80)
logger.info("[STARTUP] TDM Backend Starting Up")
logger.info("=" * 80)

from routers import (
    discover,
    pii,
    subset,
    mask,
    synthetic,
    provision,
    schemas,
    datasets,
    jobs,
    lineage,
    environments,
    audit,
    rules,
    workflow,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[READY] Application startup complete")
    logger.info("[INFO] API Documentation: http://localhost:8002/docs")
    logger.info("[INFO] Base URL: http://localhost:8002/api/v1")
    logger.info("=" * 80)
    yield
    logger.info("[SHUTDOWN] Shutting down TDM Backend")


app = FastAPI(
    title="TDM API",
    description="Test Data Management — Schema Discovery, PII, Subsetting, Masking, Synthetic, Provisioning",
    version="1.0.0",
    lifespan=lifespan,
)

logger.info("[CONFIG] Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        sys.stdout.write(f"[REQUEST] {request.method} {request.url.path}\n")
        sys.stdout.flush()
        logger.info(f"[REQUEST] {request.method} {request.url.path}")
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        status = "OK" if response.status_code < 400 else "ERROR"
        sys.stdout.write(f"[{status}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)\n")
        sys.stdout.flush()
        logger.info(f"[{status}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)")
        return response


logger.info("[CONFIG] Adding request logging middleware")
app.add_middleware(RequestLoggingMiddleware)

logger.info("[CONFIG] Registering API routers:")
logger.info("   • Discover (Schema Discovery)")
app.include_router(discover.router, prefix="/api/v1", tags=["discover"])
logger.info("   • PII (Classification)")
app.include_router(pii.router, prefix="/api/v1", tags=["pii"])
logger.info("   • Subset (Data Subsetting)")
app.include_router(subset.router, prefix="/api/v1", tags=["subset"])
logger.info("   • Mask (Data Masking)")
app.include_router(mask.router, prefix="/api/v1", tags=["mask"])
logger.info("   • Synthetic (Data Generation)")
app.include_router(synthetic.router, prefix="/api/v1", tags=["synthetic"])
logger.info("   • Provision (Deployment)")
app.include_router(provision.router, prefix="/api/v1", tags=["provision"])
logger.info("   • Schemas")
app.include_router(schemas.router, prefix="/api/v1", tags=["schemas"])
logger.info("   • Datasets")
app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
logger.info("   • Jobs")
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
logger.info("   • Lineage")
app.include_router(lineage.router, prefix="/api/v1", tags=["lineage"])
logger.info("   • Environments")
app.include_router(environments.router, prefix="/api/v1", tags=["environments"])
logger.info("   • Audit")
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
logger.info("   • Rules")
app.include_router(rules.router, prefix="/api/v1", tags=["rules"])
logger.info("   • Workflow (Orchestration)")
app.include_router(workflow.router, prefix="/api/v1", tags=["workflow"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run("main:app", host="0.0.0.0", port=settings.api_port, reload=True)

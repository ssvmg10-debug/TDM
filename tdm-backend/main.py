"""
TDM Backend API — Test Data Management.
Base URL: /api/v1
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load parent .env (TDM root)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("tdm.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

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
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # shutdown if needed


app = FastAPI(
    title="TDM API",
    description="Test Data Management — Schema Discovery, PII, Subsetting, Masking, Synthetic, Provisioning",
    version="1.0.0",
    lifespan=lifespan,
)

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
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, duration_ms)
        return response


app.add_middleware(RequestLoggingMiddleware)

app.include_router(discover.router, prefix="/api/v1", tags=["discover"])
app.include_router(pii.router, prefix="/api/v1", tags=["pii"])
app.include_router(subset.router, prefix="/api/v1", tags=["subset"])
app.include_router(mask.router, prefix="/api/v1", tags=["mask"])
app.include_router(synthetic.router, prefix="/api/v1", tags=["synthetic"])
app.include_router(provision.router, prefix="/api/v1", tags=["provision"])
app.include_router(schemas.router, prefix="/api/v1", tags=["schemas"])
app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(lineage.router, prefix="/api/v1", tags=["lineage"])
app.include_router(environments.router, prefix="/api/v1", tags=["environments"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(rules.router, prefix="/api/v1", tags=["rules"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run("main:app", host="0.0.0.0", port=settings.api_port, reload=True)

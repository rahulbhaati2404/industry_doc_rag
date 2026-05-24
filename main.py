from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from core.config import settings
from core.logger import logger
from api.health import router as health_router
from api.ingest import router as ingest_router
from api.metrics import router as metrics_router
from api.models import router as models_router
from api.query import router as query_router
from api.stream import router as stream_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

import os
import sys

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(ingest_router, prefix=settings.API_V1_STR, tags=["Ingest"])
app.include_router(metrics_router, prefix=settings.API_V1_STR, tags=["Metrics"])
app.include_router(models_router, prefix=settings.API_V1_STR, tags=["Models"])
app.include_router(query_router, prefix=settings.API_V1_STR, tags=["Query"])
app.include_router(stream_router, prefix=settings.API_V1_STR, tags=["Stream"])


@app.get("/")
async def redirect_to_swagger():
    """Automatically redirect the root URL to the Swagger documentation page."""
    return RedirectResponse(url="/docs")

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Industry Document RAG Engine starting...")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down Industry Document RAG Engine...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
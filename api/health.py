import asyncio
from typing import Any
from fastapi import APIRouter
from cache.cache_manager import cache_manager
from core.config import settings
from core.logger import logger
from models.ollama_client import ollama_client
from rag.vector_store import vector_store

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return app, vector DB, cache, and Ollama health."""

    vector_status = await _vector_health()
    cache_status = await cache_manager.health_check()
    ollama_status = await _ollama_health()

    components = {
        "vector_db": vector_status,
        "cache": cache_status,
        "ollama": ollama_status,
    }
    status = (
        "healthy"
        if all(component.get("status") in {"healthy", "disabled"} for component in components.values())
        else "degraded"
    )

    return {
        "status": status,
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
        "components": components,
    }


async def _vector_health() -> dict[str, Any]:
    try:
        count = await asyncio.to_thread(vector_store.collection.count)
        return {
            "status": "healthy",
            "store": settings.VECTOR_STORE,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
            "documents": count,
        }
    except Exception as exc:
        logger.warning(f"Vector DB health check failed: {exc}")
        return {"status": "degraded", "reason": str(exc)}


async def _ollama_health() -> dict[str, Any]:
    try:
        healthy = await asyncio.to_thread(ollama_client.health_check)
        return {
            "status": "healthy" if healthy else "degraded",
            "base_url": settings.OLLAMA_BASE_URL,
        }
    except Exception as exc:
        logger.warning(f"Ollama health check failed: {exc}")
        return {"status": "degraded", "reason": str(exc)}

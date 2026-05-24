from fastapi import APIRouter

from models.model_registry import model_registry
from models.ollama_client import ollama_client

router = APIRouter()


@router.get("/models")
async def get_models():

    ollama_status = ollama_client.health_check()

    return {
        "ollama_available": ollama_status,
        "loaded_models": model_registry.list_models()
    }
from cache.response_cache import response_cache
from models.ollama_client import ollama_client
from observability.tracing import trace_manager


async def run_generation(prompt: str, model: str) -> tuple[str, bool]:
    """Generate an answer, using prompt-response cache when available."""

    cached = await response_cache.get(prompt=prompt, model=model)
    if cached is not None:
        return str(cached.get("answer", "")), True

    with trace_manager.trace("generation"):
        answer = await ollama_client.agenerate(prompt=prompt, model=model)

    await response_cache.set(
        prompt=prompt,
        model=model,
        response={"answer": answer},
    )
    return answer, False

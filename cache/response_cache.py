from typing import Any

from cache.cache_manager import cache_manager


class ResponseCache:
    """Cache generated prompt responses by model and prompt."""

    namespace = "response"

    def key(self, prompt: str, model: str) -> str:
        return cache_manager.build_key(
            self.namespace,
            {"prompt": prompt, "model": model},
        )

    async def get(self, prompt: str, model: str) -> dict[str, Any] | None:
        return await cache_manager.get(self.key(prompt, model))

    async def set(self, prompt: str, model: str, response: dict[str, Any]) -> None:
        await cache_manager.set(self.key(prompt, model), response)


response_cache = ResponseCache()

from typing import Any

from cache.cache_manager import cache_manager


class EmbeddingCache:
    """Cache wrapper for document and query embeddings."""

    namespace = "embedding"

    def key(self, model_name: str, text: str) -> str:
        return cache_manager.build_key(
            self.namespace,
            {"model": model_name, "text": text},
        )

    async def get(self, model_name: str, text: str) -> Any | None:
        return await cache_manager.get(self.key(model_name, text))

    async def set(self, model_name: str, text: str, embedding: Any) -> None:
        await cache_manager.set(self.key(model_name, text), embedding)

    def get_sync(self, model_name: str, text: str) -> Any | None:
        return cache_manager.get_sync(self.key(model_name, text))

    def set_sync(self, model_name: str, text: str, embedding: Any) -> None:
        cache_manager.set_sync(self.key(model_name, text), embedding)


embedding_cache = EmbeddingCache()
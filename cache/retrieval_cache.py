from typing import Any
from cache.cache_manager import cache_manager

class RetrievalCache:
    """Cache retrieval and reranking results by query and top_k."""

    namespace = "retrieval"

    def key(self, query: str, top_k: int) -> str:
        return cache_manager.build_key(
            self.namespace,
            {"query": query, "top_k": top_k},
        )

    async def get(self, query: str, top_k: int) -> list[dict[str, Any]] | None:
        return await cache_manager.get(self.key(query, top_k))

    async def set(self, query: str, top_k: int, documents: list[dict[str, Any]]) -> None:
        await cache_manager.set(self.key(query, top_k), documents)

    def get_sync(self, query: str, top_k: int) -> list[dict[str, Any]] | None:
        return cache_manager.get_sync(self.key(query, top_k))

    def set_sync(self, query: str, top_k: int, documents: list[dict[str, Any]]) -> None:
        cache_manager.set_sync(self.key(query, top_k), documents)


retrieval_cache = RetrievalCache()

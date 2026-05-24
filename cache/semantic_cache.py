from cache.cache_manager import cache_manager


class SemanticCache:
    """Cache semantic memory recall results."""

    namespace = "semantic"

    def key(self, session_id: str, query: str, top_k: int) -> str:
        return cache_manager.build_key(
            self.namespace,
            {"session_id": session_id, "query": query, "top_k": top_k},
        )

    async def get(self, session_id: str, query: str, top_k: int) -> list[str] | None:
        return await cache_manager.get(self.key(session_id, query, top_k))

    async def set(
        self,
        session_id: str,
        query: str,
        top_k: int,
        memories: list[str],
    ) -> None:
        await cache_manager.set(self.key(session_id, query, top_k), memories)

    def get_sync(self, session_id: str, query: str, top_k: int) -> list[str] | None:
        return cache_manager.get_sync(self.key(session_id, query, top_k))

    def set_sync(
        self,
        session_id: str,
        query: str,
        top_k: int,
        memories: list[str],
    ) -> None:
        cache_manager.set_sync(self.key(session_id, query, top_k), memories)

    async def invalidate_all(self) -> int:
        return await cache_manager.invalidate(f"{self.namespace}:")


semantic_cache = SemanticCache()

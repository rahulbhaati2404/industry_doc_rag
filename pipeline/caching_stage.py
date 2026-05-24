from cache.cache_manager import cache_manager


async def invalidate_pipeline_cache(prefix: str | None = None) -> int:
    """Invalidate cache entries used by pipeline stages."""

    return await cache_manager.invalidate(prefix)

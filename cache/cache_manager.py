import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from core.config import settings
from core.logger import logger
from observability.metrics import metrics_collector


@dataclass
class CacheEntry:
    """Local cache entry with an absolute expiry timestamp."""

    value: str
    expires_at: float

class CacheManager:
    """Async-compatible cache manager with Redis support and memory fallback."""

    def __init__(self) -> None:
        self.enabled = settings.CACHE_ENABLED
        self.ttl_seconds = settings.CACHE_TTL_SECONDS
        self.backend = settings.CACHE_BACKEND.lower()
        self.redis_url = settings.REDIS_URL
        self._memory_store: dict[str, CacheEntry] = {}
        self._redis_client: Any | None = None
        self._lock = asyncio.Lock()

    def build_key(self, namespace: str, payload: Any) -> str:
        """Create a stable cache key from a JSON-serializable payload."""

        serialized = self._serialize(payload)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{namespace}:{digest}"

    async def get(self, key: str) -> Any | None:
        """Read and deserialize a cache value."""

        start = time.perf_counter()
        if not self.enabled:
            return None

        try:
            raw_value = await self._aget_raw(key)
            if raw_value is None:
                self._record("miss", start)
                return None

            self._record("hit", start)
            return json.loads(raw_value)
        except Exception as exc:
            logger.warning(f"Cache get failed for {key}: {exc}")
            self._record("error", start)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Serialize and write a cache value."""

        if not self.enabled:
            return

        try:
            serialized = self._serialize(value)
            await self._aset_raw(key, serialized, ttl_seconds or self.ttl_seconds)
        except Exception as exc:
            logger.warning(f"Cache set failed for {key}: {exc}")

    async def invalidate(self, key_prefix: str | None = None) -> int:
        """Invalidate either the whole cache or keys matching a prefix."""

        if not self.enabled:
            return 0

        deleted = 0
        async with self._lock:
            keys = list(self._memory_store.keys())
            for key in keys:
                if key_prefix is None or key.startswith(key_prefix):
                    self._memory_store.pop(key, None)
                    deleted += 1

        redis_client = await self._get_redis_client()
        if redis_client is not None:
            pattern = f"{key_prefix}*" if key_prefix else "*"
            async for key in redis_client.scan_iter(pattern):
                await redis_client.delete(key)
                deleted += 1

        metrics_collector.record("cache_invalidations", deleted)
        return deleted

    def invalidate_sync(self, key_prefix: str | None = None) -> int:
        """Synchronous invalidation for existing sync code paths."""

        deleted = 0
        keys = list(self._memory_store.keys())
        for key in keys:
            if key_prefix is None or key.startswith(key_prefix):
                self._memory_store.pop(key, None)
                deleted += 1

        metrics_collector.record("cache_invalidations", deleted)
        return deleted

    def get_sync(self, key: str) -> Any | None:
        """Synchronous memory-cache read for existing sync code paths."""

        start = time.perf_counter()
        if not self.enabled:
            return None

        entry = self._memory_store.get(key)
        if entry is None or entry.expires_at < time.time():
            self._memory_store.pop(key, None)
            self._record("miss", start)
            return None

        self._record("hit", start)
        return json.loads(entry.value)

    def set_sync(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Synchronous memory-cache write for existing sync code paths."""

        if not self.enabled:
            return

        self._memory_store[key] = CacheEntry(
            value=self._serialize(value),
            expires_at=time.time() + (ttl_seconds or self.ttl_seconds),
        )

    def stats(self) -> dict[str, Any]:
        """Return lightweight cache status and metrics."""

        summary = metrics_collector.summary()
        hits = summary.get("cache_hits", {}).get("count", 0)
        misses = summary.get("cache_misses", {}).get("count", 0)
        total = hits + misses

        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "ttl_seconds": self.ttl_seconds,
            "memory_entries": len(self._memory_store),
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / total if total else 0.0,
        }

    async def health_check(self) -> dict[str, Any]:
        """Check cache backend availability without failing the app."""

        if not self.enabled:
            return {"status": "disabled", **self.stats()}

        if self.backend == "redis":
            redis_client = await self._get_redis_client()
            if redis_client is None:
                return {"status": "degraded", "reason": "redis_unavailable", **self.stats()}
            try:
                await redis_client.ping()
                return {"status": "healthy", **self.stats()}
            except Exception as exc:
                logger.warning(f"Redis health check failed: {exc}")
                return {"status": "degraded", "reason": str(exc), **self.stats()}

        return {"status": "healthy", **self.stats()}

    async def _aget_raw(self, key: str) -> str | None:
        redis_client = await self._get_redis_client()
        if redis_client is not None:
            value = await redis_client.get(key)
            return value.decode("utf-8") if isinstance(value, bytes) else value

        async with self._lock:
            entry = self._memory_store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                self._memory_store.pop(key, None)
                return None
            return entry.value

    async def _aset_raw(self, key: str, value: str, ttl_seconds: int) -> None:
        redis_client = await self._get_redis_client()
        if redis_client is not None:
            await redis_client.set(key, value, ex=ttl_seconds)
            return

        async with self._lock:
            self._memory_store[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl_seconds,
            )

    async def _get_redis_client(self) -> Any | None:
        if self.backend != "redis":
            return None
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis.asyncio as redis

            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
            )
            return self._redis_client
        except Exception as exc:
            logger.warning(f"Redis backend unavailable, using memory cache: {exc}")
            self.backend = "memory"
            return None

    def _record(self, event: str, start: float) -> None:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics_collector.record("cache_latency_ms", latency_ms)
        if event == "hit":
            metrics_collector.record("cache_hits", 1)
        elif event == "miss":
            metrics_collector.record("cache_misses", 1)
        else:
            metrics_collector.record("cache_errors", 1)

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, sort_keys=True, default=self._json_default)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "tolist"):
            return value.tolist()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

cache_manager = CacheManager()

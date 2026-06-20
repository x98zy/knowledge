import redis.asyncio as aioredis

from config.settings import settings

REDIS_POOL_KWARGS = {
    "max_connections": 50,
    "retry_on_timeout": True,
    "health_check_interval": 30,
    "socket_keepalive": True,
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "decode_responses": True,
}


class FastapiRedis:
    """FastAPI Redis extension, manages connection pool and lifecycle."""

    def __init__(self) -> None:
        self._pool: aioredis.ConnectionPool | None = None
        self._client: aioredis.Redis | None = None
        self.init()

    def init(self) -> None:
        """Initialize connection pool (called synchronously at module import time)."""
        self._pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            **REDIS_POOL_KWARGS,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis not initialized, call redis.init() first.")
        return self._client

    async def close(self) -> None:
        """Close connection pool and release all connections."""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            self._client = None

    async def incr(self, *args, **kwargs) -> int:
        """Increment a counter in Redis."""
        return await self.client.incr(*args, **kwargs)

    async def expire(self, *args, **kwargs) -> int:
        """Set expiration time for a key in Redis."""
        return await self.client.expire(*args, **kwargs)

    def lock(self, name: str, timeout: int = 20):
        """Acquire a distributed lock."""
        return self.client.lock(name, timeout=timeout)

    async def get(self, key: str):
        """Get value for a key in Redis."""
        return await self.client.get(key)

    async def set(self, key: str, value: str, *args, **kwargs) -> int:
        """Set a value for a key in Redis."""
        return await self.client.set(key, value, *args, **kwargs)


redis_client = FastapiRedis()

__all__ = ["redis_client"]

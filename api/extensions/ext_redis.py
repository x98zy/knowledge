import redis.asyncio as aioredis
from api.config.settings import settings

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


redis_client = FastapiRedis()

__all__ = ["redis_client"]

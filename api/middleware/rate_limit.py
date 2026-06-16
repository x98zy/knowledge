from api.extensions.ext_redis import redis_client
from loguru import logger


class RateLimiter:
    """Rate limiter based on Redis fixed window."""

    def __init__(self, prefix: str = "rate_limit"):
        self._prefix = prefix

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 5,
        window: int = 60,
    ) -> bool:
        """Check if the request is within the rate limit window.

        Args:
            identifier: rate limit identifier (e.g., client IP)
            max_requests: max requests allowed in the window
            window: window duration in seconds

        Returns:
            True if allowed, False if rate limited
        """
        key = f"{self._prefix}:{identifier}"
        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, window)
            return not count > max_requests
        except Exception:
            logger.warning("Redis unavailable, skipping rate limit check (fail-open), key={}", key)
            return True

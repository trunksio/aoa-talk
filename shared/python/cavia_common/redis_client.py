"""
Simple Redis connection for RQ

Redis is ONLY used for RQ (Redis Queue) task management.
We use RQ directly without wrappers to keep it simple.
"""

from typing import Optional
import redis
from redis import Redis

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


def get_redis_connection(redis_url: Optional[str] = None) -> Redis:
    """
    Get a Redis connection configured for RQ.

    RQ handles all serialization and queue management itself.
    We just provide a properly configured connection.

    Args:
        redis_url: Optional Redis URL. If not provided, uses settings.

    Returns:
        Redis connection instance ready for use with RQ
    """
    settings = get_settings()
    url = redis_url or str(settings.redis_url)

    # Let RQ use its defaults - don't override decode_responses
    # RQ knows how to handle Redis correctly
    connection = redis.from_url(url, health_check_interval=30)

    logger.info("Redis connection created", redis_url=url)
    return connection

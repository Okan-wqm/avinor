# shared/common/cache.py
"""
Redis Cluster Client and Caching Utilities
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class RedisClusterClient:
    """
    Redis Cluster client wrapper with high-availability support.
    Provides a consistent interface for Redis operations.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._init_cluster()
        self._initialized = True

    def _init_cluster(self):
        """Initialize Redis cluster connection"""
        try:
            from redis.cluster import RedisCluster

            cluster_nodes = getattr(settings, 'REDIS_CLUSTER_NODES', ['localhost:7000'])
            startup_nodes = [
                {"host": node.split(':')[0], "port": int(node.split(':')[1])}
                for node in cluster_nodes
            ]

            self.cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                password=getattr(settings, 'REDIS_PASSWORD', None),
                skip_full_coverage_check=True,
                read_from_replicas=True,
            )
            logger.info("Redis cluster connection established")
        except ImportError:
            logger.warning("redis-py-cluster not installed, using Django cache")
            self.cluster = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis cluster: {e}")
            self.cluster = None

    def _get_backend(self):
        """Get Redis backend or fall back to Django cache"""
        if self.cluster:
            return self.cluster
        return cache

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            backend = self._get_backend()
            if self.cluster:
                value = backend.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
                return None
            return backend.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ex: int = None) -> bool:
        """Set value in cache with optional expiration"""
        try:
            backend = self._get_backend()
            if self.cluster:
                if not isinstance(value, str):
                    value = json.dumps(value)
                return backend.set(key, value, ex=ex)
            return backend.set(key, value, timeout=ex)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            backend = self._get_backend()
            if self.cluster:
                return backend.delete(key) > 0
            return backend.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            backend = self._get_backend()
            if self.cluster:
                return backend.exists(key) > 0
            return backend.has_key(key)
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            if self.cluster:
                return self.cluster.expire(key, seconds)
            # Django cache doesn't support expire, re-set with timeout
            value = cache.get(key)
            if value is not None:
                cache.set(key, value, timeout=seconds)
                return True
            return False
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment value"""
        try:
            backend = self._get_backend()
            if self.cluster:
                return backend.incr(key, amount)
            return backend.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache incr error: {e}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value"""
        try:
            backend = self._get_backend()
            if self.cluster:
                return backend.decr(key, amount)
            return backend.decr(key, amount)
        except Exception as e:
            logger.error(f"Cache decr error: {e}")
            return 0

    # Hash operations
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        try:
            if self.cluster:
                return self.cluster.hget(name, key)
            data = cache.get(name) or {}
            return data.get(key)
        except Exception as e:
            logger.error(f"Cache hget error: {e}")
            return None

    def hset(self, name: str, key: str, value: Any) -> bool:
        """Set hash field value"""
        try:
            if self.cluster:
                return self.cluster.hset(name, key, value)
            data = cache.get(name) or {}
            data[key] = value
            cache.set(name, data)
            return True
        except Exception as e:
            logger.error(f"Cache hset error: {e}")
            return False

    def hgetall(self, name: str) -> Dict:
        """Get all hash fields"""
        try:
            if self.cluster:
                return self.cluster.hgetall(name)
            return cache.get(name) or {}
        except Exception as e:
            logger.error(f"Cache hgetall error: {e}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            if self.cluster:
                return self.cluster.hdel(name, *keys)
            data = cache.get(name) or {}
            deleted = 0
            for key in keys:
                if key in data:
                    del data[key]
                    deleted += 1
            cache.set(name, data)
            return deleted
        except Exception as e:
            logger.error(f"Cache hdel error: {e}")
            return 0

    # List operations
    def lpush(self, name: str, *values: Any) -> int:
        """Push values to left of list"""
        try:
            if self.cluster:
                return self.cluster.lpush(name, *values)
            data = cache.get(name) or []
            data = list(values) + data
            cache.set(name, data)
            return len(data)
        except Exception as e:
            logger.error(f"Cache lpush error: {e}")
            return 0

    def rpush(self, name: str, *values: Any) -> int:
        """Push values to right of list"""
        try:
            if self.cluster:
                return self.cluster.rpush(name, *values)
            data = cache.get(name) or []
            data.extend(values)
            cache.set(name, data)
            return len(data)
        except Exception as e:
            logger.error(f"Cache rpush error: {e}")
            return 0

    def lrange(self, name: str, start: int, end: int) -> List:
        """Get range of list elements"""
        try:
            if self.cluster:
                return self.cluster.lrange(name, start, end)
            data = cache.get(name) or []
            if end == -1:
                return data[start:]
            return data[start:end + 1]
        except Exception as e:
            logger.error(f"Cache lrange error: {e}")
            return []

    # Set operations
    def sadd(self, name: str, *values: Any) -> int:
        """Add values to set"""
        try:
            if self.cluster:
                return self.cluster.sadd(name, *values)
            data = set(cache.get(name) or [])
            initial_size = len(data)
            data.update(values)
            cache.set(name, list(data))
            return len(data) - initial_size
        except Exception as e:
            logger.error(f"Cache sadd error: {e}")
            return 0

    def smembers(self, name: str) -> set:
        """Get all set members"""
        try:
            if self.cluster:
                return self.cluster.smembers(name)
            return set(cache.get(name) or [])
        except Exception as e:
            logger.error(f"Cache smembers error: {e}")
            return set()

    def sismember(self, name: str, value: Any) -> bool:
        """Check if value is in set"""
        try:
            if self.cluster:
                return self.cluster.sismember(name, value)
            data = set(cache.get(name) or [])
            return value in data
        except Exception as e:
            logger.error(f"Cache sismember error: {e}")
            return False

    # Pub/Sub operations
    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        try:
            if self.cluster:
                if not isinstance(message, str):
                    message = json.dumps(message)
                return self.cluster.publish(channel, message)
            logger.warning("Pub/Sub not available without Redis cluster")
            return 0
        except Exception as e:
            logger.error(f"Cache publish error: {e}")
            return 0

    def pipeline(self):
        """Get pipeline for batch operations"""
        if self.cluster:
            return self.cluster.pipeline()
        return None


# Singleton instance
redis_cluster = RedisClusterClient()


# =============================================================================
# CACHING DECORATORS
# =============================================================================

def cached(
    key_prefix: str,
    timeout: int = 300,
    key_func=None
):
    """
    Decorator for caching function results.

    Usage:
        @cached('user', timeout=600)
        def get_user(user_id):
            return User.objects.get(id=user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"

            # Try to get from cache
            result = redis_cluster.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_cluster.set(cache_key, result, ex=timeout)

            return result
        return wrapper
    return decorator


def cache_invalidate(key_pattern: str):
    """
    Decorator to invalidate cache after function execution.

    Usage:
        @cache_invalidate('user:*')
        def update_user(user_id, data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Invalidate matching keys
            try:
                if redis_cluster.cluster:
                    # Redis cluster pattern delete
                    for key in redis_cluster.cluster.scan_iter(key_pattern):
                        redis_cluster.delete(key)
            except Exception as e:
                logger.error(f"Cache invalidation error: {e}")
            return result
        return wrapper
    return decorator


class CacheKeyBuilder:
    """
    Helper class for building consistent cache keys.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name

    def build(self, *parts: str) -> str:
        """Build cache key from parts"""
        return f"{self.service_name}:{':'.join(str(p) for p in parts)}"

    def user(self, user_id: str) -> str:
        return self.build('user', user_id)

    def organization(self, org_id: str) -> str:
        return self.build('org', org_id)

    def list(self, resource: str, org_id: str = None) -> str:
        if org_id:
            return self.build('list', resource, org_id)
        return self.build('list', resource)

    def detail(self, resource: str, resource_id: str) -> str:
        return self.build('detail', resource, resource_id)

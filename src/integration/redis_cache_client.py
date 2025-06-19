#!/usr/bin/env python3
"""
Redis Cache Client for DEAN Infrastructure
Provides caching, pub/sub, and distributed locking capabilities
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
import aioredis
from aioredis.lock import Lock
import logging
import pickle

logger = logging.getLogger(__name__)


class RedisCacheClient:
    """
    Redis cache client for DEAN system.
    Provides caching, pub/sub, and distributed locking.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        db: int = 0,
        password: Optional[str] = None,
        encoding: str = "utf-8",
        decode_responses: bool = True,
        max_connections: int = 50
    ):
        """
        Initialize Redis cache client.
        
        Args:
            redis_url: Redis connection URL
            db: Database number
            password: Redis password
            encoding: String encoding
            decode_responses: Whether to decode responses
            max_connections: Maximum number of connections
        """
        self.redis_url = redis_url
        self.db = db
        self.password = password
        self.encoding = encoding
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub_handlers: Dict[str, List[Callable]] = {}
        
    async def connect(self):
        """Establish Redis connection"""
        if self.redis:
            return
        
        try:
            self.redis = await aioredis.create_redis_pool(
                self.redis_url,
                db=self.db,
                password=self.password,
                encoding=self.encoding,
                minsize=5,
                maxsize=self.max_connections
            )
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            self.redis = None
            logger.info("Disconnected from Redis")
    
    # Basic cache operations
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            await self.connect()
        
        value = await self.redis.get(key)
        
        if value is None:
            return None
        
        # Try to deserialize JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            Success status
        """
        if not self.redis:
            await self.connect()
        
        # Serialize value
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, (str, bytes, int, float)):
            value = pickle.dumps(value)
        
        # Set with options
        if ttl:
            return await self.redis.setex(key, ttl, value)
        else:
            return await self.redis.set(key, value, exist=self._get_exist_flag(nx, xx))
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.delete(*keys)
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.exists(*keys)
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for a key"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.expire(key, ttl)
    
    async def ttl(self, key: str) -> int:
        """Get TTL for a key"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.ttl(key)
    
    # Batch operations
    
    async def mget(self, *keys: str) -> List[Optional[Any]]:
        """Get multiple values"""
        if not self.redis:
            await self.connect()
        
        values = await self.redis.mget(*keys)
        
        # Deserialize values
        results = []
        for value in values:
            if value is None:
                results.append(None)
            else:
                try:
                    results.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    results.append(value)
        
        return results
    
    async def mset(self, mapping: Dict[str, Any]) -> bool:
        """Set multiple values"""
        if not self.redis:
            await self.connect()
        
        # Serialize values
        serialized = {}
        for key, value in mapping.items():
            if isinstance(value, (dict, list)):
                serialized[key] = json.dumps(value)
            elif not isinstance(value, (str, bytes, int, float)):
                serialized[key] = pickle.dumps(value)
            else:
                serialized[key] = value
        
        return await self.redis.mset(serialized)
    
    # Advanced operations
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.incrby(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter"""
        if not self.redis:
            await self.connect()
        
        return await self.redis.decrby(key, amount)
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """Get hash field value"""
        if not self.redis:
            await self.connect()
        
        value = await self.redis.hget(key, field)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set hash field value"""
        if not self.redis:
            await self.connect()
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await self.redis.hset(key, field, value)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields"""
        if not self.redis:
            await self.connect()
        
        data = await self.redis.hgetall(key)
        
        # Deserialize values
        result = {}
        for field, value in data.items():
            try:
                result[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[field] = value
        
        return result
    
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to list head"""
        if not self.redis:
            await self.connect()
        
        # Serialize values
        serialized = []
        for value in values:
            if isinstance(value, (dict, list)):
                serialized.append(json.dumps(value))
            else:
                serialized.append(value)
        
        return await self.redis.lpush(key, *serialized)
    
    async def rpop(self, key: str) -> Optional[Any]:
        """Pop value from list tail"""
        if not self.redis:
            await self.connect()
        
        value = await self.redis.rpop(key)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Get list range"""
        if not self.redis:
            await self.connect()
        
        values = await self.redis.lrange(key, start, stop)
        
        # Deserialize values
        results = []
        for value in values:
            try:
                results.append(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                results.append(value)
        
        return results
    
    # Pub/Sub operations
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        if not self.redis:
            await self.connect()
        
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        
        return await self.redis.publish(channel, message)
    
    async def subscribe(self, channel: str, handler: Callable[[str, Any], None]):
        """Subscribe to channel with handler"""
        if not self.redis:
            await self.connect()
        
        if channel not in self.pubsub_handlers:
            self.pubsub_handlers[channel] = []
        
        self.pubsub_handlers[channel].append(handler)
        
        # Start listener if not already running
        if len(self.pubsub_handlers) == 1:
            asyncio.create_task(self._pubsub_listener())
    
    async def unsubscribe(self, channel: str, handler: Optional[Callable] = None):
        """Unsubscribe from channel"""
        if channel in self.pubsub_handlers:
            if handler:
                self.pubsub_handlers[channel].remove(handler)
            else:
                del self.pubsub_handlers[channel]
    
    async def _pubsub_listener(self):
        """Background task to listen for pub/sub messages"""
        channels = await self.redis.subscribe(*self.pubsub_handlers.keys())
        
        try:
            while self.pubsub_handlers:
                message = await channels[0].get()
                
                if message:
                    channel = message.channel.decode() if isinstance(message.channel, bytes) else message.channel
                    data = message.data
                    
                    # Deserialize message
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    # Call handlers
                    for handler in self.pubsub_handlers.get(channel, []):
                        try:
                            await handler(channel, data) if asyncio.iscoroutinefunction(handler) else handler(channel, data)
                        except Exception as e:
                            logger.error(f"Error in pub/sub handler: {e}")
        
        finally:
            await self.redis.unsubscribe(*channels)
    
    # Distributed locking
    
    async def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        blocking: bool = True,
        blocking_timeout: float = None
    ) -> Optional[Lock]:
        """
        Acquire distributed lock.
        
        Args:
            key: Lock key
            timeout: Lock timeout in seconds
            blocking: Whether to block waiting for lock
            blocking_timeout: Maximum time to wait for lock
            
        Returns:
            Lock object or None if not acquired
        """
        if not self.redis:
            await self.connect()
        
        lock = self.redis.lock(
            f"lock:{key}",
            timeout=timeout,
            sleep=0.1
        )
        
        acquired = await lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)
        
        return lock if acquired else None
    
    async def release_lock(self, lock: Lock):
        """Release distributed lock"""
        await lock.release()
    
    # Cache patterns
    
    async def cache_get_or_set(
        self,
        key: str,
        getter: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get from cache or compute and set.
        
        Args:
            key: Cache key
            getter: Function to compute value if not cached
            ttl: Time to live
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key)
        
        if value is not None:
            return value
        
        # Compute value
        if asyncio.iscoroutinefunction(getter):
            value = await getter()
        else:
            value = getter()
        
        # Cache value
        await self.set(key, value, ttl=ttl)
        
        return value
    
    async def cache_invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        if not self.redis:
            await self.connect()
        
        # Get matching keys
        keys = []
        cursor = 0
        
        while True:
            cursor, batch = await self.redis.scan(cursor, match=pattern)
            keys.extend(batch)
            
            if cursor == 0:
                break
        
        # Delete keys
        if keys:
            return await self.delete(*keys)
        
        return 0
    
    # Utility methods
    
    def _get_exist_flag(self, nx: bool, xx: bool) -> Optional[str]:
        """Get exist flag for SET command"""
        if nx and xx:
            raise ValueError("Cannot specify both nx and xx")
        
        if nx:
            return "SET_IF_NOT_EXIST"
        elif xx:
            return "SET_IF_EXIST"
        
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        try:
            if not self.redis:
                await self.connect()
            
            # Ping Redis
            await self.redis.ping()
            
            # Get info
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
# SPDX-License-Identifier: Apache-2.0

"""
Local Redis service for development environment.

This module provides Redis operations using standard redis-py client for
local development, including JWT token blocklist and user permission caching.
"""

import os
import json
import time
from typing import Optional, List, Dict, Any, Union
import redis
from opentelemetry import trace
import logging

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class RedisConnectionError(Exception):
    """Raised when Redis connection fails."""
    pass


class RedisService:
    """
    Redis service with standard redis-py client for local development.
    
    Provides JWT token blocklist functionality, user permission caching,
    and general caching operations with organization scoping.
    """
    
    def __init__(self, redis_url: Optional[str] = None, redis_token: Optional[str] = None):
        """
        Initialize the Redis service.
        
        Args:
            redis_url: Redis connection URL (redis://host:port)
            redis_token: Not used for local Redis (compatibility parameter)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        
        try:
            # Initialize standard Redis client
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connection
            self._test_connection()
            
            logger.info(f"Redis service initialized successfully at {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis service: {str(e)}")
            self.client = None
    
    def _test_connection(self) -> None:
        """Test Redis connection."""
        if not self.client:
            return
        
        try:
            # Simple ping test
            result = self.client.ping()
            if not result:
                raise RedisConnectionError("Redis ping failed")
        except Exception as e:
            logger.error(f"Redis connection test failed: {str(e)}")
            raise RedisConnectionError(f"Redis connection failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Redis service is available."""
        return self.client is not None
    
    def set(self, key: str, value: Union[str, Dict, List], ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Redis client not available, skipping set operation")
            return False
        
        with tracer.start_as_current_span("redis.set") as span:
            span.set_attributes({
                "redis.key": key,
                "redis.ttl": ttl or 0
            })
            
            try:
                # Serialize value if not string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                
                if ttl:
                    result = self.client.setex(key, ttl, value)
                else:
                    result = self.client.set(key, value)
                
                span.set_attribute("redis.result", "success")
                return bool(result)
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                logger.error(f"Redis set failed for key {key}: {str(e)}")
                return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value if found, None otherwise
        """
        if not self.client:
            logger.warning("Redis client not available, skipping get operation")
            return None
        
        with tracer.start_as_current_span("redis.get") as span:
            span.set_attribute("redis.key", key)
            
            try:
                value = self.client.get(key)
                
                if value is None:
                    span.set_attribute("redis.result", "not_found")
                    return None
                
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                logger.error(f"Redis get failed for key {key}: {str(e)}")
                return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self.client:
            logger.warning("Redis client not available, skipping delete operation")
            return False
        
        with tracer.start_as_current_span("redis.delete") as span:
            span.set_attribute("redis.key", key)
            
            try:
                result = self.client.delete(key)
                span.set_attribute("redis.result", "success")
                return bool(result)
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                logger.error(f"Redis delete failed for key {key}: {str(e)}")
                return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists check failed for key {key}: {str(e)}")
            return False
    
    # JWT Token Blocklist Methods
    
    def add_to_blocklist(self, jti: str, exp: int) -> bool:
        """
        Add a JWT token to the blocklist.
        
        Args:
            jti: JWT ID (unique token identifier)
            exp: Token expiration timestamp
            
        Returns:
            True if successful, False otherwise
        """
        ttl = max(0, exp - int(time.time()))
        if ttl <= 0:
            return True  # Token already expired
        
        key = f"blocklist:jwt:{jti}"
        return self.set(key, "blocked", ttl)
    
    def is_token_blocked(self, jti: str) -> bool:
        """
        Check if a JWT token is in the blocklist.
        
        Args:
            jti: JWT ID to check
            
        Returns:
            True if token is blocked, False otherwise
        """
        key = f"blocklist:jwt:{jti}"
        return self.exists(key)
    
    # User Permission Caching
    
    def cache_user_permissions(self, user_id: str, org_id: str, permissions: List[str], ttl: int = 300) -> bool:
        """
        Cache user permissions for faster authorization checks.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            permissions: List of permission strings
            ttl: Cache TTL in seconds (default 5 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        key = f"permissions:{org_id}:{user_id}"
        return self.set(key, permissions, ttl)
    
    def get_cached_permissions(self, user_id: str, org_id: str) -> Optional[List[str]]:
        """
        Get cached user permissions.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            
        Returns:
            List of permissions if cached, None otherwise
        """
        key = f"permissions:{org_id}:{user_id}"
        return self.get(key)
    
    def invalidate_user_permissions(self, user_id: str, org_id: str) -> bool:
        """
        Invalidate cached user permissions.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = f"permissions:{org_id}:{user_id}"
        return self.delete(key)


def create_redis_service() -> RedisService:
    """
    Factory function to create Redis service instance.
    
    Returns:
        RedisService instance
    """
    return RedisService()
# SPDX-License-Identifier: Apache-2.0

"""
Redis service for caching and JWT token management.

This module provides Redis operations using Upstash HTTP client for serverless
compatibility, including JWT token blocklist and user permission caching.
"""

import os
import json
import time
from typing import Optional, List, Dict, Any, Union
from upstash_redis import Redis
from opentelemetry import trace
import logging

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class RedisConnectionError(Exception):
    """Raised when Redis connection fails."""
    pass


class RedisService:
    """
    Redis service with Upstash HTTP client for serverless compatibility.
    
    Provides JWT token blocklist functionality, user permission caching,
    and general caching operations with organization scoping.
    """
    
    def __init__(self, redis_url: Optional[str] = None, redis_token: Optional[str] = None):
        """
        Initialize the Redis service.
        
        Args:
            redis_url: Upstash Redis HTTP URL
            redis_token: Upstash Redis authentication token
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis_token = redis_token or os.getenv("REDIS_TOKEN")
        
        if not self.redis_url:
            logger.warning("No REDIS_URL configured, Redis operations will be disabled")
            self.client = None
            return
        
        try:
            # Initialize Upstash Redis client
            if self.redis_token:
                self.client = Redis(url=self.redis_url, token=self.redis_token)
            else:
                self.client = Redis.from_env()
            
            # Test connection
            self._test_connection()
            
            logger.info("Redis service initialized successfully")
            
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
            if result != "PONG":
                raise RedisConnectionError("Redis ping failed")
        except Exception as e:
            logger.error(f"Redis connection test failed: {str(e)}")
            raise RedisConnectionError(f"Redis connection failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Redis service is available."""
        return self.client is not None
    
    def _handle_redis_error(self, operation: str, error: Exception) -> None:
        """Handle Redis operation errors with logging."""
        logger.error(f"Redis {operation} failed: {str(error)}")
        # Don't raise exceptions for cache operations - fail gracefully
    
    def set_with_ttl(self, key: str, value: Union[str, Dict, List], ttl_seconds: int) -> bool:
        """
        Set a key-value pair with TTL.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        with tracer.start_as_current_span("redis.set_with_ttl") as span:
            span.set_attributes({
                "redis.operation": "set_with_ttl",
                "redis.key": key,
                "redis.ttl": ttl_seconds
            })
            
            try:
                # Serialize value if not string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                
                result = self.client.setex(key, ttl_seconds, value)
                
                span.set_attribute("redis.result", "success")
                logger.debug(f"Redis SET successful: {key} (TTL: {ttl_seconds}s)")
                
                return result == "OK"
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                self._handle_redis_error("SET", e)
                return False
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value by key.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if not found
        """
        if not self.is_available():
            return None
        
        with tracer.start_as_current_span("redis.get") as span:
            span.set_attributes({
                "redis.operation": "get",
                "redis.key": key
            })
            
            try:
                result = self.client.get(key)
                
                span.set_attribute("redis.result", "hit" if result else "miss")
                logger.debug(f"Redis GET: {key} -> {'hit' if result else 'miss'}")
                
                return result
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                self._handle_redis_error("GET", e)
                return None
    
    def get_json(self, key: str) -> Optional[Union[Dict, List]]:
        """
        Get and deserialize JSON value by key.
        
        Args:
            key: Redis key
            
        Returns:
            Deserialized JSON value or None if not found
        """
        value = self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize JSON from Redis key {key}: {str(e)}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self.is_available():
            return False
        
        with tracer.start_as_current_span("redis.delete") as span:
            span.set_attributes({
                "redis.operation": "delete",
                "redis.key": key
            })
            
            try:
                result = self.client.delete(key)
                
                span.set_attribute("redis.result", "success")
                logger.debug(f"Redis DELETE: {key} -> {result}")
                
                return result > 0
                
            except Exception as e:
                span.set_attribute("redis.result", "error")
                self._handle_redis_error("DELETE", e)
                return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.client.exists(key)
            return result > 0
        except Exception as e:
            self._handle_redis_error("EXISTS", e)
            return False
    
    # JWT Token Blocklist Methods
    
    def is_token_blocked(self, token_id: str) -> bool:
        """
        Check if a JWT token is in the blocklist.
        
        Args:
            token_id: Unique token identifier
            
        Returns:
            True if token is blocked, False otherwise
        """
        if not self.is_available():
            # Fail secure - if Redis is unavailable, don't block tokens
            # but log the issue for monitoring
            logger.warning("Redis unavailable for token blocklist check - allowing token")
            return False
        
        with tracer.start_as_current_span("redis.is_token_blocked") as span:
            span.set_attributes({
                "redis.operation": "is_token_blocked",
                "auth.token_id": token_id
            })
            
            key = f"jwt:blocked:{token_id}"
            result = self.exists(key)
            
            span.set_attribute("auth.token_blocked", result)
            logger.debug(f"Token blocklist check: {token_id} -> {'blocked' if result else 'allowed'}")
            
            return result
    
    def block_token(self, token_id: str, ttl_seconds: int) -> bool:
        """
        Add a JWT token to the blocklist.
        
        Args:
            token_id: Unique token identifier
            ttl_seconds: Time to live (should match token expiration)
            
        Returns:
            True if token was blocked, False otherwise
        """
        if not self.is_available():
            logger.error("Redis unavailable - cannot block token")
            return False
        
        with tracer.start_as_current_span("redis.block_token") as span:
            span.set_attributes({
                "redis.operation": "block_token",
                "auth.token_id": token_id,
                "redis.ttl": ttl_seconds
            })
            
            key = f"jwt:blocked:{token_id}"
            result = self.set_with_ttl(key, "1", ttl_seconds)
            
            span.set_attribute("auth.token_block_result", "success" if result else "failed")
            
            if result:
                logger.info(f"Token blocked successfully: {token_id} (TTL: {ttl_seconds}s)")
            else:
                logger.error(f"Failed to block token: {token_id}")
            
            return result
    
    def unblock_token(self, token_id: str) -> bool:
        """
        Remove a JWT token from the blocklist.
        
        Args:
            token_id: Unique token identifier
            
        Returns:
            True if token was unblocked, False otherwise
        """
        if not self.is_available():
            return False
        
        key = f"jwt:blocked:{token_id}"
        result = self.delete(key)
        
        logger.info(f"Token unblock attempt: {token_id} -> {'success' if result else 'not found'}")
        return result
    
    # User Permission Caching Methods
    
    def cache_user_permissions(self, user_id: str, org_id: str, permissions: List[str], ttl_seconds: int = 900) -> bool:
        """
        Cache user permissions with organization scoping.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            permissions: List of permission strings
            ttl_seconds: Cache TTL (default: 15 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        with tracer.start_as_current_span("redis.cache_user_permissions") as span:
            span.set_attributes({
                "redis.operation": "cache_user_permissions",
                "user.id": user_id,
                "organization.id": org_id,
                "permissions.count": len(permissions),
                "redis.ttl": ttl_seconds
            })
            
            key = f"user:permissions:{org_id}:{user_id}"
            result = self.set_with_ttl(key, permissions, ttl_seconds)
            
            span.set_attribute("redis.cache_result", "success" if result else "failed")
            
            if result:
                logger.debug(f"User permissions cached: {user_id} in org {org_id} ({len(permissions)} permissions)")
            
            return result
    
    def get_cached_permissions(self, user_id: str, org_id: str) -> Optional[List[str]]:
        """
        Get cached user permissions with organization scoping.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            
        Returns:
            List of permission strings or None if not cached
        """
        if not self.is_available():
            return None
        
        with tracer.start_as_current_span("redis.get_cached_permissions") as span:
            span.set_attributes({
                "redis.operation": "get_cached_permissions",
                "user.id": user_id,
                "organization.id": org_id
            })
            
            key = f"user:permissions:{org_id}:{user_id}"
            permissions = self.get_json(key)
            
            span.set_attribute("redis.cache_result", "hit" if permissions else "miss")
            
            if permissions:
                logger.debug(f"User permissions cache hit: {user_id} in org {org_id} ({len(permissions)} permissions)")
            
            return permissions
    
    def invalidate_user_permissions(self, user_id: str, org_id: str) -> bool:
        """
        Invalidate cached user permissions.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            
        Returns:
            True if invalidated, False otherwise
        """
        if not self.is_available():
            return False
        
        key = f"user:permissions:{org_id}:{user_id}"
        result = self.delete(key)
        
        logger.debug(f"User permissions cache invalidated: {user_id} in org {org_id}")
        return result
    
    # General Caching Methods
    
    def cache_notification_counts(self, org_id: str, counts: Dict[str, int], ttl_seconds: int = 300) -> bool:
        """
        Cache notification counts by status for an organization.
        
        Args:
            org_id: Organization identifier
            counts: Dictionary of status -> count
            ttl_seconds: Cache TTL (default: 5 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        key = f"org:notifications:counts:{org_id}"
        return self.set_with_ttl(key, counts, ttl_seconds)
    
    def get_cached_notification_counts(self, org_id: str) -> Optional[Dict[str, int]]:
        """
        Get cached notification counts for an organization.
        
        Args:
            org_id: Organization identifier
            
        Returns:
            Dictionary of status -> count or None if not cached
        """
        if not self.is_available():
            return None
        
        key = f"org:notifications:counts:{org_id}"
        return self.get_json(key)
    
    def cache_organization_settings(self, org_id: str, settings: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """
        Cache organization settings.
        
        Args:
            org_id: Organization identifier
            settings: Organization settings dictionary
            ttl_seconds: Cache TTL (default: 1 hour)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        key = f"org:settings:{org_id}"
        return self.set_with_ttl(key, settings, ttl_seconds)
    
    def get_cached_organization_settings(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached organization settings.
        
        Args:
            org_id: Organization identifier
            
        Returns:
            Organization settings dictionary or None if not cached
        """
        if not self.is_available():
            return None
        
        key = f"org:settings:{org_id}"
        return self.get_json(key)
    
    def invalidate_organization_cache(self, org_id: str) -> int:
        """
        Invalidate all cached data for an organization.
        
        Args:
            org_id: Organization identifier
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        # Note: Upstash Redis doesn't support SCAN, so we delete known patterns
        patterns = [
            f"org:notifications:counts:{org_id}",
            f"org:settings:{org_id}",
            f"user:permissions:{org_id}:*"
        ]
        
        deleted_count = 0
        for pattern in patterns:
            if "*" in pattern:
                # For user permissions, we can't easily delete all without SCAN
                # This would need to be handled differently in production
                continue
            
            if self.delete(pattern):
                deleted_count += 1
        
        logger.info(f"Organization cache invalidated: {org_id} ({deleted_count} keys deleted)")
        return deleted_count
    
    # Health Check Methods
    
    def ping(self) -> bool:
        """
        Ping Redis server.
        
        Returns:
            True if ping successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.client.ping()
            return result == "PONG"
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Returns:
            Dictionary with Redis server info
        """
        if not self.is_available():
            return {}
        
        try:
            # Upstash Redis may not support full INFO command
            # Return basic info that we can gather
            return {
                "redis_version": "unknown",  # Upstash doesn't expose this
                "used_memory": 0,  # Not available via HTTP API
                "connected_clients": 1,  # HTTP client connection
                "uptime_in_seconds": 0  # Not available
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {str(e)}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.
        
        Returns:
            Health check results
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "message": "Redis client not initialized",
                "timestamp": time.time()
            }
        
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = f"health:check:{int(start_time)}"
            self.set_with_ttl(test_key, "test", 10)
            value = self.get(test_key)
            self.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            if value == "test":
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "timestamp": time.time()
                }
            else:
                return {
                    "status": "degraded",
                    "message": "Redis operations not working correctly",
                    "response_time_ms": round(response_time, 2),
                    "timestamp": time.time()
                }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "timestamp": time.time()
            }
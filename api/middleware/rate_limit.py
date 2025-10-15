# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Rate limiting middleware for API endpoints.
Provides configurable rate limiting with Redis backend.
"""

from functools import wraps
from flask import request, jsonify, g
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import time
import hashlib
import logging

from services.hal import HalFormatter

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_service, hal_formatter: HalFormatter):
        self.redis_service = redis_service
        self.hal_formatter = hal_formatter
    
    def get_client_identifier(self, user_context=None) -> str:
        """
        Get unique identifier for rate limiting.
        
        Args:
            user_context: Optional user context
            
        Returns:
            Unique client identifier
        """
        if user_context:
            # Use user ID for authenticated requests
            return f"user:{user_context.user_id}"
        else:
            # Use IP address for anonymous requests
            ip_address = request.remote_addr or 'unknown'
            user_agent = request.headers.get('User-Agent', '')
            
            # Create hash of IP + User-Agent for better uniqueness
            identifier_string = f"{ip_address}:{user_agent}"
            identifier_hash = hashlib.md5(identifier_string.encode()).hexdigest()
            return f"ip:{identifier_hash}"
    
    def get_rate_limit_key(
        self, 
        identifier: str, 
        endpoint: str, 
        window_seconds: int
    ) -> str:
        """
        Generate Redis key for rate limiting.
        
        Args:
            identifier: Client identifier
            endpoint: Endpoint identifier
            window_seconds: Time window in seconds
            
        Returns:
            Redis key for rate limiting
        """
        window_start = int(time.time()) // window_seconds
        return f"rate_limit:{identifier}:{endpoint}:{window_start}"
    
    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Client identifier
            endpoint: Endpoint identifier
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Dictionary with rate limit status
        """
        key = self.get_rate_limit_key(identifier, endpoint, window_seconds)
        
        try:
            # Get current count
            current_count = self.redis_service.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Check if limit exceeded
            if current_count >= limit:
                # Calculate reset time
                window_start = int(time.time()) // window_seconds
                reset_time = (window_start + 1) * window_seconds
                
                return {
                    'allowed': False,
                    'limit': limit,
                    'remaining': 0,
                    'reset_time': reset_time,
                    'retry_after': reset_time - int(time.time())
                }
            
            # Increment counter
            new_count = current_count + 1
            self.redis_service.set_with_ttl(key, str(new_count), window_seconds)
            
            # Calculate reset time
            window_start = int(time.time()) // window_seconds
            reset_time = (window_start + 1) * window_seconds
            
            return {
                'allowed': True,
                'limit': limit,
                'remaining': limit - new_count,
                'reset_time': reset_time,
                'retry_after': 0
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open - allow request if Redis is unavailable
            return {
                'allowed': True,
                'limit': limit,
                'remaining': limit - 1,
                'reset_time': int(time.time()) + window_seconds,
                'retry_after': 0
            }
    
    def add_rate_limit_headers(self, response, rate_limit_info: Dict[str, Any]):
        """
        Add rate limit headers to response.
        
        Args:
            response: Flask response object
            rate_limit_info: Rate limit information
        """
        response.headers['X-RateLimit-Limit'] = str(rate_limit_info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rate_limit_info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(rate_limit_info['reset_time'])
        
        if rate_limit_info['retry_after'] > 0:
            response.headers['Retry-After'] = str(rate_limit_info['retry_after'])
        
        return response


def rate_limit(
    limit: int,
    window_seconds: int = 3600,
    endpoint: Optional[str] = None,
    per_user: bool = True
):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
        endpoint: Custom endpoint identifier
        per_user: Whether to apply limit per user (vs per IP)
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limiter from app
            from flask import current_app
            
            if not hasattr(current_app, 'redis_service'):
                # No Redis service available, skip rate limiting
                return f(*args, **kwargs)
            
            rate_limiter = RateLimiter(
                current_app.redis_service,
                current_app.hal_formatter
            )
            
            # Get client identifier
            user_context = getattr(g, 'user_context', None) if per_user else None
            identifier = rate_limiter.get_client_identifier(user_context)
            
            # Use custom endpoint name or derive from function
            endpoint_name = endpoint or f"{request.endpoint or f.__name__}"
            
            # Check rate limit
            rate_limit_info = rate_limiter.check_rate_limit(
                identifier,
                endpoint_name,
                limit,
                window_seconds
            )
            
            # Log rate limit check
            logger.debug(
                "Rate limit check",
                extra={
                    'identifier': identifier,
                    'endpoint': endpoint_name,
                    'limit': limit,
                    'remaining': rate_limit_info['remaining'],
                    'allowed': rate_limit_info['allowed']
                }
            )
            
            # Check if rate limit exceeded
            if not rate_limit_info['allowed']:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        'identifier': identifier,
                        'endpoint': endpoint_name,
                        'limit': limit,
                        'retry_after': rate_limit_info['retry_after']
                    }
                )
                
                error_response = rate_limiter.hal_formatter.builder.build_error_response(
                    "rate-limit-exceeded",
                    "Rate Limit Exceeded",
                    429,
                    f"Rate limit of {limit} requests per {window_seconds} seconds exceeded",
                    request.path
                )
                
                response = jsonify(error_response)
                response.status_code = 429
                rate_limiter.add_rate_limit_headers(response, rate_limit_info)
                return response
            
            # Execute the route handler
            response = f(*args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(response, 'headers'):
                rate_limiter.add_rate_limit_headers(response, rate_limit_info)
            
            return response
        
        return decorated_function
    return decorator


# Predefined rate limit decorators for common use cases
def rate_limit_strict(f: Callable) -> Callable:
    """Strict rate limit: 100 requests per hour."""
    return rate_limit(100, 3600)(f)


def rate_limit_moderate(f: Callable) -> Callable:
    """Moderate rate limit: 1000 requests per hour."""
    return rate_limit(1000, 3600)(f)


def rate_limit_lenient(f: Callable) -> Callable:
    """Lenient rate limit: 5000 requests per hour."""
    return rate_limit(5000, 3600)(f)


def rate_limit_auth(f: Callable) -> Callable:
    """Rate limit for authentication endpoints: 10 requests per 15 minutes."""
    return rate_limit(10, 900, per_user=False)(f)


def rate_limit_api_key(f: Callable) -> Callable:
    """Rate limit for API key endpoints: 10000 requests per hour."""
    return rate_limit(10000, 3600)(f)
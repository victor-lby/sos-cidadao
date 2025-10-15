# SPDX-License-Identifier: Apache-2.0

"""
Authentication middleware for JWT token validation and user context extraction.

This module provides Flask middleware for validating JWT tokens, checking
blocklists, and building user context for request processing.
"""

from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Dict, Any, Callable
from opentelemetry import trace
import logging

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    JWT authentication middleware for Flask applications.
    
    Handles token extraction, validation, blocklist checking, and user context
    building for protected endpoints.
    """
    
    def __init__(self, auth_service, redis_service):
        """
        Initialize the authentication middleware.
        
        Args:
            auth_service: JWT authentication service
            redis_service: Redis service for token blocklist
        """
        self.auth_service = auth_service
        self.redis_service = redis_service
    
    def extract_token_from_request(self) -> Optional[str]:
        """
        Extract JWT token from request headers.
        
        Returns:
            JWT token string or None if not found
        """
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header:
            return None
        
        # Handle "Bearer <token>" format
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Handle direct token (less common)
        return auth_header if auth_header else None
    
    def is_token_blocked(self, token: str) -> bool:
        """
        Check if token is in the Redis blocklist.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is blocked, False otherwise
        """
        try:
            token_id = self.auth_service.extract_token_id(token)
            return self.redis_service.is_token_blocked(token_id)
        except Exception as e:
            logger.error(f"Error checking token blocklist: {str(e)}")
            # Fail secure - treat as blocked if we can't check
            return True
    
    def build_user_context(self, token_payload: Dict[str, Any], request_info: Dict[str, Any]):
        """
        Build user context from validated token payload and request information.
        
        Args:
            token_payload: Decoded JWT payload
            request_info: Request metadata (IP, user agent, etc.)
            
        Returns:
            UserContext object for request processing
        """
        from models.entities import UserContext
        
        return UserContext(
            user_id=token_payload["sub"],
            org_id=token_payload["org_id"],
            email=token_payload.get("email"),
            name=token_payload.get("name"),
            permissions=token_payload.get("permissions", []),
            token_payload=token_payload,
            ip_address=request_info.get("ip_address"),
            user_agent=request_info.get("user_agent"),
            session_id=request_info.get("session_id")
        )
    
    def get_request_info(self) -> Dict[str, Any]:
        """
        Extract request metadata for user context.
        
        Returns:
            Dictionary with request information
        """
        return {
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', ''),
            "session_id": request.headers.get('X-Session-ID'),
            "request_id": request.headers.get('X-Request-ID')
        }


def require_auth(auth_middleware: AuthMiddleware) -> Callable:
    """
    Decorator to require JWT authentication for Flask routes.
    
    Args:
        auth_middleware: Configured AuthMiddleware instance
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            with tracer.start_as_current_span("auth.middleware.validate_request") as span:
                span.set_attribute("auth.operation", "validate_request")
                
                # Extract token from request
                token = auth_middleware.extract_token_from_request()
                if not token:
                    span.set_attribute("auth.result", "missing_token")
                    logger.warning("Authentication failed: missing token")
                    return jsonify({
                        "type": "https://api.sos-cidadao.org/problems/authentication-required",
                        "title": "Authentication Required",
                        "status": 401,
                        "detail": "Missing authorization token",
                        "instance": request.path
                    }), 401
                
                # Check if token is blocked
                if auth_middleware.is_token_blocked(token):
                    span.set_attribute("auth.result", "token_blocked")
                    logger.warning("Authentication failed: token is blocked")
                    return jsonify({
                        "type": "https://api.sos-cidadao.org/problems/token-revoked",
                        "title": "Token Revoked",
                        "status": 401,
                        "detail": "Token has been revoked",
                        "instance": request.path
                    }), 401
                
                # Validate token
                try:
                    from services.auth import TokenValidationError
                    
                    logger.info("Validating token...")
                    token_payload = auth_middleware.auth_service.validate_token(token, "access")
                    logger.info(f"Token validated successfully, payload keys: {list(token_payload.keys())}")
                    
                    # Build user context
                    logger.info("Getting request info...")
                    request_info = auth_middleware.get_request_info()
                    logger.info(f"Request info: {request_info}")
                    
                    logger.info("Building user context...")
                    user_context = auth_middleware.build_user_context(token_payload, request_info)
                    logger.info(f"User context built successfully")
                    
                    # Store user context in Flask's g object
                    g.user_context = user_context
                    
                    span.set_attributes({
                        "auth.result": "success",
                        "user.id": user_context.user_id,
                        "organization.id": user_context.org_id
                    })
                    
                    logger.debug(
                        "Authentication successful",
                        extra={
                            "user_id": user_context.user_id,
                            "organization_id": user_context.org_id,
                            "ip_address": user_context.ip_address
                        }
                    )
                    
                    # Call the protected route with user context
                    return f(user_context, *args, **kwargs)
                    
                except TokenValidationError as e:
                    span.set_attribute("auth.result", "invalid_token")
                    logger.warning(f"Authentication failed: {str(e)}")
                    return jsonify({
                        "type": "https://api.sos-cidadao.org/problems/invalid-token",
                        "title": "Invalid Token",
                        "status": 401,
                        "detail": str(e),
                        "instance": request.path
                    }), 401
                
                except Exception as e:
                    span.set_attribute("auth.result", "error")
                    logger.error(f"Authentication error: {str(e)}")
                    return jsonify({
                        "type": "https://api.sos-cidadao.org/problems/authentication-error",
                        "title": "Authentication Error",
                        "status": 500,
                        "detail": "Internal authentication error",
                        "instance": request.path
                    }), 500
        
        return decorated_function
    return decorator


def require_permission(permission: str, auth_middleware: AuthMiddleware) -> Callable:
    """
    Decorator to require specific permission for Flask routes.
    
    Args:
        permission: Required permission string
        auth_middleware: Configured AuthMiddleware instance
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @require_auth(auth_middleware)
        def decorated_function(user_context, *args, **kwargs):
            with tracer.start_as_current_span("auth.middleware.check_permission") as span:
                span.set_attributes({
                    "auth.operation": "check_permission",
                    "auth.required_permission": permission,
                    "user.id": user_context.user_id,
                    "organization.id": user_context.org_id
                })
                
                if permission not in user_context.permissions:
                    span.set_attribute("auth.permission_result", "denied")
                    logger.warning(
                        f"Authorization failed: missing permission '{permission}'",
                        extra={
                            "user_id": user_context.user_id,
                            "organization_id": user_context.org_id,
                            "required_permission": permission,
                            "user_permissions": user_context.permissions
                        }
                    )
                    return jsonify({
                        "type": "https://api.sos-cidadao.org/problems/insufficient-permissions",
                        "title": "Insufficient Permissions",
                        "status": 403,
                        "detail": f"Missing required permission: {permission}",
                        "instance": request.path
                    }), 403
                
                span.set_attribute("auth.permission_result", "granted")
                logger.debug(
                    f"Authorization successful: permission '{permission}' granted",
                    extra={
                        "user_id": user_context.user_id,
                        "organization_id": user_context.org_id,
                        "required_permission": permission
                    }
                )
                
                return f(user_context, *args, **kwargs)
        
        return decorated_function
    return decorator


def optional_auth(auth_middleware: AuthMiddleware) -> Callable:
    """
    Decorator for optional authentication (user context if token present).
    
    Args:
        auth_middleware: Configured AuthMiddleware instance
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_context = None
            
            # Try to extract and validate token if present
            token = auth_middleware.extract_token_from_request()
            if token and not auth_middleware.is_token_blocked(token):
                try:
                    token_payload = auth_middleware.auth_service.validate_token(token, "access")
                    request_info = auth_middleware.get_request_info()
                    user_context = auth_middleware.build_user_context(token_payload, request_info)
                    g.user_context = user_context
                except Exception:
                    # Ignore authentication errors for optional auth
                    pass
            
            return f(user_context, *args, **kwargs)
        
        return decorated_function
    return decorator
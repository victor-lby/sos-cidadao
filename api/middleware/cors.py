# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
CORS (Cross-Origin Resource Sharing) middleware for frontend integration.
Configures appropriate CORS headers for Vue 3 frontend communication.
"""

from flask import Flask, request, make_response
from typing import List, Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class CORSMiddleware:
    """CORS middleware for Flask applications."""
    
    def __init__(
        self,
        app: Flask,
        allowed_origins: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 86400  # 24 hours
    ):
        """
        Initialize CORS middleware.
        
        Args:
            app: Flask application
            allowed_origins: List of allowed origins
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed headers
            expose_headers: List of headers to expose to client
            allow_credentials: Whether to allow credentials
            max_age: Preflight cache duration in seconds
        """
        self.app = app
        self.allowed_origins = allowed_origins or self._get_default_origins()
        self.allowed_methods = allowed_methods or [
            'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'
        ]
        self.allowed_headers = allowed_headers or [
            'Accept',
            'Accept-Language',
            'Authorization',
            'Content-Language',
            'Content-Type',
            'X-Requested-With',
            'X-Session-ID',
            'X-Request-ID',
            'X-Trace-ID'
        ]
        self.expose_headers = expose_headers or [
            'Content-Length',
            'Content-Type',
            'X-Request-ID',
            'X-Trace-ID',
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset'
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        self.register_cors_handlers()
    
    def _get_default_origins(self) -> List[str]:
        """Get default allowed origins from environment."""
        origins = []
        
        # Development origins
        if os.getenv('ENVIRONMENT') == 'development':
            origins.extend([
                'http://localhost:3000',
                'http://localhost:5173',  # Vite default
                'http://127.0.0.1:3000',
                'http://127.0.0.1:5173'
            ])
        
        # Production origins from environment
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            origins.append(frontend_url)
        
        # Vercel preview deployments
        vercel_url = os.getenv('VERCEL_URL')
        if vercel_url:
            origins.append(f"https://{vercel_url}")
        
        # Custom origins from environment
        custom_origins = os.getenv('CORS_ALLOWED_ORIGINS')
        if custom_origins:
            origins.extend(custom_origins.split(','))
        
        return origins
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed.
        
        Args:
            origin: Request origin
            
        Returns:
            True if origin is allowed
        """
        if not origin:
            return False
        
        # Allow all origins in development (if configured)
        if os.getenv('CORS_ALLOW_ALL_ORIGINS', 'false').lower() == 'true':
            return True
        
        # Check exact matches
        if origin in self.allowed_origins:
            return True
        
        # Check wildcard patterns
        for allowed_origin in self.allowed_origins:
            if allowed_origin == '*':
                return True
            if allowed_origin.endswith('*'):
                prefix = allowed_origin[:-1]
                if origin.startswith(prefix):
                    return True
        
        return False
    
    def add_cors_headers(self, response, origin: Optional[str] = None):
        """
        Add CORS headers to response.
        
        Args:
            response: Flask response object
            origin: Request origin
        """
        # Set allowed origin
        if origin and self.is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
        elif '*' in self.allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        # Set other CORS headers
        if self.allow_credentials:
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        response.headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        response.headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        response.headers['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
        response.headers['Access-Control-Max-Age'] = str(self.max_age)
        
        return response
    
    def register_cors_handlers(self):
        """Register CORS handlers with Flask application."""
        
        @self.app.before_request
        def handle_preflight():
            """Handle CORS preflight requests."""
            if request.method == 'OPTIONS':
                origin = request.headers.get('Origin')
                
                if not origin or not self.is_origin_allowed(origin):
                    logger.warning(f"CORS preflight rejected for origin: {origin}")
                    return make_response('', 403)
                
                response = make_response('', 200)
                self.add_cors_headers(response, origin)
                
                logger.debug(f"CORS preflight handled for origin: {origin}")
                return response
        
        @self.app.after_request
        def add_cors_headers_to_response(response):
            """Add CORS headers to all responses."""
            origin = request.headers.get('Origin')
            
            if origin and self.is_origin_allowed(origin):
                self.add_cors_headers(response, origin)
                logger.debug(f"CORS headers added for origin: {origin}")
            elif request.method != 'OPTIONS':
                # Log rejected origins for non-preflight requests
                if origin:
                    logger.warning(f"CORS rejected for origin: {origin}")
            
            return response


def configure_cors(app: Flask, **kwargs) -> CORSMiddleware:
    """
    Configure CORS for Flask application.
    
    Args:
        app: Flask application
        **kwargs: CORS configuration options
        
    Returns:
        Configured CORSMiddleware instance
    """
    return CORSMiddleware(app, **kwargs)
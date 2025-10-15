# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Error handling middleware with structured HAL responses.
Provides centralized error handling and formatting for Flask applications.
"""

from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException
from typing import Dict, Any, Tuple
from opentelemetry import trace
import logging
import traceback

from services.hal import HalFormatter

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    """Centralized error handling middleware with HAL response formatting."""
    
    def __init__(self, app: Flask, base_url: str):
        self.app = app
        self.hal_formatter = HalFormatter(base_url)
        self.register_error_handlers()
    
    def register_error_handlers(self):
        """Register error handlers with Flask application."""
        
        @self.app.errorhandler(400)
        def handle_bad_request(error):
            return self.handle_client_error(error, "bad-request", "Bad Request")
        
        @self.app.errorhandler(401)
        def handle_unauthorized(error):
            return self.handle_client_error(error, "authentication-required", "Authentication Required")
        
        @self.app.errorhandler(403)
        def handle_forbidden(error):
            return self.handle_client_error(error, "insufficient-permissions", "Insufficient Permissions")
        
        @self.app.errorhandler(404)
        def handle_not_found(error):
            return self.handle_client_error(error, "resource-not-found", "Resource Not Found")
        
        @self.app.errorhandler(405)
        def handle_method_not_allowed(error):
            return self.handle_client_error(error, "method-not-allowed", "Method Not Allowed")
        
        @self.app.errorhandler(409)
        def handle_conflict(error):
            return self.handle_client_error(error, "resource-conflict", "Resource Conflict")
        
        @self.app.errorhandler(422)
        def handle_unprocessable_entity(error):
            return self.handle_client_error(error, "validation-error", "Validation Error")
        
        @self.app.errorhandler(429)
        def handle_too_many_requests(error):
            return self.handle_client_error(error, "rate-limit-exceeded", "Rate Limit Exceeded")
        
        @self.app.errorhandler(500)
        def handle_internal_server_error(error):
            return self.handle_server_error(error, "internal-server-error", "Internal Server Error")
        
        @self.app.errorhandler(502)
        def handle_bad_gateway(error):
            return self.handle_server_error(error, "bad-gateway", "Bad Gateway")
        
        @self.app.errorhandler(503)
        def handle_service_unavailable(error):
            return self.handle_server_error(error, "service-unavailable", "Service Unavailable")
        
        @self.app.errorhandler(504)
        def handle_gateway_timeout(error):
            return self.handle_server_error(error, "gateway-timeout", "Gateway Timeout")
        
        # Handle generic exceptions
        @self.app.errorhandler(Exception)
        def handle_generic_exception(error):
            return self.handle_unexpected_error(error)
    
    def handle_client_error(
        self, 
        error: HTTPException, 
        error_type: str, 
        title: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle client errors (4xx status codes).
        
        Args:
            error: HTTP exception
            error_type: Error type identifier
            title: Error title
            
        Returns:
            Tuple of (error response dict, status code)
        """
        with tracer.start_as_current_span("error_handler.client_error") as span:
            span.set_attributes({
                "error.type": error_type,
                "error.status": error.code,
                "http.method": request.method,
                "http.path": request.path
            })
            
            detail = str(error.description) if error.description else title
            
            logger.warning(
                f"Client error: {title}",
                extra={
                    "error_type": error_type,
                    "status_code": error.code,
                    "detail": detail,
                    "path": request.path,
                    "method": request.method,
                    "user_agent": request.headers.get('User-Agent'),
                    "ip_address": request.remote_addr
                }
            )
            
            # Use appropriate formatter method based on error type
            if error_type == "authentication-required":
                error_response = self.hal_formatter.format_authentication_error(detail, request.path)
            elif error_type == "insufficient-permissions":
                error_response = self.hal_formatter.format_authorization_error(detail, request.path)
            elif error_type == "resource-not-found":
                error_response = self.hal_formatter.format_not_found_error(detail, request.path)
            elif error_type == "resource-conflict":
                error_response = self.hal_formatter.format_conflict_error(detail, request.path)
            else:
                error_response = self.hal_formatter.builder.build_error_response(
                    error_type,
                    title,
                    error.code,
                    detail,
                    request.path
                )
            
            return error_response, error.code
    
    def handle_server_error(
        self, 
        error: HTTPException, 
        error_type: str, 
        title: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle server errors (5xx status codes).
        
        Args:
            error: HTTP exception
            error_type: Error type identifier
            title: Error title
            
        Returns:
            Tuple of (error response dict, status code)
        """
        with tracer.start_as_current_span("error_handler.server_error") as span:
            span.set_attributes({
                "error.type": error_type,
                "error.status": error.code,
                "http.method": request.method,
                "http.path": request.path
            })
            
            detail = str(error.description) if error.description else title
            
            logger.error(
                f"Server error: {title}",
                extra={
                    "error_type": error_type,
                    "status_code": error.code,
                    "detail": detail,
                    "path": request.path,
                    "method": request.method,
                    "user_agent": request.headers.get('User-Agent'),
                    "ip_address": request.remote_addr
                },
                exc_info=True
            )
            
            # Don't expose internal error details in production
            if self.app.config.get('ENV') == 'production':
                detail = "An internal server error occurred"
            
            error_response = self.hal_formatter.format_server_error(detail, request.path)
            
            return error_response, error.code
    
    def handle_unexpected_error(self, error: Exception) -> Tuple[Dict[str, Any], int]:
        """
        Handle unexpected exceptions not caught by specific handlers.
        
        Args:
            error: Unexpected exception
            
        Returns:
            Tuple of (error response dict, status code)
        """
        with tracer.start_as_current_span("error_handler.unexpected_error") as span:
            span.set_attributes({
                "error.type": "unexpected-error",
                "error.class": error.__class__.__name__,
                "http.method": request.method,
                "http.path": request.path
            })
            
            # Record exception in span
            span.record_exception(error)
            
            logger.error(
                f"Unexpected error: {error.__class__.__name__}",
                extra={
                    "error_type": "unexpected-error",
                    "error_class": error.__class__.__name__,
                    "error_message": str(error),
                    "path": request.path,
                    "method": request.method,
                    "user_agent": request.headers.get('User-Agent'),
                    "ip_address": request.remote_addr,
                    "traceback": traceback.format_exc()
                },
                exc_info=True
            )
            
            # Don't expose internal error details
            detail = "An unexpected error occurred"
            if self.app.config.get('ENV') != 'production':
                detail = f"{error.__class__.__name__}: {str(error)}"
            
            error_response = self.hal_formatter.format_server_error(detail, request.path)
            
            return error_response, 500


class CustomException(Exception):
    """Base class for custom application exceptions."""
    
    def __init__(self, message: str, status_code: int = 500, error_type: str = "application-error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class ValidationException(CustomException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, validation_errors: list = None):
        super().__init__(message, 400, "validation-error")
        self.validation_errors = validation_errors or []


class AuthenticationException(CustomException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str):
        super().__init__(message, 401, "authentication-required")


class AuthorizationException(CustomException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str):
        super().__init__(message, 403, "insufficient-permissions")


class NotFoundException(CustomException):
    """Exception for resource not found errors."""
    
    def __init__(self, message: str):
        super().__init__(message, 404, "resource-not-found")


class ConflictException(CustomException):
    """Exception for resource conflict errors."""
    
    def __init__(self, message: str):
        super().__init__(message, 409, "resource-conflict")


class ServiceUnavailableException(CustomException):
    """Exception for service unavailable errors."""
    
    def __init__(self, message: str):
        super().__init__(message, 503, "service-unavailable")


def register_custom_error_handlers(app: Flask, hal_formatter: HalFormatter):
    """
    Register handlers for custom exceptions.
    
    Args:
        app: Flask application
        hal_formatter: HAL formatter instance
    """
    
    @app.errorhandler(CustomException)
    def handle_custom_exception(error: CustomException):
        with tracer.start_as_current_span("error_handler.custom_exception") as span:
            span.set_attributes({
                "error.type": error.error_type,
                "error.status": error.status_code,
                "http.method": request.method,
                "http.path": request.path
            })
            
            logger.warning(
                f"Custom exception: {error.error_type}",
                extra={
                    "error_type": error.error_type,
                    "status_code": error.status_code,
                    "message": error.message,
                    "path": request.path,
                    "method": request.method
                }
            )
            
            # Use appropriate formatter method based on error type
            if isinstance(error, ValidationException):
                error_response = hal_formatter.format_validation_error(
                    error.message, 
                    request.path, 
                    error.validation_errors
                )
            elif isinstance(error, AuthenticationException):
                error_response = hal_formatter.format_authentication_error(error.message, request.path)
            elif isinstance(error, AuthorizationException):
                error_response = hal_formatter.format_authorization_error(error.message, request.path)
            elif isinstance(error, NotFoundException):
                error_response = hal_formatter.format_not_found_error(error.message, request.path)
            elif isinstance(error, ConflictException):
                error_response = hal_formatter.format_conflict_error(error.message, request.path)
            else:
                error_response = hal_formatter.format_server_error(error.message, request.path)
            
            return jsonify(error_response), error.status_code
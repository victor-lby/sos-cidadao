# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Request validation middleware using Pydantic models.
Provides automatic request body validation and error formatting.
"""

from functools import wraps
from flask import request, jsonify
from typing import Type, Callable, Dict, Any, List
from pydantic import BaseModel, ValidationError
from opentelemetry import trace
import logging

from services.hal import HalFormatter

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class ValidationMiddleware:
    """Middleware for request validation using Pydantic models."""
    
    def __init__(self, base_url: str):
        self.hal_formatter = HalFormatter(base_url)
    
    def format_validation_errors(self, validation_error: ValidationError) -> List[Dict[str, Any]]:
        """
        Format Pydantic validation errors for API response.
        
        Args:
            validation_error: Pydantic ValidationError
            
        Returns:
            List of formatted error dictionaries
        """
        errors = []
        
        for error in validation_error.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        return errors
    
    def validate_json_body(self, model_class: Type[BaseModel]) -> Callable:
        """
        Decorator to validate JSON request body against Pydantic model.
        
        Args:
            model_class: Pydantic model class for validation
            
        Returns:
            Decorator function
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                with tracer.start_as_current_span("validation.validate_json_body") as span:
                    span.set_attributes({
                        "validation.model": model_class.__name__,
                        "http.method": request.method,
                        "http.path": request.path
                    })
                    
                    # Check content type
                    if not request.is_json:
                        span.set_attribute("validation.result", "invalid_content_type")
                        error_response = self.hal_formatter.format_validation_error(
                            "Request must have Content-Type: application/json",
                            request.path,
                            [{
                                "field": "content-type",
                                "message": "Expected application/json",
                                "type": "content_type_error",
                                "input": request.content_type
                            }]
                        )
                        return jsonify(error_response), 400
                    
                    # Get JSON data
                    try:
                        json_data = request.get_json()
                        if json_data is None:
                            raise ValueError("No JSON data provided")
                    except Exception as e:
                        span.set_attribute("validation.result", "invalid_json")
                        error_response = self.hal_formatter.format_validation_error(
                            "Invalid JSON in request body",
                            request.path,
                            [{
                                "field": "body",
                                "message": str(e),
                                "type": "json_error",
                                "input": None
                            }]
                        )
                        return jsonify(error_response), 400
                    
                    # Validate against Pydantic model
                    try:
                        validated_data = model_class(**json_data)
                        span.set_attribute("validation.result", "success")
                        
                        logger.debug(
                            "Request validation successful",
                            extra={
                                "model": model_class.__name__,
                                "path": request.path,
                                "method": request.method
                            }
                        )
                        
                        # Pass validated data to route handler
                        return f(validated_data, *args, **kwargs)
                        
                    except ValidationError as e:
                        span.set_attribute("validation.result", "validation_error")
                        validation_errors = self.format_validation_errors(e)
                        
                        logger.warning(
                            "Request validation failed",
                            extra={
                                "model": model_class.__name__,
                                "path": request.path,
                                "method": request.method,
                                "errors": validation_errors
                            }
                        )
                        
                        error_response = self.hal_formatter.format_validation_error(
                            f"Request validation failed for {model_class.__name__}",
                            request.path,
                            validation_errors
                        )
                        return jsonify(error_response), 400
            
            return decorated_function
        return decorator
    
    def validate_query_params(self, model_class: Type[BaseModel]) -> Callable:
        """
        Decorator to validate query parameters against Pydantic model.
        
        Args:
            model_class: Pydantic model class for validation
            
        Returns:
            Decorator function
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                with tracer.start_as_current_span("validation.validate_query_params") as span:
                    span.set_attributes({
                        "validation.model": model_class.__name__,
                        "http.method": request.method,
                        "http.path": request.path
                    })
                    
                    # Convert query parameters to dict
                    query_data = request.args.to_dict()
                    
                    # Handle multi-value parameters (convert to lists)
                    for key in request.args.keys():
                        values = request.args.getlist(key)
                        if len(values) > 1:
                            query_data[key] = values
                    
                    # Validate against Pydantic model
                    try:
                        validated_params = model_class(**query_data)
                        span.set_attribute("validation.result", "success")
                        
                        logger.debug(
                            "Query parameter validation successful",
                            extra={
                                "model": model_class.__name__,
                                "path": request.path,
                                "method": request.method,
                                "params": query_data
                            }
                        )
                        
                        # Pass validated parameters to route handler
                        return f(validated_params, *args, **kwargs)
                        
                    except ValidationError as e:
                        span.set_attribute("validation.result", "validation_error")
                        validation_errors = self.format_validation_errors(e)
                        
                        logger.warning(
                            "Query parameter validation failed",
                            extra={
                                "model": model_class.__name__,
                                "path": request.path,
                                "method": request.method,
                                "params": query_data,
                                "errors": validation_errors
                            }
                        )
                        
                        error_response = self.hal_formatter.format_validation_error(
                            f"Query parameter validation failed for {model_class.__name__}",
                            request.path,
                            validation_errors
                        )
                        return jsonify(error_response), 400
            
            return decorated_function
        return decorator


def validate_json(model_class: Type[BaseModel], validation_middleware: ValidationMiddleware) -> Callable:
    """
    Convenience decorator for JSON body validation.
    
    Args:
        model_class: Pydantic model class
        validation_middleware: ValidationMiddleware instance
        
    Returns:
        Decorator function
    """
    return validation_middleware.validate_json_body(model_class)


def validate_query(model_class: Type[BaseModel], validation_middleware: ValidationMiddleware) -> Callable:
    """
    Convenience decorator for query parameter validation.
    
    Args:
        model_class: Pydantic model class
        validation_middleware: ValidationMiddleware instance
        
    Returns:
        Decorator function
    """
    return validation_middleware.validate_query_params(model_class)
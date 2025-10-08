# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Request utilities for extracting and processing request data.
"""

from flask import request
from typing import Dict, Any, Optional, List, Union
from urllib.parse import unquote
import json
import logging

logger = logging.getLogger(__name__)


class RequestParser:
    """Utility for parsing and extracting request data."""
    
    @staticmethod
    def get_pagination_params(
        default_page: int = 1,
        default_page_size: int = 20,
        max_page_size: int = 100
    ) -> Dict[str, int]:
        """
        Extract pagination parameters from request.
        
        Args:
            default_page: Default page number
            default_page_size: Default page size
            max_page_size: Maximum allowed page size
            
        Returns:
            Dictionary with page and page_size
        """
        try:
            page = int(request.args.get('page', default_page))
            page = max(1, page)  # Ensure page is at least 1
        except (ValueError, TypeError):
            page = default_page
        
        try:
            page_size = int(request.args.get('page_size', default_page_size))
            page_size = max(1, min(page_size, max_page_size))  # Clamp between 1 and max
        except (ValueError, TypeError):
            page_size = default_page_size
        
        return {
            'page': page,
            'page_size': page_size
        }
    
    @staticmethod
    def get_sort_params(
        allowed_fields: Optional[List[str]] = None,
        default_field: Optional[str] = None,
        default_order: str = 'asc'
    ) -> Dict[str, str]:
        """
        Extract sorting parameters from request.
        
        Args:
            allowed_fields: List of allowed sort fields
            default_field: Default sort field
            default_order: Default sort order ('asc' or 'desc')
            
        Returns:
            Dictionary with sort_by and sort_order
        """
        sort_by = request.args.get('sort_by', default_field)
        sort_order = request.args.get('sort_order', default_order).lower()
        
        # Validate sort field
        if allowed_fields and sort_by and sort_by not in allowed_fields:
            sort_by = default_field
        
        # Validate sort order
        if sort_order not in ['asc', 'desc']:
            sort_order = default_order
        
        return {
            'sort_by': sort_by,
            'sort_order': sort_order
        }
    
    @staticmethod
    def get_filter_params(
        allowed_filters: Optional[List[str]] = None,
        type_conversions: Optional[Dict[str, type]] = None
    ) -> Dict[str, Any]:
        """
        Extract filter parameters from request.
        
        Args:
            allowed_filters: List of allowed filter parameters
            type_conversions: Dictionary mapping filter names to types
            
        Returns:
            Dictionary with filter parameters
        """
        filters = {}
        type_conversions = type_conversions or {}
        
        for key, value in request.args.items():
            # Skip pagination and sorting parameters
            if key in ['page', 'page_size', 'sort_by', 'sort_order']:
                continue
            
            # Check if filter is allowed
            if allowed_filters and key not in allowed_filters:
                continue
            
            # Apply type conversion if specified
            if key in type_conversions:
                try:
                    target_type = type_conversions[key]
                    if target_type == bool:
                        value = value.lower() in ['true', '1', 'yes', 'on']
                    elif target_type == list:
                        value = value.split(',') if value else []
                    else:
                        value = target_type(value)
                except (ValueError, TypeError):
                    logger.warning(f"Failed to convert filter {key} to {target_type}")
                    continue
            
            filters[key] = value
        
        return filters
    
    @staticmethod
    def get_search_params() -> Dict[str, str]:
        """
        Extract search parameters from request.
        
        Returns:
            Dictionary with search parameters
        """
        return {
            'q': request.args.get('q', '').strip(),
            'search': request.args.get('search', '').strip()
        }
    
    @staticmethod
    def get_request_metadata() -> Dict[str, Any]:
        """
        Extract request metadata for logging and auditing.
        
        Returns:
            Dictionary with request metadata
        """
        return {
            'method': request.method,
            'path': request.path,
            'full_path': request.full_path,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.content_type,
            'content_length': request.content_length,
            'referrer': request.referrer,
            'session_id': request.headers.get('X-Session-ID'),
            'request_id': request.headers.get('X-Request-ID'),
            'trace_id': request.headers.get('X-Trace-ID')
        }
    
    @staticmethod
    def parse_json_body(required: bool = True) -> Optional[Dict[str, Any]]:
        """
        Parse JSON request body with error handling.
        
        Args:
            required: Whether JSON body is required
            
        Returns:
            Parsed JSON data or None
            
        Raises:
            ValueError: If JSON is required but missing or invalid
        """
        if not request.is_json:
            if required:
                raise ValueError("Request must have Content-Type: application/json")
            return None
        
        try:
            data = request.get_json()
            if data is None and required:
                raise ValueError("No JSON data provided")
            return data
        except Exception as e:
            if required:
                raise ValueError(f"Invalid JSON: {str(e)}")
            return None
    
    @staticmethod
    def extract_path_params(*param_names: str) -> Dict[str, str]:
        """
        Extract path parameters from URL.
        
        Args:
            param_names: Names of path parameters to extract
            
        Returns:
            Dictionary with path parameters
        """
        params = {}
        view_args = request.view_args or {}
        
        for param_name in param_names:
            value = view_args.get(param_name)
            if value:
                params[param_name] = unquote(value)
        
        return params


class ResponseBuilder:
    """Utility for building consistent API responses."""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> tuple:
        """
        Build success response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            headers: Additional headers
            
        Returns:
            Tuple of (response_data, status_code, headers)
        """
        response = {
            'success': True,
            'message': message
        }
        
        if data is not None:
            response['data'] = data
        
        return response, status_code, headers or {}
    
    @staticmethod
    def error(
        message: str,
        status_code: int = 400,
        error_type: str = "error",
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> tuple:
        """
        Build error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_type: Error type identifier
            details: Additional error details
            headers: Additional headers
            
        Returns:
            Tuple of (response_data, status_code, headers)
        """
        response = {
            'success': False,
            'error': {
                'type': error_type,
                'message': message
            }
        }
        
        if details:
            response['error']['details'] = details
        
        return response, status_code, headers or {}
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build paginated response data.
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page
            additional_data: Additional response data
            
        Returns:
            Paginated response dictionary
        """
        import math
        
        total_pages = math.ceil(total / page_size) if page_size > 0 else 1
        
        response = {
            'items': items,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        if additional_data:
            response.update(additional_data)
        
        return response


class HeaderUtils:
    """Utilities for working with HTTP headers."""
    
    @staticmethod
    def get_bearer_token() -> Optional[str]:
        """
        Extract Bearer token from Authorization header.
        
        Returns:
            Token string or None if not found
        """
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None
    
    @staticmethod
    def get_content_type() -> str:
        """
        Get request content type.
        
        Returns:
            Content type string
        """
        return request.content_type or 'application/octet-stream'
    
    @staticmethod
    def accepts_json() -> bool:
        """
        Check if client accepts JSON responses.
        
        Returns:
            True if client accepts JSON
        """
        accept_header = request.headers.get('Accept', '')
        return (
            'application/json' in accept_header or
            'application/hal+json' in accept_header or
            '*/*' in accept_header
        )
    
    @staticmethod
    def prefers_hal() -> bool:
        """
        Check if client prefers HAL+JSON responses.
        
        Returns:
            True if client prefers HAL+JSON
        """
        accept_header = request.headers.get('Accept', '')
        return 'application/hal+json' in accept_header
    
    @staticmethod
    def build_cache_headers(
        max_age: int = 0,
        private: bool = True,
        no_cache: bool = False,
        no_store: bool = False
    ) -> Dict[str, str]:
        """
        Build cache control headers.
        
        Args:
            max_age: Cache max age in seconds
            private: Whether cache is private
            no_cache: Whether to disable caching
            no_store: Whether to disable storage
            
        Returns:
            Dictionary with cache headers
        """
        cache_parts = []
        
        if no_store:
            cache_parts.append('no-store')
        elif no_cache:
            cache_parts.append('no-cache')
        else:
            if private:
                cache_parts.append('private')
            else:
                cache_parts.append('public')
            
            cache_parts.append(f'max-age={max_age}')
        
        return {
            'Cache-Control': ', '.join(cache_parts)
        }
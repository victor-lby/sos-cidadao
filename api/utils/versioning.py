# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
API versioning utilities for handling multiple API versions.
"""

from flask import request
from typing import Optional, Dict, Any, List
from functools import wraps
import re
import logging

logger = logging.getLogger(__name__)


class APIVersionManager:
    """Manager for API versioning and compatibility."""
    
    def __init__(self, default_version: str = "1.0"):
        self.default_version = default_version
        self.supported_versions = ["1.0"]
        self.deprecated_versions = []
    
    def add_supported_version(self, version: str):
        """Add a supported API version."""
        if version not in self.supported_versions:
            self.supported_versions.append(version)
    
    def deprecate_version(self, version: str):
        """Mark a version as deprecated."""
        if version not in self.deprecated_versions:
            self.deprecated_versions.append(version)
    
    def extract_version_from_header(self) -> Optional[str]:
        """
        Extract API version from Accept header.
        
        Returns:
            API version string or None
        """
        accept_header = request.headers.get('Accept', '')
        
        # Look for version in Accept header: application/vnd.api+json;version=1.0
        version_match = re.search(r'version=([0-9]+\.[0-9]+)', accept_header)
        if version_match:
            return version_match.group(1)
        
        return None
    
    def extract_version_from_path(self) -> Optional[str]:
        """
        Extract API version from URL path.
        
        Returns:
            API version string or None
        """
        path = request.path
        
        # Look for version in path: /api/v1.0/... or /api/v1/...
        version_match = re.search(r'/api/v([0-9]+(?:\.[0-9]+)?)', path)
        if version_match:
            version = version_match.group(1)
            # Normalize version (add .0 if missing)
            if '.' not in version:
                version += '.0'
            return version
        
        return None
    
    def extract_version_from_query(self) -> Optional[str]:
        """
        Extract API version from query parameter.
        
        Returns:
            API version string or None
        """
        return request.args.get('version') or request.args.get('api_version')
    
    def get_requested_version(self) -> str:
        """
        Get the requested API version from various sources.
        
        Returns:
            Requested API version (defaults to default_version)
        """
        # Priority order: header > path > query > default
        version = (
            self.extract_version_from_header() or
            self.extract_version_from_path() or
            self.extract_version_from_query() or
            self.default_version
        )
        
        return version
    
    def is_version_supported(self, version: str) -> bool:
        """
        Check if API version is supported.
        
        Args:
            version: API version to check
            
        Returns:
            True if version is supported
        """
        return version in self.supported_versions
    
    def is_version_deprecated(self, version: str) -> bool:
        """
        Check if API version is deprecated.
        
        Args:
            version: API version to check
            
        Returns:
            True if version is deprecated
        """
        return version in self.deprecated_versions
    
    def get_version_info(self, version: str) -> Dict[str, Any]:
        """
        Get information about an API version.
        
        Args:
            version: API version
            
        Returns:
            Dictionary with version information
        """
        return {
            'version': version,
            'supported': self.is_version_supported(version),
            'deprecated': self.is_version_deprecated(version),
            'default': version == self.default_version
        }
    
    def add_version_headers(self, response, version: str):
        """
        Add version-related headers to response.
        
        Args:
            response: Flask response object
            version: API version used
        """
        response.headers['API-Version'] = version
        response.headers['API-Supported-Versions'] = ', '.join(self.supported_versions)
        
        if self.is_version_deprecated(version):
            response.headers['API-Deprecated'] = 'true'
            response.headers['Warning'] = f'299 - "API version {version} is deprecated"'
        
        return response


def require_api_version(
    supported_versions: Optional[List[str]] = None,
    version_manager: Optional[APIVersionManager] = None
):
    """
    Decorator to require specific API versions for endpoints.
    
    Args:
        supported_versions: List of supported versions for this endpoint
        version_manager: APIVersionManager instance
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app, jsonify
            
            # Get version manager
            if version_manager:
                vm = version_manager
            elif hasattr(current_app, 'version_manager'):
                vm = current_app.version_manager
            else:
                vm = APIVersionManager()
            
            # Get requested version
            requested_version = vm.get_requested_version()
            
            # Check if version is supported globally
            if not vm.is_version_supported(requested_version):
                error_response = {
                    'type': 'https://api.sos-cidadao.org/problems/unsupported-version',
                    'title': 'Unsupported API Version',
                    'status': 400,
                    'detail': f'API version {requested_version} is not supported',
                    'instance': request.path,
                    'supported_versions': vm.supported_versions
                }
                return jsonify(error_response), 400
            
            # Check if version is supported for this specific endpoint
            if supported_versions and requested_version not in supported_versions:
                error_response = {
                    'type': 'https://api.sos-cidadao.org/problems/version-not-supported-for-endpoint',
                    'title': 'Version Not Supported for Endpoint',
                    'status': 400,
                    'detail': f'API version {requested_version} is not supported for this endpoint',
                    'instance': request.path,
                    'supported_versions': supported_versions
                }
                return jsonify(error_response), 400
            
            # Log version usage
            logger.debug(
                f"API version {requested_version} used for {request.path}",
                extra={
                    'api_version': requested_version,
                    'endpoint': request.path,
                    'method': request.method,
                    'deprecated': vm.is_version_deprecated(requested_version)
                }
            )
            
            # Execute the route handler with version context
            response = f(requested_version, *args, **kwargs)
            
            # Add version headers to response
            if hasattr(response, 'headers'):
                vm.add_version_headers(response, requested_version)
            
            return response
        
        return decorated_function
    return decorator


def version_compatibility(version_mappings: Dict[str, str]):
    """
    Decorator to handle version compatibility and data transformation.
    
    Args:
        version_mappings: Dictionary mapping versions to transformation functions
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(version: str, *args, **kwargs):
            # Execute the route handler
            response_data = f(version, *args, **kwargs)
            
            # Apply version-specific transformations
            if version in version_mappings:
                transform_func = version_mappings[version]
                if callable(transform_func):
                    response_data = transform_func(response_data)
            
            return response_data
        
        return decorated_function
    return decorator


class VersionedResponse:
    """Utility for building version-aware responses."""
    
    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager
    
    def build_response(
        self,
        data: Any,
        version: str,
        transformations: Optional[Dict[str, callable]] = None
    ) -> Any:
        """
        Build version-aware response with optional transformations.
        
        Args:
            data: Response data
            version: API version
            transformations: Version-specific transformation functions
            
        Returns:
            Transformed response data
        """
        if transformations and version in transformations:
            transform_func = transformations[version]
            if callable(transform_func):
                data = transform_func(data)
        
        # Add version metadata if it's a dictionary
        if isinstance(data, dict):
            data['_version'] = version
            
            if self.version_manager.is_version_deprecated(version):
                data['_deprecated'] = True
        
        return data


# Common version transformation functions
def transform_v1_0_to_v1_1(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform response from v1.0 to v1.1 format."""
    # Example transformation - add new fields, rename fields, etc.
    if isinstance(data, dict):
        # Add new fields introduced in v1.1
        if 'created_at' in data and 'created_date' not in data:
            data['created_date'] = data['created_at']
    
    return data


def transform_v1_1_to_v1_0(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform response from v1.1 to v1.0 format (backward compatibility)."""
    if isinstance(data, dict):
        # Remove fields not present in v1.0
        data.pop('created_date', None)
    
    return data
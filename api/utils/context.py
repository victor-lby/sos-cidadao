# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Organization context extraction utilities.
Provides utilities for extracting and validating organization context from requests.
"""

from flask import request, g
from typing import Optional, Dict, Any
from opentelemetry import trace
import logging

from models.entities import UserContext
from middleware.error_handler import AuthorizationException, NotFoundException

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class OrganizationContextExtractor:
    """Utility for extracting organization context from requests."""
    
    def __init__(self, mongodb_service):
        self.mongodb_service = mongodb_service
    
    def extract_org_id_from_path(self, path_param: str = 'org_id') -> Optional[str]:
        """
        Extract organization ID from URL path parameters.
        
        Args:
            path_param: Name of the path parameter containing org ID
            
        Returns:
            Organization ID or None if not found
        """
        from flask import request
        return request.view_args.get(path_param) if request.view_args else None
    
    def extract_org_id_from_user_context(self) -> Optional[str]:
        """
        Extract organization ID from authenticated user context.
        
        Returns:
            Organization ID from user context or None
        """
        user_context = getattr(g, 'user_context', None)
        return user_context.org_id if user_context else None
    
    def validate_org_access(self, org_id: str, user_context: UserContext) -> bool:
        """
        Validate that user has access to the specified organization.
        
        Args:
            org_id: Organization ID to validate
            user_context: User context from authentication
            
        Returns:
            True if user has access to organization
        """
        with tracer.start_as_current_span("context.validate_org_access") as span:
            span.set_attributes({
                "organization.id": org_id,
                "user.id": user_context.user_id,
                "user.org_id": user_context.org_id
            })
            
            # Check if user belongs to the organization
            if user_context.org_id != org_id:
                span.set_attribute("access.result", "denied")
                logger.warning(
                    "Organization access denied: user not member",
                    extra={
                        "user_id": user_context.user_id,
                        "user_org_id": user_context.org_id,
                        "requested_org_id": org_id
                    }
                )
                return False
            
            span.set_attribute("access.result", "granted")
            return True
    
    def get_organization_context(self, org_id: str, user_context: UserContext) -> Dict[str, Any]:
        """
        Get organization context with validation.
        
        Args:
            org_id: Organization ID
            user_context: User context from authentication
            
        Returns:
            Organization context dictionary
            
        Raises:
            AuthorizationException: If user doesn't have access
            NotFoundException: If organization doesn't exist
        """
        with tracer.start_as_current_span("context.get_organization_context") as span:
            span.set_attributes({
                "organization.id": org_id,
                "user.id": user_context.user_id
            })
            
            # Validate user access to organization
            if not self.validate_org_access(org_id, user_context):
                raise AuthorizationException(
                    f"Access denied to organization {org_id}"
                )
            
            # Fetch organization details
            organization = self.mongodb_service.find_one_by_org(
                "organizations", org_id, org_id
            )
            
            if not organization:
                span.set_attribute("organization.found", False)
                logger.warning(
                    "Organization not found",
                    extra={
                        "organization_id": org_id,
                        "user_id": user_context.user_id
                    }
                )
                raise NotFoundException(f"Organization {org_id} not found")
            
            span.set_attribute("organization.found", True)
            span.set_attribute("organization.name", organization.get('name', ''))
            
            logger.debug(
                "Organization context retrieved",
                extra={
                    "organization_id": org_id,
                    "organization_name": organization.get('name'),
                    "user_id": user_context.user_id
                }
            )
            
            return {
                "id": organization["id"],
                "name": organization["name"],
                "slug": organization["slug"],
                "settings": organization.get("settings", {}),
                "user_context": user_context
            }


class RequestContextBuilder:
    """Builder for comprehensive request context."""
    
    def __init__(self, mongodb_service):
        self.org_extractor = OrganizationContextExtractor(mongodb_service)
    
    def build_request_context(
        self,
        user_context: UserContext,
        org_id: Optional[str] = None,
        include_org_details: bool = True
    ) -> Dict[str, Any]:
        """
        Build comprehensive request context.
        
        Args:
            user_context: Authenticated user context
            org_id: Optional organization ID (defaults to user's org)
            include_org_details: Whether to include full organization details
            
        Returns:
            Complete request context dictionary
        """
        with tracer.start_as_current_span("context.build_request_context") as span:
            # Use user's organization if not specified
            target_org_id = org_id or user_context.org_id
            
            span.set_attributes({
                "user.id": user_context.user_id,
                "organization.id": target_org_id,
                "include_org_details": include_org_details
            })
            
            context = {
                "user": {
                    "id": user_context.user_id,
                    "email": user_context.email,
                    "name": user_context.name,
                    "permissions": user_context.permissions,
                    "org_id": user_context.org_id
                },
                "request": {
                    "method": request.method,
                    "path": request.path,
                    "ip_address": user_context.ip_address,
                    "user_agent": user_context.user_agent,
                    "session_id": user_context.session_id
                },
                "organization_id": target_org_id
            }
            
            # Include organization details if requested
            if include_org_details:
                try:
                    org_context = self.org_extractor.get_organization_context(
                        target_org_id, user_context
                    )
                    context["organization"] = {
                        "id": org_context["id"],
                        "name": org_context["name"],
                        "slug": org_context["slug"],
                        "settings": org_context["settings"]
                    }
                except Exception as e:
                    logger.warning(
                        "Failed to load organization details",
                        extra={
                            "organization_id": target_org_id,
                            "user_id": user_context.user_id,
                            "error": str(e)
                        }
                    )
                    # Continue without organization details
                    context["organization"] = {"id": target_org_id}
            
            logger.debug(
                "Request context built",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": target_org_id,
                    "path": request.path,
                    "method": request.method
                }
            )
            
            return context


def get_organization_context(
    org_id: Optional[str] = None,
    mongodb_service = None,
    require_auth: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to get organization context from current request.
    
    Args:
        org_id: Optional organization ID (extracted from path if not provided)
        mongodb_service: MongoDB service instance
        require_auth: Whether authentication is required
        
    Returns:
        Organization context dictionary
        
    Raises:
        AuthorizationException: If authentication required but not present
        NotFoundException: If organization not found
    """
    # Get user context from Flask g object
    user_context = getattr(g, 'user_context', None)
    
    if require_auth and not user_context:
        raise AuthorizationException("Authentication required")
    
    # Extract org ID from path if not provided
    if not org_id:
        extractor = OrganizationContextExtractor(mongodb_service)
        org_id = extractor.extract_org_id_from_path()
        
        # Fall back to user's organization
        if not org_id and user_context:
            org_id = user_context.org_id
    
    if not org_id:
        raise ValueError("Organization ID not found in request")
    
    # Build and return context
    if user_context and mongodb_service:
        extractor = OrganizationContextExtractor(mongodb_service)
        return extractor.get_organization_context(org_id, user_context)
    
    return {"id": org_id}


def require_organization_access(mongodb_service):
    """
    Decorator to require and validate organization access.
    
    Args:
        mongodb_service: MongoDB service instance
        
    Returns:
        Decorator function
    """
    from functools import wraps
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get organization context and validate access
            org_context = get_organization_context(
                mongodb_service=mongodb_service,
                require_auth=True
            )
            
            # Pass organization context to route handler
            return f(org_context, *args, **kwargs)
        
        return decorated_function
    return decorator
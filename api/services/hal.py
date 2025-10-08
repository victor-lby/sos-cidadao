# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
HAL (Hypertext Application Language) response formatting utilities.
Implements HATEOAS Level-3 API responses with conditional affordance links.
"""

from typing import Dict, List, Any, Optional, Type, TypeVar, Union
from urllib.parse import urljoin, urlencode
import math
from datetime import datetime

from models.responses import (
    HalLink, HalResponse, HalCollection, ErrorResponse, ValidationErrorResponse
)

T = TypeVar('T', bound=HalResponse)


class HalLinkBuilder:
    """Builder for HAL links with proper URL construction."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def build_link(
        self, 
        path: str, 
        method: str = "GET", 
        content_type: Optional[str] = None,
        title: Optional[str] = None,
        templated: bool = False
    ) -> HalLink:
        """Build a HAL link with proper URL construction."""
        href = urljoin(self.base_url, path.lstrip('/'))
        
        return HalLink(
            href=href,
            method=method,
            type=content_type,
            title=title,
            templated=templated
        )
    
    def build_self_link(self, resource_path: str) -> HalLink:
        """Build self link for a resource."""
        return self.build_link(resource_path, title="Self")
    
    def build_collection_link(self, collection_path: str) -> HalLink:
        """Build link to parent collection."""
        return self.build_link(collection_path, title="Collection")
    
    def build_action_link(
        self, 
        resource_path: str, 
        action: str, 
        method: str = "POST",
        title: Optional[str] = None
    ) -> HalLink:
        """Build action link for a resource."""
        action_path = f"{resource_path}/{action}"
        return self.build_link(
            action_path, 
            method=method, 
            content_type="application/json",
            title=title or action.title()
        )


class PaginationLinkBuilder:
    """Builder for pagination links in HAL collections."""
    
    def __init__(self, base_url: str):
        self.link_builder = HalLinkBuilder(base_url)
    
    def build_pagination_links(
        self,
        base_path: str,
        current_page: int,
        total_pages: int,
        page_size: int,
        query_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, HalLink]:
        """Build pagination links for a collection."""
        links = {}
        params = query_params or {}
        
        # Self link (current page)
        self_params = {**params, 'page': current_page, 'page_size': page_size}
        self_query = urlencode(self_params)
        links['self'] = self.link_builder.build_link(
            f"{base_path}?{self_query}",
            title="Current page"
        )
        
        # First page link
        if current_page > 1:
            first_params = {**params, 'page': 1, 'page_size': page_size}
            first_query = urlencode(first_params)
            links['first'] = self.link_builder.build_link(
                f"{base_path}?{first_query}",
                title="First page"
            )
        
        # Previous page link
        if current_page > 1:
            prev_params = {**params, 'page': current_page - 1, 'page_size': page_size}
            prev_query = urlencode(prev_params)
            links['prev'] = self.link_builder.build_link(
                f"{base_path}?{prev_query}",
                title="Previous page"
            )
        
        # Next page link
        if current_page < total_pages:
            next_params = {**params, 'page': current_page + 1, 'page_size': page_size}
            next_query = urlencode(next_params)
            links['next'] = self.link_builder.build_link(
                f"{base_path}?{next_query}",
                title="Next page"
            )
        
        # Last page link
        if current_page < total_pages:
            last_params = {**params, 'page': total_pages, 'page_size': page_size}
            last_query = urlencode(last_params)
            links['last'] = self.link_builder.build_link(
                f"{base_path}?{last_query}",
                title="Last page"
            )
        
        return links


class AffordanceLinkBuilder:
    """Builder for conditional affordance links based on permissions and state."""
    
    def __init__(self, base_url: str):
        self.link_builder = HalLinkBuilder(base_url)
    
    def build_notification_affordances(
        self,
        notification_id: str,
        notification_status: str,
        user_permissions: List[str],
        organization_id: str
    ) -> Dict[str, HalLink]:
        """Build conditional affordance links for notifications."""
        links = {}
        base_path = f"/api/organizations/{organization_id}/notifications/{notification_id}"
        
        # Self link (always present)
        links['self'] = self.link_builder.build_self_link(base_path)
        
        # Collection link (always present)
        links['collection'] = self.link_builder.build_collection_link(
            f"/api/organizations/{organization_id}/notifications"
        )
        
        # Conditional action links based on status and permissions
        if notification_status == "received":
            if "notification:approve" in user_permissions:
                links['approve'] = self.link_builder.build_action_link(
                    base_path, "approve", title="Approve notification"
                )
            
            if "notification:deny" in user_permissions:
                links['deny'] = self.link_builder.build_action_link(
                    base_path, "deny", title="Deny notification"
                )
        
        # Edit link (if user has edit permissions)
        if "notification:edit" in user_permissions:
            links['edit'] = self.link_builder.build_link(
                base_path, 
                method="PUT", 
                content_type="application/json",
                title="Edit notification"
            )
        
        # Delete link (if user has delete permissions)
        if "notification:delete" in user_permissions:
            links['delete'] = self.link_builder.build_link(
                base_path, 
                method="DELETE",
                title="Delete notification"
            )
        
        return links
    
    def build_organization_affordances(
        self,
        organization_id: str,
        user_permissions: List[str]
    ) -> Dict[str, HalLink]:
        """Build conditional affordance links for organizations."""
        links = {}
        base_path = f"/api/organizations/{organization_id}"
        
        # Self link (always present)
        links['self'] = self.link_builder.build_self_link(base_path)
        
        # Collection link (always present)
        links['collection'] = self.link_builder.build_collection_link("/api/organizations")
        
        # Conditional action links based on permissions
        if "organization:edit" in user_permissions:
            links['edit'] = self.link_builder.build_link(
                base_path, 
                method="PUT", 
                content_type="application/json",
                title="Edit organization"
            )
        
        if "organization:delete" in user_permissions:
            links['delete'] = self.link_builder.build_link(
                base_path, 
                method="DELETE",
                title="Delete organization"
            )
        
        # Related resource links
        if "user:list" in user_permissions:
            links['users'] = self.link_builder.build_link(
                f"{base_path}/users",
                title="Organization users"
            )
        
        if "notification:list" in user_permissions:
            links['notifications'] = self.link_builder.build_link(
                f"{base_path}/notifications",
                title="Organization notifications"
            )
        
        if "role:list" in user_permissions:
            links['roles'] = self.link_builder.build_link(
                f"{base_path}/roles",
                title="Organization roles"
            )
        
        return links
    
    def build_user_affordances(
        self,
        user_id: str,
        organization_id: str,
        user_permissions: List[str],
        current_user_id: str
    ) -> Dict[str, HalLink]:
        """Build conditional affordance links for users."""
        links = {}
        base_path = f"/api/organizations/{organization_id}/users/{user_id}"
        
        # Self link (always present)
        links['self'] = self.link_builder.build_self_link(base_path)
        
        # Collection link (always present)
        links['collection'] = self.link_builder.build_collection_link(
            f"/api/organizations/{organization_id}/users"
        )
        
        # Conditional action links based on permissions
        is_self = user_id == current_user_id
        
        if "user:edit" in user_permissions or is_self:
            links['edit'] = self.link_builder.build_link(
                base_path, 
                method="PUT", 
                content_type="application/json",
                title="Edit user"
            )
        
        if "user:delete" in user_permissions and not is_self:
            links['delete'] = self.link_builder.build_link(
                base_path, 
                method="DELETE",
                title="Delete user"
            )
        
        if "user:manage_roles" in user_permissions:
            links['assign_roles'] = self.link_builder.build_action_link(
                base_path, "roles", method="PUT", title="Assign roles"
            )
        
        return links


class HalResponseBuilder:
    """Main HAL response builder with comprehensive formatting capabilities."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.link_builder = HalLinkBuilder(base_url)
        self.pagination_builder = PaginationLinkBuilder(base_url)
        self.affordance_builder = AffordanceLinkBuilder(base_url)
    
    def build_resource_response(
        self,
        data: Dict[str, Any],
        resource_type: str,
        resource_id: str,
        organization_id: str,
        user_permissions: List[str],
        current_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build a HAL resource response with appropriate affordance links."""
        response = dict(data)
        
        # Build affordance links based on resource type
        if resource_type == "notification":
            links = self.affordance_builder.build_notification_affordances(
                resource_id,
                data.get('status', ''),
                user_permissions,
                organization_id
            )
        elif resource_type == "organization":
            links = self.affordance_builder.build_organization_affordances(
                resource_id,
                user_permissions
            )
        elif resource_type == "user":
            links = self.affordance_builder.build_user_affordances(
                resource_id,
                organization_id,
                user_permissions,
                current_user_id or ""
            )
        else:
            # Generic resource links
            links = {
                'self': self.link_builder.build_self_link(
                    f"/api/organizations/{organization_id}/{resource_type}s/{resource_id}"
                )
            }
        
        response['_links'] = {rel: link.model_dump() for rel, link in links.items()}
        return response
    
    def build_collection_response(
        self,
        items: List[Dict[str, Any]],
        total: int,
        page: int,
        page_size: int,
        collection_path: str,
        query_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a HAL collection response with pagination links."""
        total_pages = math.ceil(total / page_size) if page_size > 0 else 1
        
        # Build pagination links
        pagination_links = self.pagination_builder.build_pagination_links(
            collection_path,
            page,
            total_pages,
            page_size,
            query_params
        )
        
        response = {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            '_links': {rel: link.model_dump() for rel, link in pagination_links.items()},
            '_embedded': {
                'items': items
            }
        }
        
        return response
    
    def build_error_response(
        self,
        error_type: str,
        title: str,
        status: int,
        detail: str,
        instance: str,
        validation_errors: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build RFC 7807 compliant error response with HAL links."""
        error_response = {
            'type': f"https://api.sos-cidadao.org/problems/{error_type}",
            'title': title,
            'status': status,
            'detail': detail,
            'instance': instance
        }
        
        if validation_errors:
            error_response['errors'] = validation_errors
        
        # Add helpful links
        links = {
            'help': self.link_builder.build_link(
                f"/docs/errors#{error_type}",
                title="Error documentation"
            )
        }
        
        # Add specific links based on error type
        if error_type == "validation-error":
            links['schema'] = self.link_builder.build_link(
                "/openapi.json",
                title="API schema"
            )
        elif error_type == "authentication-required":
            links['login'] = self.link_builder.build_link(
                "/api/auth/login",
                method="POST",
                content_type="application/json",
                title="Login"
            )
        elif error_type == "insufficient-permissions":
            links['permissions'] = self.link_builder.build_link(
                "/api/user/permissions",
                title="User permissions"
            )
        
        error_response['_links'] = {rel: link.model_dump() for rel, link in links.items()}
        return error_response


class HalFormatter:
    """High-level HAL formatter with convenience methods."""
    
    def __init__(self, base_url: str):
        self.builder = HalResponseBuilder(base_url)
    
    def format_notification(
        self,
        notification: Dict[str, Any],
        organization_id: str,
        user_permissions: List[str]
    ) -> Dict[str, Any]:
        """Format a notification with HAL links."""
        return self.builder.build_resource_response(
            notification,
            "notification",
            notification['id'],
            organization_id,
            user_permissions
        )
    
    def format_notification_collection(
        self,
        notifications: List[Dict[str, Any]],
        total: int,
        page: int,
        page_size: int,
        organization_id: str,
        user_permissions: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a collection of notifications with HAL links."""
        # Add HAL links to each notification
        formatted_notifications = [
            self.format_notification(notification, organization_id, user_permissions)
            for notification in notifications
        ]
        
        collection_path = f"/api/organizations/{organization_id}/notifications"
        return self.builder.build_collection_response(
            formatted_notifications,
            total,
            page,
            page_size,
            collection_path,
            filters
        )
    
    def format_organization(
        self,
        organization: Dict[str, Any],
        user_permissions: List[str]
    ) -> Dict[str, Any]:
        """Format an organization with HAL links."""
        return self.builder.build_resource_response(
            organization,
            "organization",
            organization['id'],
            organization['id'],  # org_id is same as resource_id for organizations
            user_permissions
        )
    
    def format_user(
        self,
        user: Dict[str, Any],
        organization_id: str,
        user_permissions: List[str],
        current_user_id: str
    ) -> Dict[str, Any]:
        """Format a user with HAL links."""
        return self.builder.build_resource_response(
            user,
            "user",
            user['id'],
            organization_id,
            user_permissions,
            current_user_id
        )
    
    def format_validation_error(
        self,
        detail: str,
        instance: str,
        validation_errors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format a validation error response."""
        return self.builder.build_error_response(
            "validation-error",
            "Validation Error",
            400,
            detail,
            instance,
            validation_errors
        )
    
    def format_authentication_error(
        self,
        detail: str,
        instance: str
    ) -> Dict[str, Any]:
        """Format an authentication error response."""
        return self.builder.build_error_response(
            "authentication-required",
            "Authentication Required",
            401,
            detail,
            instance
        )
    
    def format_authorization_error(
        self,
        detail: str,
        instance: str
    ) -> Dict[str, Any]:
        """Format an authorization error response."""
        return self.builder.build_error_response(
            "insufficient-permissions",
            "Insufficient Permissions",
            403,
            detail,
            instance
        )
    
    def format_not_found_error(
        self,
        detail: str,
        instance: str
    ) -> Dict[str, Any]:
        """Format a not found error response."""
        return self.builder.build_error_response(
            "resource-not-found",
            "Resource Not Found",
            404,
            detail,
            instance
        )
    
    def format_conflict_error(
        self,
        detail: str,
        instance: str
    ) -> Dict[str, Any]:
        """Format a conflict error response."""
        return self.builder.build_error_response(
            "resource-conflict",
            "Resource Conflict",
            409,
            detail,
            instance
        )
    
    def format_server_error(
        self,
        detail: str,
        instance: str
    ) -> Dict[str, Any]:
        """Format a server error response."""
        return self.builder.build_error_response(
            "internal-server-error",
            "Internal Server Error",
            500,
            detail,
            instance
        )


# Convenience function for creating HAL formatter
def create_hal_formatter(base_url: str) -> HalFormatter:
    """Create a HAL formatter instance."""
    return HalFormatter(base_url)
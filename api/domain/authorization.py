# SPDX-License-Identifier: Apache-2.0

"""
Authorization domain logic for role-based access control.

This module contains pure functions for permission aggregation, role management,
and authorization checks with organization scoping.
"""

from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass
from ..models.entities import User, Role, Permission, UserContext


@dataclass
class AuthorizationResult:
    """Result of an authorization check."""
    allowed: bool
    reason: Optional[str] = None
    missing_permissions: List[str] = None


def aggregate_permissions_from_roles(roles: List[Role]) -> List[str]:
    """
    Aggregate unique permissions from a list of roles.
    
    Args:
        roles: List of Role entities
        
    Returns:
        List of unique permission strings
    """
    permissions: Set[str] = set()
    
    for role in roles:
        permissions.update(role.permissions)
    
    return sorted(list(permissions))


def build_user_permissions(user: User, user_roles: List[Role]) -> List[str]:
    """
    Build complete permission list for a user based on their roles.
    
    Args:
        user: User entity
        user_roles: List of Role entities assigned to the user
        
    Returns:
        List of permission strings for the user
    """
    # Filter roles to only those assigned to the user
    assigned_roles = [role for role in user_roles if role.id in user.roles]
    
    # Aggregate permissions from assigned roles
    permissions = aggregate_permissions_from_roles(assigned_roles)
    
    return permissions


def check_permission(user_context: UserContext, required_permission: str) -> AuthorizationResult:
    """
    Check if user has a specific permission.
    
    Args:
        user_context: User context with permissions
        required_permission: Permission string to check
        
    Returns:
        AuthorizationResult indicating if permission is granted
    """
    if required_permission in user_context.permissions:
        return AuthorizationResult(allowed=True)
    
    return AuthorizationResult(
        allowed=False,
        reason=f"Missing required permission: {required_permission}",
        missing_permissions=[required_permission]
    )


def check_permissions(user_context: UserContext, required_permissions: List[str], require_all: bool = True) -> AuthorizationResult:
    """
    Check if user has required permissions.
    
    Args:
        user_context: User context with permissions
        required_permissions: List of permission strings to check
        require_all: If True, user must have all permissions. If False, any permission is sufficient.
        
    Returns:
        AuthorizationResult indicating if permissions are granted
    """
    user_permissions = set(user_context.permissions)
    required_set = set(required_permissions)
    
    if require_all:
        missing = required_set - user_permissions
        if not missing:
            return AuthorizationResult(allowed=True)
        
        return AuthorizationResult(
            allowed=False,
            reason=f"Missing required permissions: {', '.join(sorted(missing))}",
            missing_permissions=sorted(list(missing))
        )
    else:
        # Require any permission
        if user_permissions & required_set:
            return AuthorizationResult(allowed=True)
        
        return AuthorizationResult(
            allowed=False,
            reason=f"Missing any of required permissions: {', '.join(sorted(required_permissions))}",
            missing_permissions=required_permissions
        )


def check_organization_access(user_context: UserContext, target_org_id: str) -> AuthorizationResult:
    """
    Check if user has access to a specific organization.
    
    Args:
        user_context: User context with organization info
        target_org_id: Organization ID to check access for
        
    Returns:
        AuthorizationResult indicating if access is granted
    """
    if user_context.org_id == target_org_id:
        return AuthorizationResult(allowed=True)
    
    return AuthorizationResult(
        allowed=False,
        reason=f"Access denied to organization {target_org_id}"
    )


def can_manage_user(manager_context: UserContext, target_user: User) -> AuthorizationResult:
    """
    Check if a user can manage another user (create, update, delete).
    
    Args:
        manager_context: Context of user attempting to manage
        target_user: User being managed
        
    Returns:
        AuthorizationResult indicating if management is allowed
    """
    # Check organization access
    org_check = check_organization_access(manager_context, target_user.organization_id)
    if not org_check.allowed:
        return org_check
    
    # Check user management permission
    perm_check = check_permission(manager_context, "user:manage")
    if not perm_check.allowed:
        return perm_check
    
    return AuthorizationResult(allowed=True)


def can_assign_role(manager_context: UserContext, role: Role, target_user: User) -> AuthorizationResult:
    """
    Check if a user can assign a specific role to another user.
    
    Args:
        manager_context: Context of user attempting to assign role
        role: Role being assigned
        target_user: User receiving the role
        
    Returns:
        AuthorizationResult indicating if role assignment is allowed
    """
    # Check organization access
    org_check = check_organization_access(manager_context, target_user.organization_id)
    if not org_check.allowed:
        return org_check
    
    # Check role management permission
    perm_check = check_permission(manager_context, "role:assign")
    if not perm_check.allowed:
        return perm_check
    
    # System roles can only be assigned by users with system role management permission
    if role.is_system_role:
        system_perm_check = check_permission(manager_context, "role:assign_system")
        if not system_perm_check.allowed:
            return AuthorizationResult(
                allowed=False,
                reason="Cannot assign system roles without system role management permission",
                missing_permissions=["role:assign_system"]
            )
    
    return AuthorizationResult(allowed=True)


def filter_accessible_resources(user_context: UserContext, resources: List[Dict[str, Any]], 
                               org_id_field: str = "organization_id") -> List[Dict[str, Any]]:
    """
    Filter a list of resources to only those accessible by the user's organization.
    
    Args:
        user_context: User context with organization info
        resources: List of resource dictionaries
        org_id_field: Field name containing organization ID
        
    Returns:
        Filtered list of resources accessible to the user
    """
    return [
        resource for resource in resources 
        if resource.get(org_id_field) == user_context.org_id
    ]


def generate_hal_affordances(resource: Dict[str, Any], user_context: UserContext, 
                            base_url: str, resource_type: str) -> Dict[str, Dict[str, str]]:
    """
    Generate HAL affordance links based on user permissions and resource state.
    
    Args:
        resource: Resource dictionary
        user_context: User context with permissions
        base_url: Base URL for link generation
        resource_type: Type of resource (notification, user, etc.)
        
    Returns:
        Dictionary of HAL links based on available actions
    """
    links = {
        "self": {"href": f"{base_url}/api/{resource_type}s/{resource['id']}"}
    }
    
    # Resource-specific affordances
    if resource_type == "notification":
        return _generate_notification_affordances(resource, user_context, base_url, links)
    elif resource_type == "user":
        return _generate_user_affordances(resource, user_context, base_url, links)
    elif resource_type == "organization":
        return _generate_organization_affordances(resource, user_context, base_url, links)
    
    return links


def _generate_notification_affordances(resource: Dict[str, Any], user_context: UserContext, 
                                     base_url: str, links: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Generate notification-specific HAL affordances."""
    notification_id = resource["id"]
    status = resource.get("status", "")
    
    # Approve action
    if (status == "received" and 
        check_permission(user_context, "notification:approve").allowed):
        links["approve"] = {
            "href": f"{base_url}/api/notifications/{notification_id}/approve",
            "method": "POST"
        }
    
    # Deny action
    if (status == "received" and 
        check_permission(user_context, "notification:deny").allowed):
        links["deny"] = {
            "href": f"{base_url}/api/notifications/{notification_id}/deny",
            "method": "POST"
        }
    
    # Edit action
    if (status == "received" and 
        check_permission(user_context, "notification:edit").allowed):
        links["edit"] = {
            "href": f"{base_url}/api/notifications/{notification_id}",
            "method": "PUT"
        }
    
    return links


def _generate_user_affordances(resource: Dict[str, Any], user_context: UserContext, 
                              base_url: str, links: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Generate user-specific HAL affordances."""
    user_id = resource["id"]
    
    # Edit user
    if check_permission(user_context, "user:manage").allowed:
        links["edit"] = {
            "href": f"{base_url}/api/users/{user_id}",
            "method": "PUT"
        }
    
    # Delete user
    if (check_permission(user_context, "user:delete").allowed and 
        user_id != user_context.user_id):  # Can't delete self
        links["delete"] = {
            "href": f"{base_url}/api/users/{user_id}",
            "method": "DELETE"
        }
    
    # Assign roles
    if check_permission(user_context, "role:assign").allowed:
        links["assign-roles"] = {
            "href": f"{base_url}/api/users/{user_id}/roles",
            "method": "POST"
        }
    
    return links


def _generate_organization_affordances(resource: Dict[str, Any], user_context: UserContext, 
                                     base_url: str, links: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Generate organization-specific HAL affordances."""
    org_id = resource["id"]
    
    # Edit organization
    if check_permission(user_context, "organization:manage").allowed:
        links["edit"] = {
            "href": f"{base_url}/api/organizations/{org_id}",
            "method": "PUT"
        }
    
    # View users
    if check_permission(user_context, "user:list").allowed:
        links["users"] = {
            "href": f"{base_url}/api/organizations/{org_id}/users"
        }
    
    # View roles
    if check_permission(user_context, "role:list").allowed:
        links["roles"] = {
            "href": f"{base_url}/api/organizations/{org_id}/roles"
        }
    
    return links


def validate_role_hierarchy(roles: List[Role]) -> Tuple[bool, Optional[str]]:
    """
    Validate role hierarchy for circular dependencies and conflicts.
    
    Args:
        roles: List of roles to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # For now, we don't have role hierarchy, but this function
    # provides a place to add hierarchy validation in the future
    
    # Check for duplicate role names within the same organization
    role_names = {}
    for role in roles:
        org_id = role.organization_id
        name = role.name.lower()
        
        if org_id not in role_names:
            role_names[org_id] = set()
        
        if name in role_names[org_id]:
            return False, f"Duplicate role name '{role.name}' in organization"
        
        role_names[org_id].add(name)
    
    return True, None


def calculate_effective_permissions(user: User, all_roles: List[Role]) -> List[str]:
    """
    Calculate effective permissions for a user considering all their roles.
    
    Args:
        user: User entity
        all_roles: All available roles in the system
        
    Returns:
        List of effective permission strings
    """
    # Get user's assigned roles
    user_roles = [role for role in all_roles if role.id in user.roles]
    
    # Build permissions from roles
    permissions = build_user_permissions(user, user_roles)
    
    return permissions


def get_permission_description(permission: str) -> str:
    """
    Get human-readable description for a permission.
    
    Args:
        permission: Permission string (e.g., "notification:approve")
        
    Returns:
        Human-readable description
    """
    permission_descriptions = {
        # Notification permissions
        "notification:create": "Create new notifications",
        "notification:read": "View notifications",
        "notification:approve": "Approve notifications for dispatch",
        "notification:deny": "Deny notifications",
        "notification:edit": "Edit notification details",
        "notification:delete": "Delete notifications",
        
        # User permissions
        "user:create": "Create new users",
        "user:read": "View user information",
        "user:manage": "Manage user accounts",
        "user:delete": "Delete user accounts",
        "user:list": "List users in organization",
        
        # Role permissions
        "role:create": "Create new roles",
        "role:read": "View role information",
        "role:manage": "Manage roles",
        "role:delete": "Delete roles",
        "role:assign": "Assign roles to users",
        "role:assign_system": "Assign system roles",
        "role:list": "List roles in organization",
        
        # Organization permissions
        "organization:read": "View organization information",
        "organization:manage": "Manage organization settings",
        
        # Audit permissions
        "audit:read": "View audit logs",
        "audit:export": "Export audit logs",
        
        # System permissions
        "system:admin": "System administration access"
    }
    
    return permission_descriptions.get(permission, f"Permission: {permission}")


def is_system_permission(permission: str) -> bool:
    """
    Check if a permission is a system-level permission.
    
    Args:
        permission: Permission string
        
    Returns:
        True if it's a system permission
    """
    system_permissions = {
        "system:admin",
        "role:assign_system",
        "organization:create"
    }
    
    return permission in system_permissions
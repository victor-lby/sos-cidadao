# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Models package - Pydantic schemas and data models for S.O.S Cidadão platform.
"""

# Base models
from .base import BaseEntity, BaseEntityCreate, BaseEntityUpdate

# Enumerations
from .enums import (
    NotificationStatus,
    NotificationSeverity,
    UserStatus,
    PermissionAction,
    PermissionResource
)

# Core entities
from .entities import (
    Organization,
    User,
    Role,
    Permission,
    Notification,
    NotificationTarget,
    NotificationCategory,
    Endpoint,
    AuditLog
)

# Request models
from .requests import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest,
    CreateRoleRequest,
    UpdateRoleRequest,
    CreateNotificationRequest,
    ApproveNotificationRequest,
    DenyNotificationRequest,
    CreateNotificationTargetRequest,
    UpdateNotificationTargetRequest,
    CreateNotificationCategoryRequest,
    UpdateNotificationCategoryRequest,
    CreateEndpointRequest,
    UpdateEndpointRequest,
    LoginRequest,
    RefreshTokenRequest,
    NotificationFilters,
    AuditLogFilters,
    PaginationParams
)

# Response models
from .responses import (
    HalLink,
    HalResponse,
    HalCollection,
    OrganizationResponse,
    UserResponse,
    RoleResponse,
    PermissionResponse,
    NotificationResponse,
    NotificationTargetResponse,
    NotificationCategoryResponse,
    EndpointResponse,
    AuditLogResponse,
    AuthTokenResponse,
    HealthCheckResponse,
    ErrorResponse,
    ValidationErrorResponse,
    SuccessResponse,
    BulkOperationResponse,
    ExportResponse,
    OrganizationCollection,
    UserCollection,
    RoleCollection,
    NotificationCollection,
    NotificationTargetCollection,
    NotificationCategoryCollection,
    EndpointCollection,
    AuditLogCollection
)

__all__ = [
    # Base models
    "BaseEntity",
    "BaseEntityCreate", 
    "BaseEntityUpdate",
    
    # Enumerations
    "NotificationStatus",
    "NotificationSeverity",
    "UserStatus",
    "PermissionAction",
    "PermissionResource",
    
    # Core entities
    "Organization",
    "User",
    "Role",
    "Permission",
    "Notification",
    "NotificationTarget",
    "NotificationCategory",
    "Endpoint",
    "AuditLog",
    
    # Request models
    "CreateOrganizationRequest",
    "UpdateOrganizationRequest",
    "CreateUserRequest",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    "CreateRoleRequest",
    "UpdateRoleRequest",
    "CreateNotificationRequest",
    "ApproveNotificationRequest",
    "DenyNotificationRequest",
    "CreateNotificationTargetRequest",
    "UpdateNotificationTargetRequest",
    "CreateNotificationCategoryRequest",
    "UpdateNotificationCategoryRequest",
    "CreateEndpointRequest",
    "UpdateEndpointRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "NotificationFilters",
    "AuditLogFilters",
    "PaginationParams",
    
    # Response models
    "HalLink",
    "HalResponse",
    "HalCollection",
    "OrganizationResponse",
    "UserResponse",
    "RoleResponse",
    "PermissionResponse",
    "NotificationResponse",
    "NotificationTargetResponse",
    "NotificationCategoryResponse",
    "EndpointResponse",
    "AuditLogResponse",
    "AuthTokenResponse",
    "HealthCheckResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "SuccessResponse",
    "BulkOperationResponse",
    "ExportResponse",
    "OrganizationCollection",
    "UserCollection",
    "RoleCollection",
    "NotificationCollection",
    "NotificationTargetCollection",
    "NotificationCategoryCollection",
    "EndpointCollection",
    "AuditLogCollection"
]
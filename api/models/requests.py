# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Request models for API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .base import BaseEntityCreate, BaseEntityUpdate
from .enums import NotificationSeverity, UserStatus


class CreateOrganizationRequest(BaseEntityCreate):
    """Request model for creating an organization."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly identifier")
    description: Optional[str] = Field(None, max_length=1000, description="Organization description")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Organization settings")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v


class UpdateOrganizationRequest(BaseEntityUpdate):
    """Request model for updating an organization."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Organization name")
    description: Optional[str] = Field(None, max_length=1000, description="Organization description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Organization settings")


class CreateUserRequest(BaseEntityCreate):
    """Request model for creating a user."""
    
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=200, description="User full name")
    password: str = Field(..., min_length=8, description="User password")
    roles: List[str] = Field(default_factory=list, description="List of role IDs")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User account status")
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.lower()):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UpdateUserRequest(BaseEntityUpdate):
    """Request model for updating a user."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="User full name")
    roles: Optional[List[str]] = Field(None, description="List of role IDs")
    status: Optional[UserStatus] = Field(None, description="User account status")


class ChangePasswordRequest(BaseModel):
    """Request model for changing user password."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    updated_by: str = Field(..., description="User ID making the change")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class CreateRoleRequest(BaseEntityCreate):
    """Request model for creating a role."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: List[str] = Field(default_factory=list, description="List of permission IDs")


class UpdateRoleRequest(BaseEntityUpdate):
    """Request model for updating a role."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: Optional[List[str]] = Field(None, description="List of permission IDs")


class CreateNotificationRequest(BaseEntityCreate):
    """Request model for creating a notification via webhook."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, max_length=2000, description="Notification body")
    severity: NotificationSeverity = Field(..., description="Notification severity level")
    origin: str = Field(..., description="Source system or service")
    original_payload: Dict[str, Any] = Field(..., description="Original webhook payload")
    base_target_id: Optional[str] = Field(None, description="Base target for hierarchy expansion")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class ApproveNotificationRequest(BaseModel):
    """Request model for approving a notification."""
    
    target_ids: List[str] = Field(..., min_items=1, description="Selected target IDs")
    category_ids: List[str] = Field(..., min_items=1, description="Selected category IDs")
    approved_by: str = Field(..., description="User ID approving the notification")


class DenyNotificationRequest(BaseModel):
    """Request model for denying a notification."""
    
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for denial")
    denied_by: str = Field(..., description="User ID denying the notification")


class CreateNotificationTargetRequest(BaseEntityCreate):
    """Request model for creating a notification target."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Target name")
    description: Optional[str] = Field(None, max_length=1000, description="Target description")
    parent_id: Optional[str] = Field(None, description="Parent target ID for hierarchy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional target metadata")


class UpdateNotificationTargetRequest(BaseEntityUpdate):
    """Request model for updating a notification target."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Target name")
    description: Optional[str] = Field(None, max_length=1000, description="Target description")
    parent_id: Optional[str] = Field(None, description="Parent target ID for hierarchy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional target metadata")


class CreateNotificationCategoryRequest(BaseEntityCreate):
    """Request model for creating a notification category."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    color: Optional[str] = Field(None, description="UI color code")
    icon: Optional[str] = Field(None, description="UI icon identifier")
    target_ids: List[str] = Field(default_factory=list, description="Associated target IDs")


class UpdateNotificationCategoryRequest(BaseEntityUpdate):
    """Request model for updating a notification category."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    color: Optional[str] = Field(None, description="UI color code")
    icon: Optional[str] = Field(None, description="UI icon identifier")
    target_ids: Optional[List[str]] = Field(None, description="Associated target IDs")


class CreateEndpointRequest(BaseEntityCreate):
    """Request model for creating an endpoint."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Endpoint name")
    description: Optional[str] = Field(None, max_length=500, description="Endpoint description")
    url: str = Field(..., description="Endpoint URL")
    data_mapping: Dict[str, Any] = Field(..., description="JSONPath data transformation mapping")
    category_ids: List[str] = Field(default_factory=list, description="Associated category IDs")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Retry attempts")


class UpdateEndpointRequest(BaseEntityUpdate):
    """Request model for updating an endpoint."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Endpoint name")
    description: Optional[str] = Field(None, max_length=500, description="Endpoint description")
    url: Optional[str] = Field(None, description="Endpoint URL")
    data_mapping: Optional[Dict[str, Any]] = Field(None, description="JSONPath data transformation mapping")
    category_ids: Optional[List[str]] = Field(None, description="Associated category IDs")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Request timeout")
    retry_attempts: Optional[int] = Field(None, ge=0, le=10, description="Retry attempts")
    is_active: Optional[bool] = Field(None, description="Whether endpoint is active")


class LoginRequest(BaseModel):
    """Request model for user authentication."""
    
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.lower()):
            raise ValueError('Invalid email format')
        return v.lower()


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    
    refresh_token: str = Field(..., description="Refresh token")


class NotificationFilters(BaseModel):
    """Filters for notification queries."""
    
    status: Optional[str] = Field(None, description="Filter by status")
    severity: Optional[int] = Field(None, ge=0, le=5, description="Filter by severity")
    origin: Optional[str] = Field(None, description="Filter by origin")
    date_from: Optional[str] = Field(None, description="Filter from date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter to date (ISO format)")
    search: Optional[str] = Field(None, description="Search in title and body")


class AuditLogFilters(BaseModel):
    """Filters for audit log queries."""
    
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    entity: Optional[str] = Field(None, description="Filter by entity type")
    action: Optional[str] = Field(None, description="Filter by action")
    date_from: Optional[str] = Field(None, description="Filter from date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter to date (ISO format)")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(default="desc", regex="^(asc|desc)$", description="Sort order")
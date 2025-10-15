# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Core entity models for the S.O.S Cidadão platform.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from .base import BaseEntity, BaseEntityCreate, BaseEntityUpdate
from .enums import (
    NotificationStatus, 
    NotificationSeverity, 
    UserStatus, 
    PermissionAction, 
    PermissionResource
)


class Organization(BaseEntity):
    """Organization entity for multi-tenant isolation."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly identifier")
    description: Optional[str] = Field(None, max_length=1000, description="Organization description")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Organization-specific settings")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate organization name."""
        if not v.strip():
            raise ValueError('Organization name cannot be empty')
        return v.strip()


class Permission(BaseModel):
    """Permission definition for RBAC."""
    
    id: str = Field(..., description="Permission identifier")
    resource: PermissionResource = Field(..., description="Resource type")
    action: PermissionAction = Field(..., description="Action type")
    description: str = Field(..., description="Human-readable description")
    
    @model_validator(mode='after')
    def validate_permission_id(self):
        """Validate permission ID format."""
        expected_id = f"{self.resource}:{self.action}"
        if self.id != expected_id:
            raise ValueError(f'Permission ID must be "{expected_id}"')
        return self


class Role(BaseEntity):
    """Role entity for RBAC."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: List[str] = Field(default_factory=list, description="List of permission IDs")
    is_system_role: bool = Field(default=False, description="Whether this is a system-defined role")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate role name."""
        if not v.strip():
            raise ValueError('Role name cannot be empty')
        return v.strip()
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        """Validate permission format."""
        for perm in v:
            if ':' not in perm:
                raise ValueError(f'Invalid permission format: {perm}')
        return v


class User(BaseEntity):
    """User entity with authentication and authorization."""
    
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=200, description="User full name")
    password_hash: str = Field(..., description="Hashed password")
    roles: List[str] = Field(default_factory=list, description="List of role IDs")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User account status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    failed_login_attempts: int = Field(default=0, description="Failed login attempt counter")
    locked_until: Optional[datetime] = Field(None, description="Account lock expiration")
    permissions: List[str] = Field(default_factory=list, description="Aggregated permissions from roles")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.lower()):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate user name."""
        if not v.strip():
            raise ValueError('User name cannot be empty')
        return v.strip()
    
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_locked() and not self.is_deleted()


class NotificationTarget(BaseEntity):
    """Hierarchical notification target for geographic or organizational grouping."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Target name")
    description: Optional[str] = Field(None, max_length=1000, description="Target description")
    parent_id: Optional[str] = Field(None, description="Parent target ID for hierarchy")
    children_ids: List[str] = Field(default_factory=list, description="Child target IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional target metadata")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate target name."""
        if not v.strip():
            raise ValueError('Target name cannot be empty')
        return v.strip()
    
    @model_validator(mode='after')
    def validate_hierarchy(self):
        """Validate hierarchy constraints."""
        # Cannot be parent of itself
        if self.parent_id and self.parent_id == self.id:
            raise ValueError('Target cannot be parent of itself')
        
        return self


class NotificationCategory(BaseEntity):
    """Notification category for routing and classification."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    color: Optional[str] = Field(None, description="UI color code")
    icon: Optional[str] = Field(None, description="UI icon identifier")
    target_ids: List[str] = Field(default_factory=list, description="Associated target IDs")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate category name."""
        if not v.strip():
            raise ValueError('Category name cannot be empty')
        return v.strip()
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        """Validate color format."""
        if v is None:
            return v
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color code')
        return v


class Endpoint(BaseEntity):
    """External endpoint configuration for message dispatch."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Endpoint name")
    description: Optional[str] = Field(None, max_length=500, description="Endpoint description")
    url: str = Field(..., description="Endpoint URL")
    data_mapping: Dict[str, Any] = Field(..., description="JSONPath data transformation mapping")
    category_ids: List[str] = Field(default_factory=list, description="Associated category IDs")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Retry attempts")
    is_active: bool = Field(default=True, description="Whether endpoint is active")
    schema_version: int = Field(default=1, description="Schema version")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate endpoint name."""
        if not v.strip():
            raise ValueError('Endpoint name cannot be empty')
        return v.strip()
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate URL format."""
        import re
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, v):
            raise ValueError('Invalid URL format')
        return v
    
    @field_validator('data_mapping')
    @classmethod
    def validate_data_mapping(cls, v):
        """Validate data mapping structure."""
        if not isinstance(v, dict):
            raise ValueError('Data mapping must be a dictionary')
        return v


class Notification(BaseEntity):
    """Core notification entity."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, max_length=2000, description="Notification body")
    severity: NotificationSeverity = Field(..., description="Notification severity level")
    origin: str = Field(..., description="Source system or service")
    original_payload: Dict[str, Any] = Field(..., description="Original webhook payload")
    base_target_id: Optional[str] = Field(None, description="Base target for hierarchy expansion")
    target_ids: List[str] = Field(default_factory=list, description="Selected target IDs")
    category_ids: List[str] = Field(default_factory=list, description="Selected category IDs")
    status: NotificationStatus = Field(default=NotificationStatus.RECEIVED, description="Workflow status")
    denial_reason: Optional[str] = Field(None, description="Reason for denial")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approved_by: Optional[str] = Field(None, description="User ID who approved")
    denied_at: Optional[datetime] = Field(None, description="Denial timestamp")
    denied_by: Optional[str] = Field(None, description="User ID who denied")
    dispatched_at: Optional[datetime] = Field(None, description="Dispatch timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    schema_version: int = Field(default=2, description="Schema version")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate notification title."""
        if not v.strip():
            raise ValueError('Notification title cannot be empty')
        return v.strip()
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v):
        """Validate notification body."""
        if not v.strip():
            raise ValueError('Notification body cannot be empty')
        return v.strip()
    
    @field_validator('origin')
    @classmethod
    def validate_origin(cls, v):
        """Validate origin."""
        if not v.strip():
            raise ValueError('Origin cannot be empty')
        return v.strip()
    
    @model_validator(mode='after')
    def validate_status_transitions(self):
        """Validate status-dependent fields."""
        if self.status == NotificationStatus.DENIED and not self.denial_reason:
            raise ValueError('Denial reason is required when status is denied')
        
        if self.status == NotificationStatus.APPROVED and not self.approved_by:
            raise ValueError('approved_by is required when status is approved')
        
        if self.status == NotificationStatus.DENIED and not self.denied_by:
            raise ValueError('denied_by is required when status is denied')
        
        return self
    
    def can_approve(self) -> bool:
        """Check if notification can be approved."""
        return self.status == NotificationStatus.RECEIVED and not self.is_deleted()
    
    def can_deny(self) -> bool:
        """Check if notification can be denied."""
        return self.status == NotificationStatus.RECEIVED and not self.is_deleted()
    
    def approve(self, user_id: str, target_ids: List[str], category_ids: List[str]) -> None:
        """Approve the notification."""
        if not self.can_approve():
            raise ValueError('Notification cannot be approved in current state')
        
        self.status = NotificationStatus.APPROVED
        self.approved_by = user_id
        self.approved_at = datetime.utcnow()
        self.target_ids = target_ids
        self.category_ids = category_ids
        self.update_timestamp(user_id)
    
    def deny(self, user_id: str, reason: str) -> None:
        """Deny the notification."""
        if not self.can_deny():
            raise ValueError('Notification cannot be denied in current state')
        
        self.status = NotificationStatus.DENIED
        self.denied_by = user_id
        self.denied_at = datetime.utcnow()
        self.denial_reason = reason
        self.update_timestamp(user_id)
    
    def mark_dispatched(self, user_id: str) -> None:
        """Mark notification as dispatched."""
        if self.status != NotificationStatus.APPROVED:
            raise ValueError('Only approved notifications can be marked as dispatched')
        
        self.status = NotificationStatus.DISPATCHED
        self.dispatched_at = datetime.utcnow()
        self.update_timestamp(user_id)


class AuditLog(BaseModel):
    """Audit log entry for compliance and accountability."""
    
    id: str = Field(default_factory=lambda: str(__import__('bson').ObjectId()), description="Unique identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Action timestamp")
    user_id: str = Field(..., description="User who performed the action")
    organization_id: str = Field(..., description="Organization scope")
    entity: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity identifier")
    action: str = Field(..., description="Action performed")
    before: Optional[Dict[str, Any]] = Field(None, description="State before action")
    after: Optional[Dict[str, Any]] = Field(None, description="State after action")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    session_id: Optional[str] = Field(None, description="Session identifier")
    trace_id: Optional[str] = Field(None, description="OpenTelemetry trace ID")
    span_id: Optional[str] = Field(None, description="OpenTelemetry span ID")
    schema_version: int = Field(default=1, description="Schema version")
    
    model_config = ConfigDict(
        use_enum_values=True
    )
    
    @field_validator('entity')
    @classmethod
    def validate_entity(cls, v):
        """Validate entity type."""
        valid_entities = [
            'organization', 'user', 'role', 'notification', 
            'notification_target', 'notification_category', 'endpoint'
        ]
        if v not in valid_entities:
            raise ValueError(f'Invalid entity type: {v}')
        return v
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate action type."""
        valid_actions = [
            'create', 'update', 'delete', 'approve', 'deny', 
            'login', 'logout', 'export', 'import'
        ]
        if v not in valid_actions:
            raise ValueError(f'Invalid action type: {v}')
        return v


class UserContext(BaseModel):
    """User context for request processing with authentication and authorization data."""
    
    user_id: str = Field(..., description="Authenticated user ID")
    org_id: str = Field(..., description="User's organization ID")
    email: Optional[str] = Field(None, description="User email")
    name: Optional[str] = Field(None, description="User display name")
    permissions: List[str] = Field(default_factory=list, description="User's effective permissions")
    token_payload: Optional[Dict[str, Any]] = Field(None, description="Original JWT payload")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    model_config = ConfigDict(
        use_enum_values=True
    )
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(perm in self.permissions for perm in permissions)
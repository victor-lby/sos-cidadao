# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Response models for API endpoints with HAL support.
"""

from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class HalLink(BaseModel):
    """HAL link representation."""
    
    href: str = Field(..., description="Link URL")
    method: Optional[str] = Field(None, description="HTTP method")
    type: Optional[str] = Field(None, description="Content type")
    title: Optional[str] = Field(None, description="Link title")
    templated: Optional[bool] = Field(None, description="Whether URL is templated")


class HalResponse(BaseModel, Generic[T]):
    """Base HAL response with links."""
    
    _links: Dict[str, HalLink] = Field(default_factory=dict, description="HAL links")
    
    class Config:
        """Pydantic configuration."""
        allow_population_by_field_name = True


class HalCollection(HalResponse[T]):
    """HAL collection response with embedded items."""
    
    _embedded: Dict[str, List[T]] = Field(default_factory=dict, description="Embedded resources")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class OrganizationResponse(HalResponse):
    """Organization response model."""
    
    id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Organization description")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Organization settings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    updated_by: str = Field(..., description="Last updater user ID")


class UserResponse(HalResponse):
    """User response model (without sensitive data)."""
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    roles: List[str] = Field(default_factory=list, description="Role IDs")
    status: str = Field(..., description="User status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    organization_id: str = Field(..., description="Organization ID")


class RoleResponse(HalResponse):
    """Role response model."""
    
    id: str = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: List[str] = Field(default_factory=list, description="Permission IDs")
    is_system_role: bool = Field(..., description="Whether this is a system role")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    organization_id: str = Field(..., description="Organization ID")


class PermissionResponse(BaseModel):
    """Permission response model."""
    
    id: str = Field(..., description="Permission ID")
    resource: str = Field(..., description="Resource type")
    action: str = Field(..., description="Action type")
    description: str = Field(..., description="Permission description")


class NotificationResponse(HalResponse):
    """Notification response model."""
    
    id: str = Field(..., description="Notification ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    severity: int = Field(..., description="Severity level")
    origin: str = Field(..., description="Source system")
    status: str = Field(..., description="Workflow status")
    target_ids: List[str] = Field(default_factory=list, description="Target IDs")
    category_ids: List[str] = Field(default_factory=list, description="Category IDs")
    denial_reason: Optional[str] = Field(None, description="Denial reason")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approved_by: Optional[str] = Field(None, description="Approver user ID")
    denied_at: Optional[datetime] = Field(None, description="Denial timestamp")
    denied_by: Optional[str] = Field(None, description="Denier user ID")
    dispatched_at: Optional[datetime] = Field(None, description="Dispatch timestamp")
    organization_id: str = Field(..., description="Organization ID")


class NotificationTargetResponse(HalResponse):
    """Notification target response model."""
    
    id: str = Field(..., description="Target ID")
    name: str = Field(..., description="Target name")
    description: Optional[str] = Field(None, description="Target description")
    parent_id: Optional[str] = Field(None, description="Parent target ID")
    children_ids: List[str] = Field(default_factory=list, description="Child target IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Target metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    organization_id: str = Field(..., description="Organization ID")


class NotificationCategoryResponse(HalResponse):
    """Notification category response model."""
    
    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    color: Optional[str] = Field(None, description="UI color code")
    icon: Optional[str] = Field(None, description="UI icon identifier")
    target_ids: List[str] = Field(default_factory=list, description="Associated target IDs")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    organization_id: str = Field(..., description="Organization ID")


class EndpointResponse(HalResponse):
    """Endpoint response model."""
    
    id: str = Field(..., description="Endpoint ID")
    name: str = Field(..., description="Endpoint name")
    description: Optional[str] = Field(None, description="Endpoint description")
    url: str = Field(..., description="Endpoint URL")
    data_mapping: Dict[str, Any] = Field(..., description="Data transformation mapping")
    category_ids: List[str] = Field(default_factory=list, description="Associated category IDs")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    timeout_seconds: int = Field(..., description="Request timeout")
    retry_attempts: int = Field(..., description="Retry attempts")
    is_active: bool = Field(..., description="Whether endpoint is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    organization_id: str = Field(..., description="Organization ID")


class AuditLogResponse(BaseModel):
    """Audit log response model."""
    
    id: str = Field(..., description="Audit log ID")
    timestamp: datetime = Field(..., description="Action timestamp")
    user_id: str = Field(..., description="User who performed action")
    entity: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    action: str = Field(..., description="Action performed")
    before: Optional[Dict[str, Any]] = Field(None, description="State before action")
    after: Optional[Dict[str, Any]] = Field(None, description="State after action")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    trace_id: Optional[str] = Field(None, description="OpenTelemetry trace ID")
    organization_id: str = Field(..., description="Organization ID")


class AuthTokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: UserResponse = Field(..., description="Authenticated user information")


class HealthCheckResponse(HalResponse):
    """Health check response model."""
    
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(..., description="Check timestamp")
    dependencies: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Dependency health")


class ErrorResponse(BaseModel):
    """Error response model following RFC 7807."""
    
    type: str = Field(..., description="Error type URI")
    title: str = Field(..., description="Error title")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Error detail")
    instance: str = Field(..., description="Request instance")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Validation errors")
    _links: Optional[Dict[str, HalLink]] = Field(None, description="HAL links")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field details."""
    
    errors: List[Dict[str, Any]] = Field(..., description="Field validation errors")


class SuccessResponse(BaseModel):
    """Generic success response."""
    
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class BulkOperationResponse(BaseModel):
    """Bulk operation response."""
    
    total: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class ExportResponse(BaseModel):
    """Export operation response."""
    
    format: str = Field(..., description="Export format")
    filename: str = Field(..., description="Generated filename")
    size: int = Field(..., description="File size in bytes")
    download_url: str = Field(..., description="Download URL")
    expires_at: datetime = Field(..., description="Download expiration")


# Collection response types
OrganizationCollection = HalCollection[OrganizationResponse]
UserCollection = HalCollection[UserResponse]
RoleCollection = HalCollection[RoleResponse]
NotificationCollection = HalCollection[NotificationResponse]
NotificationTargetCollection = HalCollection[NotificationTargetResponse]
NotificationCategoryCollection = HalCollection[NotificationCategoryResponse]
EndpointCollection = HalCollection[EndpointResponse]
AuditLogCollection = HalCollection[AuditLogResponse]
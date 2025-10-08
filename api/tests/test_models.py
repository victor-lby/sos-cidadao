# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from models.entities import (
    Organization, User, Role, Permission, Notification, 
    NotificationTarget, NotificationCategory, Endpoint, AuditLog
)
from models.enums import NotificationStatus, NotificationSeverity, UserStatus
from models.requests import (
    CreateOrganizationRequest, CreateUserRequest, CreateNotificationRequest,
    ApproveNotificationRequest, DenyNotificationRequest
)


class TestOrganizationModel:
    """Test Organization model validation."""
    
    def test_valid_organization(self):
        """Test valid organization creation."""
        org_data = {
            "name": "Test Municipality",
            "slug": "test-municipality",
            "description": "Test organization",
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        org = Organization(**org_data)
        assert org.name == "Test Municipality"
        assert org.slug == "test-municipality"
        assert org.schema_version == 1
        assert isinstance(org.created_at, datetime)
    
    def test_invalid_slug_format(self):
        """Test invalid slug format validation."""
        org_data = {
            "name": "Test Municipality",
            "slug": "Test Municipality!",  # Invalid characters
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Organization(**org_data)
        
        assert "Slug must contain only lowercase letters" in str(exc_info.value)
    
    def test_empty_name_validation(self):
        """Test empty name validation."""
        org_data = {
            "name": "   ",  # Empty after strip
            "slug": "test-municipality",
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Organization(**org_data)
        
        assert "Organization name cannot be empty" in str(exc_info.value)


class TestUserModel:
    """Test User model validation."""
    
    def test_valid_user(self):
        """Test valid user creation."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": "$2b$12$test.hash.value",
            "roles": [str(ObjectId())],
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        user = User(**user_data)
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.status == UserStatus.ACTIVE
        assert user.failed_login_attempts == 0
        assert user.schema_version == 1
    
    def test_email_validation(self):
        """Test email format validation."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password_hash": "$2b$12$test.hash.value",
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        with pytest.raises(ValidationError) as exc_info:
            User(**user_data)
        
        assert "Invalid email format" in str(exc_info.value)
    
    def test_email_normalization(self):
        """Test email normalization to lowercase."""
        user_data = {
            "email": "Test@EXAMPLE.COM",
            "name": "Test User",
            "password_hash": "$2b$12$test.hash.value",
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        user = User(**user_data)
        assert user.email == "test@example.com"
    
    def test_user_status_methods(self):
        """Test user status checking methods."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": "$2b$12$test.hash.value",
            "status": UserStatus.ACTIVE,
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        user = User(**user_data)
        assert user.is_active() is True
        assert user.is_locked() is False
        
        # Test locked user
        user.locked_until = datetime.utcnow().replace(year=2025)
        assert user.is_locked() is True
        assert user.is_active() is False


class TestNotificationModel:
    """Test Notification model validation."""
    
    def test_valid_notification(self):
        """Test valid notification creation."""
        notification_data = {
            "title": "Emergency Alert",
            "body": "This is an emergency notification",
            "severity": NotificationSeverity.CRITICAL,
            "origin": "emergency-system",
            "original_payload": {"source": "test", "data": "sample"},
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        notification = Notification(**notification_data)
        assert notification.title == "Emergency Alert"
        assert notification.severity == NotificationSeverity.CRITICAL
        assert notification.status == NotificationStatus.RECEIVED
        assert notification.schema_version == 2
    
    def test_notification_approval(self):
        """Test notification approval method."""
        notification_data = {
            "title": "Test Alert",
            "body": "Test notification",
            "severity": NotificationSeverity.HIGH,
            "origin": "test-system",
            "original_payload": {"test": "data"},
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        notification = Notification(**notification_data)
        user_id = str(ObjectId())
        target_ids = [str(ObjectId())]
        category_ids = [str(ObjectId())]
        
        assert notification.can_approve() is True
        
        notification.approve(user_id, target_ids, category_ids)
        
        assert notification.status == NotificationStatus.APPROVED
        assert notification.approved_by == user_id
        assert notification.target_ids == target_ids
        assert notification.category_ids == category_ids
        assert notification.approved_at is not None
    
    def test_notification_denial(self):
        """Test notification denial method."""
        notification_data = {
            "title": "Test Alert",
            "body": "Test notification",
            "severity": NotificationSeverity.LOW,
            "origin": "test-system",
            "original_payload": {"test": "data"},
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        notification = Notification(**notification_data)
        user_id = str(ObjectId())
        reason = "Invalid notification content"
        
        assert notification.can_deny() is True
        
        notification.deny(user_id, reason)
        
        assert notification.status == NotificationStatus.DENIED
        assert notification.denied_by == user_id
        assert notification.denial_reason == reason
        assert notification.denied_at is not None
    
    def test_invalid_status_transition(self):
        """Test invalid status transitions."""
        notification_data = {
            "title": "Test Alert",
            "body": "Test notification",
            "severity": NotificationSeverity.MEDIUM,
            "origin": "test-system",
            "original_payload": {"test": "data"},
            "status": NotificationStatus.APPROVED,
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        notification = Notification(**notification_data)
        
        # Cannot approve already approved notification
        assert notification.can_approve() is False
        
        with pytest.raises(ValueError) as exc_info:
            notification.approve(str(ObjectId()), [], [])
        
        assert "cannot be approved in current state" in str(exc_info.value)


class TestRoleModel:
    """Test Role model validation."""
    
    def test_valid_role(self):
        """Test valid role creation."""
        role_data = {
            "name": "Administrator",
            "description": "Full system access",
            "permissions": ["notification:read", "notification:approve", "user:create"],
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        role = Role(**role_data)
        assert role.name == "Administrator"
        assert len(role.permissions) == 3
        assert role.is_system_role is False
        assert role.schema_version == 1
    
    def test_invalid_permission_format(self):
        """Test invalid permission format validation."""
        role_data = {
            "name": "Test Role",
            "permissions": ["invalid_permission"],  # Missing colon
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId()),
            "updated_by": str(ObjectId())
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Role(**role_data)
        
        assert "Invalid permission format" in str(exc_info.value)


class TestPermissionModel:
    """Test Permission model validation."""
    
    def test_valid_permission(self):
        """Test valid permission creation."""
        permission_data = {
            "id": "notification:approve",
            "resource": "notification",
            "action": "approve",
            "description": "Approve notifications"
        }
        
        permission = Permission(**permission_data)
        assert permission.id == "notification:approve"
        assert permission.resource == "notification"
        assert permission.action == "approve"
    
    def test_permission_id_validation(self):
        """Test permission ID format validation."""
        permission_data = {
            "id": "wrong:format",
            "resource": "notification",
            "action": "approve",
            "description": "Test permission"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Permission(**permission_data)
        
        assert 'Permission ID must be "notification:approve"' in str(exc_info.value)


class TestAuditLogModel:
    """Test AuditLog model validation."""
    
    def test_valid_audit_log(self):
        """Test valid audit log creation."""
        audit_data = {
            "userId": str(ObjectId()),
            "organization_id": str(ObjectId()),
            "entity": "notification",
            "entityId": str(ObjectId()),
            "action": "approve",
            "before": {"status": "received"},
            "after": {"status": "approved"},
            "ipAddress": "192.168.1.1",
            "traceId": "test-trace-123"
        }
        
        audit_log = AuditLog(**audit_data)
        assert audit_log.entity == "notification"
        assert audit_log.action == "approve"
        assert audit_log.schema_version == 1
        assert isinstance(audit_log.timestamp, datetime)
    
    def test_invalid_entity_type(self):
        """Test invalid entity type validation."""
        audit_data = {
            "userId": str(ObjectId()),
            "organization_id": str(ObjectId()),
            "entity": "invalid_entity",
            "entityId": str(ObjectId()),
            "action": "create"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AuditLog(**audit_data)
        
        assert "Invalid entity type" in str(exc_info.value)
    
    def test_invalid_action_type(self):
        """Test invalid action type validation."""
        audit_data = {
            "userId": str(ObjectId()),
            "organization_id": str(ObjectId()),
            "entity": "notification",
            "entityId": str(ObjectId()),
            "action": "invalid_action"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AuditLog(**audit_data)
        
        assert "Invalid action type" in str(exc_info.value)


class TestRequestModels:
    """Test request model validation."""
    
    def test_create_organization_request(self):
        """Test organization creation request validation."""
        request_data = {
            "name": "New Municipality",
            "slug": "new-municipality",
            "description": "A new test municipality",
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId())
        }
        
        request = CreateOrganizationRequest(**request_data)
        assert request.name == "New Municipality"
        assert request.slug == "new-municipality"
    
    def test_create_user_request_password_validation(self):
        """Test user creation request password validation."""
        request_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "weak",  # Too weak
            "organization_id": str(ObjectId()),
            "created_by": str(ObjectId())
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CreateUserRequest(**request_data)
        
        assert "Password must be at least 8 characters" in str(exc_info.value)
    
    def test_approve_notification_request(self):
        """Test notification approval request validation."""
        request_data = {
            "target_ids": [str(ObjectId()), str(ObjectId())],
            "category_ids": [str(ObjectId())],
            "approvedBy": str(ObjectId())
        }
        
        request = ApproveNotificationRequest(**request_data)
        assert len(request.target_ids) == 2
        assert len(request.category_ids) == 1
    
    def test_deny_notification_request(self):
        """Test notification denial request validation."""
        request_data = {
            "reason": "Content violates policy",
            "deniedBy": str(ObjectId())
        }
        
        request = DenyNotificationRequest(**request_data)
        assert request.reason == "Content violates policy"
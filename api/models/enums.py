# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Enumeration types for the S.O.S Cidadão platform.
"""

from enum import Enum


class NotificationStatus(str, Enum):
    """Notification workflow status enumeration."""
    RECEIVED = "received"
    APPROVED = "approved"
    DENIED = "denied"
    DISPATCHED = "dispatched"


class NotificationSeverity(int, Enum):
    """Notification severity levels (0-5)."""
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class UserStatus(str, Enum):
    """User account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class PermissionAction(str, Enum):
    """Available permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    DENY = "deny"
    EXPORT = "export"


class PermissionResource(str, Enum):
    """Available permission resources."""
    NOTIFICATION = "notification"
    USER = "user"
    ROLE = "role"
    ORGANIZATION = "organization"
    AUDIT_LOG = "audit_log"
    NOTIFICATION_TARGET = "notification_target"
    NOTIFICATION_CATEGORY = "notification_category"
    ENDPOINT = "endpoint"
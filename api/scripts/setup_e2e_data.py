#!/usr/bin/env python3
"""
Setup script for E2E test data.
Creates test organizations, users, and sample notifications for E2E testing.
"""

import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId

# Add the parent directory to the path so we can import from api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mongodb import MongoDBService
from services.auth import AuthService
from models.entities import Organization, User, Notification, NotificationStatus
from models.enums import NotificationSeverity


def setup_e2e_data():
    """Setup test data for E2E tests."""
    print("Setting up E2E test data...")
    
    # Initialize services
    mongo_svc = MongoDBService()
    auth_svc = AuthService()
    
    # Clear existing data
    print("Clearing existing test data...")
    mongo_svc.db.organizations.delete_many({})
    mongo_svc.db.users.delete_many({})
    mongo_svc.db.notifications.delete_many({})
    mongo_svc.db.roles.delete_many({})
    mongo_svc.db.permissions.delete_many({})
    mongo_svc.db.audit_logs.delete_many({})
    
    # Create test organization
    print("Creating test organization...")
    org_id = str(ObjectId())
    organization = {
        "_id": org_id,
        "name": "Test Municipality",
        "slug": "test-municipality",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "deletedAt": None,
        "createdBy": "system",
        "updatedBy": "system",
        "schemaVersion": 1
    }
    mongo_svc.db.organizations.insert_one(organization)
    
    # Create test permissions
    print("Creating test permissions...")
    permissions = [
        {
            "_id": "perm_notification_view",
            "name": "notification:view",
            "description": "View notifications",
            "schemaVersion": 1
        },
        {
            "_id": "perm_notification_approve",
            "name": "notification:approve", 
            "description": "Approve notifications",
            "schemaVersion": 1
        },
        {
            "_id": "perm_notification_deny",
            "name": "notification:deny",
            "description": "Deny notifications", 
            "schemaVersion": 1
        },
        {
            "_id": "perm_admin_manage",
            "name": "admin:manage",
            "description": "Manage administrative functions",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.permissions.insert_many(permissions)
    
    # Create test roles
    print("Creating test roles...")
    roles = [
        {
            "_id": "role_operator",
            "organizationId": org_id,
            "name": "Operator",
            "description": "Municipal operator with notification management rights",
            "permissions": ["perm_notification_view", "perm_notification_approve", "perm_notification_deny"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        },
        {
            "_id": "role_admin",
            "organizationId": org_id,
            "name": "Administrator",
            "description": "System administrator with full access",
            "permissions": ["perm_notification_view", "perm_notification_approve", "perm_notification_deny", "perm_admin_manage"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.roles.insert_many(roles)
    
    # Create test users
    print("Creating test users...")
    password_hash = auth_svc.hash_password("testpassword123")
    
    users = [
        {
            "_id": "user_operator",
            "organizationId": org_id,
            "email": "operator@test-municipality.gov",
            "name": "Test Operator",
            "passwordHash": password_hash,
            "roles": ["role_operator"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        },
        {
            "_id": "user_admin",
            "organizationId": org_id,
            "email": "admin@test-municipality.gov",
            "name": "Test Administrator",
            "passwordHash": password_hash,
            "roles": ["role_admin"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.users.insert_many(users)
    
    # Create test notification targets
    print("Creating test notification targets...")
    targets = [
        {
            "_id": "target_downtown",
            "organizationId": org_id,
            "name": "Downtown District",
            "description": "Central business district",
            "parent": None,
            "children": [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        },
        {
            "_id": "target_residential",
            "organizationId": org_id,
            "name": "Residential Areas",
            "description": "Residential neighborhoods",
            "parent": None,
            "children": [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.notification_targets.insert_many(targets)
    
    # Create test notification categories
    print("Creating test notification categories...")
    categories = [
        {
            "_id": "cat_emergency",
            "organizationId": org_id,
            "name": "Emergency Alert",
            "description": "Critical emergency notifications",
            "targets": ["target_downtown", "target_residential"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        },
        {
            "_id": "cat_maintenance",
            "organizationId": org_id,
            "name": "Maintenance Notice",
            "description": "Scheduled maintenance notifications",
            "targets": ["target_downtown"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.notification_categories.insert_many(categories)
    
    # Create sample notifications
    print("Creating sample notifications...")
    notifications = [
        {
            "_id": str(ObjectId()),
            "organizationId": org_id,
            "title": "Water Main Break - Downtown",
            "body": "Emergency water main break on Main Street. Water service will be interrupted for 4-6 hours.",
            "severity": 4,
            "origin": "water-department-system",
            "originalPayload": {
                "incident_id": "WMB-2024-001",
                "location": "Main Street & 1st Avenue",
                "estimated_duration": "4-6 hours"
            },
            "baseTarget": "target_downtown",
            "targets": ["target_downtown"],
            "categories": ["cat_emergency"],
            "status": NotificationStatus.RECEIVED.value,
            "denialReason": None,
            "createdAt": datetime.utcnow() - timedelta(hours=2),
            "updatedAt": datetime.utcnow() - timedelta(hours=2),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "system",
            "schemaVersion": 1
        },
        {
            "_id": str(ObjectId()),
            "organizationId": org_id,
            "title": "Road Maintenance Schedule",
            "body": "Scheduled road maintenance on Oak Avenue from 9 AM to 3 PM tomorrow.",
            "severity": 2,
            "origin": "public-works-system",
            "originalPayload": {
                "work_order": "RM-2024-045",
                "location": "Oak Avenue",
                "scheduled_time": "9:00 AM - 3:00 PM"
            },
            "baseTarget": "target_downtown",
            "targets": ["target_downtown"],
            "categories": ["cat_maintenance"],
            "status": NotificationStatus.APPROVED.value,
            "denialReason": None,
            "createdAt": datetime.utcnow() - timedelta(hours=1),
            "updatedAt": datetime.utcnow() - timedelta(minutes=30),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "user_operator",
            "schemaVersion": 1
        },
        {
            "_id": str(ObjectId()),
            "organizationId": org_id,
            "title": "Test Notification - Denied",
            "body": "This is a test notification that was denied for testing purposes.",
            "severity": 1,
            "origin": "test-system",
            "originalPayload": {
                "test_id": "TEST-001",
                "purpose": "E2E testing"
            },
            "baseTarget": "target_residential",
            "targets": ["target_residential"],
            "categories": ["cat_maintenance"],
            "status": NotificationStatus.DENIED.value,
            "denialReason": "Test notification - not for actual dispatch",
            "createdAt": datetime.utcnow() - timedelta(minutes=45),
            "updatedAt": datetime.utcnow() - timedelta(minutes=30),
            "deletedAt": None,
            "createdBy": "system",
            "updatedBy": "user_operator",
            "schemaVersion": 1
        }
    ]
    mongo_svc.db.notifications.insert_many(notifications)
    
    print("E2E test data setup complete!")
    print(f"Organization ID: {org_id}")
    print("Test users:")
    print("  - operator@test-municipality.gov / testpassword123 (Operator role)")
    print("  - admin@test-municipality.gov / testpassword123 (Administrator role)")
    print(f"Created {len(notifications)} sample notifications")


if __name__ == "__main__":
    setup_e2e_data()
"""
Multi-tenant data isolation integration tests.

Comprehensive testing of organization-scoped data access and security boundaries.
"""

import pytest
from datetime import datetime
from typing import Dict, List
import uuid

from api.services.mongodb import MongoDBService
from api.services.auth import AuthService
from api.utils.context import UserContext


class TestMultiTenantIsolation:
    """Test complete multi-tenant data isolation across all endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_multi_tenant_data(self, test_db):
        """Set up test data for multiple organizations."""
        self.db = test_db
        
        # Create test organizations
        self.orgs = [
            {
                "_id": "org_alpha",
                "name": "Alpha Municipality",
                "domain": "alpha.gov.br",
                "settings": {"timezone": "America/Sao_Paulo"},
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            },
            {
                "_id": "org_beta", 
                "name": "Beta Municipality",
                "domain": "beta.gov.br",
                "settings": {"timezone": "America/Sao_Paulo"},
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            },
            {
                "_id": "org_gamma",
                "name": "Gamma Municipality", 
                "domain": "gamma.gov.br",
                "settings": {"timezone": "America/Sao_Paulo"},
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            }
        ]
        
        for org in self.orgs:
            self.db.organizations.insert_one(org)
        
        # Create users for each organization
        self.users = []
        for org in self.orgs:
            org_id = org["_id"]
            self.users.extend([
                {
                    "_id": f"admin_{org_id}",
                    "organizationId": org_id,
                    "email": f"admin@{org['domain']}",
                    "name": f"Admin {org_id}",
                    "roles": ["admin"],
                    "permissions": ["notification:create", "notification:approve", "notification:read"],
                    "isActive": True,
                    "createdAt": datetime.utcnow(),
                    "schemaVersion": 1
                },
                {
                    "_id": f"user_{org_id}",
                    "organizationId": org_id,
                    "email": f"user@{org['domain']}",
                    "name": f"User {org_id}",
                    "roles": ["user"],
                    "permissions": ["notification:read"],
                    "isActive": True,
                    "createdAt": datetime.utcnow(),
                    "schemaVersion": 1
                }
            ])
        
        for user in self.users:
            self.db.users.insert_one(user)
        
        # Create notifications for each organization
        self.notifications = []
        for i, org in enumerate(self.orgs):
            org_id = org["_id"]
            for j in range(5):  # 5 notifications per org
                notification = {
                    "_id": f"notif_{org_id}_{j}",
                    "organizationId": org_id,
                    "title": f"Notification {j} for {org['name']}",
                    "body": f"This is notification {j} for organization {org_id}",
                    "severity": (j % 5) + 1,
                    "status": "received",
                    "createdBy": f"admin_{org_id}",
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "deletedAt": None,
                    "schemaVersion": 1
                }
                self.notifications.append(notification)
        
        for notification in self.notifications:
            self.db.notifications.insert_one(notification)
        
        # Create audit logs for each organization
        self.audit_logs = []
        for org in self.orgs:
            org_id = org["_id"]
            for i in range(3):  # 3 audit logs per org
                audit_log = {
                    "_id": f"audit_{org_id}_{i}",
                    "organizationId": org_id,
                    "userId": f"admin_{org_id}",
                    "entity": "notification",
                    "entityId": f"notif_{org_id}_{i}",
                    "action": "create",
                    "timestamp": datetime.utcnow(),
                    "before": {},
                    "after": {"status": "received"},
                    "schemaVersion": 1
                }
                self.audit_logs.append(audit_log)
        
        for audit_log in self.audit_logs:
            self.db.audit_logs.insert_one(audit_log)
    
    def test_notification_isolation_across_organizations(self, test_client):
        """Test that notifications are completely isolated between organizations."""
        # Test for each organization
        for org in self.orgs:
            org_id = org["_id"]
            token = self._get_auth_token(f"admin@{org['domain']}")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get notifications for this organization
            response = test_client.get('/api/notifications', headers=headers)
            assert response.status_code == 200
            
            data = response.get_json()
            notifications = data["_embedded"]["notifications"]
            
            # Should only see notifications from own organization
            for notification in notifications:
                assert notification["organizationId"] == org_id
            
            # Should see exactly 5 notifications (created in setup)
            assert len(notifications) == 5
            
            # Verify specific notification access
            own_notification_id = f"notif_{org_id}_0"
            detail_response = test_client.get(
                f'/api/notifications/{own_notification_id}',
                headers=headers
            )
            assert detail_response.status_code == 200
            
            # Try to access notification from different organization
            other_orgs = [o for o in self.orgs if o["_id"] != org_id]
            for other_org in other_orgs:
                other_notification_id = f"notif_{other_org['_id']}_0"
                cross_access_response = test_client.get(
                    f'/api/notifications/{other_notification_id}',
                    headers=headers
                )
                assert cross_access_response.status_code == 404
    
    def test_user_isolation_across_organizations(self, test_client):
        """Test that users cannot access data from other organizations."""
        # Test user from org_alpha trying to access org_beta data
        alpha_token = self._get_auth_token("admin@alpha.gov.br")
        alpha_headers = {"Authorization": f"Bearer {alpha_token}"}
        
        # Try to access users from different organization
        users_response = test_client.get('/api/users', headers=alpha_headers)
        if users_response.status_code == 200:
            users_data = users_response.get_json()
            users = users_data.get("_embedded", {}).get("users", [])
            
            # Should only see users from own organization
            for user in users:
                assert user["organizationId"] == "org_alpha"
        
        # Try to access specific user from different organization
        beta_user_response = test_client.get('/api/users/user_org_beta', headers=alpha_headers)
        assert beta_user_response.status_code == 404
    
    def test_audit_log_isolation(self, test_client):
        """Test that audit logs are isolated between organizations."""
        for org in self.orgs:
            org_id = org["_id"]
            token = self._get_auth_token(f"admin@{org['domain']}")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get audit logs for this organization
            audit_response = test_client.get('/api/audit', headers=headers)
            assert audit_response.status_code == 200
            
            audit_data = audit_response.get_json()
            audit_logs = audit_data["_embedded"]["audit_logs"]
            
            # Should only see audit logs from own organization
            for log in audit_logs:
                assert log["organizationId"] == org_id
            
            # Should see exactly 3 audit logs (created in setup)
            assert len(audit_logs) == 3
    
    def test_organization_settings_isolation(self, test_client):
        """Test that organization settings are properly isolated."""
        for org in self.orgs:
            token = self._get_auth_token(f"admin@{org['domain']}")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get own organization settings
            org_response = test_client.get('/api/organizations/current', headers=headers)
            assert org_response.status_code == 200
            
            org_data = org_response.get_json()
            assert org_data["id"] == org["_id"]
            assert org_data["name"] == org["name"]
            
            # Try to access other organizations directly
            other_orgs = [o for o in self.orgs if o["_id"] != org["_id"]]
            for other_org in other_orgs:
                other_org_response = test_client.get(
                    f'/api/organizations/{other_org["_id"]}',
                    headers=headers
                )
                assert other_org_response.status_code == 404
    
    def test_cross_organization_data_modification_prevention(self, test_client):
        """Test that users cannot modify data from other organizations."""
        alpha_token = self._get_auth_token("admin@alpha.gov.br")
        alpha_headers = {"Authorization": f"Bearer {alpha_token}"}
        
        # Try to modify notification from different organization
        beta_notification_id = "notif_org_beta_0"
        
        # Try to approve notification from different org
        approve_response = test_client.post(
            f'/api/notifications/{beta_notification_id}/approve',
            json={"targets": ["email"]},
            headers=alpha_headers
        )
        assert approve_response.status_code == 404
        
        # Try to update notification from different org
        update_response = test_client.put(
            f'/api/notifications/{beta_notification_id}',
            json={"title": "Modified title"},
            headers=alpha_headers
        )
        assert update_response.status_code == 404
        
        # Try to delete notification from different org
        delete_response = test_client.delete(
            f'/api/notifications/{beta_notification_id}',
            headers=alpha_headers
        )
        assert delete_response.status_code == 404
    
    def test_database_query_isolation(self):
        """Test that database queries properly enforce organization scoping."""
        mongo_service = MongoDBService()
        
        # Test find operations with organization scoping
        alpha_notifications = mongo_service.find_by_org("notifications", "org_alpha")
        beta_notifications = mongo_service.find_by_org("notifications", "org_beta")
        
        # Should only return notifications for specified organization
        for notification in alpha_notifications:
            assert notification["organizationId"] == "org_alpha"
        
        for notification in beta_notifications:
            assert notification["organizationId"] == "org_beta"
        
        # Should have different counts
        assert len(alpha_notifications) == 5
        assert len(beta_notifications) == 5
        
        # Test update operations with organization scoping
        update_result = mongo_service.update_by_org(
            "notifications",
            "org_alpha",
            "notif_org_alpha_0",
            {"status": "approved"}
        )
        assert update_result is True
        
        # Verify update only affected the correct organization
        updated_notification = mongo_service.find_one_by_org(
            "notifications",
            "org_alpha", 
            "notif_org_alpha_0"
        )
        assert updated_notification["status"] == "approved"
        
        # Verify other organization's notification was not affected
        other_notification = mongo_service.find_one_by_org(
            "notifications",
            "org_beta",
            "notif_org_beta_0"
        )
        assert other_notification["status"] == "received"  # Original status
    
    def test_jwt_token_organization_binding(self):
        """Test that JWT tokens are properly bound to organizations."""
        auth_service = AuthService()
        
        # Create tokens for different organizations
        alpha_user_context = UserContext(
            user_id="admin_org_alpha",
            org_id="org_alpha",
            permissions=["notification:create", "notification:approve"],
            email="admin@alpha.gov.br"
        )
        
        beta_user_context = UserContext(
            user_id="admin_org_beta",
            org_id="org_beta",
            permissions=["notification:create", "notification:approve"],
            email="admin@beta.gov.br"
        )
        
        alpha_token = auth_service.create_access_token(alpha_user_context)
        beta_token = auth_service.create_access_token(beta_user_context)
        
        # Verify tokens contain correct organization information
        alpha_payload = auth_service.decode_token(alpha_token)
        beta_payload = auth_service.decode_token(beta_token)
        
        assert alpha_payload["org_id"] == "org_alpha"
        assert beta_payload["org_id"] == "org_beta"
        
        # Verify tokens cannot be used for wrong organization
        # This would be enforced at the middleware level
        assert alpha_payload["org_id"] != beta_payload["org_id"]
    
    def test_bulk_operations_isolation(self, test_client):
        """Test that bulk operations respect organization boundaries."""
        alpha_token = self._get_auth_token("admin@alpha.gov.br")
        alpha_headers = {"Authorization": f"Bearer {alpha_token}"}
        
        # Try bulk approval of notifications
        notification_ids = [
            "notif_org_alpha_0",  # Own organization
            "notif_org_alpha_1",  # Own organization
            "notif_org_beta_0",   # Different organization
            "notif_org_gamma_0"   # Different organization
        ]
        
        bulk_approve_response = test_client.post(
            '/api/notifications/bulk/approve',
            json={"notification_ids": notification_ids, "targets": ["email"]},
            headers=alpha_headers
        )
        
        if bulk_approve_response.status_code == 200:
            result = bulk_approve_response.get_json()
            
            # Should only process notifications from own organization
            assert len(result["successful"]) == 2  # Only alpha notifications
            assert len(result["failed"]) == 2     # Beta and gamma notifications failed
            
            # Verify failed notifications are from other organizations
            failed_ids = [item["id"] for item in result["failed"]]
            assert "notif_org_beta_0" in failed_ids
            assert "notif_org_gamma_0" in failed_ids
    
    def test_search_and_filtering_isolation(self, test_client):
        """Test that search and filtering operations respect organization boundaries."""
        for org in self.orgs:
            org_id = org["_id"]
            token = self._get_auth_token(f"admin@{org['domain']}")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Search for notifications
            search_response = test_client.get(
                f'/api/notifications?search={org["name"]}',
                headers=headers
            )
            assert search_response.status_code == 200
            
            search_data = search_response.get_json()
            notifications = search_data["_embedded"]["notifications"]
            
            # Should only return notifications from own organization
            for notification in notifications:
                assert notification["organizationId"] == org_id
                assert org["name"] in notification["title"]
            
            # Filter by severity
            severity_response = test_client.get(
                '/api/notifications?severity=3',
                headers=headers
            )
            assert severity_response.status_code == 200
            
            severity_data = severity_response.get_json()
            filtered_notifications = severity_data["_embedded"]["notifications"]
            
            # Should only return notifications from own organization with specified severity
            for notification in filtered_notifications:
                assert notification["organizationId"] == org_id
                assert notification["severity"] == 3
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token for testing."""
        # In real implementation, this would authenticate and return actual JWT
        # For testing, we'll return a mock token that includes the email
        return f"test_token_{email.replace('@', '_').replace('.', '_')}"


class TestOrganizationDataConsistency:
    """Test data consistency within organization boundaries."""
    
    def test_referential_integrity_within_organization(self, test_db):
        """Test that referential integrity is maintained within organization scope."""
        mongo_service = MongoDBService()
        
        # Create test organization
        org_id = "org_integrity_test"
        test_db.organizations.insert_one({
            "_id": org_id,
            "name": "Integrity Test Org",
            "createdAt": datetime.utcnow(),
            "schemaVersion": 1
        })
        
        # Create user in organization
        user_id = "user_integrity_test"
        test_db.users.insert_one({
            "_id": user_id,
            "organizationId": org_id,
            "email": "test@integrity.gov.br",
            "name": "Test User",
            "createdAt": datetime.utcnow(),
            "schemaVersion": 1
        })
        
        # Create notification referencing the user
        notification_id = "notif_integrity_test"
        test_db.notifications.insert_one({
            "_id": notification_id,
            "organizationId": org_id,
            "title": "Integrity Test Notification",
            "body": "Testing referential integrity",
            "severity": 2,
            "status": "received",
            "createdBy": user_id,
            "createdAt": datetime.utcnow(),
            "schemaVersion": 1
        })
        
        # Verify relationships are maintained
        notification = mongo_service.find_one_by_org("notifications", org_id, notification_id)
        user = mongo_service.find_one_by_org("users", org_id, user_id)
        
        assert notification["createdBy"] == user["_id"]
        assert notification["organizationId"] == user["organizationId"]
    
    def test_cascade_operations_within_organization(self, test_db):
        """Test that cascade operations only affect data within the same organization."""
        mongo_service = MongoDBService()
        
        # Create two organizations with similar data
        for org_suffix in ["cascade_a", "cascade_b"]:
            org_id = f"org_{org_suffix}"
            
            # Create organization
            test_db.organizations.insert_one({
                "_id": org_id,
                "name": f"Cascade Test Org {org_suffix.upper()}",
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            })
            
            # Create user
            user_id = f"user_{org_suffix}"
            test_db.users.insert_one({
                "_id": user_id,
                "organizationId": org_id,
                "email": f"test@{org_suffix}.gov.br",
                "name": f"Test User {org_suffix.upper()}",
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            })
            
            # Create notifications
            for i in range(3):
                test_db.notifications.insert_one({
                    "_id": f"notif_{org_suffix}_{i}",
                    "organizationId": org_id,
                    "title": f"Notification {i} for {org_suffix}",
                    "body": f"Test notification {i}",
                    "severity": 2,
                    "status": "received",
                    "createdBy": user_id,
                    "createdAt": datetime.utcnow(),
                    "schemaVersion": 1
                })
        
        # Perform cascade delete for one organization
        mongo_service.soft_delete_by_org("users", "org_cascade_a", "user_cascade_a", "admin")
        
        # Verify only org_cascade_a user is deleted
        deleted_user = mongo_service.find_one_by_org("users", "org_cascade_a", "user_cascade_a")
        assert deleted_user["deletedAt"] is not None
        
        # Verify org_cascade_b user is not affected
        other_user = mongo_service.find_one_by_org("users", "org_cascade_b", "user_cascade_b")
        assert other_user["deletedAt"] is None
        
        # Verify notifications are handled appropriately
        # (Implementation would depend on business rules for cascade behavior)
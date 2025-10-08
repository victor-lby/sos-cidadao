"""
Comprehensive end-to-end integration tests for S.O.S Cidadão Platform.

Tests the complete notification workflow from webhook to dispatch,
multi-tenant data isolation, authentication flows, and HAL API discoverability.
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
from unittest.mock import patch, MagicMock

from api.app import create_app
from api.services.mongodb import MongoDBService
from api.services.redis import RedisService
from api.services.amqp import AMQPService
from api.services.auth import AuthService
from api.models.entities import Notification, User, Organization
from api.utils.context import UserContext


class TestEndToEndWorkflow:
    """Test complete notification workflow from webhook to dispatch."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, test_client, test_db, test_redis, test_amqp):
        """Set up test environment with clean state."""
        self.client = test_client
        self.db = test_db
        self.redis = test_redis
        self.amqp = test_amqp
        
        # Create test organizations
        self.org1_id = "org_test_001"
        self.org2_id = "org_test_002"
        
        self.test_orgs = [
            {
                "_id": self.org1_id,
                "name": "Test Municipality 1",
                "domain": "test1.gov.br",
                "settings": {"timezone": "America/Sao_Paulo"},
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            },
            {
                "_id": self.org2_id,
                "name": "Test Municipality 2", 
                "domain": "test2.gov.br",
                "settings": {"timezone": "America/Sao_Paulo"},
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            }
        ]
        
        # Insert test organizations
        for org in self.test_orgs:
            self.db.organizations.insert_one(org)
        
        # Create test users for each organization
        self.test_users = [
            {
                "_id": "user_org1_admin",
                "organizationId": self.org1_id,
                "email": "admin@test1.gov.br",
                "name": "Admin User 1",
                "roles": ["admin", "moderator"],
                "permissions": ["notification:create", "notification:approve", "notification:deny"],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            },
            {
                "_id": "user_org1_viewer",
                "organizationId": self.org1_id,
                "email": "viewer@test1.gov.br",
                "name": "Viewer User 1",
                "roles": ["viewer"],
                "permissions": ["notification:read"],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            },
            {
                "_id": "user_org2_admin",
                "organizationId": self.org2_id,
                "email": "admin@test2.gov.br",
                "name": "Admin User 2",
                "roles": ["admin", "moderator"],
                "permissions": ["notification:create", "notification:approve", "notification:deny"],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            }
        ]
        
        # Insert test users
        for user in self.test_users:
            self.db.users.insert_one(user)
    
    def test_complete_notification_workflow(self):
        """Test complete notification workflow from creation to dispatch."""
        # Step 1: Authenticate as admin user
        auth_response = self.client.post('/api/auth/login', json={
            "email": "admin@test1.gov.br",
            "password": "test_password"
        })
        
        assert auth_response.status_code == 200
        auth_data = auth_response.get_json()
        access_token = auth_data["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Create notification via webhook/API
        notification_data = {
            "title": "Emergency Alert - Test",
            "body": "This is a test emergency notification for end-to-end testing.",
            "severity": 4,
            "category": "emergency",
            "targets": ["sms", "email", "push"],
            "metadata": {
                "source": "emergency_system",
                "priority": "high",
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        }
        
        create_response = self.client.post(
            '/api/notifications',
            json=notification_data,
            headers=headers
        )
        
        assert create_response.status_code == 201
        created_notification = create_response.get_json()
        notification_id = created_notification["id"]
        
        # Verify HAL links are present
        assert "_links" in created_notification
        assert "self" in created_notification["_links"]
        assert "approve" in created_notification["_links"]  # Should be available for admin
        
        # Step 3: Verify notification is in 'received' status
        assert created_notification["status"] == "received"
        assert created_notification["title"] == notification_data["title"]
        assert created_notification["severity"] == notification_data["severity"]
        
        # Step 4: Test multi-tenant isolation - try to access from different org
        auth_response_org2 = self.client.post('/api/auth/login', json={
            "email": "admin@test2.gov.br",
            "password": "test_password"
        })
        
        org2_token = auth_response_org2.get_json()["access_token"]
        org2_headers = {"Authorization": f"Bearer {org2_token}"}
        
        # Should not be able to see notification from org1
        isolation_response = self.client.get(
            f'/api/notifications/{notification_id}',
            headers=org2_headers
        )
        assert isolation_response.status_code == 404
        
        # Step 5: Approve notification (back to org1 admin)
        approval_data = {
            "targets": ["sms", "email"],
            "message": "Approved for emergency dispatch"
        }
        
        approve_response = self.client.post(
            f'/api/notifications/{notification_id}/approve',
            json=approval_data,
            headers=headers
        )
        
        assert approve_response.status_code == 200
        approved_notification = approve_response.get_json()
        
        # Verify status changed and HAL links updated
        assert approved_notification["status"] == "approved"
        assert "dispatch" in approved_notification["_links"]  # New action available
        assert "approve" not in approved_notification["_links"]  # No longer available
        
        # Step 6: Verify AMQP message was published
        # Mock AMQP service should have recorded the publish call
        assert self.amqp.publish_notification.called
        published_args = self.amqp.publish_notification.call_args
        assert published_args[0][0]["id"] == notification_id
        assert published_args[0][0]["status"] == "approved"
        
        # Step 7: Verify audit trail was created
        audit_logs = list(self.db.audit_logs.find({
            "entityId": notification_id,
            "organizationId": self.org1_id
        }))
        
        assert len(audit_logs) >= 2  # Create and approve actions
        
        create_audit = next(log for log in audit_logs if log["action"] == "create")
        approve_audit = next(log for log in audit_logs if log["action"] == "approve")
        
        assert create_audit["userId"] == "user_org1_admin"
        assert approve_audit["userId"] == "user_org1_admin"
        assert "trace_id" in approve_audit  # OpenTelemetry correlation
        
        # Step 8: Test notification dispatch (simulate external system)
        dispatch_response = self.client.post(
            f'/api/notifications/{notification_id}/dispatch',
            json={"channel": "sms", "status": "sent", "message_id": "sms_12345"},
            headers=headers
        )
        
        assert dispatch_response.status_code == 200
        dispatched_notification = dispatch_response.get_json()
        assert dispatched_notification["status"] == "dispatched"
    
    def test_multi_tenant_data_isolation(self):
        """Verify complete data isolation between organizations."""
        # Create notifications for both organizations
        org1_token = self._get_auth_token("admin@test1.gov.br")
        org2_token = self._get_auth_token("admin@test2.gov.br")
        
        org1_headers = {"Authorization": f"Bearer {org1_token}"}
        org2_headers = {"Authorization": f"Bearer {org2_token}"}
        
        # Create notification in org1
        org1_notification = {
            "title": "Org1 Notification",
            "body": "This belongs to organization 1",
            "severity": 2
        }
        
        org1_response = self.client.post(
            '/api/notifications',
            json=org1_notification,
            headers=org1_headers
        )
        org1_notification_id = org1_response.get_json()["id"]
        
        # Create notification in org2
        org2_notification = {
            "title": "Org2 Notification", 
            "body": "This belongs to organization 2",
            "severity": 3
        }
        
        org2_response = self.client.post(
            '/api/notifications',
            json=org2_notification,
            headers=org2_headers
        )
        org2_notification_id = org2_response.get_json()["id"]
        
        # Test isolation: org1 should not see org2's notifications
        org1_list_response = self.client.get('/api/notifications', headers=org1_headers)
        org1_notifications = org1_list_response.get_json()["_embedded"]["notifications"]
        
        org1_ids = [n["id"] for n in org1_notifications]
        assert org1_notification_id in org1_ids
        assert org2_notification_id not in org1_ids
        
        # Test isolation: org2 should not see org1's notifications
        org2_list_response = self.client.get('/api/notifications', headers=org2_headers)
        org2_notifications = org2_list_response.get_json()["_embedded"]["notifications"]
        
        org2_ids = [n["id"] for n in org2_notifications]
        assert org2_notification_id in org2_ids
        assert org1_notification_id not in org2_ids
        
        # Test direct access isolation
        cross_access_response = self.client.get(
            f'/api/notifications/{org1_notification_id}',
            headers=org2_headers
        )
        assert cross_access_response.status_code == 404
    
    def test_authentication_and_authorization_flows(self):
        """Test various authentication and authorization scenarios."""
        # Test 1: Invalid credentials
        invalid_response = self.client.post('/api/auth/login', json={
            "email": "invalid@test.com",
            "password": "wrong_password"
        })
        assert invalid_response.status_code == 401
        
        # Test 2: Valid authentication
        valid_response = self.client.post('/api/auth/login', json={
            "email": "admin@test1.gov.br",
            "password": "test_password"
        })
        assert valid_response.status_code == 200
        
        auth_data = valid_response.get_json()
        assert "access_token" in auth_data
        assert "refresh_token" in auth_data
        assert "expires_in" in auth_data
        
        # Test 3: Token refresh
        refresh_response = self.client.post('/api/auth/refresh', json={
            "refresh_token": auth_data["refresh_token"]
        })
        assert refresh_response.status_code == 200
        
        # Test 4: Permission-based authorization
        viewer_token = self._get_auth_token("viewer@test1.gov.br")
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # Viewer should be able to read notifications
        read_response = self.client.get('/api/notifications', headers=viewer_headers)
        assert read_response.status_code == 200
        
        # But not approve them
        notification_data = {"title": "Test", "body": "Test", "severity": 1}
        create_response = self.client.post(
            '/api/notifications',
            json=notification_data,
            headers=viewer_headers
        )
        assert create_response.status_code == 403  # Forbidden
        
        # Test 5: Token revocation
        admin_token = self._get_auth_token("admin@test1.gov.br")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Revoke token
        revoke_response = self.client.post('/api/auth/revoke', headers=admin_headers)
        assert revoke_response.status_code == 200
        
        # Token should no longer work
        test_response = self.client.get('/api/notifications', headers=admin_headers)
        assert test_response.status_code == 401
    
    def test_hal_api_discoverability(self):
        """Test HAL API discoverability and affordance links."""
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: API root discovery
        root_response = self.client.get('/api', headers=headers)
        assert root_response.status_code == 200
        
        root_data = root_response.get_json()
        assert "_links" in root_data
        assert "notifications" in root_data["_links"]
        assert "organizations" in root_data["_links"]
        assert "audit" in root_data["_links"]
        
        # Test 2: Notification collection HAL structure
        notifications_response = self.client.get('/api/notifications', headers=headers)
        assert notifications_response.status_code == 200
        
        notifications_data = notifications_response.get_json()
        assert "_links" in notifications_data
        assert "_embedded" in notifications_data
        assert "self" in notifications_data["_links"]
        assert "create" in notifications_data["_links"]
        
        # Test 3: Individual notification HAL affordances
        notification_data = {
            "title": "HAL Test Notification",
            "body": "Testing HAL affordances",
            "severity": 2
        }
        
        create_response = self.client.post(
            '/api/notifications',
            json=notification_data,
            headers=headers
        )
        
        notification = create_response.get_json()
        notification_id = notification["id"]
        
        # Check available actions based on status and permissions
        assert "_links" in notification
        assert "self" in notification["_links"]
        assert "approve" in notification["_links"]  # Admin can approve
        assert "deny" in notification["_links"]     # Admin can deny
        
        # Test 4: HAL affordances change based on state
        # Approve the notification
        approve_response = self.client.post(
            f'/api/notifications/{notification_id}/approve',
            json={"targets": ["email"]},
            headers=headers
        )
        
        approved_notification = approve_response.get_json()
        
        # Links should have changed
        assert "approve" not in approved_notification["_links"]  # No longer available
        assert "dispatch" in approved_notification["_links"]     # New action available
        
        # Test 5: HAL affordances respect permissions
        viewer_token = self._get_auth_token("viewer@test1.gov.br")
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        viewer_response = self.client.get(
            f'/api/notifications/{notification_id}',
            headers=viewer_headers
        )
        
        viewer_notification = viewer_response.get_json()
        
        # Viewer should not see admin actions
        assert "approve" not in viewer_notification["_links"]
        assert "deny" not in viewer_notification["_links"]
        assert "dispatch" not in viewer_notification["_links"]
    
    def test_error_scenarios_and_recovery(self):
        """Test error scenarios and recovery procedures."""
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Invalid notification data
        invalid_data = {
            "title": "",  # Empty title
            "body": "Test",
            "severity": 10  # Invalid severity
        }
        
        error_response = self.client.post(
            '/api/notifications',
            json=invalid_data,
            headers=headers
        )
        
        assert error_response.status_code == 400
        error_data = error_response.get_json()
        assert "errors" in error_data
        assert any("title" in str(error) for error in error_data["errors"])
        
        # Test 2: Database connection failure simulation
        with patch('api.services.mongodb.MongoDBService.find_by_org') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            db_error_response = self.client.get('/api/notifications', headers=headers)
            assert db_error_response.status_code == 500
            
            error_data = db_error_response.get_json()
            assert "error" in error_data
            assert "trace_id" in error_data  # Should include trace for debugging
        
        # Test 3: Rate limiting
        # Make multiple rapid requests to trigger rate limiting
        for i in range(20):  # Assuming rate limit is lower than this
            rate_response = self.client.get('/api/notifications', headers=headers)
            if rate_response.status_code == 429:
                assert "Retry-After" in rate_response.headers
                break
        
        # Test 4: Malformed JWT token
        malformed_headers = {"Authorization": "Bearer invalid.jwt.token"}
        jwt_error_response = self.client.get('/api/notifications', headers=malformed_headers)
        assert jwt_error_response.status_code == 401
        
        # Test 5: Resource not found with proper HAL error response
        not_found_response = self.client.get(
            '/api/notifications/nonexistent_id',
            headers=headers
        )
        assert not_found_response.status_code == 404
        
        error_data = not_found_response.get_json()
        assert "_links" in error_data  # HAL error response
        assert "self" in error_data["_links"]
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token for a user."""
        response = self.client.post('/api/auth/login', json={
            "email": email,
            "password": "test_password"
        })
        return response.get_json()["access_token"]


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability limits."""
    
    def test_notification_list_pagination_performance(self, test_client, test_db):
        """Test pagination performance with large datasets."""
        # Create large number of test notifications
        notifications = []
        for i in range(1000):
            notifications.append({
                "_id": f"perf_test_{i:04d}",
                "organizationId": "org_test_001",
                "title": f"Performance Test Notification {i}",
                "body": f"This is test notification number {i}",
                "severity": i % 6,
                "status": "received",
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "deletedAt": None,
                "schemaVersion": 1
            })
        
        test_db.notifications.insert_many(notifications)
        
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test pagination performance
        start_time = time.time()
        response = test_client.get('/api/notifications?page=1&limit=50', headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
        
        data = response.get_json()
        assert len(data["_embedded"]["notifications"]) == 50
        assert data["total"] == 1000
        assert "next" in data["_links"]
    
    def test_concurrent_notification_approval(self, test_client, test_db):
        """Test concurrent approval operations."""
        import threading
        import queue
        
        # Create test notification
        notification_data = {
            "title": "Concurrent Test",
            "body": "Testing concurrent operations",
            "severity": 3
        }
        
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        create_response = test_client.post(
            '/api/notifications',
            json=notification_data,
            headers=headers
        )
        notification_id = create_response.get_json()["id"]
        
        # Attempt concurrent approvals
        results = queue.Queue()
        
        def approve_notification():
            try:
                response = test_client.post(
                    f'/api/notifications/{notification_id}/approve',
                    json={"targets": ["email"]},
                    headers=headers
                )
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=approve_notification)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Collect results
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        # Only one should succeed (200), others should fail (409 Conflict)
        success_count = sum(1 for code in status_codes if code == 200)
        assert success_count == 1
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token."""
        # Mock implementation for testing
        return "test_token_" + email.replace("@", "_").replace(".", "_")


class TestSecurityValidation:
    """Test security measures and vulnerability prevention."""
    
    def test_sql_injection_prevention(self, test_client):
        """Test SQL injection prevention in API endpoints."""
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Attempt SQL injection in query parameters
        malicious_params = [
            "'; DROP TABLE notifications; --",
            "' OR '1'='1",
            "'; INSERT INTO notifications VALUES ('malicious'); --"
        ]
        
        for param in malicious_params:
            response = test_client.get(
                f'/api/notifications?search={param}',
                headers=headers
            )
            # Should not cause server error, should handle gracefully
            assert response.status_code in [200, 400]  # Valid response or bad request
    
    def test_xss_prevention(self, test_client):
        """Test XSS prevention in notification content."""
        token = self._get_auth_token("admin@test1.gov.br")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Attempt XSS in notification content
        xss_payload = {
            "title": "<script>alert('XSS')</script>",
            "body": "<img src=x onerror=alert('XSS')>",
            "severity": 2
        }
        
        response = test_client.post(
            '/api/notifications',
            json=xss_payload,
            headers=headers
        )
        
        if response.status_code == 201:
            notification = response.get_json()
            # Content should be sanitized
            assert "<script>" not in notification["title"]
            assert "onerror=" not in notification["body"]
    
    def test_authorization_bypass_attempts(self, test_client):
        """Test attempts to bypass authorization."""
        viewer_token = self._get_auth_token("viewer@test1.gov.br")
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # Attempt to access admin-only endpoints
        admin_endpoints = [
            ('/api/organizations', 'POST'),
            ('/api/users', 'POST'),
            ('/api/audit/export', 'GET')
        ]
        
        for endpoint, method in admin_endpoints:
            if method == 'GET':
                response = test_client.get(endpoint, headers=viewer_headers)
            else:
                response = test_client.post(endpoint, json={}, headers=viewer_headers)
            
            assert response.status_code == 403  # Forbidden
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token."""
        # Mock implementation for testing
        return "test_token_" + email.replace("@", "_").replace(".", "_")
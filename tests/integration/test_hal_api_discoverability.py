"""
HAL API discoverability and affordance link integration tests.

Tests HATEOAS Level-3 implementation with dynamic affordance links
based on resource state and user permissions.
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any
import json

from api.services.hal import HALService
from api.utils.context import UserContext


class TestHALAPIDiscoverability:
    """Test HAL API discoverability and HATEOAS Level-3 implementation."""
    
    @pytest.fixture(autouse=True)
    def setup_hal_test_data(self, test_client, test_db):
        """Set up test data for HAL API testing."""
        self.client = test_client
        self.db = test_db
        
        # Create test organization
        self.org_id = "org_hal_test"
        self.db.organizations.insert_one({
            "_id": self.org_id,
            "name": "HAL Test Organization",
            "domain": "hal-test.gov.br",
            "settings": {"timezone": "America/Sao_Paulo"},
            "createdAt": datetime.utcnow(),
            "schemaVersion": 1
        })
        
        # Create test users with different permission levels
        self.test_users = [
            {
                "_id": "admin_hal_test",
                "organizationId": self.org_id,
                "email": "admin@hal-test.gov.br",
                "name": "HAL Admin User",
                "roles": ["admin", "moderator"],
                "permissions": [
                    "notification:create", "notification:read", "notification:update",
                    "notification:approve", "notification:deny", "notification:dispatch",
                    "organization:read", "organization:update",
                    "user:create", "user:read", "user:update",
                    "audit:read", "audit:export"
                ],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            },
            {
                "_id": "moderator_hal_test",
                "organizationId": self.org_id,
                "email": "moderator@hal-test.gov.br",
                "name": "HAL Moderator User",
                "roles": ["moderator"],
                "permissions": [
                    "notification:create", "notification:read", "notification:update",
                    "notification:approve", "notification:deny"
                ],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            },
            {
                "_id": "viewer_hal_test",
                "organizationId": self.org_id,
                "email": "viewer@hal-test.gov.br",
                "name": "HAL Viewer User",
                "roles": ["viewer"],
                "permissions": ["notification:read"],
                "isActive": True,
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            }
        ]
        
        for user in self.test_users:
            self.db.users.insert_one(user)
    
    def test_api_root_discoverability(self):
        """Test API root endpoint provides complete discoverability."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = self.client.get('/api', headers=headers)
        assert response.status_code == 200
        assert response.headers.get('Content-Type') == 'application/hal+json'
        
        root_data = response.get_json()
        
        # Verify HAL structure
        assert "_links" in root_data
        assert "self" in root_data["_links"]
        assert root_data["_links"]["self"]["href"] == "/api"
        
        # Verify all major resource collections are discoverable
        expected_links = [
            "notifications", "organizations", "users", "audit", "health"
        ]
        
        for link_rel in expected_links:
            assert link_rel in root_data["_links"]
            assert "href" in root_data["_links"][link_rel]
        
        # Verify API metadata
        assert "version" in root_data
        assert "title" in root_data
        assert "description" in root_data
        
        # Verify templated links for parameterized resources
        notifications_link = root_data["_links"]["notifications"]
        if "templated" in notifications_link:
            assert "{?page,limit,status,severity}" in notifications_link["href"]
    
    def test_notification_collection_hal_structure(self):
        """Test notification collection HAL structure and pagination links."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create test notifications
        for i in range(25):  # Create enough for pagination
            notification_data = {
                "title": f"HAL Test Notification {i}",
                "body": f"Testing HAL structure {i}",
                "severity": (i % 5) + 1
            }
            self.client.post('/api/notifications', json=notification_data, headers=headers)
        
        # Test collection endpoint
        response = self.client.get('/api/notifications?page=1&limit=10', headers=headers)
        assert response.status_code == 200
        
        data = response.get_json()
        
        # Verify HAL collection structure
        assert "_links" in data
        assert "_embedded" in data
        assert "notifications" in data["_embedded"]
        
        # Verify pagination links
        assert "self" in data["_links"]
        assert "first" in data["_links"]
        assert "next" in data["_links"]  # Should have next page
        
        # Verify collection metadata
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert data["total"] >= 25
        assert data["page"] == 1
        assert data["limit"] == 10
        
        # Verify individual notification HAL structure
        notifications = data["_embedded"]["notifications"]
        assert len(notifications) == 10  # Page limit
        
        for notification in notifications:
            assert "_links" in notification
            assert "self" in notification["_links"]
            
            # Verify self link is properly formed
            self_href = notification["_links"]["self"]["href"]
            assert f"/api/notifications/{notification['id']}" == self_href
    
    def test_notification_affordance_links_by_status(self):
        """Test that affordance links change based on notification status."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create notification
        notification_data = {
            "title": "Status Transition Test",
            "body": "Testing status-based affordances",
            "severity": 3
        }
        
        create_response = self.client.post('/api/notifications', json=notification_data, headers=headers)
        notification = create_response.get_json()
        notification_id = notification["id"]
        
        # Test 1: 'received' status affordances
        assert notification["status"] == "received"
        received_links = notification["_links"]
        
        assert "self" in received_links
        assert "approve" in received_links
        assert "deny" in received_links
        assert "edit" in received_links
        
        # Should not have dispatch link yet
        assert "dispatch" not in received_links
        
        # Verify link methods
        assert received_links["approve"]["method"] == "POST"
        assert received_links["deny"]["method"] == "POST"
        assert received_links["edit"]["method"] == "PUT"
        
        # Test 2: Approve notification and check new affordances
        approve_response = self.client.post(
            f'/api/notifications/{notification_id}/approve',
            json={"targets": ["email", "sms"]},
            headers=headers
        )
        
        approved_notification = approve_response.get_json()
        assert approved_notification["status"] == "approved"
        
        approved_links = approved_notification["_links"]
        
        # Should have new affordances
        assert "dispatch" in approved_links
        assert "cancel" in approved_links  # Can cancel approved notification
        
        # Should not have approval affordances anymore
        assert "approve" not in approved_links
        assert "deny" not in approved_links
        
        # Test 3: Dispatch notification and check final affordances
        dispatch_response = self.client.post(
            f'/api/notifications/{notification_id}/dispatch',
            json={"channel": "email", "status": "sent"},
            headers=headers
        )
        
        dispatched_notification = dispatch_response.get_json()
        assert dispatched_notification["status"] == "dispatched"
        
        dispatched_links = dispatched_notification["_links"]
        
        # Should have minimal affordances for dispatched notification
        assert "self" in dispatched_links
        assert "history" in dispatched_links  # Can view dispatch history
        
        # Should not have modification affordances
        assert "approve" not in dispatched_links
        assert "deny" not in dispatched_links
        assert "dispatch" not in dispatched_links
        assert "edit" not in dispatched_links
    
    def test_affordance_links_by_user_permissions(self):
        """Test that affordance links respect user permissions."""
        # Create test notification as admin
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        notification_data = {
            "title": "Permission Test Notification",
            "body": "Testing permission-based affordances",
            "severity": 2
        }
        
        create_response = self.client.post('/api/notifications', json=notification_data, headers=admin_headers)
        notification_id = create_response.get_json()["id"]
        
        # Test 1: Admin user affordances
        admin_response = self.client.get(f'/api/notifications/{notification_id}', headers=admin_headers)
        admin_notification = admin_response.get_json()
        admin_links = admin_notification["_links"]
        
        assert "approve" in admin_links
        assert "deny" in admin_links
        assert "edit" in admin_links
        assert "delete" in admin_links
        
        # Test 2: Moderator user affordances
        moderator_token = self._get_auth_token("moderator@hal-test.gov.br")
        moderator_headers = {"Authorization": f"Bearer {moderator_token}"}
        
        moderator_response = self.client.get(f'/api/notifications/{notification_id}', headers=moderator_headers)
        moderator_notification = moderator_response.get_json()
        moderator_links = moderator_notification["_links"]
        
        assert "approve" in moderator_links  # Has approval permission
        assert "deny" in moderator_links     # Has denial permission
        assert "edit" in moderator_links     # Has update permission
        assert "delete" not in moderator_links  # No delete permission
        
        # Test 3: Viewer user affordances
        viewer_token = self._get_auth_token("viewer@hal-test.gov.br")
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        viewer_response = self.client.get(f'/api/notifications/{notification_id}', headers=viewer_headers)
        viewer_notification = viewer_response.get_json()
        viewer_links = viewer_notification["_links"]
        
        # Should only have read-only affordances
        assert "self" in viewer_links
        assert "history" in viewer_links  # Can view history
        
        # Should not have modification affordances
        assert "approve" not in viewer_links
        assert "deny" not in viewer_links
        assert "edit" not in viewer_links
        assert "delete" not in viewer_links
    
    def test_hal_embedded_resources(self):
        """Test HAL embedded resources and their links."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create notification with embedded resources
        notification_data = {
            "title": "Embedded Resources Test",
            "body": "Testing embedded HAL resources",
            "severity": 4,
            "targets": ["email", "sms"],
            "metadata": {
                "category": "emergency",
                "priority": "high"
            }
        }
        
        create_response = self.client.post('/api/notifications', json=notification_data, headers=headers)
        notification = create_response.get_json()
        
        # Test embedded creator information
        if "_embedded" in notification:
            embedded = notification["_embedded"]
            
            if "creator" in embedded:
                creator = embedded["creator"]
                assert "_links" in creator
                assert "self" in creator["_links"]
                assert creator["_links"]["self"]["href"].startswith("/api/users/")
            
            if "organization" in embedded:
                organization = embedded["organization"]
                assert "_links" in organization
                assert "self" in organization["_links"]
                assert organization["_links"]["self"]["href"].startswith("/api/organizations/")
    
    def test_hal_link_templating(self):
        """Test HAL link templating for parameterized resources."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test collection with templated links
        response = self.client.get('/api/notifications', headers=headers)
        data = response.get_json()
        
        links = data["_links"]
        
        # Check for templated search link
        if "search" in links:
            search_link = links["search"]
            assert "templated" in search_link
            assert search_link["templated"] is True
            assert "{?q,status,severity,page,limit}" in search_link["href"]
        
        # Check for templated filter links
        if "filter" in links:
            filter_link = links["filter"]
            assert "templated" in filter_link
            assert filter_link["templated"] is True
    
    def test_hal_curies_and_documentation(self):
        """Test HAL CURIEs (Compact URIs) for link relation documentation."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = self.client.get('/api', headers=headers)
        data = response.get_json()
        
        # Check for CURIEs in root response
        if "curies" in data["_links"]:
            curies = data["_links"]["curies"]
            
            # Should be an array of CURIE objects
            assert isinstance(curies, list)
            
            for curie in curies:
                assert "name" in curie
                assert "href" in curie
                assert "templated" in curie
                assert curie["templated"] is True
                
                # Common CURIE for API documentation
                if curie["name"] == "sos":
                    assert "/docs/rels/{rel}" in curie["href"]
    
    def test_hal_error_responses(self):
        """Test HAL structure in error responses."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test 404 error
        not_found_response = self.client.get('/api/notifications/nonexistent', headers=headers)
        assert not_found_response.status_code == 404
        
        error_data = not_found_response.get_json()
        
        # Error should still follow HAL structure
        assert "_links" in error_data
        assert "self" in error_data["_links"]
        
        # Should include helpful links
        if "help" in error_data["_links"]:
            help_link = error_data["_links"]["help"]
            assert "href" in help_link
        
        # Test validation error (400)
        invalid_data = {
            "title": "",  # Invalid empty title
            "body": "Test",
            "severity": 10  # Invalid severity
        }
        
        validation_response = self.client.post('/api/notifications', json=invalid_data, headers=headers)
        assert validation_response.status_code == 400
        
        validation_error = validation_response.get_json()
        
        # Should follow HAL structure
        assert "_links" in validation_error
        assert "self" in validation_error["_links"]
        
        # Should include validation details
        assert "errors" in validation_error
        assert isinstance(validation_error["errors"], list)
    
    def test_hal_content_negotiation(self):
        """Test HAL content negotiation and media types."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        
        # Test 1: Request with HAL media type
        hal_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Accept": "application/hal+json"
        }
        
        hal_response = self.client.get('/api/notifications', headers=hal_headers)
        assert hal_response.status_code == 200
        assert hal_response.headers.get('Content-Type') == 'application/hal+json'
        
        # Test 2: Request with generic JSON (should still return HAL)
        json_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Accept": "application/json"
        }
        
        json_response = self.client.get('/api/notifications', headers=json_headers)
        assert json_response.status_code == 200
        # Should still return HAL structure even with generic JSON accept
        
        json_data = json_response.get_json()
        assert "_links" in json_data
    
    def test_hal_link_profiles(self):
        """Test HAL link profiles for semantic information."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = self.client.get('/api/notifications', headers=headers)
        data = response.get_json()
        
        # Check for profile links that describe the resource semantics
        if "profile" in data["_links"]:
            profile_link = data["_links"]["profile"]
            assert "href" in profile_link
            assert "/profiles/notification-collection" in profile_link["href"]
        
        # Create notification and check individual resource profile
        notification_data = {
            "title": "Profile Test",
            "body": "Testing HAL profiles",
            "severity": 2
        }
        
        create_response = self.client.post('/api/notifications', json=notification_data, headers=headers)
        notification = create_response.get_json()
        
        if "profile" in notification["_links"]:
            profile_link = notification["_links"]["profile"]
            assert "/profiles/notification" in profile_link["href"]
    
    def test_conditional_affordances_complex_scenarios(self):
        """Test complex conditional affordance scenarios."""
        admin_token = self._get_auth_token("admin@hal-test.gov.br")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Scenario 1: High severity notification with special affordances
        high_severity_data = {
            "title": "Critical Emergency Alert",
            "body": "Critical emergency requiring immediate attention",
            "severity": 5  # Maximum severity
        }
        
        create_response = self.client.post('/api/notifications', json=high_severity_data, headers=headers)
        critical_notification = create_response.get_json()
        
        critical_links = critical_notification["_links"]
        
        # High severity notifications might have special affordances
        if "escalate" in critical_links:
            escalate_link = critical_links["escalate"]
            assert "method" in escalate_link
            assert escalate_link["method"] == "POST"
        
        # Scenario 2: Notification with expiration
        expiring_data = {
            "title": "Time-Sensitive Alert",
            "body": "This alert expires soon",
            "severity": 3,
            "metadata": {
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }
        
        expiring_response = self.client.post('/api/notifications', json=expiring_data, headers=headers)
        expiring_notification = expiring_response.get_json()
        
        expiring_links = expiring_notification["_links"]
        
        # Expiring notifications might have extend affordance
        if "extend" in expiring_links:
            extend_link = expiring_links["extend"]
            assert "method" in extend_link
            assert extend_link["method"] == "PATCH"
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token for testing."""
        # Mock authentication for testing
        return f"test_token_{email.replace('@', '_').replace('.', '_')}"


class TestHALServiceUnit:
    """Unit tests for HAL service functionality."""
    
    def test_hal_link_generation(self):
        """Test HAL link generation utilities."""
        hal_service = HALService()
        
        # Test basic link generation
        base_url = "https://api.example.com"
        resource_path = "/notifications/123"
        
        link = hal_service.create_link(base_url + resource_path)
        assert link["href"] == base_url + resource_path
        
        # Test link with method
        post_link = hal_service.create_link(base_url + resource_path, method="POST")
        assert post_link["method"] == "POST"
        
        # Test templated link
        templated_link = hal_service.create_link(
            base_url + "/notifications{?page,limit}",
            templated=True
        )
        assert templated_link["templated"] is True
    
    def test_affordance_calculation(self):
        """Test affordance link calculation based on state and permissions."""
        hal_service = HALService()
        
        # Mock notification in 'received' status
        notification = {
            "id": "test_123",
            "status": "received",
            "severity": 3
        }
        
        # Mock user context with admin permissions
        user_context = UserContext(
            user_id="admin_user",
            org_id="test_org",
            permissions=["notification:approve", "notification:deny", "notification:update"],
            email="admin@test.com"
        )
        
        base_url = "https://api.example.com"
        
        affordances = hal_service.calculate_notification_affordances(
            notification, user_context, base_url
        )
        
        # Should include affordances based on status and permissions
        assert "approve" in affordances
        assert "deny" in affordances
        assert "edit" in affordances
        
        # Verify link structure
        approve_link = affordances["approve"]
        assert approve_link["href"] == f"{base_url}/api/notifications/test_123/approve"
        assert approve_link["method"] == "POST"
    
    def test_embedded_resource_handling(self):
        """Test embedded resource handling in HAL responses."""
        hal_service = HALService()
        
        # Mock notification with related resources
        notification = {
            "id": "test_123",
            "title": "Test Notification",
            "createdBy": "user_456"
        }
        
        # Mock related user
        creator = {
            "id": "user_456",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        base_url = "https://api.example.com"
        
        # Build HAL response with embedded resources
        hal_response = hal_service.build_notification_response(
            notification,
            base_url,
            embedded_resources={"creator": creator}
        )
        
        # Verify embedded structure
        assert "_embedded" in hal_response
        assert "creator" in hal_response["_embedded"]
        
        embedded_creator = hal_response["_embedded"]["creator"]
        assert embedded_creator["id"] == "user_456"
        assert "_links" in embedded_creator
        assert "self" in embedded_creator["_links"]
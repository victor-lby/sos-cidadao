# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for notification workflow endpoints.

Tests the complete notification workflow including webhook intake,
listing, detail view, approval, and denial operations.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from bson import ObjectId

from app import app
from models.entities import NotificationStatus, NotificationSeverity, UserContext
from services.mongodb import MongoDBService
from services.redis import RedisService
from services.auth import AuthService


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    app.config['MONGODB_URI'] = 'mongodb://localhost:27017/sos_cidadao_test'
    app.config['REDIS_URL'] = 'redis://localhost:6379/1'
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_services():
    """Mock external services."""
    with patch('app.mongodb_service') as mock_mongo, \
         patch('app.redis_service') as mock_redis, \
         patch('app.auth_service') as mock_auth:
        
        # Configure MongoDB mock
        mock_mongo.create.return_value = str(ObjectId())
        mock_mongo.find_one_by_org.return_value = None
        mock_mongo.update_by_org.return_value = True
        mock_mongo.paginate_by_org.return_value = MagicMock(
            items=[],
            total=0,
            page=1,
            page_size=20
        )
        
        # Configure Redis mock
        mock_redis.is_token_blocked.return_value = False
        
        # Configure Auth mock
        mock_auth.validate_token.return_value = {
            "sub": "user123",
            "org_id": "org123",
            "email": "test@example.com",
            "name": "Test User",
            "permissions": ["notification:create", "notification:approve", "notification:deny"]
        }
        mock_auth.extract_token_id.return_value = "token123"
        
        yield {
            'mongo': mock_mongo,
            'redis': mock_redis,
            'auth': mock_auth
        }


@pytest.fixture
def auth_headers():
    """Authentication headers for requests."""
    return {
        'Authorization': 'Bearer test-jwt-token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_notification():
    """Sample notification data."""
    return {
        "_id": ObjectId(),
        "organizationId": "org123",
        "title": "Test Emergency Alert",
        "body": "This is a test emergency notification",
        "severity": 4,
        "origin": "test-system",
        "originalPayload": {"test": "data"},
        "baseTargetId": None,
        "targetIds": ["target1", "target2"],
        "categoryIds": ["category1"],
        "status": "received",
        "denialReason": None,
        "approvedAt": None,
        "approvedBy": None,
        "deniedAt": None,
        "deniedBy": None,
        "dispatchedAt": None,
        "correlationId": "test-correlation-123",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "deletedAt": None,
        "createdBy": "user123",
        "updatedBy": "user123",
        "schemaVersion": 2
    }


class TestNotificationWebhook:
    """Test notification webhook intake endpoint."""
    
    def test_receive_notification_success(self, client, mock_services, auth_headers):
        """Test successful notification reception via webhook."""
        webhook_payload = {
            "title": "Emergency Alert",
            "body": "Severe weather warning in effect",
            "severity": 4,
            "targets": ["target1", "target2"],
            "categories": ["weather"]
        }
        
        response = client.post(
            '/api/notifications/incoming',
            data=json.dumps(webhook_payload),
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Check HAL structure
        assert '_links' in data
        assert 'self' in data['_links']
        
        # Check notification data
        assert data['title'] == webhook_payload['title']
        assert data['body'] == webhook_payload['body']
        assert data['severity'] == webhook_payload['severity']
        assert data['status'] == 'received'
        
        # Verify MongoDB create was called
        mock_services['mongo'].create.assert_called_once()
        call_args = mock_services['mongo'].create.call_args
        assert call_args[0][0] == "notifications"
        notification_data = call_args[0][1]
        assert notification_data['title'] == webhook_payload['title']
        assert notification_data['organizationId'] == "org123"
    
    def test_receive_notification_missing_auth(self, client, mock_services):
        """Test webhook rejection without authentication."""
        webhook_payload = {
            "title": "Emergency Alert",
            "body": "Test alert",
            "severity": 3
        }
        
        response = client.post(
            '/api/notifications/incoming',
            data=json.dumps(webhook_payload),
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['title'] == 'Authentication Required'
    
    def test_receive_notification_invalid_payload(self, client, mock_services, auth_headers):
        """Test webhook with invalid payload."""
        invalid_payload = {
            "title": "",  # Empty title
            "body": "Test body",
            "severity": 10  # Invalid severity
        }
        
        response = client.post(
            '/api/notifications/incoming',
            data=json.dumps(invalid_payload),
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'validation' in data['type'].lower()
    
    def test_receive_notification_missing_body(self, client, mock_services, auth_headers):
        """Test webhook without request body."""
        response = client.post(
            '/api/notifications/incoming',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Missing request body' in data['detail']


class TestNotificationListing:
    """Test notification listing endpoint."""
    
    def test_list_notifications_success(self, client, mock_services, auth_headers, sample_notification):
        """Test successful notification listing."""
        # Configure mock to return sample notification
        mock_services['mongo'].paginate_by_org.return_value = MagicMock(
            items=[sample_notification],
            total=1,
            page=1,
            page_size=20
        )
        
        response = client.get(
            '/api/notifications',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check HAL collection structure
        assert '_embedded' in data
        assert 'notifications' in data['_embedded']
        assert '_links' in data
        assert 'self' in data['_links']
        
        # Check pagination info
        assert data['total'] == 1
        assert data['page'] == 1
        assert data['page_size'] == 20
        
        # Check notification data
        notifications = data['_embedded']['notifications']
        assert len(notifications) == 1
        assert notifications[0]['title'] == sample_notification['title']
        assert notifications[0]['status'] == sample_notification['status']
    
    def test_list_notifications_with_filters(self, client, mock_services, auth_headers):
        """Test notification listing with filters."""
        response = client.get(
            '/api/notifications?status=received&severity=4&search=emergency',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify MongoDB query was called with filters
        mock_services['mongo'].paginate_by_org.assert_called_once()
        call_args = mock_services['mongo'].paginate_by_org.call_args
        query = call_args[0][3]  # Fourth argument is the query
        
        assert query['organizationId'] == "org123"
        assert query['status'] == "received"
        assert query['severity'] == 4
        assert '$or' in query  # Search filter
    
    def test_list_notifications_pagination(self, client, mock_services, auth_headers):
        """Test notification listing with pagination."""
        response = client.get(
            '/api/notifications?page=2&size=10',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify pagination parameters
        mock_services['mongo'].paginate_by_org.assert_called_once()
        call_args = mock_services['mongo'].paginate_by_org.call_args
        assert call_args[0][2] == 2  # page
        assert call_args[0][3] == 10  # page_size
    
    def test_list_notifications_invalid_date_filter(self, client, mock_services, auth_headers):
        """Test notification listing with invalid date filter."""
        response = client.get(
            '/api/notifications?date_from=invalid-date',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid date_from format' in data['detail']


class TestNotificationDetail:
    """Test notification detail endpoint."""
    
    def test_get_notification_success(self, client, mock_services, auth_headers, sample_notification):
        """Test successful notification detail retrieval."""
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        response = client.get(
            f'/api/notifications/{notification_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check HAL structure with affordance links
        assert '_links' in data
        assert 'self' in data['_links']
        assert 'collection' in data['_links']
        
        # Check for conditional affordance links (should have approve/deny for received status)
        assert 'approve' in data['_links']
        assert 'deny' in data['_links']
        
        # Check notification data
        assert data['id'] == notification_id
        assert data['title'] == sample_notification['title']
        assert data['status'] == sample_notification['status']
        
        # Verify MongoDB query
        mock_services['mongo'].find_one_by_org.assert_called_once_with(
            "notifications", "org123", notification_id
        )
    
    def test_get_notification_not_found(self, client, mock_services, auth_headers):
        """Test notification detail for non-existent notification."""
        mock_services['mongo'].find_one_by_org.return_value = None
        
        response = client.get(
            '/api/notifications/nonexistent123',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['title'] == 'Notification not found'
    
    def test_get_notification_different_org(self, client, mock_services, auth_headers, sample_notification):
        """Test notification detail access across organizations."""
        # Notification belongs to different org
        sample_notification['organizationId'] = 'different-org'
        mock_services['mongo'].find_one_by_org.return_value = None  # Simulates org scoping
        
        notification_id = str(sample_notification['_id'])
        response = client.get(
            f'/api/notifications/{notification_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestNotificationApproval:
    """Test notification approval endpoint."""
    
    def test_approve_notification_success(self, client, mock_services, auth_headers, sample_notification):
        """Test successful notification approval."""
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        approval_data = {
            "target_ids": ["target1", "target2"],
            "category_ids": ["category1"],
            "approved_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/approve',
            data=json.dumps(approval_data),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check updated status
        assert data['status'] == 'approved'
        assert data['approved_by'] == "user123"
        assert 'approved_at' in data
        
        # Check HAL links (should not have approve/deny anymore)
        assert 'approve' not in data['_links']
        assert 'deny' not in data['_links']
        
        # Verify database update
        mock_services['mongo'].update_by_org.assert_called_once()
    
    def test_approve_notification_insufficient_permissions(self, client, mock_services, auth_headers, sample_notification):
        """Test approval without sufficient permissions."""
        # Remove approval permission
        mock_services['auth'].validate_token.return_value = {
            "sub": "user123",
            "org_id": "org123",
            "permissions": ["notification:create"]  # No approve permission
        }
        
        notification_id = str(sample_notification['_id'])
        approval_data = {
            "target_ids": ["target1"],
            "category_ids": ["category1"],
            "approved_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/approve',
            data=json.dumps(approval_data),
            headers=auth_headers
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'Insufficient permissions' in data['detail']
    
    def test_approve_notification_invalid_status(self, client, mock_services, auth_headers, sample_notification):
        """Test approval of already processed notification."""
        # Set notification as already approved
        sample_notification['status'] = 'approved'
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        approval_data = {
            "target_ids": ["target1"],
            "category_ids": ["category1"],
            "approved_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/approve',
            data=json.dumps(approval_data),
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'cannot be approved' in data['detail'].lower()
    
    def test_approve_notification_missing_targets(self, client, mock_services, auth_headers, sample_notification):
        """Test approval without required targets."""
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        approval_data = {
            "target_ids": [],  # Empty targets
            "category_ids": ["category1"],
            "approved_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/approve',
            data=json.dumps(approval_data),
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestNotificationDenial:
    """Test notification denial endpoint."""
    
    def test_deny_notification_success(self, client, mock_services, auth_headers, sample_notification):
        """Test successful notification denial."""
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        denial_data = {
            "reason": "Insufficient information provided for emergency alert",
            "denied_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/deny',
            data=json.dumps(denial_data),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check updated status
        assert data['status'] == 'denied'
        assert data['denied_by'] == "user123"
        assert data['denial_reason'] == denial_data['reason']
        assert 'denied_at' in data
        
        # Check HAL links (should not have approve/deny anymore)
        assert 'approve' not in data['_links']
        assert 'deny' not in data['_links']
        
        # Verify database update
        mock_services['mongo'].update_by_org.assert_called_once()
    
    def test_deny_notification_insufficient_permissions(self, client, mock_services, auth_headers, sample_notification):
        """Test denial without sufficient permissions."""
        # Remove denial permission
        mock_services['auth'].validate_token.return_value = {
            "sub": "user123",
            "org_id": "org123",
            "permissions": ["notification:create"]  # No deny permission
        }
        
        notification_id = str(sample_notification['_id'])
        denial_data = {
            "reason": "Test denial reason",
            "denied_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/deny',
            data=json.dumps(denial_data),
            headers=auth_headers
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'Insufficient permissions' in data['detail']
    
    def test_deny_notification_short_reason(self, client, mock_services, auth_headers, sample_notification):
        """Test denial with insufficient reason length."""
        notification_id = str(sample_notification['_id'])
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        denial_data = {
            "reason": "Short",  # Too short
            "denied_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/deny',
            data=json.dumps(denial_data),
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'at least 10 characters' in data['detail'].lower()


class TestNotificationWorkflow:
    """Test complete notification workflow integration."""
    
    def test_complete_approval_workflow(self, client, mock_services, auth_headers):
        """Test complete workflow: receive → list → detail → approve."""
        # Step 1: Receive notification
        webhook_payload = {
            "title": "Emergency Alert",
            "body": "Severe weather warning",
            "severity": 4,
            "targets": ["target1"],
            "categories": ["weather"]
        }
        
        response = client.post(
            '/api/notifications/incoming',
            data=json.dumps(webhook_payload),
            headers=auth_headers
        )
        assert response.status_code == 201
        notification_data = response.get_json()
        notification_id = notification_data['id']
        
        # Step 2: List notifications (should include new one)
        sample_notification = {
            "_id": ObjectId(notification_id),
            "organizationId": "org123",
            "title": webhook_payload['title'],
            "body": webhook_payload['body'],
            "severity": webhook_payload['severity'],
            "status": "received",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "createdBy": "user123",
            "updatedBy": "user123",
            "schemaVersion": 2
        }
        
        mock_services['mongo'].paginate_by_org.return_value = MagicMock(
            items=[sample_notification],
            total=1
        )
        
        response = client.get('/api/notifications', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        
        # Step 3: Get notification detail
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        response = client.get(f'/api/notifications/{notification_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'approve' in data['_links']
        
        # Step 4: Approve notification
        approval_data = {
            "target_ids": ["target1"],
            "category_ids": ["weather"],
            "approved_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/approve',
            data=json.dumps(approval_data),
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'approved'
    
    def test_complete_denial_workflow(self, client, mock_services, auth_headers):
        """Test complete workflow: receive → deny."""
        # Create notification
        notification_id = str(ObjectId())
        sample_notification = {
            "_id": ObjectId(notification_id),
            "organizationId": "org123",
            "title": "Test Alert",
            "body": "Test body",
            "severity": 2,
            "status": "received",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "createdBy": "user123",
            "updatedBy": "user123",
            "schemaVersion": 2
        }
        
        mock_services['mongo'].find_one_by_org.return_value = sample_notification
        
        # Deny notification
        denial_data = {
            "reason": "Insufficient information provided for this alert type",
            "denied_by": "user123"
        }
        
        response = client.post(
            f'/api/notifications/{notification_id}/deny',
            data=json.dumps(denial_data),
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'denied'
        assert data['denial_reason'] == denial_data['reason']


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""
    
    def test_organization_scoping_in_queries(self, client, mock_services, auth_headers):
        """Test that all queries are properly scoped to organization."""
        # Test listing
        client.get('/api/notifications', headers=auth_headers)
        mock_services['mongo'].paginate_by_org.assert_called()
        call_args = mock_services['mongo'].paginate_by_org.call_args
        assert call_args[0][1] == "org123"  # org_id parameter
        
        # Test detail
        notification_id = str(ObjectId())
        client.get(f'/api/notifications/{notification_id}', headers=auth_headers)
        mock_services['mongo'].find_one_by_org.assert_called_with(
            "notifications", "org123", notification_id
        )
    
    def test_cross_organization_access_denied(self, client, mock_services, auth_headers):
        """Test that users cannot access notifications from other organizations."""
        # Mock returns None (simulating org scoping in MongoDB service)
        mock_services['mongo'].find_one_by_org.return_value = None
        
        notification_id = str(ObjectId())
        response = client.get(f'/api/notifications/{notification_id}', headers=auth_headers)
        assert response.status_code == 404
        
        # Verify the query was scoped to user's organization
        mock_services['mongo'].find_one_by_org.assert_called_with(
            "notifications", "org123", notification_id
        )


class TestHALAffordances:
    """Test HAL affordance link generation."""
    
    def test_affordance_links_based_on_status(self, client, mock_services, auth_headers):
        """Test that affordance links are generated based on notification status."""
        notification_id = str(ObjectId())
        
        # Test received status (should have approve/deny links)
        received_notification = {
            "_id": ObjectId(notification_id),
            "organizationId": "org123",
            "title": "Test",
            "body": "Test",
            "severity": 3,
            "status": "received",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "createdBy": "user123",
            "updatedBy": "user123",
            "schemaVersion": 2
        }
        
        mock_services['mongo'].find_one_by_org.return_value = received_notification
        
        response = client.get(f'/api/notifications/{notification_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'approve' in data['_links']
        assert 'deny' in data['_links']
        assert data['_links']['approve']['method'] == 'POST'
        assert data['_links']['deny']['method'] == 'POST'
    
    def test_affordance_links_based_on_permissions(self, client, mock_services, auth_headers):
        """Test that affordance links respect user permissions."""
        # Remove approval permission
        mock_services['auth'].validate_token.return_value = {
            "sub": "user123",
            "org_id": "org123",
            "permissions": ["notification:deny"]  # Only deny permission
        }
        
        notification_id = str(ObjectId())
        received_notification = {
            "_id": ObjectId(notification_id),
            "organizationId": "org123",
            "title": "Test",
            "body": "Test",
            "severity": 3,
            "status": "received",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "createdBy": "user123",
            "updatedBy": "user123",
            "schemaVersion": 2
        }
        
        mock_services['mongo'].find_one_by_org.return_value = received_notification
        
        response = client.get(f'/api/notifications/{notification_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        
        # Should only have deny link, not approve
        assert 'approve' not in data['_links']
        assert 'deny' in data['_links']
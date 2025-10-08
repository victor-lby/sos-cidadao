# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Tests for HAL response formatting utilities.
"""

import pytest
from unittest.mock import Mock, patch
from services.hal import (
    HalLinkBuilder, PaginationLinkBuilder, AffordanceLinkBuilder,
    HalResponseBuilder, HalFormatter, create_hal_formatter
)
from models.responses import HalLink


class TestHalLinkBuilder:
    """Test HAL link builder functionality."""
    
    def test_build_basic_link(self):
        """Test building a basic HAL link."""
        builder = HalLinkBuilder("https://api.example.com")
        
        link = builder.build_link("/api/notifications/123")
        
        assert isinstance(link, HalLink)
        assert link.href == "https://api.example.com/api/notifications/123"
        assert link.method == "GET"
        assert link.type is None
    
    def test_build_link_with_options(self):
        """Test building a link with all options."""
        builder = HalLinkBuilder("https://api.example.com")
        
        link = builder.build_link(
            "/api/notifications/123/approve",
            method="POST",
            content_type="application/json",
            title="Approve Notification",
            templated=True
        )
        
        assert link.href == "https://api.example.com/api/notifications/123/approve"
        assert link.method == "POST"
        assert link.type == "application/json"
        assert link.title == "Approve Notification"
        assert link.templated is True
    
    def test_build_self_link(self):
        """Test building a self link."""
        builder = HalLinkBuilder("https://api.example.com")
        
        link = builder.build_self_link("/api/notifications/123")
        
        assert link.href == "https://api.example.com/api/notifications/123"
        assert link.title == "Self"
    
    def test_build_action_link(self):
        """Test building an action link."""
        builder = HalLinkBuilder("https://api.example.com")
        
        link = builder.build_action_link("/api/notifications/123", "approve")
        
        assert link.href == "https://api.example.com/api/notifications/123/approve"
        assert link.method == "POST"
        assert link.type == "application/json"
        assert link.title == "Approve"
    
    def test_base_url_normalization(self):
        """Test that base URL is properly normalized."""
        builder = HalLinkBuilder("https://api.example.com/")  # Trailing slash
        
        link = builder.build_link("/api/test")
        
        assert link.href == "https://api.example.com/api/test"


class TestPaginationLinkBuilder:
    """Test pagination link builder functionality."""
    
    def test_build_pagination_links_first_page(self):
        """Test pagination links for first page."""
        builder = PaginationLinkBuilder("https://api.example.com")
        
        links = builder.build_pagination_links(
            "/api/notifications",
            current_page=1,
            total_pages=5,
            page_size=20
        )
        
        assert "self" in links
        assert "next" in links
        assert "last" in links
        assert "first" not in links  # Not needed on first page
        assert "prev" not in links   # Not needed on first page
        
        assert "page=1" in links["self"].href
        assert "page=2" in links["next"].href
        assert "page=5" in links["last"].href
    
    def test_build_pagination_links_middle_page(self):
        """Test pagination links for middle page."""
        builder = PaginationLinkBuilder("https://api.example.com")
        
        links = builder.build_pagination_links(
            "/api/notifications",
            current_page=3,
            total_pages=5,
            page_size=20
        )
        
        assert "self" in links
        assert "first" in links
        assert "prev" in links
        assert "next" in links
        assert "last" in links
        
        assert "page=3" in links["self"].href
        assert "page=1" in links["first"].href
        assert "page=2" in links["prev"].href
        assert "page=4" in links["next"].href
        assert "page=5" in links["last"].href
    
    def test_build_pagination_links_last_page(self):
        """Test pagination links for last page."""
        builder = PaginationLinkBuilder("https://api.example.com")
        
        links = builder.build_pagination_links(
            "/api/notifications",
            current_page=5,
            total_pages=5,
            page_size=20
        )
        
        assert "self" in links
        assert "first" in links
        assert "prev" in links
        assert "next" not in links  # Not needed on last page
        assert "last" not in links  # Not needed on last page
    
    def test_build_pagination_links_with_query_params(self):
        """Test pagination links with additional query parameters."""
        builder = PaginationLinkBuilder("https://api.example.com")
        
        links = builder.build_pagination_links(
            "/api/notifications",
            current_page=2,
            total_pages=3,
            page_size=20,
            query_params={"status": "received", "severity": "4"}
        )
        
        # All links should preserve query parameters
        for link in links.values():
            assert "status=received" in link.href
            assert "severity=4" in link.href
            assert "page_size=20" in link.href


class TestAffordanceLinkBuilder:
    """Test affordance link builder functionality."""
    
    def test_build_notification_affordances_received_status(self):
        """Test notification affordances for received status."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_notification_affordances(
            notification_id="123",
            notification_status="received",
            user_permissions=["notification:approve", "notification:deny"],
            organization_id="org1"
        )
        
        assert "self" in links
        assert "collection" in links
        assert "approve" in links
        assert "deny" in links
        
        assert links["approve"].method == "POST"
        assert links["deny"].method == "POST"
    
    def test_build_notification_affordances_limited_permissions(self):
        """Test notification affordances with limited permissions."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_notification_affordances(
            notification_id="123",
            notification_status="received",
            user_permissions=["notification:approve"],  # Only approve permission
            organization_id="org1"
        )
        
        assert "approve" in links
        assert "deny" not in links  # No deny permission
    
    def test_build_notification_affordances_approved_status(self):
        """Test notification affordances for approved status."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_notification_affordances(
            notification_id="123",
            notification_status="approved",  # Already approved
            user_permissions=["notification:approve", "notification:deny"],
            organization_id="org1"
        )
        
        assert "self" in links
        assert "collection" in links
        assert "approve" not in links  # Can't approve already approved
        assert "deny" not in links     # Can't deny already approved
    
    def test_build_organization_affordances(self):
        """Test organization affordances."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_organization_affordances(
            organization_id="org1",
            user_permissions=["organization:edit", "user:list", "notification:list"]
        )
        
        assert "self" in links
        assert "collection" in links
        assert "edit" in links
        assert "users" in links
        assert "notifications" in links
        assert "delete" not in links  # No delete permission
    
    def test_build_user_affordances_self(self):
        """Test user affordances for self."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_user_affordances(
            user_id="user1",
            organization_id="org1",
            user_permissions=["user:edit"],
            current_user_id="user1"  # Same user
        )
        
        assert "edit" in links
        assert "delete" not in links  # Can't delete self
    
    def test_build_user_affordances_other_user(self):
        """Test user affordances for other user."""
        builder = AffordanceLinkBuilder("https://api.example.com")
        
        links = builder.build_user_affordances(
            user_id="user2",
            organization_id="org1",
            user_permissions=["user:edit", "user:delete"],
            current_user_id="user1"  # Different user
        )
        
        assert "edit" in links
        assert "delete" in links  # Can delete other users


class TestHalResponseBuilder:
    """Test HAL response builder functionality."""
    
    def test_build_resource_response_notification(self):
        """Test building a notification resource response."""
        builder = HalResponseBuilder("https://api.example.com")
        
        notification_data = {
            "id": "123",
            "title": "Test Alert",
            "status": "received"
        }
        
        response = builder.build_resource_response(
            notification_data,
            "notification",
            "123",
            "org1",
            ["notification:approve", "notification:deny"]
        )
        
        assert response["id"] == "123"
        assert response["title"] == "Test Alert"
        assert "_links" in response
        assert "self" in response["_links"]
        assert "approve" in response["_links"]
        assert "deny" in response["_links"]
    
    def test_build_collection_response(self):
        """Test building a collection response."""
        builder = HalResponseBuilder("https://api.example.com")
        
        items = [
            {"id": "1", "title": "Item 1"},
            {"id": "2", "title": "Item 2"}
        ]
        
        response = builder.build_collection_response(
            items,
            total=10,
            page=1,
            page_size=2,
            collection_path="/api/notifications"
        )
        
        assert response["total"] == 10
        assert response["page"] == 1
        assert response["page_size"] == 2
        assert response["total_pages"] == 5
        assert "_links" in response
        assert "_embedded" in response
        assert response["_embedded"]["items"] == items
    
    def test_build_error_response(self):
        """Test building an error response."""
        builder = HalResponseBuilder("https://api.example.com")
        
        response = builder.build_error_response(
            "validation-error",
            "Validation Error",
            400,
            "Request validation failed",
            "/api/notifications",
            [{"field": "title", "message": "Required"}]
        )
        
        assert response["type"] == "https://api.sos-cidadao.org/problems/validation-error"
        assert response["title"] == "Validation Error"
        assert response["status"] == 400
        assert response["detail"] == "Request validation failed"
        assert response["instance"] == "/api/notifications"
        assert response["errors"] == [{"field": "title", "message": "Required"}]
        assert "_links" in response
        assert "help" in response["_links"]


class TestHalFormatter:
    """Test HAL formatter functionality."""
    
    def test_format_notification(self):
        """Test formatting a notification."""
        formatter = HalFormatter("https://api.example.com")
        
        notification = {
            "id": "123",
            "title": "Test Alert",
            "status": "received"
        }
        
        result = formatter.format_notification(
            notification,
            "org1",
            ["notification:approve"]
        )
        
        assert result["id"] == "123"
        assert "_links" in result
        assert "approve" in result["_links"]
    
    def test_format_notification_collection(self):
        """Test formatting a notification collection."""
        formatter = HalFormatter("https://api.example.com")
        
        notifications = [
            {"id": "1", "title": "Alert 1", "status": "received"},
            {"id": "2", "title": "Alert 2", "status": "approved"}
        ]
        
        result = formatter.format_notification_collection(
            notifications,
            total=2,
            page=1,
            page_size=10,
            organization_id="org1",
            user_permissions=["notification:approve"]
        )
        
        assert result["total"] == 2
        assert "_embedded" in result
        assert len(result["_embedded"]["items"]) == 2
        # Check that each item has HAL links
        for item in result["_embedded"]["items"]:
            assert "_links" in item
    
    def test_format_validation_error(self):
        """Test formatting a validation error."""
        formatter = HalFormatter("https://api.example.com")
        
        result = formatter.format_validation_error(
            "Request validation failed",
            "/api/notifications",
            [{"field": "title", "message": "Required"}]
        )
        
        assert result["status"] == 400
        assert result["errors"] == [{"field": "title", "message": "Required"}]
        assert "_links" in result
    
    def test_format_authentication_error(self):
        """Test formatting an authentication error."""
        formatter = HalFormatter("https://api.example.com")
        
        result = formatter.format_authentication_error(
            "Missing authorization token",
            "/api/notifications"
        )
        
        assert result["status"] == 401
        assert result["detail"] == "Missing authorization token"
        assert "_links" in result
        assert "login" in result["_links"]
    
    def test_format_authorization_error(self):
        """Test formatting an authorization error."""
        formatter = HalFormatter("https://api.example.com")
        
        result = formatter.format_authorization_error(
            "Insufficient permissions",
            "/api/notifications"
        )
        
        assert result["status"] == 403
        assert result["detail"] == "Insufficient permissions"
        assert "_links" in result


class TestCreateHalFormatter:
    """Test HAL formatter factory function."""
    
    def test_create_hal_formatter(self):
        """Test creating a HAL formatter."""
        formatter = create_hal_formatter("https://api.example.com")
        
        assert isinstance(formatter, HalFormatter)
        assert formatter.builder.base_url == "https://api.example.com"


# Integration tests
class TestHalIntegration:
    """Integration tests for HAL functionality."""
    
    def test_complete_notification_workflow(self):
        """Test complete notification HAL workflow."""
        formatter = HalFormatter("https://api.example.com")
        
        # Initial notification (received status)
        notification = {
            "id": "123",
            "title": "Emergency Alert",
            "body": "Test emergency notification",
            "status": "received",
            "severity": 4
        }
        
        # Format with approval permissions
        result = formatter.format_notification(
            notification,
            "org1",
            ["notification:approve", "notification:deny"]
        )
        
        # Should have approve and deny links
        assert "approve" in result["_links"]
        assert "deny" in result["_links"]
        
        # Simulate approval - update status
        notification["status"] = "approved"
        
        # Format again with same permissions
        result = formatter.format_notification(
            notification,
            "org1",
            ["notification:approve", "notification:deny"]
        )
        
        # Should no longer have approve/deny links
        assert "approve" not in result["_links"]
        assert "deny" not in result["_links"]
        assert "self" in result["_links"]  # Always has self link
    
    def test_pagination_with_filters(self):
        """Test pagination with filter parameters."""
        formatter = HalFormatter("https://api.example.com")
        
        notifications = [
            {"id": "1", "title": "Alert 1", "status": "received"},
            {"id": "2", "title": "Alert 2", "status": "received"}
        ]
        
        result = formatter.format_notification_collection(
            notifications,
            total=25,
            page=2,
            page_size=10,
            organization_id="org1",
            user_permissions=["notification:list"],
            filters={"status": "received", "severity": "4"}
        )
        
        # Check pagination links preserve filters
        links = result["_links"]
        assert "prev" in links
        assert "next" in links
        
        # All pagination links should preserve filters
        for link_name in ["prev", "next", "first", "last"]:
            if link_name in links:
                href = links[link_name]["href"]
                assert "status=received" in href
                assert "severity=4" in href
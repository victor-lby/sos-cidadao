# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for MongoDB service layer.
"""

import pytest
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from services.mongodb import MongoDBService, PaginationResult


class TestMongoDBService:
    """Test MongoDB service functionality."""
    
    @pytest.fixture
    def mongodb_service(self, test_mongodb_uri, test_database_name):
        """MongoDB service instance for testing."""
        service = MongoDBService(test_mongodb_uri, test_database_name)
        yield service
        service.close_connection()
    
    def test_connection_and_health_check(self, mongodb_service):
        """Test MongoDB connection and health check."""
        health = mongodb_service.health_check()
        
        assert health['status'] == 'healthy'
        assert health['ping'] is True
        assert 'version' in health
        assert health['database'] == 'sos_cidadao_test'
    
    def test_create_document(self, mongodb_service, clean_database, sample_organization_data):
        """Test document creation with organization scoping."""
        user_id = str(ObjectId())
        
        doc_id = mongodb_service.create("organizations", sample_organization_data, user_id)
        
        assert doc_id is not None
        assert ObjectId.is_valid(doc_id)
        
        # Verify document was created
        created_doc = mongodb_service.find_one_by_org(
            "organizations", 
            sample_organization_data["organization_id"], 
            doc_id
        )
        
        assert created_doc is not None
        assert created_doc["name"] == sample_organization_data["name"]
        assert created_doc["createdBy"] == user_id
        assert "createdAt" in created_doc
        assert "updatedAt" in created_doc
    
    def test_find_by_org(self, mongodb_service, clean_database, sample_organization_data):
        """Test finding documents by organization."""
        user_id = str(ObjectId())
        org_id = sample_organization_data["organization_id"]
        
        # Create multiple documents
        doc1_id = mongodb_service.create("organizations", sample_organization_data, user_id)
        
        sample_organization_data2 = sample_organization_data.copy()
        sample_organization_data2["name"] = "Second Organization"
        sample_organization_data2["slug"] = "second-org"
        doc2_id = mongodb_service.create("organizations", sample_organization_data2, user_id)
        
        # Create document for different organization (should not be returned)
        different_org_data = sample_organization_data.copy()
        different_org_data["organization_id"] = str(ObjectId())
        different_org_data["name"] = "Different Org"
        different_org_data["slug"] = "different-org"
        mongodb_service.create("organizations", different_org_data, user_id)
        
        # Find documents by organization
        docs = mongodb_service.find_by_org("organizations", org_id)
        
        assert len(docs) == 2
        doc_ids = [doc["id"] for doc in docs]
        assert doc1_id in doc_ids
        assert doc2_id in doc_ids
    
    def test_find_one_by_org(self, mongodb_service, clean_database, sample_organization_data):
        """Test finding single document by organization and ID."""
        user_id = str(ObjectId())
        org_id = sample_organization_data["organization_id"]
        
        doc_id = mongodb_service.create("organizations", sample_organization_data, user_id)
        
        # Find the document
        found_doc = mongodb_service.find_one_by_org("organizations", org_id, doc_id)
        
        assert found_doc is not None
        assert found_doc["id"] == doc_id
        assert found_doc["name"] == sample_organization_data["name"]
        
        # Try to find with wrong organization ID
        wrong_org_id = str(ObjectId())
        not_found = mongodb_service.find_one_by_org("organizations", wrong_org_id, doc_id)
        assert not_found is None
    
    def test_update_by_org(self, mongodb_service, clean_database, sample_organization_data):
        """Test updating document by organization and ID."""
        user_id = str(ObjectId())
        org_id = sample_organization_data["organization_id"]
        
        doc_id = mongodb_service.create("organizations", sample_organization_data, user_id)
        
        # Update the document
        updates = {"name": "Updated Organization Name", "description": "Updated description"}
        updated_user_id = str(ObjectId())
        
        success = mongodb_service.update_by_org("organizations", org_id, doc_id, updates, updated_user_id)
        
        assert success is True
        
        # Verify update
        updated_doc = mongodb_service.find_one_by_org("organizations", org_id, doc_id)
        assert updated_doc["name"] == "Updated Organization Name"
        assert updated_doc["description"] == "Updated description"
        assert updated_doc["updatedBy"] == updated_user_id
        assert updated_doc["updatedAt"] != updated_doc["createdAt"]
    
    def test_soft_delete_by_org(self, mongodb_service, clean_database, sample_organization_data):
        """Test soft deleting document by organization and ID."""
        user_id = str(ObjectId())
        org_id = sample_organization_data["organization_id"]
        
        doc_id = mongodb_service.create("organizations", sample_organization_data, user_id)
        
        # Soft delete the document
        deleter_user_id = str(ObjectId())
        success = mongodb_service.soft_delete_by_org("organizations", org_id, doc_id, deleter_user_id)
        
        assert success is True
        
        # Verify document is not found in normal queries
        found_doc = mongodb_service.find_one_by_org("organizations", org_id, doc_id)
        assert found_doc is None
        
        # Verify document exists when including deleted
        deleted_doc = mongodb_service.find_one_by_org("organizations", org_id, doc_id, include_deleted=True)
        assert deleted_doc is not None
        assert deleted_doc["deletedAt"] is not None
        assert deleted_doc["updatedBy"] == deleter_user_id
    
    def test_pagination(self, mongodb_service, clean_database, sample_notification_data):
        """Test pagination functionality."""
        user_id = str(ObjectId())
        org_id = sample_notification_data["organization_id"]
        
        # Create multiple notifications
        for i in range(25):
            notification_data = sample_notification_data.copy()
            notification_data["title"] = f"Notification {i+1}"
            mongodb_service.create("notifications", notification_data, user_id)
        
        # Test first page
        page1 = mongodb_service.paginate_by_org("notifications", org_id, page=1, page_size=10)
        
        assert isinstance(page1, PaginationResult)
        assert len(page1.items) == 10
        assert page1.total == 25
        assert page1.page == 1
        assert page1.page_size == 10
        assert page1.total_pages == 3
        assert page1.has_next is True
        assert page1.has_prev is False
        
        # Test second page
        page2 = mongodb_service.paginate_by_org("notifications", org_id, page=2, page_size=10)
        
        assert len(page2.items) == 10
        assert page2.page == 2
        assert page2.has_next is True
        assert page2.has_prev is True
        
        # Test last page
        page3 = mongodb_service.paginate_by_org("notifications", org_id, page=3, page_size=10)
        
        assert len(page3.items) == 5
        assert page3.page == 3
        assert page3.has_next is False
        assert page3.has_prev is True
    
    def test_count_by_org(self, mongodb_service, clean_database, sample_notification_data):
        """Test counting documents by organization."""
        user_id = str(ObjectId())
        org_id = sample_notification_data["organization_id"]
        
        # Initially no documents
        count = mongodb_service.count_by_org("notifications", org_id)
        assert count == 0
        
        # Create some documents
        for i in range(5):
            notification_data = sample_notification_data.copy()
            notification_data["title"] = f"Notification {i+1}"
            mongodb_service.create("notifications", notification_data, user_id)
        
        # Count should be 5
        count = mongodb_service.count_by_org("notifications", org_id)
        assert count == 5
        
        # Count with filters
        count_high_severity = mongodb_service.count_by_org(
            "notifications", 
            org_id, 
            filters={"severity": {"$gte": 4}}
        )
        assert count_high_severity == 5  # All notifications have severity 4
    
    def test_multi_tenant_isolation(self, mongodb_service, clean_database, sample_organization_data):
        """Test multi-tenant data isolation."""
        user_id = str(ObjectId())
        
        # Create organizations for two different tenants
        org1_id = str(ObjectId())
        org2_id = str(ObjectId())
        
        org1_data = sample_organization_data.copy()
        org1_data["organization_id"] = org1_id
        org1_data["name"] = "Organization 1"
        org1_data["slug"] = "org-1"
        
        org2_data = sample_organization_data.copy()
        org2_data["organization_id"] = org2_id
        org2_data["name"] = "Organization 2"
        org2_data["slug"] = "org-2"
        
        doc1_id = mongodb_service.create("organizations", org1_data, user_id)
        doc2_id = mongodb_service.create("organizations", org2_data, user_id)
        
        # Org 1 should only see its own documents
        org1_docs = mongodb_service.find_by_org("organizations", org1_id)
        assert len(org1_docs) == 1
        assert org1_docs[0]["id"] == doc1_id
        
        # Org 2 should only see its own documents
        org2_docs = mongodb_service.find_by_org("organizations", org2_id)
        assert len(org2_docs) == 1
        assert org2_docs[0]["id"] == doc2_id
        
        # Cross-tenant access should fail
        cross_access = mongodb_service.find_one_by_org("organizations", org1_id, doc2_id)
        assert cross_access is None
    
    def test_aggregation_with_org_scoping(self, mongodb_service, clean_database, sample_notification_data):
        """Test aggregation pipeline with organization scoping."""
        user_id = str(ObjectId())
        org_id = sample_notification_data["organization_id"]
        
        # Create notifications with different severities
        severities = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        for severity in severities:
            notification_data = sample_notification_data.copy()
            notification_data["severity"] = severity
            notification_data["title"] = f"Notification Severity {severity}"
            mongodb_service.create("notifications", notification_data, user_id)
        
        # Aggregation pipeline to count by severity
        pipeline = [
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = mongodb_service.aggregate_by_org("notifications", org_id, pipeline)
        
        assert len(results) == 5  # 5 different severity levels
        
        # Verify counts
        severity_counts = {result["_id"]: result["count"] for result in results}
        assert severity_counts[1] == 2
        assert severity_counts[2] == 2
        assert severity_counts[3] == 2
        assert severity_counts[4] == 2
        assert severity_counts[5] == 1
    
    def test_invalid_object_id(self, mongodb_service, clean_database):
        """Test handling of invalid ObjectId."""
        org_id = str(ObjectId())
        invalid_id = "invalid-object-id"
        
        # Should return None for invalid ID
        result = mongodb_service.find_one_by_org("organizations", org_id, invalid_id)
        assert result is None
        
        # Update should return False for invalid ID
        success = mongodb_service.update_by_org("organizations", org_id, invalid_id, {}, str(ObjectId()))
        assert success is False
        
        # Soft delete should return False for invalid ID
        success = mongodb_service.soft_delete_by_org("organizations", org_id, invalid_id, str(ObjectId()))
        assert success is False
    
    def test_create_indexes(self, mongodb_service, clean_database):
        """Test index creation."""
        # This should not raise any exceptions
        mongodb_service.create_indexes()
        
        # Verify some indexes were created
        orgs_collection = mongodb_service.get_collection("organizations")
        indexes = list(orgs_collection.list_indexes())
        
        # Should have at least _id index and slug index
        index_names = [idx["name"] for idx in indexes]
        assert "_id_" in index_names
        assert "slug_1" in index_names
    
    def test_collection_stats(self, mongodb_service, clean_database, sample_organization_data):
        """Test collection statistics."""
        user_id = str(ObjectId())
        
        # Create some documents
        for i in range(3):
            org_data = sample_organization_data.copy()
            org_data["name"] = f"Organization {i+1}"
            org_data["slug"] = f"org-{i+1}"
            mongodb_service.create("organizations", org_data, user_id)
        
        stats = mongodb_service.get_collection_stats("organizations")
        
        assert stats["collection"] == "organizations"
        assert stats["count"] == 3
        assert "size" in stats
        assert "storageSize" in stats
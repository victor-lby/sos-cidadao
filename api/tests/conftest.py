# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Pytest configuration and fixtures.
"""

import os
import pytest
from datetime import datetime
from typing import Dict, Any
from pymongo import MongoClient
from bson import ObjectId

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['MONGODB_DATABASE'] = 'sos_cidadao_test'


@pytest.fixture(scope="session")
def test_mongodb_uri():
    """Test MongoDB connection URI."""
    return os.getenv('MONGODB_TEST_URI', 'mongodb://localhost:27017/sos_cidadao_test')


@pytest.fixture(scope="session")
def test_database_name():
    """Test database name."""
    return 'sos_cidadao_test'


@pytest.fixture(scope="function")
def mongodb_client(test_mongodb_uri):
    """MongoDB client for testing."""
    client = MongoClient(test_mongodb_uri)
    yield client
    client.close()


@pytest.fixture(scope="function")
def clean_database(mongodb_client, test_database_name):
    """Clean test database before each test."""
    # Drop test database to ensure clean state
    mongodb_client.drop_database(test_database_name)
    yield mongodb_client[test_database_name]
    # Clean up after test
    mongodb_client.drop_database(test_database_name)


@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing."""
    return {
        "name": "Test Municipality",
        "slug": "test-municipality",
        "description": "Test organization for unit tests",
        "settings": {"timezone": "UTC", "language": "en"},
        "organization_id": str(ObjectId()),
        "created_by": str(ObjectId()),
        "updated_by": str(ObjectId())
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password_hash": "$2b$12$test.hash.value",
        "roles": [str(ObjectId())],
        "status": "active",
        "organization_id": str(ObjectId()),
        "created_by": str(ObjectId()),
        "updated_by": str(ObjectId())
    }


@pytest.fixture
def sample_notification_data():
    """Sample notification data for testing."""
    return {
        "title": "Test Emergency Alert",
        "body": "This is a test emergency notification",
        "severity": 4,
        "origin": "test-system",
        "original_payload": {"source": "test", "data": "sample"},
        "target_ids": [str(ObjectId())],
        "category_ids": [str(ObjectId())],
        "status": "received",
        "organization_id": str(ObjectId()),
        "created_by": str(ObjectId()),
        "updated_by": str(ObjectId())
    }


@pytest.fixture
def sample_role_data():
    """Sample role data for testing."""
    return {
        "name": "Test Role",
        "description": "Test role for unit tests",
        "permissions": ["notification:read", "notification:approve"],
        "is_system_role": False,
        "organization_id": str(ObjectId()),
        "created_by": str(ObjectId()),
        "updated_by": str(ObjectId())
    }


@pytest.fixture
def sample_audit_log_data():
    """Sample audit log data for testing."""
    return {
        "userId": str(ObjectId()),
        "organization_id": str(ObjectId()),
        "entity": "notification",
        "entityId": str(ObjectId()),
        "action": "approve",
        "before": {"status": "received"},
        "after": {"status": "approved"},
        "ipAddress": "192.168.1.1",
        "userAgent": "Mozilla/5.0 Test Browser",
        "traceId": "test-trace-id-123"
    }
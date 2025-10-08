# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Tests for API utilities.
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask, g
from datetime import datetime

from utils.request import RequestParser, ResponseBuilder, HeaderUtils
from utils.context import (
    OrganizationContextExtractor, RequestContextBuilder,
    get_organization_context, require_organization_access
)
from utils.versioning import APIVersionManager, require_api_version, version_compatibility
from middleware.error_handler import AuthorizationException, NotFoundException


class TestRequestParser:
    """Test request parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
    
    def test_get_pagination_params_defaults(self):
        """Test pagination parameters with defaults."""
        with self.app.test_request_context('/test'):
            params = RequestParser.get_pagination_params()
            
            assert params['page'] == 1
            assert params['page_size'] == 20
    
    def test_get_pagination_params_custom(self):
        """Test pagination parameters with custom values."""
        with self.app.test_request_context('/test?page=3&page_size=50'):
            params = RequestParser.get_pagination_params()
            
            assert params['page'] == 3
            assert params['page_size'] == 50
    
    def test_get_pagination_params_invalid(self):
        """Test pagination parameters with invalid values."""
        with self.app.test_request_context('/test?page=invalid&page_size=-5'):
            params = RequestParser.get_pagination_params()
            
            assert params['page'] == 1  # Default for invalid
            assert params['page_size'] == 20  # Default for invalid
    
    def test_get_pagination_params_max_limit(self):
        """Test pagination parameters with max limit."""
        with self.app.test_request_context('/test?page_size=200'):
            params = RequestParser.get_pagination_params(max_page_size=100)
            
            assert params['page_size'] == 100  # Clamped to max
    
    def test_get_sort_params_defaults(self):
        """Test sort parameters with defaults."""
        with self.app.test_request_context('/test'):
            params = RequestParser.get_sort_params(
                default_field='created_at',
                default_order='desc'
            )
            
            assert params['sort_by'] == 'created_at'
            assert params['sort_order'] == 'desc'
    
    def test_get_sort_params_custom(self):
        """Test sort parameters with custom values."""
        with self.app.test_request_context('/test?sort_by=title&sort_order=asc'):
            params = RequestParser.get_sort_params(
                allowed_fields=['title', 'created_at']
            )
            
            assert params['sort_by'] == 'title'
            assert params['sort_order'] == 'asc'
    
    def test_get_sort_params_invalid_field(self):
        """Test sort parameters with invalid field."""
        with self.app.test_request_context('/test?sort_by=invalid_field'):
            params = RequestParser.get_sort_params(
                allowed_fields=['title', 'created_at'],
                default_field='created_at'
            )
            
            assert params['sort_by'] == 'created_at'  # Falls back to default
    
    def test_get_filter_params(self):
        """Test filter parameter extraction."""
        with self.app.test_request_context('/test?status=received&severity=4&invalid=test'):
            params = RequestParser.get_filter_params(
                allowed_filters=['status', 'severity'],
                type_conversions={'severity': int}
            )
            
            assert params['status'] == 'received'
            assert params['severity'] == 4
            assert 'invalid' not in params  # Not in allowed filters
    
    def test_get_filter_params_type_conversion(self):
        """Test filter parameter type conversion."""
        with self.app.test_request_context('/test?active=true&tags=tag1,tag2,tag3'):
            params = RequestParser.get_filter_params(
                allowed_filters=['active', 'tags'],
                type_conversions={'active': bool, 'tags': list}
            )
            
            assert params['active'] is True
            assert params['tags'] == ['tag1', 'tag2', 'tag3']
    
    def test_get_search_params(self):
        """Test search parameter extraction."""
        with self.app.test_request_context('/test?q=emergency&search=alert'):
            params = RequestParser.get_search_params()
            
            assert params['q'] == 'emergency'
            assert params['search'] == 'alert'
    
    def test_get_request_metadata(self):
        """Test request metadata extraction."""
        with self.app.test_request_context(
            '/test',
            method='POST',
            headers={
                'User-Agent': 'Test Browser',
                'X-Session-ID': 'session123'
            }
        ):
            metadata = RequestParser.get_request_metadata()
            
            assert metadata['method'] == 'POST'
            assert metadata['path'] == '/test'
            assert metadata['user_agent'] == 'Test Browser'
            assert metadata['session_id'] == 'session123'
    
    def test_parse_json_body_success(self):
        """Test successful JSON body parsing."""
        with self.app.test_request_context(
            '/test',
            method='POST',
            json={'title': 'Test'},
            content_type='application/json'
        ):
            data = RequestParser.parse_json_body()
            
            assert data == {'title': 'Test'}
    
    def test_parse_json_body_missing_required(self):
        """Test JSON body parsing when required but missing."""
        with self.app.test_request_context('/test', method='POST'):
            with pytest.raises(ValueError, match="Content-Type"):
                RequestParser.parse_json_body(required=True)
    
    def test_parse_json_body_optional(self):
        """Test optional JSON body parsing."""
        with self.app.test_request_context('/test', method='GET'):
            data = RequestParser.parse_json_body(required=False)
            
            assert data is None
    
    def test_extract_path_params(self):
        """Test path parameter extraction."""
        with self.app.test_request_context('/orgs/org123/notifications/notif456'):
            # Mock view_args
            with patch('flask.request') as mock_request:
                mock_request.view_args = {
                    'org_id': 'org123',
                    'notification_id': 'notif456'
                }
                
                params = RequestParser.extract_path_params('org_id', 'notification_id')
                
                assert params['org_id'] == 'org123'
                assert params['notification_id'] == 'notif456'


class TestResponseBuilder:
    """Test response builder functionality."""
    
    def test_success_response(self):
        """Test building success response."""
        response, status_code, headers = ResponseBuilder.success(
            data={'id': '123'},
            message='Created successfully',
            status_code=201
        )
        
        assert response['success'] is True
        assert response['message'] == 'Created successfully'
        assert response['data'] == {'id': '123'}
        assert status_code == 201
    
    def test_success_response_no_data(self):
        """Test building success response without data."""
        response, status_code, headers = ResponseBuilder.success()
        
        assert response['success'] is True
        assert response['message'] == 'Success'
        assert 'data' not in response
        assert status_code == 200
    
    def test_error_response(self):
        """Test building error response."""
        response, status_code, headers = ResponseBuilder.error(
            message='Validation failed',
            status_code=400,
            error_type='validation_error',
            details={'field': 'title'}
        )
        
        assert response['success'] is False
        assert response['error']['type'] == 'validation_error'
        assert response['error']['message'] == 'Validation failed'
        assert response['error']['details'] == {'field': 'title'}
        assert status_code == 400
    
    def test_paginated_response(self):
        """Test building paginated response."""
        items = [{'id': '1'}, {'id': '2'}]
        
        response = ResponseBuilder.paginated(
            items=items,
            total=25,
            page=2,
            page_size=10,
            additional_data={'filters': {'status': 'active'}}
        )
        
        assert response['items'] == items
        assert response['pagination']['total'] == 25
        assert response['pagination']['page'] == 2
        assert response['pagination']['total_pages'] == 3
        assert response['pagination']['has_next'] is True
        assert response['pagination']['has_prev'] is True
        assert response['filters'] == {'status': 'active'}


class TestHeaderUtils:
    """Test header utilities functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
    
    def test_get_bearer_token(self):
        """Test Bearer token extraction."""
        with self.app.test_request_context(
            '/test',
            headers={'Authorization': 'Bearer abc123token'}
        ):
            token = HeaderUtils.get_bearer_token()
            assert token == 'abc123token'
    
    def test_get_bearer_token_missing(self):
        """Test Bearer token extraction when missing."""
        with self.app.test_request_context('/test'):
            token = HeaderUtils.get_bearer_token()
            assert token is None
    
    def test_accepts_json(self):
        """Test JSON acceptance check."""
        with self.app.test_request_context(
            '/test',
            headers={'Accept': 'application/json'}
        ):
            assert HeaderUtils.accepts_json() is True
        
        with self.app.test_request_context(
            '/test',
            headers={'Accept': 'text/html'}
        ):
            assert HeaderUtils.accepts_json() is False
    
    def test_prefers_hal(self):
        """Test HAL preference check."""
        with self.app.test_request_context(
            '/test',
            headers={'Accept': 'application/hal+json'}
        ):
            assert HeaderUtils.prefers_hal() is True
        
        with self.app.test_request_context(
            '/test',
            headers={'Accept': 'application/json'}
        ):
            assert HeaderUtils.prefers_hal() is False
    
    def test_build_cache_headers(self):
        """Test cache header building."""
        headers = HeaderUtils.build_cache_headers(
            max_age=3600,
            private=True
        )
        
        assert headers['Cache-Control'] == 'private, max-age=3600'
        
        headers = HeaderUtils.build_cache_headers(no_cache=True)
        assert headers['Cache-Control'] == 'no-cache'


class TestOrganizationContextExtractor:
    """Test organization context extractor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mongodb_service = Mock()
        self.extractor = OrganizationContextExtractor(self.mongodb_service)
        self.app = Flask(__name__)
    
    def test_extract_org_id_from_path(self):
        """Test organization ID extraction from path."""
        with self.app.test_request_context('/orgs/org123/notifications'):
            with patch('flask.request') as mock_request:
                mock_request.view_args = {'org_id': 'org123'}
                
                org_id = self.extractor.extract_org_id_from_path()
                assert org_id == 'org123'
    
    def test_extract_org_id_from_user_context(self):
        """Test organization ID extraction from user context."""
        user_context = Mock()
        user_context.org_id = 'org456'
        
        with self.app.test_request_context('/test'):
            g.user_context = user_context
            
            org_id = self.extractor.extract_org_id_from_user_context()
            assert org_id == 'org456'
    
    def test_validate_org_access_success(self):
        """Test successful organization access validation."""
        user_context = Mock()
        user_context.org_id = 'org123'
        user_context.user_id = 'user456'
        
        result = self.extractor.validate_org_access('org123', user_context)
        assert result is True
    
    def test_validate_org_access_denied(self):
        """Test denied organization access validation."""
        user_context = Mock()
        user_context.org_id = 'org123'
        user_context.user_id = 'user456'
        
        result = self.extractor.validate_org_access('org456', user_context)
        assert result is False
    
    def test_get_organization_context_success(self):
        """Test successful organization context retrieval."""
        user_context = Mock()
        user_context.org_id = 'org123'
        user_context.user_id = 'user456'
        
        # Mock organization data
        org_data = {
            'id': 'org123',
            'name': 'Test Org',
            'slug': 'test-org',
            'settings': {'timezone': 'UTC'}
        }
        self.mongodb_service.find_one_by_org.return_value = org_data
        
        context = self.extractor.get_organization_context('org123', user_context)
        
        assert context['id'] == 'org123'
        assert context['name'] == 'Test Org'
        assert context['user_context'] == user_context
    
    def test_get_organization_context_access_denied(self):
        """Test organization context with access denied."""
        user_context = Mock()
        user_context.org_id = 'org123'
        
        with pytest.raises(AuthorizationException):
            self.extractor.get_organization_context('org456', user_context)
    
    def test_get_organization_context_not_found(self):
        """Test organization context when organization not found."""
        user_context = Mock()
        user_context.org_id = 'org123'
        user_context.user_id = 'user456'
        
        self.mongodb_service.find_one_by_org.return_value = None
        
        with pytest.raises(NotFoundException):
            self.extractor.get_organization_context('org123', user_context)


class TestAPIVersionManager:
    """Test API version manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.version_manager = APIVersionManager(default_version="1.0")
        self.app = Flask(__name__)
    
    def test_add_supported_version(self):
        """Test adding supported version."""
        self.version_manager.add_supported_version("1.1")
        
        assert "1.1" in self.version_manager.supported_versions
    
    def test_deprecate_version(self):
        """Test deprecating version."""
        self.version_manager.deprecate_version("1.0")
        
        assert "1.0" in self.version_manager.deprecated_versions
    
    def test_extract_version_from_header(self):
        """Test version extraction from Accept header."""
        with self.app.test_request_context(
            '/test',
            headers={'Accept': 'application/vnd.api+json;version=1.1'}
        ):
            version = self.version_manager.extract_version_from_header()
            assert version == "1.1"
    
    def test_extract_version_from_path(self):
        """Test version extraction from URL path."""
        with self.app.test_request_context('/api/v1.2/notifications'):
            version = self.version_manager.extract_version_from_path()
            assert version == "1.2"
        
        with self.app.test_request_context('/api/v2/notifications'):
            version = self.version_manager.extract_version_from_path()
            assert version == "2.0"  # Normalized
    
    def test_extract_version_from_query(self):
        """Test version extraction from query parameter."""
        with self.app.test_request_context('/test?version=1.3'):
            version = self.version_manager.extract_version_from_query()
            assert version == "1.3"
    
    def test_get_requested_version_priority(self):
        """Test version extraction priority order."""
        with self.app.test_request_context(
            '/api/v2.0/test?version=1.5',
            headers={'Accept': 'application/vnd.api+json;version=1.1'}
        ):
            version = self.version_manager.get_requested_version()
            assert version == "1.1"  # Header has highest priority
    
    def test_is_version_supported(self):
        """Test version support checking."""
        assert self.version_manager.is_version_supported("1.0") is True
        assert self.version_manager.is_version_supported("2.0") is False
    
    def test_is_version_deprecated(self):
        """Test version deprecation checking."""
        self.version_manager.deprecate_version("1.0")
        
        assert self.version_manager.is_version_deprecated("1.0") is True
        assert self.version_manager.is_version_deprecated("1.1") is False
    
    def test_get_version_info(self):
        """Test version information retrieval."""
        self.version_manager.add_supported_version("1.1")
        self.version_manager.deprecate_version("1.0")
        
        info = self.version_manager.get_version_info("1.0")
        
        assert info['version'] == "1.0"
        assert info['supported'] is True
        assert info['deprecated'] is True
        assert info['default'] is True
    
    def test_require_api_version_decorator(self):
        """Test API version requirement decorator."""
        self.version_manager.add_supported_version("1.1")
        
        @require_api_version(["1.0", "1.1"], self.version_manager)
        def test_endpoint(version):
            return {"version": version}
        
        with self.app.test_request_context('/test?version=1.1'):
            result = test_endpoint()
            assert result == {"version": "1.1"}
    
    def test_require_api_version_unsupported(self):
        """Test API version decorator with unsupported version."""
        @require_api_version(["1.0"], self.version_manager)
        def test_endpoint(version):
            return {"version": version}
        
        with self.app.test_request_context('/test?version=2.0'):
            with self.app.app_context():
                result, status_code = test_endpoint()
                assert status_code == 400


# Integration tests
class TestAPIUtilitiesIntegration:
    """Integration tests for API utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.mongodb_service = Mock()
    
    def test_request_parsing_integration(self):
        """Test complete request parsing workflow."""
        with self.app.test_request_context(
            '/api/notifications?page=2&page_size=10&status=received&sort_by=created_at&sort_order=desc'
        ):
            # Parse all parameters
            pagination = RequestParser.get_pagination_params()
            sorting = RequestParser.get_sort_params(['created_at', 'title'])
            filters = RequestParser.get_filter_params(['status'])
            
            assert pagination['page'] == 2
            assert pagination['page_size'] == 10
            assert sorting['sort_by'] == 'created_at'
            assert sorting['sort_order'] == 'desc'
            assert filters['status'] == 'received'
    
    def test_organization_context_workflow(self):
        """Test complete organization context workflow."""
        user_context = Mock()
        user_context.org_id = 'org123'
        user_context.user_id = 'user456'
        
        # Mock organization data
        org_data = {
            'id': 'org123',
            'name': 'Test Municipality',
            'slug': 'test-municipality',
            'settings': {'timezone': 'UTC'}
        }
        self.mongodb_service.find_one_by_org.return_value = org_data
        
        with self.app.test_request_context('/orgs/org123/notifications'):
            g.user_context = user_context
            
            with patch('flask.request') as mock_request:
                mock_request.view_args = {'org_id': 'org123'}
                
                context = get_organization_context(
                    mongodb_service=self.mongodb_service
                )
                
                assert context['id'] == 'org123'
                assert context['name'] == 'Test Municipality'
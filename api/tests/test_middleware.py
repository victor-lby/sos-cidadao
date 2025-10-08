# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Tests for middleware functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, request, g
from pydantic import BaseModel, ValidationError
from datetime import datetime

from middleware.validation import ValidationMiddleware, validate_json, validate_query
from middleware.error_handler import (
    ErrorHandlerMiddleware, CustomException, ValidationException,
    AuthenticationException, AuthorizationException, NotFoundException
)
from middleware.cors import CORSMiddleware, configure_cors
from middleware.rate_limit import RateLimiter, rate_limit
from services.hal import HalFormatter


class TestValidationMiddleware:
    """Test validation middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.validation_middleware = ValidationMiddleware("https://api.example.com")
    
    def test_format_validation_errors(self):
        """Test formatting Pydantic validation errors."""
        # Create a mock ValidationError
        errors = [
            {
                "loc": ("title",),
                "msg": "field required",
                "type": "value_error.missing",
                "input": None
            },
            {
                "loc": ("severity",),
                "msg": "ensure this value is less than or equal to 5",
                "type": "value_error.number.not_le",
                "input": 10
            }
        ]
        
        # Mock ValidationError
        validation_error = Mock()
        validation_error.errors.return_value = errors
        
        result = self.validation_middleware.format_validation_errors(validation_error)
        
        assert len(result) == 2
        assert result[0]["field"] == "title"
        assert result[0]["message"] == "field required"
        assert result[1]["field"] == "severity"
        assert result[1]["input"] == 10
    
    def test_validate_json_body_success(self):
        """Test successful JSON body validation."""
        class TestModel(BaseModel):
            title: str
            severity: int
        
        with self.app.test_request_context(
            '/test',
            method='POST',
            json={"title": "Test", "severity": 3},
            content_type='application/json'
        ):
            decorator = self.validation_middleware.validate_json_body(TestModel)
            
            @decorator
            def test_route(validated_data):
                assert validated_data.title == "Test"
                assert validated_data.severity == 3
                return {"success": True}
            
            result = test_route()
            assert result == {"success": True}
    
    def test_validate_json_body_invalid_content_type(self):
        """Test JSON validation with invalid content type."""
        class TestModel(BaseModel):
            title: str
        
        with self.app.test_request_context(
            '/test',
            method='POST',
            data="not json",
            content_type='text/plain'
        ):
            decorator = self.validation_middleware.validate_json_body(TestModel)
            
            @decorator
            def test_route(validated_data):
                return {"success": True}
            
            result, status_code = test_route()
            assert status_code == 400
            assert "content-type" in str(result)
    
    def test_validate_json_body_validation_error(self):
        """Test JSON validation with Pydantic validation error."""
        class TestModel(BaseModel):
            title: str
            severity: int
        
        with self.app.test_request_context(
            '/test',
            method='POST',
            json={"title": "", "severity": "invalid"},  # Invalid data
            content_type='application/json'
        ):
            decorator = self.validation_middleware.validate_json_body(TestModel)
            
            @decorator
            def test_route(validated_data):
                return {"success": True}
            
            result, status_code = test_route()
            assert status_code == 400
            assert "validation" in str(result).lower()
    
    def test_validate_query_params_success(self):
        """Test successful query parameter validation."""
        class QueryModel(BaseModel):
            page: int = 1
            page_size: int = 20
            status: str = None
        
        with self.app.test_request_context('/test?page=2&page_size=10&status=received'):
            decorator = self.validation_middleware.validate_query_params(QueryModel)
            
            @decorator
            def test_route(validated_params):
                assert validated_params.page == 2
                assert validated_params.page_size == 10
                assert validated_params.status == "received"
                return {"success": True}
            
            result = test_route()
            assert result == {"success": True}
    
    def test_validate_query_params_validation_error(self):
        """Test query parameter validation with error."""
        class QueryModel(BaseModel):
            page: int
        
        with self.app.test_request_context('/test?page=invalid'):
            decorator = self.validation_middleware.validate_query_params(QueryModel)
            
            @decorator
            def test_route(validated_params):
                return {"success": True}
            
            result, status_code = test_route()
            assert status_code == 400


class TestErrorHandlerMiddleware:
    """Test error handler middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.error_handler = ErrorHandlerMiddleware(self.app, "https://api.example.com")
    
    def test_custom_exception_handling(self):
        """Test handling of custom exceptions."""
        with self.app.test_request_context('/test'):
            error = ValidationException("Test validation error", [{"field": "test"}])
            
            result, status_code = self.error_handler.handle_unexpected_error(error)
            
            # Should be handled by custom exception handler
            assert status_code == 500  # Unexpected error handler
    
    def test_authentication_exception(self):
        """Test authentication exception."""
        error = AuthenticationException("Invalid token")
        
        assert error.status_code == 401
        assert error.error_type == "authentication-required"
        assert error.message == "Invalid token"
    
    def test_authorization_exception(self):
        """Test authorization exception."""
        error = AuthorizationException("Insufficient permissions")
        
        assert error.status_code == 403
        assert error.error_type == "insufficient-permissions"
    
    def test_not_found_exception(self):
        """Test not found exception."""
        error = NotFoundException("Resource not found")
        
        assert error.status_code == 404
        assert error.error_type == "resource-not-found"


class TestCORSMiddleware:
    """Test CORS middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
    
    def test_cors_configuration(self):
        """Test CORS middleware configuration."""
        cors_middleware = configure_cors(
            self.app,
            allowed_origins=["http://localhost:3000"],
            allow_credentials=True
        )
        
        assert isinstance(cors_middleware, CORSMiddleware)
        assert "http://localhost:3000" in cors_middleware.allowed_origins
        assert cors_middleware.allow_credentials is True
    
    def test_is_origin_allowed(self):
        """Test origin validation."""
        cors_middleware = CORSMiddleware(
            self.app,
            allowed_origins=["http://localhost:3000", "https://*.example.com"]
        )
        
        assert cors_middleware.is_origin_allowed("http://localhost:3000") is True
        assert cors_middleware.is_origin_allowed("https://app.example.com") is True
        assert cors_middleware.is_origin_allowed("http://malicious.com") is False
    
    def test_preflight_request_handling(self):
        """Test CORS preflight request handling."""
        cors_middleware = CORSMiddleware(
            self.app,
            allowed_origins=["http://localhost:3000"]
        )
        
        with self.app.test_request_context(
            '/test',
            method='OPTIONS',
            headers={'Origin': 'http://localhost:3000'}
        ):
            # Simulate preflight handling
            response = cors_middleware.add_cors_headers(
                self.app.response_class(),
                "http://localhost:3000"
            )
            
            assert response.headers.get('Access-Control-Allow-Origin') == "http://localhost:3000"
            assert 'Access-Control-Allow-Methods' in response.headers
            assert 'Access-Control-Allow-Headers' in response.headers


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.redis_service = Mock()
        self.hal_formatter = Mock()
        self.rate_limiter = RateLimiter(self.redis_service, self.hal_formatter)
    
    def test_get_client_identifier_with_user(self):
        """Test client identifier generation with user context."""
        user_context = Mock()
        user_context.user_id = "user123"
        
        identifier = self.rate_limiter.get_client_identifier(user_context)
        
        assert identifier == "user:user123"
    
    def test_get_client_identifier_without_user(self):
        """Test client identifier generation without user context."""
        with patch('flask.request') as mock_request:
            mock_request.remote_addr = "192.168.1.1"
            mock_request.headers.get.return_value = "Mozilla/5.0"
            
            identifier = self.rate_limiter.get_client_identifier(None)
            
            assert identifier.startswith("ip:")
    
    def test_check_rate_limit_within_limit(self):
        """Test rate limit check when within limit."""
        self.redis_service.get.return_value = "5"  # Current count
        self.redis_service.set_with_ttl.return_value = True
        
        result = self.rate_limiter.check_rate_limit(
            "user:123", "test_endpoint", 10, 3600
        )
        
        assert result['allowed'] is True
        assert result['limit'] == 10
        assert result['remaining'] == 4  # 10 - 6 (5 + 1)
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded."""
        self.redis_service.get.return_value = "10"  # At limit
        
        result = self.rate_limiter.check_rate_limit(
            "user:123", "test_endpoint", 10, 3600
        )
        
        assert result['allowed'] is False
        assert result['remaining'] == 0
        assert result['retry_after'] > 0
    
    def test_check_rate_limit_redis_failure(self):
        """Test rate limit check when Redis fails."""
        self.redis_service.get.side_effect = Exception("Redis error")
        
        result = self.rate_limiter.check_rate_limit(
            "user:123", "test_endpoint", 10, 3600
        )
        
        # Should fail open (allow request)
        assert result['allowed'] is True
    
    def test_rate_limit_decorator(self):
        """Test rate limit decorator functionality."""
        app = Flask(__name__)
        app.redis_service = Mock()
        app.hal_formatter = Mock()
        
        # Mock successful rate limit check
        with patch.object(RateLimiter, 'check_rate_limit') as mock_check:
            mock_check.return_value = {
                'allowed': True,
                'limit': 100,
                'remaining': 99,
                'reset_time': 1234567890,
                'retry_after': 0
            }
            
            @rate_limit(100, 3600)
            def test_endpoint():
                return {"success": True}
            
            with app.test_request_context('/test'):
                with app.app_context():
                    result = test_endpoint()
                    assert result == {"success": True}
    
    def test_rate_limit_decorator_exceeded(self):
        """Test rate limit decorator when limit exceeded."""
        app = Flask(__name__)
        app.redis_service = Mock()
        app.hal_formatter = Mock()
        
        # Mock rate limit exceeded
        with patch.object(RateLimiter, 'check_rate_limit') as mock_check:
            mock_check.return_value = {
                'allowed': False,
                'limit': 100,
                'remaining': 0,
                'reset_time': 1234567890,
                'retry_after': 3600
            }
            
            # Mock HAL formatter
            app.hal_formatter.builder.build_error_response.return_value = {
                "error": "rate limit exceeded"
            }
            
            @rate_limit(100, 3600)
            def test_endpoint():
                return {"success": True}
            
            with app.test_request_context('/test'):
                with app.app_context():
                    response = test_endpoint()
                    assert response.status_code == 429


# Integration tests
class TestMiddlewareIntegration:
    """Integration tests for middleware components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    def test_validation_and_error_handling_integration(self):
        """Test integration between validation and error handling."""
        # Set up middleware
        validation_middleware = ValidationMiddleware("https://api.example.com")
        error_handler = ErrorHandlerMiddleware(self.app, "https://api.example.com")
        
        class TestModel(BaseModel):
            title: str
            severity: int
        
        @self.app.route('/test', methods=['POST'])
        @validation_middleware.validate_json_body(TestModel)
        def test_route(validated_data):
            return {"title": validated_data.title}
        
        with self.app.test_client() as client:
            # Test successful validation
            response = client.post(
                '/test',
                json={"title": "Test", "severity": 3},
                content_type='application/json'
            )
            assert response.status_code == 200
            
            # Test validation error
            response = client.post(
                '/test',
                json={"title": "", "severity": "invalid"},
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_cors_and_error_handling_integration(self):
        """Test integration between CORS and error handling."""
        # Configure CORS
        cors_middleware = configure_cors(
            self.app,
            allowed_origins=["http://localhost:3000"]
        )
        
        error_handler = ErrorHandlerMiddleware(self.app, "https://api.example.com")
        
        @self.app.route('/test')
        def test_route():
            return {"success": True}
        
        with self.app.test_client() as client:
            # Test CORS headers on successful response
            response = client.get(
                '/test',
                headers={'Origin': 'http://localhost:3000'}
            )
            assert 'Access-Control-Allow-Origin' in response.headers
            
            # Test CORS headers on error response
            response = client.get('/nonexistent')
            assert response.status_code == 404
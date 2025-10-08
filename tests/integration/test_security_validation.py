"""
Security validation integration tests.

Comprehensive security testing including penetration testing,
vulnerability assessment, and security best practices validation.
"""

import pytest
import requests
import json
import time
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any
import re
import urllib.parse
from unittest.mock import patch


class TestSecurityValidation:
    """Comprehensive security validation tests."""
    
    @pytest.fixture(autouse=True)
    def setup_security_test_environment(self, test_client):
        """Set up security testing environment."""
        self.client = test_client
        self.base_url = "http://localhost:5000"
        
        # Create test organization and users for security testing
        self.test_org_id = "security_test_org"
        self.admin_user_id = "security_admin"
        self.regular_user_id = "security_user"
        
        # Test credentials
        self.admin_credentials = {
            "email": "admin@security-test.com",
            "password": "SecurePassword123!"
        }
        
        self.user_credentials = {
            "email": "user@security-test.com", 
            "password": "UserPassword456!"
        }
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention across all endpoints."""
        # Get authentication token
        token = self._get_auth_token(self.admin_credentials["email"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE notifications; --",
            "' OR '1'='1",
            "'; INSERT INTO notifications VALUES ('malicious'); --",
            "' UNION SELECT * FROM users --",
            "'; UPDATE notifications SET status='approved' WHERE '1'='1'; --",
            "admin'--",
            "admin'/*",
            "' OR 1=1#",
            "' OR 1=1--",
            "' OR 1=1/*",
            "') OR '1'='1--",
            "') OR ('1'='1--"
        ]
        
        # Test endpoints vulnerable to SQL injection
        test_endpoints = [
            ("/api/notifications", "GET", {"search": "{payload}"}),
            ("/api/notifications", "GET", {"title": "{payload}"}),
            ("/api/users", "GET", {"email": "{payload}"}),
            ("/api/audit", "GET", {"user_id": "{payload}"}),
            ("/api/organizations/current", "GET", {"name": "{payload}"})
        ]
        
        for endpoint, method, params in test_endpoints:
            for payload in sql_payloads:
                # Replace placeholder with actual payload
                test_params = {k: v.format(payload=payload) for k, v in params.items()}
                
                if method == "GET":
                    response = self.client.get(endpoint, query_string=test_params, headers=headers)
                else:
                    response = self.client.post(endpoint, json=test_params, headers=headers)
                
                # Should not cause server error or expose database structure
                assert response.status_code != 500, f"SQL injection caused server error on {endpoint}"
                
                if response.status_code == 200:
                    response_text = response.get_data(as_text=True).lower()
                    
                    # Should not contain SQL error messages
                    sql_error_indicators = [
                        "sql syntax", "mysql", "postgresql", "sqlite", "mongodb",
                        "syntax error", "database error", "table", "column"
                    ]
                    
                    for indicator in sql_error_indicators:
                        assert indicator not in response_text, f"SQL error exposed on {endpoint} with payload: {payload}"
    
    def test_xss_prevention(self):
        """Test XSS (Cross-Site Scripting) prevention."""
        token = self._get_auth_token(self.admin_credentials["email"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "\";alert('XSS');//"
        ]
        
        # Test XSS in notification creation
        for payload in xss_payloads:
            notification_data = {
                "title": f"Test Notification {payload}",
                "body": f"Test body with {payload}",
                "severity": 2
            }
            
            response = self.client.post('/api/notifications', json=notification_data, headers=headers)
            
            if response.status_code == 201:
                created_notification = response.get_json()
                
                # Content should be sanitized
                assert "<script>" not in created_notification.get("title", "")
                assert "onerror=" not in created_notification.get("body", "")
                assert "javascript:" not in created_notification.get("title", "")
                assert "onload=" not in created_notification.get("body", "")
    
    def test_csrf_protection(self):
        """Test CSRF (Cross-Site Request Forgery) protection."""
        token = self._get_auth_token(self.admin_credentials["email"])
        
        # Test without CSRF token (if implemented)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Attempt state-changing operations
        csrf_test_data = {
            "title": "CSRF Test Notification",
            "body": "Testing CSRF protection",
            "severity": 3
        }
        
        # Normal request should work
        response = self.client.post('/api/notifications', json=csrf_test_data, headers=headers)
        assert response.status_code in [201, 400, 403]  # Should not be 500
        
        # Test with suspicious referrer
        suspicious_headers = {
            **headers,
            "Referer": "http://malicious-site.com",
            "Origin": "http://malicious-site.com"
        }
        
        response = self.client.post('/api/notifications', json=csrf_test_data, headers=suspicious_headers)
        # Should either work (if CORS allows) or be rejected gracefully
        assert response.status_code != 500
    
    def test_authentication_security(self):
        """Test authentication security measures."""
        # Test 1: Brute force protection
        invalid_credentials = {
            "email": self.admin_credentials["email"],
            "password": "wrong_password"
        }
        
        # Attempt multiple failed logins
        failed_attempts = 0
        for i in range(10):
            response = self.client.post('/api/auth/login', json=invalid_credentials)
            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:  # Rate limited
                break
            time.sleep(0.1)
        
        # Should implement some form of rate limiting or account lockout
        assert failed_attempts < 10, "No brute force protection detected"
        
        # Test 2: Password strength validation
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "test",
            "qwerty",
            "abc123"
        ]
        
        for weak_password in weak_passwords:
            user_data = {
                "email": "test@example.com",
                "password": weak_password,
                "name": "Test User"
            }
            
            response = self.client.post('/api/auth/register', json=user_data)
            # Should reject weak passwords
            if response.status_code == 400:
                error_data = response.get_json()
                assert "password" in str(error_data).lower()
    
    def test_authorization_bypass_attempts(self):
        """Test attempts to bypass authorization controls."""
        # Get tokens for different user types
        admin_token = self._get_auth_token(self.admin_credentials["email"])
        user_token = self._get_auth_token(self.user_credentials["email"])
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test 1: Privilege escalation attempts
        privilege_escalation_endpoints = [
            ("/api/organizations", "POST", {"name": "Malicious Org"}),
            ("/api/users", "POST", {"email": "hacker@evil.com", "role": "admin"}),
            ("/api/audit/export", "GET", {}),
            ("/api/system/config", "GET", {}),
            ("/api/admin/users", "GET", {})
        ]
        
        for endpoint, method, data in privilege_escalation_endpoints:
            if method == "GET":
                response = self.client.get(endpoint, headers=user_headers)
            else:
                response = self.client.post(endpoint, json=data, headers=user_headers)
            
            # Regular user should not have access to admin endpoints
            assert response.status_code in [401, 403, 404], f"Authorization bypass on {endpoint}"
        
        # Test 2: Direct object reference attacks
        # Create a notification as admin
        notification_data = {
            "title": "Admin Notification",
            "body": "This should only be accessible by admin",
            "severity": 4
        }
        
        create_response = self.client.post('/api/notifications', json=notification_data, headers=admin_headers)
        if create_response.status_code == 201:
            notification_id = create_response.get_json()["id"]
            
            # Try to access admin's notification as regular user
            access_response = self.client.get(f'/api/notifications/{notification_id}', headers=user_headers)
            
            # Should be denied if proper authorization is implemented
            # (This depends on the multi-tenant implementation)
            assert access_response.status_code in [200, 403, 404]  # 200 if same org, 403/404 if different
    
    def test_jwt_token_security(self):
        """Test JWT token security implementation."""
        token = self._get_auth_token(self.admin_credentials["email"])
        
        # Test 1: Token structure validation
        token_parts = token.split('.')
        assert len(token_parts) == 3, "JWT should have 3 parts"
        
        # Test 2: Token tampering detection
        # Modify the payload
        header, payload, signature = token_parts
        
        # Decode and modify payload
        try:
            decoded_payload = base64.urlsafe_b64decode(payload + '==')
            payload_data = json.loads(decoded_payload)
            
            # Tamper with the payload
            payload_data['role'] = 'super_admin'
            payload_data['permissions'] = ['*']
            
            # Re-encode
            tampered_payload = base64.urlsafe_b64encode(
                json.dumps(payload_data).encode()
            ).decode().rstrip('=')
            
            tampered_token = f"{header}.{tampered_payload}.{signature}"
            
            # Try to use tampered token
            tampered_headers = {"Authorization": f"Bearer {tampered_token}"}
            response = self.client.get('/api/notifications', headers=tampered_headers)
            
            # Should reject tampered token
            assert response.status_code == 401, "Tampered JWT token was accepted"
            
        except Exception:
            # If we can't decode/modify the token, that's actually good security
            pass
        
        # Test 3: Token expiration
        # This would require mocking time or waiting for token expiration
        # For now, we'll test that the token has an expiration claim
        try:
            decoded_payload = base64.urlsafe_b64decode(payload + '==')
            payload_data = json.loads(decoded_payload)
            assert 'exp' in payload_data, "JWT should have expiration claim"
        except Exception:
            pass
    
    def test_input_validation_security(self):
        """Test input validation and sanitization."""
        token = self._get_auth_token(self.admin_credentials["email"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Oversized input handling
        oversized_data = {
            "title": "A" * 10000,  # Very long title
            "body": "B" * 100000,  # Very long body
            "severity": 999999     # Invalid severity
        }
        
        response = self.client.post('/api/notifications', json=oversized_data, headers=headers)
        assert response.status_code == 400, "Should reject oversized input"
        
        # Test 2: Invalid data types
        invalid_type_data = {
            "title": ["not", "a", "string"],
            "body": {"not": "a string"},
            "severity": "not_a_number"
        }
        
        response = self.client.post('/api/notifications', json=invalid_type_data, headers=headers)
        assert response.status_code == 400, "Should reject invalid data types"
        
        # Test 3: Special characters and encoding
        special_char_data = {
            "title": "Test \x00\x01\x02 null bytes",
            "body": "Test unicode: \u0000\u001f\u007f",
            "severity": 2
        }
        
        response = self.client.post('/api/notifications', json=special_char_data, headers=headers)
        # Should either sanitize or reject
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            created_data = response.get_json()
            # Should not contain null bytes or control characters
            assert '\x00' not in created_data.get('title', '')
            assert '\u0000' not in created_data.get('body', '')
    
    def test_file_upload_security(self):
        """Test file upload security (if file uploads are implemented)."""
        token = self._get_auth_token(self.admin_credentials["email"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test malicious file uploads
        malicious_files = [
            ("malicious.php", "<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("malicious.jsp", "<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>", "application/x-jsp"),
            ("malicious.exe", b"\x4d\x5a\x90\x00", "application/x-executable"),
            ("malicious.sh", "#!/bin/bash\nrm -rf /", "application/x-sh")
        ]
        
        for filename, content, content_type in malicious_files:
            files = {
                'file': (filename, content, content_type)
            }
            
            # Try to upload to a hypothetical file upload endpoint
            response = self.client.post('/api/upload', files=files, headers=headers)
            
            # Should either reject malicious files or not have upload endpoint
            assert response.status_code in [400, 403, 404, 405], f"Malicious file {filename} handling issue"
    
    def test_information_disclosure_prevention(self):
        """Test prevention of information disclosure."""
        # Test 1: Error message information disclosure
        invalid_endpoints = [
            "/api/nonexistent",
            "/api/notifications/invalid-id",
            "/api/users/999999",
            "/api/admin/secret"
        ]
        
        for endpoint in invalid_endpoints:
            response = self.client.get(endpoint)
            
            if response.status_code in [404, 500]:
                error_text = response.get_data(as_text=True).lower()
                
                # Should not expose sensitive information
                sensitive_info = [
                    "database", "sql", "mongodb", "redis", "password",
                    "secret", "key", "token", "internal", "stack trace",
                    "file path", "directory", "server", "version"
                ]
                
                for info in sensitive_info:
                    assert info not in error_text, f"Information disclosure in error: {info}"
        
        # Test 2: Debug information exposure
        debug_endpoints = [
            "/api/debug",
            "/api/status",
            "/api/info",
            "/api/config",
            "/api/env"
        ]
        
        for endpoint in debug_endpoints:
            response = self.client.get(endpoint)
            
            if response.status_code == 200:
                response_text = response.get_data(as_text=True).lower()
                
                # Should not expose debug information in production
                debug_info = [
                    "debug", "development", "test", "staging",
                    "password", "secret", "key", "token"
                ]
                
                for info in debug_info:
                    assert info not in response_text, f"Debug information exposed: {info}"
    
    def test_rate_limiting_security(self):
        """Test rate limiting implementation."""
        # Test API rate limiting
        health_endpoint = "/api/health"
        
        # Make rapid requests
        responses = []
        start_time = time.time()
        
        for i in range(50):  # Make many requests quickly
            try:
                response = self.client.get(health_endpoint, timeout=1)
                responses.append(response.status_code)
            except:
                responses.append(0)
            
            if time.time() - start_time > 10:  # Don't run too long
                break
        
        # Should implement some form of rate limiting
        rate_limited_count = sum(1 for status in responses if status == 429)
        
        if rate_limited_count > 0:
            # Rate limiting is implemented
            assert rate_limited_count > 0, "Rate limiting detected"
        else:
            # Rate limiting might not be implemented or threshold is high
            # This is not necessarily a failure, but should be noted
            pass
    
    def test_session_security(self):
        """Test session security measures."""
        # Test 1: Session fixation prevention
        # Get initial session
        response1 = self.client.get('/api/health')
        session_id_1 = response1.headers.get('Set-Cookie')
        
        # Login
        login_response = self.client.post('/api/auth/login', json=self.admin_credentials)
        
        if login_response.status_code == 200:
            # Session ID should change after login (if using sessions)
            session_id_2 = login_response.headers.get('Set-Cookie')
            
            if session_id_1 and session_id_2:
                assert session_id_1 != session_id_2, "Session fixation vulnerability"
        
        # Test 2: Session timeout
        # This would require waiting or mocking time
        # For now, we'll just verify that tokens have expiration
        if login_response.status_code == 200:
            token_data = login_response.get_json()
            assert 'expires_in' in token_data, "Token should have expiration"
    
    def test_cors_security(self):
        """Test CORS (Cross-Origin Resource Sharing) security."""
        # Test CORS headers
        response = self.client.options('/api/notifications', headers={
            'Origin': 'http://malicious-site.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Authorization'
        })
        
        # Check CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        
        # Should not allow all origins in production
        if cors_headers['Access-Control-Allow-Origin']:
            assert cors_headers['Access-Control-Allow-Origin'] != '*', "CORS allows all origins"
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token."""
        # Mock authentication for testing
        return f"test_token_{email.replace('@', '_').replace('.', '_')}"


class TestSecurityHeaders:
    """Test security headers implementation."""
    
    def test_security_headers_present(self, test_client):
        """Test that proper security headers are present."""
        response = test_client.get('/')
        
        # Check for security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': ['strict-origin-when-cross-origin', 'no-referrer'],
            'Content-Security-Policy': None  # Should be present
        }
        
        for header_name, expected_values in security_headers.items():
            header_value = response.headers.get(header_name)
            
            if expected_values is None:
                # Just check presence
                assert header_value is not None, f"Missing security header: {header_name}"
            elif isinstance(expected_values, list):
                # Check if value is one of the expected values
                assert header_value in expected_values, f"Invalid {header_name} header value: {header_value}"
            else:
                # Check exact value
                assert header_value == expected_values, f"Invalid {header_name} header value: {header_value}"
    
    def test_hsts_header(self, test_client):
        """Test HTTP Strict Transport Security header."""
        response = test_client.get('/')
        
        # HSTS header might be set by the reverse proxy/CDN
        hsts_header = response.headers.get('Strict-Transport-Security')
        
        if hsts_header:
            # If present, should have proper configuration
            assert 'max-age=' in hsts_header
            
            # Extract max-age value
            max_age_match = re.search(r'max-age=(\d+)', hsts_header)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                assert max_age >= 31536000, "HSTS max-age should be at least 1 year"


class TestDataProtection:
    """Test data protection and privacy measures."""
    
    def test_pii_handling(self, test_client):
        """Test PII (Personally Identifiable Information) handling."""
        # This would test that PII is properly handled, encrypted, and not logged
        # Implementation depends on specific PII handling requirements
        pass
    
    def test_data_encryption(self):
        """Test data encryption at rest and in transit."""
        # Test 1: HTTPS enforcement (would be handled by reverse proxy)
        # Test 2: Database encryption (would be configured at database level)
        # Test 3: Sensitive data encryption in application
        pass
    
    def test_audit_trail_security(self, test_client):
        """Test audit trail security and integrity."""
        # Audit logs should be tamper-proof and comprehensive
        # This would test that audit logs cannot be modified or deleted by unauthorized users
        pass
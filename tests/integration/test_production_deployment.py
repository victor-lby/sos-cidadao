"""
Production deployment integration tests.

Tests production deployment configuration, external service integrations,
and production-specific functionality.
"""

import pytest
import os
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional
import json
import pymongo
import redis
import pika
from urllib.parse import urlparse


class TestProductionDeployment:
    """Test production deployment configuration and external services."""
    
    @pytest.fixture(autouse=True)
    def setup_production_config(self):
        """Set up production configuration for testing."""
        self.deployment_url = os.getenv('DEPLOYMENT_URL', 'https://sos-cidadao-platform.vercel.app')
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.redis_url = os.getenv('REDIS_URL')
        self.redis_token = os.getenv('REDIS_TOKEN')
        self.amqp_url = os.getenv('AMQP_URL')
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.otel_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
        
        # Ensure deployment URL has protocol
        if not self.deployment_url.startswith(('http://', 'https://')):
            self.deployment_url = f'https://{self.deployment_url}'
        
        # Remove trailing slash
        self.deployment_url = self.deployment_url.rstrip('/')
    
    def test_vercel_deployment_accessibility(self):
        """Test that Vercel deployment is accessible and responsive."""
        response = requests.get(self.deployment_url, timeout=30)
        
        assert response.status_code in [200, 301, 302], f"Deployment not accessible: {response.status_code}"
        
        # Check response time
        assert response.elapsed.total_seconds() < 5.0, "Deployment response time too slow"
        
        # Check for basic HTML structure (frontend)
        if response.status_code == 200:
            assert 'html' in response.text.lower(), "Response doesn't contain HTML"
    
    def test_api_health_endpoint_production(self):
        """Test API health endpoint in production environment."""
        health_url = f"{self.deployment_url}/api/health"
        response = requests.get(health_url, timeout=30)
        
        assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
        assert response.headers.get('content-type') == 'application/hal+json'
        
        health_data = response.json()
        
        # Verify health response structure
        assert health_data['status'] == 'healthy'
        assert 'version' in health_data
        assert 'environment' in health_data
        assert health_data['environment'] == 'production'
        
        # Verify HAL structure
        assert '_links' in health_data
        assert 'self' in health_data['_links']
        
        # Verify dependency checks
        if 'dependencies' in health_data:
            dependencies = health_data['dependencies']
            
            # MongoDB should be healthy
            if 'mongodb' in dependencies:
                assert dependencies['mongodb']['status'] == 'healthy'
            
            # Redis should be healthy
            if 'redis' in dependencies:
                assert dependencies['redis']['status'] == 'healthy'
            
            # AMQP should be healthy
            if 'amqp' in dependencies:
                assert dependencies['amqp']['status'] == 'healthy'
    
    def test_mongodb_atlas_integration(self):
        """Test MongoDB Atlas integration and connectivity."""
        if not self.mongodb_uri:
            pytest.skip("MongoDB URI not configured")
        
        # Test connection
        client = pymongo.MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=10000)
        
        try:
            # Test server info
            server_info = client.server_info()
            assert 'version' in server_info
            
            # Test database access
            db = client.get_default_database()
            
            # Test collection operations
            test_collection = db.test_connection
            
            # Insert test document
            test_doc = {
                'test': True,
                'timestamp': datetime.utcnow(),
                'deployment_test': True
            }
            
            result = test_collection.insert_one(test_doc)
            assert result.inserted_id is not None
            
            # Read test document
            retrieved_doc = test_collection.find_one({'_id': result.inserted_id})
            assert retrieved_doc is not None
            assert retrieved_doc['test'] is True
            
            # Clean up test document
            test_collection.delete_one({'_id': result.inserted_id})
            
        finally:
            client.close()
    
    def test_upstash_redis_integration(self):
        """Test Upstash Redis integration and connectivity."""
        if not self.redis_url:
            pytest.skip("Redis URL not configured")
        
        # Parse Redis URL for HTTP-based connection (Upstash)
        if self.redis_url.startswith('https://'):
            # HTTP-based Redis (Upstash)
            self._test_upstash_http_redis()
        else:
            # Standard Redis connection
            self._test_standard_redis()
    
    def _test_upstash_http_redis(self):
        """Test Upstash HTTP-based Redis."""
        headers = {}
        if self.redis_token:
            headers['Authorization'] = f'Bearer {self.redis_token}'
        
        # Test PING command
        ping_url = f"{self.redis_url}/ping"
        response = requests.get(ping_url, headers=headers, timeout=10)
        
        assert response.status_code == 200
        assert response.json()['result'] == 'PONG'
        
        # Test SET command
        set_url = f"{self.redis_url}/set/test_key/test_value"
        response = requests.post(set_url, headers=headers, timeout=10)
        assert response.status_code == 200
        
        # Test GET command
        get_url = f"{self.redis_url}/get/test_key"
        response = requests.get(get_url, headers=headers, timeout=10)
        assert response.status_code == 200
        assert response.json()['result'] == 'test_value'
        
        # Clean up test key
        del_url = f"{self.redis_url}/del/test_key"
        requests.post(del_url, headers=headers, timeout=10)
    
    def _test_standard_redis(self):
        """Test standard Redis connection."""
        # Parse Redis URL
        parsed_url = urlparse(self.redis_url)
        
        redis_client = redis.Redis(
            host=parsed_url.hostname,
            port=parsed_url.port or 6379,
            password=parsed_url.password,
            decode_responses=True,
            socket_timeout=10
        )
        
        try:
            # Test PING
            assert redis_client.ping() is True
            
            # Test SET/GET
            redis_client.set('test_key', 'test_value', ex=60)
            assert redis_client.get('test_key') == 'test_value'
            
            # Clean up
            redis_client.delete('test_key')
            
        finally:
            redis_client.close()
    
    def test_cloudamqp_lavinmq_integration(self):
        """Test CloudAMQP LavinMQ integration and connectivity."""
        if not self.amqp_url:
            pytest.skip("AMQP URL not configured")
        
        # Test AMQP connection
        connection = pika.BlockingConnection(
            pika.URLParameters(self.amqp_url)
        )
        
        try:
            channel = connection.channel()
            
            # Declare test queue
            test_queue = 'test_deployment_queue'
            channel.queue_declare(queue=test_queue, durable=False, auto_delete=True)
            
            # Publish test message
            test_message = json.dumps({
                'test': True,
                'timestamp': datetime.utcnow().isoformat(),
                'deployment_test': True
            })
            
            channel.basic_publish(
                exchange='',
                routing_key=test_queue,
                body=test_message,
                properties=pika.BasicProperties(
                    delivery_mode=1,  # Non-persistent
                    timestamp=int(time.time())
                )
            )
            
            # Consume test message
            method_frame, header_frame, body = channel.basic_get(queue=test_queue)
            
            assert method_frame is not None, "No message received"
            assert body is not None
            
            received_message = json.loads(body)
            assert received_message['test'] is True
            assert received_message['deployment_test'] is True
            
            # Acknowledge message
            channel.basic_ack(method_frame.delivery_tag)
            
            # Clean up test queue
            channel.queue_delete(queue=test_queue)
            
        finally:
            connection.close()
    
    def test_opentelemetry_observability_production(self):
        """Test OpenTelemetry observability in production environment."""
        health_url = f"{self.deployment_url}/api/health"
        response = requests.get(health_url, timeout=30)
        
        assert response.status_code == 200
        health_data = response.json()
        
        # Check observability configuration
        if 'observability' in health_data:
            observability = health_data['observability']
            
            # OpenTelemetry should be enabled in production
            assert observability.get('otel_enabled') is True
            
            # Check if OTLP endpoint is configured
            if self.otel_endpoint:
                # Make a test request to generate traces
                test_url = f"{self.deployment_url}/api"
                requests.get(test_url, timeout=30)
                
                # Note: We can't directly verify trace export without access to the collector
                # This would typically be verified through the observability platform
    
    def test_environment_variables_configuration(self):
        """Test that all required environment variables are properly configured."""
        health_url = f"{self.deployment_url}/api/health"
        response = requests.get(health_url, timeout=30)
        
        assert response.status_code == 200
        health_data = response.json()
        
        # Check configuration status
        if 'configuration' in health_data:
            config = health_data['configuration']
            
            # All critical configurations should be present
            assert config.get('mongodb_uri_configured') is True, "MongoDB URI not configured"
            assert config.get('redis_configured') is True, "Redis not configured"
            assert config.get('amqp_configured') is True, "AMQP not configured"
            assert config.get('jwt_secret_configured') is True, "JWT secret not configured"
            
            # Environment should be production
            assert config.get('environment') == 'production'
    
    def test_api_endpoints_hal_compliance(self):
        """Test that API endpoints return proper HAL responses in production."""
        # Test API root
        api_url = f"{self.deployment_url}/api"
        response = requests.get(api_url, timeout=30)
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/hal+json'
        
        api_data = response.json()
        
        # Verify HAL structure
        assert '_links' in api_data
        assert 'self' in api_data['_links']
        
        # Verify major resource links
        expected_links = ['notifications', 'organizations', 'audit', 'health']
        for link_rel in expected_links:
            assert link_rel in api_data['_links'], f"Missing {link_rel} link"
    
    def test_security_headers_production(self):
        """Test that proper security headers are set in production."""
        response = requests.get(self.deployment_url, timeout=30)
        
        headers = response.headers
        
        # Check security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header_name, expected_value in security_headers.items():
            assert header_name in headers, f"Missing security header: {header_name}"
            assert headers[header_name] == expected_value, f"Incorrect {header_name} header value"
        
        # Check HTTPS
        assert self.deployment_url.startswith('https://'), "Deployment should use HTTPS"
        
        # Check for HSTS header (may be set by Vercel)
        if 'Strict-Transport-Security' in headers:
            assert 'max-age=' in headers['Strict-Transport-Security']
    
    def test_api_rate_limiting_production(self):
        """Test API rate limiting in production environment."""
        health_url = f"{self.deployment_url}/api/health"
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            try:
                response = requests.get(health_url, timeout=5)
                responses.append(response.status_code)
            except requests.RequestException:
                responses.append(0)
            
            time.sleep(0.1)  # Small delay between requests
        
        # Most requests should succeed
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 8, "Too many requests failed, possible rate limiting issues"
        
        # Check for rate limiting headers if any request was rate limited
        rate_limited = any(status == 429 for status in responses)
        if rate_limited:
            # Make one more request to check rate limiting headers
            response = requests.get(health_url, timeout=5)
            if response.status_code == 429:
                assert 'Retry-After' in response.headers
    
    def test_error_handling_production(self):
        """Test error handling in production environment."""
        # Test 404 error
        not_found_url = f"{self.deployment_url}/api/nonexistent-endpoint"
        response = requests.get(not_found_url, timeout=30)
        
        assert response.status_code == 404
        
        # Should still return HAL structure for API errors
        if response.headers.get('content-type') == 'application/hal+json':
            error_data = response.json()
            assert '_links' in error_data
            assert 'self' in error_data['_links']
    
    def test_frontend_production_build(self):
        """Test that frontend is properly built and served in production."""
        response = requests.get(self.deployment_url, timeout=30)
        
        assert response.status_code == 200
        
        # Check for production build indicators
        html_content = response.text
        
        # Should contain minified assets
        assert 'assets/' in html_content or 'static/' in html_content
        
        # Should not contain development indicators
        assert 'localhost' not in html_content
        assert 'development' not in html_content.lower()
        
        # Should contain proper meta tags
        assert '<meta' in html_content
        assert 'viewport' in html_content
    
    def test_cors_configuration_production(self):
        """Test CORS configuration in production."""
        api_url = f"{self.deployment_url}/api"
        
        # Test preflight request
        response = requests.options(
            api_url,
            headers={
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Authorization'
            },
            timeout=30
        )
        
        # CORS should be properly configured
        # The exact behavior depends on the CORS configuration
        assert response.status_code in [200, 204, 405]  # Various valid responses
    
    def test_performance_production(self):
        """Test performance characteristics in production."""
        health_url = f"{self.deployment_url}/api/health"
        
        # Measure response times
        response_times = []
        for i in range(5):
            start_time = time.time()
            response = requests.get(health_url, timeout=30)
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
            
            time.sleep(1)  # Wait between requests
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times)
        
        # Production should respond quickly
        assert avg_response_time < 2.0, f"Average response time too slow: {avg_response_time:.2f}s"
        
        # No response should be extremely slow
        max_response_time = max(response_times)
        assert max_response_time < 5.0, f"Maximum response time too slow: {max_response_time:.2f}s"


class TestProductionDataIntegrity:
    """Test data integrity and consistency in production environment."""
    
    def test_database_indexes_production(self):
        """Test that proper database indexes are created in production."""
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            pytest.skip("MongoDB URI not configured")
        
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        
        try:
            db = client.get_default_database()
            
            # Check indexes on critical collections
            collections_to_check = ['notifications', 'users', 'organizations', 'audit_logs']
            
            for collection_name in collections_to_check:
                if collection_name in db.list_collection_names():
                    collection = db[collection_name]
                    indexes = list(collection.list_indexes())
                    
                    # Should have at least _id index
                    assert len(indexes) >= 1
                    
                    # Check for organization scoping index
                    org_index_found = any(
                        'organizationId' in idx.get('key', {})
                        for idx in indexes
                    )
                    
                    if collection_name != 'organizations':
                        assert org_index_found, f"Missing organizationId index on {collection_name}"
        
        finally:
            client.close()
    
    def test_data_migration_status(self):
        """Test that data migrations have been applied in production."""
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            pytest.skip("MongoDB URI not configured")
        
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        
        try:
            db = client.get_default_database()
            
            # Check for migration tracking collection
            if 'migrations' in db.list_collection_names():
                migrations = db.migrations
                applied_migrations = list(migrations.find({}))
                
                # Should have some migrations applied
                assert len(applied_migrations) > 0, "No migrations found"
                
                # Check that migrations have proper structure
                for migration in applied_migrations:
                    assert 'name' in migration
                    assert 'applied_at' in migration
                    assert 'version' in migration
        
        finally:
            client.close()


class TestProductionMonitoring:
    """Test production monitoring and observability."""
    
    def test_health_check_comprehensive(self):
        """Test comprehensive health check in production."""
        deployment_url = os.getenv('DEPLOYMENT_URL', 'https://sos-cidadao-platform.vercel.app')
        if not deployment_url.startswith(('http://', 'https://')):
            deployment_url = f'https://{deployment_url}'
        
        health_url = f"{deployment_url.rstrip('/')}/api/health"
        response = requests.get(health_url, timeout=30)
        
        assert response.status_code == 200
        health_data = response.json()
        
        # Verify comprehensive health information
        assert 'status' in health_data
        assert 'version' in health_data
        assert 'environment' in health_data
        assert 'timestamp' in health_data
        assert 'response_time_ms' in health_data
        
        # Verify dependency health checks
        if 'dependencies' in health_data:
            dependencies = health_data['dependencies']
            
            for service_name, service_health in dependencies.items():
                assert 'status' in service_health
                assert 'response_time_ms' in service_health
                
                # Critical services should be healthy
                if service_name in ['mongodb', 'redis']:
                    assert service_health['status'] == 'healthy', f"{service_name} is not healthy"
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint if available."""
        deployment_url = os.getenv('DEPLOYMENT_URL', 'https://sos-cidadao-platform.vercel.app')
        if not deployment_url.startswith(('http://', 'https://')):
            deployment_url = f'https://{deployment_url}'
        
        metrics_url = f"{deployment_url.rstrip('/')}/api/metrics"
        response = requests.get(metrics_url, timeout=30)
        
        # Metrics endpoint might not be publicly available
        if response.status_code == 200:
            # If available, should return proper metrics format
            metrics_data = response.text
            assert len(metrics_data) > 0
        elif response.status_code == 404:
            # Metrics endpoint not available, which is acceptable
            pass
        else:
            # Other status codes might indicate issues
            assert response.status_code in [401, 403], f"Unexpected metrics endpoint status: {response.status_code}"
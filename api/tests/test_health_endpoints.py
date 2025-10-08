"""
Tests for health check and system status endpoints.

This module tests the comprehensive health monitoring functionality
including dependency checks, system metrics, and status reporting.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from services.health import HealthCheckService
from services.mongodb import MongoDBService
from services.redis import RedisService
from services.amqp import AMQPService


class TestHealthCheckEndpoint:
    """Test cases for the /api/healthz endpoint."""
    
    def test_health_check_success_all_healthy(self, client, mock_services):
        """Test health check when all dependencies are healthy."""
        # Mock all services as healthy
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check HAL structure
        assert '_links' in data
        assert 'self' in data['_links']
        
        # Check health data
        assert data['status'] == 'healthy'
        assert data['service'] == 'sos-cidadao-api'
        assert data['version'] == '1.0.0'
        assert 'timestamp' in data
        assert 'dependencies' in data
        
        # Check dependencies
        deps = data['dependencies']
        assert deps['mongodb']['status'] == 'healthy'
        assert deps['redis']['status'] == 'healthy'
        assert deps['amqp']['status'] == 'healthy'
        
        # Check system metrics
        assert 'system_metrics' in data
        assert 'feature_flags' in data
        assert 'configuration' in data
    
    def test_health_check_degraded_redis_unhealthy(self, client, mock_services):
        """Test health check when Redis is unhealthy but other services are healthy."""
        # Mock MongoDB and AMQP as healthy, Redis as unhealthy
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.side_effect = Exception("Redis connection failed")
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200  # Still operational
        data = json.loads(response.data)
        
        assert data['status'] == 'degraded'
        assert data['dependencies']['redis']['status'] == 'unhealthy'
        assert 'error' in data['dependencies']['redis']
    
    def test_health_check_unhealthy_all_dependencies_down(self, client, mock_services):
        """Test health check when all dependencies are unhealthy."""
        # Mock all services as unhealthy
        mock_services['mongodb'].client.admin.command.side_effect = Exception("MongoDB down")
        mock_services['redis'].ping.side_effect = Exception("Redis down")
        mock_services['amqp'].health_check.return_value = False
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 503  # Service unavailable
        data = json.loads(response.data)
        
        assert data['status'] == 'unhealthy'
        assert data['dependencies']['mongodb']['status'] == 'unhealthy'
        assert data['dependencies']['redis']['status'] == 'unhealthy'
        assert data['dependencies']['amqp']['status'] == 'unhealthy'
    
    def test_health_check_response_time_monitoring(self, client, mock_services):
        """Test that health check includes response time monitoring."""
        # Mock services with slight delay
        def slow_mongodb_command(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay
            return True
        
        mock_services['mongodb'].client.admin.command.side_effect = slow_mongodb_command
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'response_time_ms' in data
        assert isinstance(data['response_time_ms'], (int, float))
        assert data['response_time_ms'] > 0
        
        # Check individual dependency response times
        assert 'response_time_ms' in data['dependencies']['mongodb']
        assert 'response_time_ms' in data['dependencies']['redis']
        assert 'response_time_ms' in data['dependencies']['amqp']
    
    def test_health_check_feature_flags_reporting(self, client, mock_services):
        """Test that health check reports feature flag status."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'feature_flags' in data
        flags = data['feature_flags']
        
        assert 'docs_enabled' in flags
        assert 'otel_enabled' in flags
        assert 'hal_strict' in flags
        assert isinstance(flags['docs_enabled'], bool)
        assert isinstance(flags['otel_enabled'], bool)
        assert isinstance(flags['hal_strict'], bool)
    
    def test_health_check_system_metrics(self, client, mock_services):
        """Test that health check includes system metrics."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'system_metrics' in data
        metrics = data['system_metrics']
        
        # Check for expected metric categories
        expected_metrics = ['cpu_percent', 'memory', 'disk']
        for metric in expected_metrics:
            assert metric in metrics
        
        # Check memory metrics structure
        if 'memory' in metrics and isinstance(metrics['memory'], dict):
            memory = metrics['memory']
            assert 'used_mb' in memory
            assert 'total_mb' in memory
            assert 'percent' in memory
    
    def test_health_check_hal_links(self, client, mock_services):
        """Test that health check response includes proper HAL links."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/healthz')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check HAL structure
        assert '_links' in data
        links = data['_links']
        
        assert 'self' in links
        assert 'href' in links['self']
        assert '/api/healthz' in links['self']['href']
    
    def test_health_check_error_handling(self, client):
        """Test health check error handling when health service fails."""
        with patch('app.health_service') as mock_health_service:
            mock_health_service.get_comprehensive_health.side_effect = Exception("Health service failed")
            
            response = client.get('/api/healthz')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            
            assert data['status'] == 'unhealthy'
            assert 'error' in data
            assert 'Health check service failed' in data['error']


class TestSystemStatusEndpoint:
    """Test cases for the /api/status endpoint."""
    
    def test_system_status_success(self, client, mock_services):
        """Test system status endpoint returns comprehensive information."""
        # Mock all services as healthy
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check basic service information
        assert data['service'] == 'sos-cidadao-api'
        assert data['version'] == '1.0.0'
        assert 'environment' in data
        assert 'timestamp' in data
        
        # Check comprehensive status sections
        assert 'uptime' in data
        assert 'configuration' in data
        assert 'feature_flags' in data
        assert 'openapi_status' in data
        assert 'system_metrics' in data
        assert 'dependencies' in data
    
    def test_system_status_uptime_information(self, client, mock_services):
        """Test that system status includes uptime information."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'uptime' in data
        uptime = data['uptime']
        
        if 'error' not in uptime:
            assert 'uptime_seconds' in uptime
            assert 'started_at' in uptime
            assert 'process_id' in uptime
            assert isinstance(uptime['uptime_seconds'], (int, float))
            assert uptime['uptime_seconds'] >= 0
    
    def test_system_status_configuration_summary(self, client, mock_services):
        """Test that system status includes configuration summary."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'configuration' in data
        config = data['configuration']
        
        # Check configuration flags
        expected_config_keys = [
            'mongodb_configured',
            'redis_configured',
            'amqp_configured',
            'jwt_configured',
            'base_url',
            'debug_mode',
            'docs_enabled'
        ]
        
        for key in expected_config_keys:
            assert key in config
    
    def test_system_status_openapi_validation(self, client, mock_services):
        """Test that system status includes OpenAPI validation status."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'openapi_status' in data
        openapi = data['openapi_status']
        
        assert 'spec_available' in openapi
        assert 'validation_status' in openapi
        assert isinstance(openapi['spec_available'], bool)
    
    def test_system_status_hal_structure(self, client, mock_services):
        """Test that system status response follows HAL format."""
        mock_services['mongodb'].client.admin.command.return_value = True
        mock_services['redis'].ping.return_value = True
        mock_services['amqp'].health_check.return_value = True
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check HAL structure
        assert '_links' in data
        links = data['_links']
        
        assert 'self' in links
        assert 'href' in links['self']
        assert '/api/status' in links['self']['href']
    
    def test_system_status_error_handling(self, client):
        """Test system status error handling."""
        with patch('app.health_service') as mock_health_service:
            mock_health_service._get_system_metrics.side_effect = Exception("Metrics failed")
            
            response = client.get('/api/status')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            
            assert 'error' in data
            assert 'Status endpoint failed' in data['error']


class TestHealthCheckService:
    """Test cases for the HealthCheckService class."""
    
    def test_health_service_initialization(self):
        """Test health service initialization."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        
        assert health_service.mongodb_service == mongodb_service
        assert health_service.redis_service == redis_service
        assert health_service.amqp_service == amqp_service
        assert health_service.service_version == "1.0.0"
    
    def test_mongodb_health_check_success(self):
        """Test MongoDB health check when healthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock successful MongoDB operations
        mongodb_service.client.admin.command.return_value = True
        mongodb_service.client.server_info.return_value = {"version": "6.0.0"}
        mongodb_service.db.health_check.insert_one.return_value = Mock(inserted_id="test_id")
        mongodb_service.db.health_check.delete_one.return_value = Mock()
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_mongodb_health()
        
        assert result['status'] == 'healthy'
        assert 'response_time_ms' in result
        assert 'version' in result
        assert 'last_check' in result
    
    def test_mongodb_health_check_failure(self):
        """Test MongoDB health check when unhealthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock MongoDB failure
        mongodb_service.client.admin.command.side_effect = Exception("Connection failed")
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_mongodb_health()
        
        assert result['status'] == 'unhealthy'
        assert 'error' in result
        assert 'Connection failed' in result['error']
        assert 'last_check' in result
    
    def test_redis_health_check_success(self):
        """Test Redis health check when healthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock successful Redis operations
        redis_service.ping.return_value = True
        redis_service.set_with_ttl.return_value = True
        redis_service.get.return_value = "test_value"
        redis_service.delete.return_value = True
        redis_service.get_info.return_value = {
            "redis_version": "7.0.0",
            "used_memory": 1024000,
            "connected_clients": 5
        }
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_redis_health()
        
        assert result['status'] == 'healthy'
        assert 'response_time_ms' in result
        assert 'version' in result
        assert 'memory_usage_mb' in result
        assert 'connected_clients' in result
        assert 'last_check' in result
    
    def test_redis_health_check_failure(self):
        """Test Redis health check when unhealthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock Redis failure
        redis_service.ping.side_effect = Exception("Redis connection failed")
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_redis_health()
        
        assert result['status'] == 'unhealthy'
        assert 'error' in result
        assert 'Redis connection failed' in result['error']
        assert 'last_check' in result
    
    def test_amqp_health_check_success(self):
        """Test AMQP health check when healthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock successful AMQP health check
        amqp_service.health_check.return_value = True
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_amqp_health()
        
        assert result['status'] == 'healthy'
        assert 'response_time_ms' in result
        assert 'broker' in result
        assert result['broker'] == 'LavinMQ'
        assert 'last_check' in result
    
    def test_amqp_health_check_failure(self):
        """Test AMQP health check when unhealthy."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock AMQP failure
        amqp_service.health_check.return_value = False
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        result = health_service._check_amqp_health()
        
        assert result['status'] == 'unhealthy'
        assert 'error' in result
        assert 'last_check' in result
    
    def test_overall_status_determination(self):
        """Test overall status determination logic."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        
        # All healthy
        assert health_service._determine_overall_status(['healthy', 'healthy', 'healthy']) == 'healthy'
        
        # Some unhealthy
        assert health_service._determine_overall_status(['healthy', 'unhealthy', 'healthy']) == 'degraded'
        
        # All unhealthy
        assert health_service._determine_overall_status(['unhealthy', 'unhealthy', 'unhealthy']) == 'unhealthy'
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_collection(self, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection."""
        mongodb_service = Mock(spec=MongoDBService)
        redis_service = Mock(spec=RedisService)
        amqp_service = Mock(spec=AMQPService)
        
        # Mock psutil responses
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(
            used=1024*1024*1024,  # 1GB
            total=4*1024*1024*1024,  # 4GB
            percent=25.0
        )
        mock_disk.return_value = Mock(
            used=50*1024*1024*1024,  # 50GB
            total=100*1024*1024*1024,  # 100GB
        )
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        metrics = health_service._get_system_metrics()
        
        assert 'cpu_percent' in metrics
        assert metrics['cpu_percent'] == 25.5
        
        assert 'memory' in metrics
        memory = metrics['memory']
        assert 'used_mb' in memory
        assert 'total_mb' in memory
        assert 'percent' in memory
        
        assert 'disk' in metrics
        disk = metrics['disk']
        assert 'used_gb' in disk
        assert 'total_gb' in disk
        assert 'percent' in disk


@pytest.fixture
def mock_services():
    """Fixture providing mocked services for testing."""
    mongodb_service = Mock(spec=MongoDBService)
    redis_service = Mock(spec=RedisService)
    amqp_service = Mock(spec=AMQPService)
    
    # Set up default mock behaviors
    mongodb_service.client = Mock()
    mongodb_service.client.admin = Mock()
    mongodb_service.client.server_info = Mock()
    mongodb_service.db = Mock()
    mongodb_service.db.health_check = Mock()
    
    redis_service.ping = Mock()
    redis_service.set_with_ttl = Mock()
    redis_service.get = Mock()
    redis_service.delete = Mock()
    redis_service.get_info = Mock()
    
    amqp_service.health_check = Mock()
    
    with patch('app.mongodb_service', mongodb_service), \
         patch('app.redis_service', redis_service), \
         patch('app.amqp_service', amqp_service), \
         patch('app.health_service') as mock_health_service:
        
        # Create a real health service with mocked dependencies
        from services.health import HealthCheckService
        real_health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        mock_health_service.get_comprehensive_health = real_health_service.get_comprehensive_health
        mock_health_service._check_mongodb_health = real_health_service._check_mongodb_health
        mock_health_service._check_redis_health = real_health_service._check_redis_health
        mock_health_service._check_amqp_health = real_health_service._check_amqp_health
        mock_health_service._get_system_metrics = real_health_service._get_system_metrics
        
        yield {
            'mongodb': mongodb_service,
            'redis': redis_service,
            'amqp': amqp_service,
            'health': mock_health_service
        }
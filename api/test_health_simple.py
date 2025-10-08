#!/usr/bin/env python3
"""
Simple health endpoint test without full dependency installation.
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_health_service_logic():
    """Test the health service logic without Flask dependencies."""
    
    # Mock the dependencies
    with patch('services.health.MongoDBService') as MockMongoDB, \
         patch('services.health.RedisService') as MockRedis, \
         patch('services.health.AMQPService') as MockAMQP, \
         patch('services.health.psutil') as mock_psutil:
        
        # Set up mocks
        mongodb_service = Mock()
        redis_service = Mock()
        amqp_service = Mock()
        
        # Mock successful operations
        mongodb_service.client.admin.command.return_value = True
        mongodb_service.client.server_info.return_value = {"version": "6.0.0"}
        mongodb_service.db.health_check.insert_one.return_value = Mock(inserted_id="test_id")
        mongodb_service.db.health_check.delete_one.return_value = Mock()
        
        redis_service.ping.return_value = True
        redis_service.set_with_ttl.return_value = True
        redis_service.get.return_value = "test_value"
        redis_service.delete.return_value = True
        redis_service.get_info.return_value = {
            "redis_version": "7.0.0",
            "used_memory": 1024000,
            "connected_clients": 5
        }
        
        amqp_service.health_check.return_value = True
        
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = Mock(
            used=1024*1024*1024,  # 1GB
            total=4*1024*1024*1024,  # 4GB
            percent=25.0
        )
        mock_psutil.disk_usage.return_value = Mock(
            used=50*1024*1024*1024,  # 50GB
            total=100*1024*1024*1024,  # 100GB
        )
        
        # Import and test the health service
        from services.health import HealthCheckService
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        
        # Test individual health checks
        mongodb_health = health_service._check_mongodb_health()
        print("MongoDB Health Check:")
        print(json.dumps(mongodb_health, indent=2))
        assert mongodb_health['status'] == 'healthy'
        assert 'response_time_ms' in mongodb_health
        
        redis_health = health_service._check_redis_health()
        print("\nRedis Health Check:")
        print(json.dumps(redis_health, indent=2))
        assert redis_health['status'] == 'healthy'
        assert 'response_time_ms' in redis_health
        
        amqp_health = health_service._check_amqp_health()
        print("\nAMQP Health Check:")
        print(json.dumps(amqp_health, indent=2))
        assert amqp_health['status'] == 'healthy'
        assert 'response_time_ms' in amqp_health
        
        # Test system metrics
        system_metrics = health_service._get_system_metrics()
        print("\nSystem Metrics:")
        print(json.dumps(system_metrics, indent=2))
        assert 'cpu_percent' in system_metrics
        assert 'memory' in system_metrics
        assert 'disk' in system_metrics
        
        # Test comprehensive health check
        comprehensive_health = health_service.get_comprehensive_health()
        print("\nComprehensive Health Check:")
        print(json.dumps(comprehensive_health, indent=2))
        
        assert comprehensive_health['status'] == 'healthy'
        assert comprehensive_health['service'] == 'sos-cidadao-api'
        assert 'dependencies' in comprehensive_health
        assert 'system_metrics' in comprehensive_health
        assert 'feature_flags' in comprehensive_health
        
        print("\n✅ All health service tests passed!")


def test_health_service_failure_scenarios():
    """Test health service failure scenarios."""
    
    with patch('services.health.MongoDBService') as MockMongoDB, \
         patch('services.health.RedisService') as MockRedis, \
         patch('services.health.AMQPService') as MockAMQP:
        
        # Set up mocks
        mongodb_service = Mock()
        redis_service = Mock()
        amqp_service = Mock()
        
        # Mock failures
        mongodb_service.client.admin.command.side_effect = Exception("MongoDB connection failed")
        redis_service.ping.side_effect = Exception("Redis connection failed")
        amqp_service.health_check.return_value = False
        
        from services.health import HealthCheckService
        
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        
        # Test individual failures
        mongodb_health = health_service._check_mongodb_health()
        print("MongoDB Health Check (Failure):")
        print(json.dumps(mongodb_health, indent=2))
        assert mongodb_health['status'] == 'unhealthy'
        assert 'error' in mongodb_health
        
        redis_health = health_service._check_redis_health()
        print("\nRedis Health Check (Failure):")
        print(json.dumps(redis_health, indent=2))
        assert redis_health['status'] == 'unhealthy'
        assert 'error' in redis_health
        
        amqp_health = health_service._check_amqp_health()
        print("\nAMQP Health Check (Failure):")
        print(json.dumps(amqp_health, indent=2))
        assert amqp_health['status'] == 'unhealthy'
        assert 'error' in amqp_health
        
        # Test overall status determination
        assert health_service._determine_overall_status(['unhealthy', 'unhealthy', 'unhealthy']) == 'unhealthy'
        assert health_service._determine_overall_status(['healthy', 'unhealthy', 'healthy']) == 'degraded'
        assert health_service._determine_overall_status(['healthy', 'healthy', 'healthy']) == 'healthy'
        
        print("\n✅ All failure scenario tests passed!")


if __name__ == "__main__":
    print("Testing Health Service Logic...")
    test_health_service_logic()
    print("\nTesting Failure Scenarios...")
    test_health_service_failure_scenarios()
    print("\n🎉 All tests completed successfully!")
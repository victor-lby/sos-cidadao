#!/usr/bin/env python3
"""
Validate health service implementation.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_health_service():
    """Validate the health service can be imported and basic logic works."""
    
    try:
        # Test import
        from services.health import HealthCheckService
        print("✅ Health service imported successfully")
        
        # Create mock services
        mongodb_service = Mock()
        redis_service = Mock()
        amqp_service = Mock()
        
        # Initialize health service
        health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)
        print("✅ Health service initialized successfully")
        
        # Test status determination logic
        assert health_service._determine_overall_status(['healthy', 'healthy', 'healthy']) == 'healthy'
        assert health_service._determine_overall_status(['healthy', 'unhealthy', 'healthy']) == 'degraded'
        assert health_service._determine_overall_status(['unhealthy', 'unhealthy', 'unhealthy']) == 'unhealthy'
        print("✅ Status determination logic works correctly")
        
        # Test feature flags method
        feature_flags = health_service._get_feature_flags()
        assert isinstance(feature_flags, dict)
        assert 'docs_enabled' in feature_flags
        assert 'otel_enabled' in feature_flags
        assert 'hal_strict' in feature_flags
        print("✅ Feature flags method works correctly")
        
        # Test configuration status method
        config_status = health_service._get_configuration_status()
        assert isinstance(config_status, dict)
        assert 'mongodb_uri_configured' in config_status
        assert 'redis_configured' in config_status
        assert 'amqp_configured' in config_status
        print("✅ Configuration status method works correctly")
        
        print("\n🎉 Health service validation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Health service validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def validate_redis_service():
    """Validate Redis service has the required methods."""
    
    try:
        from services.redis import RedisService
        print("✅ Redis service imported successfully")
        
        # Check if required methods exist
        redis_service = RedisService()
        
        required_methods = ['ping', 'get_info', 'set_with_ttl', 'get', 'delete']
        for method in required_methods:
            assert hasattr(redis_service, method), f"Missing method: {method}"
        
        print("✅ Redis service has all required methods")
        return True
        
    except Exception as e:
        print(f"❌ Redis service validation failed: {str(e)}")
        return False


def validate_app_structure():
    """Validate the app has the health endpoints."""
    
    try:
        # Check if health service file exists
        health_service_path = os.path.join(os.path.dirname(__file__), 'services', 'health.py')
        assert os.path.exists(health_service_path), "Health service file not found"
        print("✅ Health service file exists")
        
        # Check if app.py has been updated
        app_path = os.path.join(os.path.dirname(__file__), 'app.py')
        with open(app_path, 'r') as f:
            app_content = f.read()
        
        assert 'from services.health import HealthCheckService' in app_content, "Health service import not found in app.py"
        assert 'health_service = HealthCheckService' in app_content, "Health service initialization not found in app.py"
        assert '/api/healthz' in app_content, "Health endpoint not found in app.py"
        assert '/api/status' in app_content, "Status endpoint not found in app.py"
        print("✅ App.py has been properly updated with health endpoints")
        
        return True
        
    except Exception as e:
        print(f"❌ App structure validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("Validating Health Service Implementation...\n")
    
    success = True
    success &= validate_app_structure()
    success &= validate_redis_service()
    success &= validate_health_service()
    
    if success:
        print("\n🎉 All validations passed! Health service implementation is ready.")
    else:
        print("\n❌ Some validations failed. Please check the implementation.")
        sys.exit(1)
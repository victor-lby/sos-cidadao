"""
S.O.S Cidadão API - Flask Application Entry Point

This module initializes the Flask application with OpenAPI 3.0 support,
configures middleware, and sets up the core infrastructure for the
multi-tenant civic notification platform.
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_openapi3 import OpenAPI, Info, Tag
from observability.config import setup_observability
from observability.middleware import add_observability_middleware

# Import middleware and utilities
from middleware.cors import configure_cors
from middleware.error_handler import ErrorHandlerMiddleware, register_custom_error_handlers
from middleware.validation import ValidationMiddleware
from middleware.auth import AuthMiddleware
from services.hal import create_hal_formatter
from services.mongodb import MongoDBService
from services.redis import RedisService
from services.auth import AuthService

# Initialize observability first
setup_observability()

# OpenAPI info
info = Info(
    title="S.O.S Cidadão API",
    version="1.0.0",
    description="Multi-tenant civic notification platform API with HATEOAS Level-3 support"
)

# API tags for organization
tags = [
    Tag(name="Authentication", description="User authentication and authorization"),
    Tag(name="Notifications", description="Notification workflow management"),
    Tag(name="Organizations", description="Organization and user management"),
    Tag(name="Audit", description="Audit trail and compliance"),
    Tag(name="Health", description="System health and status")
]

# Create Flask app with OpenAPI
app = OpenAPI(__name__, info=info, tags=tags)

# Add observability middleware
add_observability_middleware(app)

# Environment configuration
app.config['ENVIRONMENT'] = os.getenv('ENVIRONMENT', 'development')
app.config['DEBUG'] = app.config['ENVIRONMENT'] == 'development'
app.config['DOCS_ENABLED'] = os.getenv('DOCS_ENABLED', 'true').lower() == 'true'

# Security configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'dev-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 900  # 15 minutes
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800  # 7 days

# Database configuration
app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/sos_cidadao_dev')
app.config['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379')
app.config['REDIS_TOKEN'] = os.getenv('REDIS_TOKEN', '')

# Message queue configuration
app.config['AMQP_URL'] = os.getenv('AMQP_URL', 'amqp://admin:admin123@localhost:5672/')

# Feature flags
app.config['HAL_STRICT'] = os.getenv('HAL_STRICT', 'false').lower() == 'true'
app.config['OTEL_ENABLED'] = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'

# API configuration
app.config['BASE_URL'] = os.getenv('BASE_URL', 'http://localhost:5000')

# Initialize services
mongodb_service = MongoDBService(app.config['MONGODB_URI'])
redis_service = RedisService(
    app.config['REDIS_URL'], 
    app.config['REDIS_TOKEN']
)
auth_service = AuthService(
    app.config['JWT_SECRET_KEY'],
    app.config['JWT_ACCESS_TOKEN_EXPIRES'],
    app.config['JWT_REFRESH_TOKEN_EXPIRES']
)

# Initialize AMQP service
from services.amqp import create_amqp_service
amqp_service = create_amqp_service()

# Initialize audit service
from services.audit import AuditService
audit_service = AuditService(mongodb_service)

# Initialize health service
from services.health import HealthCheckService
health_service = HealthCheckService(mongodb_service, redis_service, amqp_service)

# Initialize middleware
hal_formatter = create_hal_formatter(app.config['BASE_URL'])
validation_middleware = ValidationMiddleware(app.config['BASE_URL'])
auth_middleware = AuthMiddleware(auth_service, redis_service)
error_handler = ErrorHandlerMiddleware(app, app.config['BASE_URL'])

# Configure CORS
cors_middleware = configure_cors(
    app,
    allowed_origins=None,  # Will use defaults from environment
    allow_credentials=True
)

# Register custom error handlers
register_custom_error_handlers(app, hal_formatter)

# Make services available to routes
app.mongodb_service = mongodb_service
app.redis_service = redis_service
app.auth_service = auth_service
app.amqp_service = amqp_service
app.audit_service = audit_service
app.hal_formatter = hal_formatter
app.validation_middleware = validation_middleware
app.auth_middleware = auth_middleware

# Register routes
from routes.notifications import notifications_bp
from routes.organizations import org_bp
from routes.auth import auth_bp
from routes.audit import audit_bp

app.register_blueprint(notifications_bp)
app.register_blueprint(org_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(audit_bp)

@app.route('/api/healthz')
def health_check():
    """Enhanced health check endpoint with comprehensive dependency monitoring"""
    try:
        # Get comprehensive health status
        health_data = health_service.get_comprehensive_health()
        
        # Determine HTTP status code based on overall health
        status_code = 200
        if health_data["status"] == "degraded":
            status_code = 200  # Still operational but with issues
        elif health_data["status"] == "unhealthy":
            status_code = 503  # Service unavailable
        
        # Add HAL links
        health_response = hal_formatter.builder.build_resource_response(
            health_data,
            "health",
            "system",
            "system",
            []  # No user permissions needed for health check
        )
        
        return jsonify(health_response), status_code
        
    except Exception as e:
        # Fallback health response if health service fails
        error_health = {
            "status": "unhealthy",
            "service": "sos-cidadao-api",
            "version": "1.0.0",
            "environment": app.config['ENVIRONMENT'],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": f"Health check service failed: {str(e)}"
        }
        
        health_response = hal_formatter.builder.build_resource_response(
            error_health,
            "health",
            "system",
            "system",
            []
        )
        
        return jsonify(health_response), 503


@app.route('/api/status')
def system_status():
    """Detailed system status and metrics endpoint"""
    try:
        # Get comprehensive system information
        status_data = {
            "service": "sos-cidadao-api",
            "version": "1.0.0",
            "environment": app.config['ENVIRONMENT'],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime": _get_application_uptime(),
            "configuration": _get_configuration_summary(),
            "feature_flags": _get_feature_flags_status(),
            "openapi_status": _get_openapi_validation_status(),
            "system_metrics": health_service._get_system_metrics(),
            "dependencies": {
                "mongodb": health_service._check_mongodb_health(),
                "redis": health_service._check_redis_health(),
                "amqp": health_service._check_amqp_health()
            }
        }
        
        # Add HAL links
        status_response = hal_formatter.builder.build_resource_response(
            status_data,
            "status",
            "system",
            "system",
            []  # No user permissions needed for status
        )
        
        return jsonify(status_response)
        
    except Exception as e:
        error_status = {
            "service": "sos-cidadao-api",
            "version": "1.0.0",
            "environment": app.config['ENVIRONMENT'],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": f"Status endpoint failed: {str(e)}"
        }
        
        status_response = hal_formatter.builder.build_resource_response(
            error_status,
            "status",
            "system",
            "system",
            []
        )
        
        return jsonify(status_response), 500


def _get_application_uptime():
    """Get application uptime information."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        create_time = process.create_time()
        uptime_seconds = time.time() - create_time
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "started_at": datetime.fromtimestamp(create_time).isoformat() + "Z",
            "process_id": os.getpid()
        }
    except Exception as e:
        return {
            "error": f"Failed to get uptime: {str(e)}"
        }


def _get_configuration_summary():
    """Get configuration validation summary."""
    return {
        "mongodb_configured": bool(app.config.get('MONGODB_URI')),
        "redis_configured": bool(app.config.get('REDIS_URL')),
        "amqp_configured": bool(app.config.get('AMQP_URL')),
        "jwt_configured": bool(app.config.get('JWT_SECRET_KEY')),
        "base_url": app.config.get('BASE_URL', 'not_set'),
        "debug_mode": app.config.get('DEBUG', False),
        "docs_enabled": app.config.get('DOCS_ENABLED', False)
    }


def _get_feature_flags_status():
    """Get current feature flags status."""
    return {
        "docs_enabled": app.config.get('DOCS_ENABLED', False),
        "otel_enabled": app.config.get('OTEL_ENABLED', True),
        "hal_strict": app.config.get('HAL_STRICT', False),
        "debug_mode": app.config.get('DEBUG', False)
    }


def _get_openapi_validation_status():
    """Get OpenAPI specification validation status."""
    try:
        # Check if OpenAPI spec is accessible
        from flask import url_for
        
        # Try to access the OpenAPI spec
        spec_available = hasattr(app, 'api_doc')
        
        return {
            "spec_available": spec_available,
            "spec_endpoint": "/openapi/openapi.json" if spec_available else None,
            "docs_endpoint": "/openapi/swagger" if app.config.get('DOCS_ENABLED') else None,
            "redoc_endpoint": "/openapi/redoc" if app.config.get('DOCS_ENABLED') else None,
            "validation_status": "valid" if spec_available else "unavailable"
        }
    except Exception as e:
        return {
            "spec_available": False,
            "error": f"OpenAPI validation failed: {str(e)}",
            "validation_status": "error"
        }


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )
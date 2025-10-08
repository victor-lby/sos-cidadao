"""
S.O.S Cidadão API - Flask Application Entry Point

This module initializes the Flask application with OpenAPI 3.0 support,
configures middleware, and sets up the core infrastructure for the
multi-tenant civic notification platform.
"""

import os
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
app.hal_formatter = hal_formatter
app.validation_middleware = validation_middleware
app.auth_middleware = auth_middleware

# Register routes (will be implemented in later tasks)
# from routes.auth import auth_bp
# from routes.notifications import notifications_bp
# from routes.admin import admin_bp
# from routes.audit import audit_bp
# from routes.health import health_bp

# app.register_blueprint(auth_bp)
# app.register_blueprint(notifications_bp)
# app.register_blueprint(admin_bp)
# app.register_blueprint(audit_bp)
# app.register_blueprint(health_bp)

@app.route('/api/healthz')
def health_check():
    """Enhanced health check endpoint with HAL formatting"""
    from datetime import datetime
    
    health_data = {
        "status": "healthy",
        "service": "sos-cidadao-api",
        "version": "1.0.0",
        "environment": app.config['ENVIRONMENT'],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "mongodb": {"status": "healthy"},  # Will be enhanced in later tasks
            "redis": {"status": "healthy"},
            "amqp": {"status": "healthy"}
        }
    }
    
    # Add HAL links
    health_response = hal_formatter.builder.build_resource_response(
        health_data,
        "health",
        "system",
        "system",
        []  # No user permissions needed for health check
    )
    
    return jsonify(health_response)

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )
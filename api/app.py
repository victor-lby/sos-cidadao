"""
S.O.S Cidadão API - Flask Application Entry Point

This module initializes the Flask application with OpenAPI 3.0 support,
configures middleware, and sets up the core infrastructure for the
multi-tenant civic notification platform.
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_openapi3 import OpenAPI, Info, Tag
from observability.config import setup_observability
from observability.middleware import add_observability_middleware

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

# Configure CORS
CORS(app, origins=["http://localhost:3000", "https://*.vercel.app"])

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
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "sos-cidadao-api",
        "version": "1.0.0",
        "environment": app.config['ENVIRONMENT'],
        "_links": {
            "self": {"href": "/api/healthz"}
        }
    }

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )
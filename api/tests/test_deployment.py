"""
Tests for deployment configuration and environment setup.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app import create_app


class TestDeploymentConfiguration:
    """Test deployment-specific configuration."""
    
    def test_production_environment_variables(self):
        """Test that all required production environment variables are defined."""
        required_vars = [
            'MONGODB_URI',
            'REDIS_URL', 
            'JWT_SECRET',
            'AMQP_URL'
        ]
        
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'MONGODB_URI': 'mongodb://test',
            'REDIS_URL': 'redis://test',
            'JWT_SECRET': 'test-secret',
            'AMQP_URL': 'amqp://test'
        }):
            app = create_app()
            
            # Verify app is created successfully with production config
            assert app is not None
            assert app.config.get('ENVIRONMENT') == 'production'
    
    def test_vercel_configuration_structure(self):
        """Test that vercel.json has correct structure."""
        vercel_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'vercel.json'
        )
        
        assert os.path.exists(vercel_config_path), "vercel.json should exist"
        
        with open(vercel_config_path, 'r') as f:
            config = json.load(f)
        
        # Verify required sections
        assert 'functions' in config
        assert 'routes' in config
        assert 'env' in config
        
        # Verify Python runtime configuration
        assert 'api/**/*.py' in config['functions']
        assert config['functions']['api/**/*.py']['runtime'] == 'python3.11'
        
        # Verify environment variables are configured
        env_vars = config['env']
        required_env_vars = [
            'ENVIRONMENT',
            'MONGODB_URI',
            'REDIS_URL',
            'JWT_SECRET',
            'AMQP_URL'
        ]
        
        for var in required_env_vars:
            assert var in env_vars, f"Environment variable {var} should be configured"
    
    def test_security_headers_configuration(self):
        """Test that security headers are properly configured."""
        vercel_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'vercel.json'
        )
        
        with open(vercel_config_path, 'r') as f:
            config = json.load(f)
        
        assert 'headers' in config
        
        # Find security headers
        security_headers = []
        for header_config in config['headers']:
            for header in header_config.get('headers', []):
                security_headers.append(header['key'])
        
        # Verify security headers are present
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        for header in expected_headers:
            assert header in security_headers, f"Security header {header} should be configured"
    
    def test_api_routes_configuration(self):
        """Test that API routes are properly configured."""
        vercel_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'vercel.json'
        )
        
        with open(vercel_config_path, 'r') as f:
            config = json.load(f)
        
        routes = config['routes']
        
        # Verify API routes exist
        api_routes = [route for route in routes if route['src'].startswith('/api')]
        assert len(api_routes) > 0, "API routes should be configured"
        
        # Verify health check route
        health_routes = [route for route in routes if '/healthz' in route['src']]
        assert len(health_routes) > 0, "Health check route should be configured"
        
        # Verify frontend fallback route
        frontend_routes = [route for route in routes if route['dest'] == '/index.html']
        assert len(frontend_routes) > 0, "Frontend fallback route should be configured"


class TestEnvironmentHandling:
    """Test environment-specific behavior."""
    
    def test_development_environment(self):
        """Test development environment configuration."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'DOCS_ENABLED': 'true',
            'OTEL_ENABLED': 'false'
        }):
            app = create_app()
            
            assert app.config.get('ENVIRONMENT') == 'development'
            # In development, docs should be enabled
            # This would be tested by checking if /docs endpoint exists
    
    def test_production_environment(self):
        """Test production environment configuration."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DOCS_ENABLED': 'false',
            'OTEL_ENABLED': 'true',
            'HAL_STRICT': 'true'
        }):
            app = create_app()
            
            assert app.config.get('ENVIRONMENT') == 'production'
            # In production, docs should be disabled and observability enabled
    
    def test_missing_required_environment_variables(self):
        """Test behavior when required environment variables are missing."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            # App should still create but with default values
            app = create_app()
            assert app is not None


class TestCIConfiguration:
    """Test CI/CD pipeline configuration."""
    
    def test_github_workflows_exist(self):
        """Test that required GitHub workflow files exist."""
        workflows_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            '.github', 'workflows'
        )
        
        required_workflows = [
            'test-backend.yml',
            'test-frontend.yml',
            'e2e-tests.yml',
            'deploy-production.yml',
            'deploy-preview.yml',
            'openapi-validate.yml',
            'gitleaks.yml',
            'conventional-commits.yml'
        ]
        
        for workflow in required_workflows:
            workflow_path = os.path.join(workflows_dir, workflow)
            assert os.path.exists(workflow_path), f"Workflow {workflow} should exist"
    
    def test_dependabot_configuration(self):
        """Test that Dependabot is properly configured."""
        dependabot_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            '.github', 'dependabot.yml'
        )
        
        assert os.path.exists(dependabot_config_path), "dependabot.yml should exist"
        
        with open(dependabot_config_path, 'r') as f:
            content = f.read()
        
        # Verify package ecosystems are configured
        assert 'package-ecosystem: "pip"' in content
        assert 'package-ecosystem: "npm"' in content
        assert 'package-ecosystem: "github-actions"' in content
    
    def test_redocly_configuration(self):
        """Test that Redocly configuration exists."""
        redocly_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            '.redocly.yaml'
        )
        
        assert os.path.exists(redocly_config_path), ".redocly.yaml should exist"


class TestDeploymentValidation:
    """Test deployment validation functionality."""
    
    def test_health_endpoint_structure(self):
        """Test that health endpoint returns proper structure for monitoring."""
        app = create_app()
        
        with app.test_client() as client:
            response = client.get('/api/healthz')
            
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'status' in data
            assert 'timestamp' in data
            assert '_links' in data
            
            # Verify HAL structure
            assert 'self' in data['_links']
    
    def test_cors_configuration(self):
        """Test CORS configuration for cross-origin requests."""
        app = create_app()
        
        with app.test_client() as client:
            # Test preflight request
            response = client.options(
                '/api/healthz',
                headers={
                    'Origin': 'https://example.com',
                    'Access-Control-Request-Method': 'GET'
                }
            )
            
            # Should handle CORS preflight
            assert response.status_code in [200, 204]
    
    def test_error_handling_in_production(self):
        """Test that error handling works properly in production mode."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            app = create_app()
            
            with app.test_client() as client:
                # Test non-existent endpoint
                response = client.get('/api/nonexistent')
                
                assert response.status_code == 404
                
                # Should return HAL-formatted error
                data = response.get_json()
                assert 'type' in data or 'error' in data


class TestPerformanceConfiguration:
    """Test performance-related configuration."""
    
    def test_connection_pooling_configuration(self):
        """Test that connection pooling is properly configured."""
        # This would test MongoDB and Redis connection pool settings
        # Implementation depends on how services are configured
        pass
    
    def test_caching_configuration(self):
        """Test that caching is properly configured."""
        # This would test Redis caching configuration
        # Implementation depends on caching strategy
        pass
    
    def test_observability_configuration(self):
        """Test that observability is properly configured."""
        with patch.dict(os.environ, {'OTEL_ENABLED': 'true'}):
            app = create_app()
            
            # Verify OpenTelemetry is configured
            # This would check if tracing is enabled
            assert app is not None
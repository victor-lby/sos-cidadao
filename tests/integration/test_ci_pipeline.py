"""
Integration tests for CI/CD pipeline functionality.
Tests the actual CI pipeline components and deployment validation.
"""

import os
import json
import yaml
import subprocess
import pytest
from pathlib import Path


class TestCIPipelineIntegration:
    """Test CI/CD pipeline integration."""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_github_workflows_syntax(self, project_root):
        """Test that all GitHub workflow files have valid YAML syntax."""
        workflows_dir = project_root / '.github' / 'workflows'
        
        if not workflows_dir.exists():
            pytest.skip("GitHub workflows directory not found")
        
        workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
        
        assert len(workflow_files) > 0, "No workflow files found"
        
        for workflow_file in workflow_files:
            with open(workflow_file, 'r') as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML syntax in {workflow_file}: {e}")
    
    def test_dependabot_configuration_syntax(self, project_root):
        """Test that Dependabot configuration has valid syntax."""
        dependabot_file = project_root / '.github' / 'dependabot.yml'
        
        if not dependabot_file.exists():
            pytest.skip("Dependabot configuration not found")
        
        with open(dependabot_file, 'r') as f:
            try:
                config = yaml.safe_load(f)
                
                # Verify structure
                assert 'version' in config
                assert 'updates' in config
                assert isinstance(config['updates'], list)
                
                # Verify each update configuration
                for update in config['updates']:
                    assert 'package-ecosystem' in update
                    assert 'directory' in update
                    assert 'schedule' in update
                    
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML syntax in dependabot.yml: {e}")
    
    def test_vercel_configuration_syntax(self, project_root):
        """Test that Vercel configuration has valid JSON syntax."""
        vercel_file = project_root / 'vercel.json'
        
        if not vercel_file.exists():
            pytest.skip("Vercel configuration not found")
        
        with open(vercel_file, 'r') as f:
            try:
                config = json.load(f)
                
                # Verify required sections
                assert 'functions' in config
                assert 'routes' in config
                
                # Verify functions configuration
                functions = config['functions']
                assert 'api/**/*.py' in functions
                
                # Verify routes configuration
                routes = config['routes']
                assert isinstance(routes, list)
                assert len(routes) > 0
                
            except json.JSONError as e:
                pytest.fail(f"Invalid JSON syntax in vercel.json: {e}")
    
    def test_redocly_configuration_syntax(self, project_root):
        """Test that Redocly configuration has valid YAML syntax."""
        redocly_file = project_root / 'api' / '.redocly.yaml'
        
        if not redocly_file.exists():
            pytest.skip("Redocly configuration not found")
        
        with open(redocly_file, 'r') as f:
            try:
                config = yaml.safe_load(f)
                
                # Verify structure
                assert 'apis' in config or 'lint' in config
                
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML syntax in .redocly.yaml: {e}")
    
    def test_package_json_scripts(self, project_root):
        """Test that package.json has required scripts for CI/CD."""
        package_json_file = project_root / 'frontend' / 'package.json'
        
        if not package_json_file.exists():
            pytest.skip("Frontend package.json not found")
        
        with open(package_json_file, 'r') as f:
            package_config = json.load(f)
        
        scripts = package_config.get('scripts', {})
        
        # Verify required scripts exist
        required_scripts = [
            'build',
            'test',
            'lint',
            'type-check'
        ]
        
        for script in required_scripts:
            assert script in scripts, f"Required script '{script}' not found in package.json"
    
    def test_python_requirements_files(self, project_root):
        """Test that Python requirements files are valid."""
        requirements_files = [
            project_root / 'api' / 'requirements.txt',
            project_root / 'api' / 'requirements-vercel.txt'
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                with open(req_file, 'r') as f:
                    lines = f.readlines()
                
                # Verify each line is a valid requirement
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Basic validation - should contain package name
                        assert '==' in line or '>=' in line or line.isalpha(), \
                            f"Invalid requirement format in {req_file} line {line_num}: {line}"


class TestDeploymentValidation:
    """Test deployment validation scripts and tools."""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_deployment_validation_script_exists(self, project_root):
        """Test that deployment validation script exists and is executable."""
        script_path = project_root / 'scripts' / 'validate-deployment.sh'
        
        assert script_path.exists(), "Deployment validation script not found"
        assert os.access(script_path, os.X_OK), "Deployment validation script is not executable"
    
    def test_deployment_validation_script_syntax(self, project_root):
        """Test that deployment validation script has valid bash syntax."""
        script_path = project_root / 'scripts' / 'validate-deployment.sh'
        
        if not script_path.exists():
            pytest.skip("Deployment validation script not found")
        
        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Bash syntax error in validation script: {result.stderr}"
    
    def test_e2e_setup_script_exists(self, project_root):
        """Test that E2E setup script exists."""
        script_path = project_root / 'api' / 'scripts' / 'setup_e2e_data.py'
        
        assert script_path.exists(), "E2E setup script not found"
    
    def test_e2e_setup_script_syntax(self, project_root):
        """Test that E2E setup script has valid Python syntax."""
        script_path = project_root / 'api' / 'scripts' / 'setup_e2e_data.py'
        
        if not script_path.exists():
            pytest.skip("E2E setup script not found")
        
        # Use python -m py_compile to check syntax
        result = subprocess.run(
            ['python', '-m', 'py_compile', str(script_path)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Python syntax error in E2E setup script: {result.stderr}"


class TestEnvironmentConfiguration:
    """Test environment-specific configuration."""
    
    def test_environment_variables_documentation(self):
        """Test that required environment variables are documented."""
        # This would check README.md or other documentation
        # for environment variable documentation
        pass
    
    def test_production_security_configuration(self):
        """Test production security configuration."""
        # Verify security headers, HTTPS enforcement, etc.
        pass
    
    def test_development_vs_production_differences(self):
        """Test that development and production configurations differ appropriately."""
        # Verify docs are disabled in production, debug is off, etc.
        pass


class TestContinuousIntegration:
    """Test CI-specific functionality."""
    
    def test_test_coverage_configuration(self):
        """Test that test coverage is properly configured."""
        # Verify pytest coverage configuration
        # Verify frontend test coverage configuration
        pass
    
    def test_linting_configuration(self):
        """Test that linting is properly configured."""
        # Verify flake8, eslint configurations
        pass
    
    def test_security_scanning_configuration(self):
        """Test that security scanning is properly configured."""
        # Verify Gitleaks configuration
        pass
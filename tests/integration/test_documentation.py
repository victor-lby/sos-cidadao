"""
Documentation validation tests.

Tests to ensure documentation is complete, accurate, and up-to-date.

SPDX-License-Identifier: Apache-2.0
Copyright 2024 S.O.S Cidadão Contributors
"""

import os
import re
import yaml
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import pytest
import requests


class TestDocumentationValidation:
    """Test suite for documentation validation."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    @pytest.fixture
    def readme_path(self, project_root: Path) -> Path:
        """Get README.md path."""
        return project_root / "README.md"
    
    @pytest.fixture
    def contributing_path(self, project_root: Path) -> Path:
        """Get CONTRIBUTING.md path."""
        return project_root / "CONTRIBUTING.md"
    
    @pytest.fixture
    def openapi_path(self, project_root: Path) -> Path:
        """Get OpenAPI specification path."""
        return project_root / "docs" / "API" / "openapi.yaml"
    
    def test_readme_exists_and_complete(self, readme_path: Path):
        """Test that README.md exists and contains required sections."""
        assert readme_path.exists(), "README.md file must exist"
        
        content = readme_path.read_text(encoding='utf-8')
        
        # Required sections
        required_sections = [
            "# S.O.S Cidadão",
            "## 🚀 Features",
            "## 🏗️ Architecture", 
            "## 🛠️ Development Setup",
            "## 🧪 Testing",
            "## 🚀 Deployment",
            "## 📚 API Documentation",
            "## 🔒 Security",
            "## 📊 Observability",
            "## 🤝 Contributing",
            "## 📄 License"
        ]
        
        for section in required_sections:
            assert section in content, f"README.md must contain section: {section}"
    
    def test_readme_setup_instructions(self, readme_path: Path):
        """Test that README contains complete setup instructions."""
        content = readme_path.read_text(encoding='utf-8')
        
        # Required setup steps
        setup_requirements = [
            "Prerequisites",
            "Clone the repository",
            "docker-compose up",
            "pip install",
            "npm install",
            "flask run",
            "npm run dev"
        ]
        
        for requirement in setup_requirements:
            assert requirement in content, f"README.md must contain setup instruction: {requirement}"
    
    def test_readme_environment_variables(self, readme_path: Path):
        """Test that README documents required environment variables."""
        content = readme_path.read_text(encoding='utf-8')
        
        # Required environment variables
        required_env_vars = [
            "MONGODB_URI",
            "REDIS_URL", 
            "JWT_SECRET",
            "AMQP_URL",
            "OTEL_ENABLED"
        ]
        
        for env_var in required_env_vars:
            assert env_var in content, f"README.md must document environment variable: {env_var}"
    
    def test_contributing_guide_exists(self, contributing_path: Path):
        """Test that CONTRIBUTING.md exists and is complete."""
        assert contributing_path.exists(), "CONTRIBUTING.md file must exist"
        
        content = contributing_path.read_text(encoding='utf-8')
        
        # Required sections
        required_sections = [
            "# Contributing to S.O.S Cidadão",
            "## 📜 Code of Conduct",
            "## 🚀 Getting Started",
            "## 🔄 Development Workflow",
            "## 🎯 Coding Standards",
            "## 🧪 Testing Guidelines",
            "## 🔄 Pull Request Process"
        ]
        
        for section in required_sections:
            assert section in content, f"CONTRIBUTING.md must contain section: {section}"
    
    def test_code_of_conduct_exists(self, project_root: Path):
        """Test that CODE_OF_CONDUCT.md exists."""
        coc_path = project_root / "CODE_OF_CONDUCT.md"
        assert coc_path.exists(), "CODE_OF_CONDUCT.md file must exist"
        
        content = coc_path.read_text(encoding='utf-8')
        assert "Contributor Covenant" in content, "Must use Contributor Covenant"
    
    def test_license_file_exists(self, project_root: Path):
        """Test that LICENSE file exists and contains Apache 2.0."""
        license_path = project_root / "LICENSE"
        assert license_path.exists(), "LICENSE file must exist"
        
        content = license_path.read_text(encoding='utf-8')
        assert "Apache License" in content, "Must use Apache License 2.0"
        assert "Version 2.0" in content, "Must be version 2.0"
    
    def test_openapi_specification_valid(self, openapi_path: Path):
        """Test that OpenAPI specification is valid YAML and complete."""
        assert openapi_path.exists(), "OpenAPI specification must exist"
        
        # Test YAML parsing
        with open(openapi_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        # Required OpenAPI fields
        assert "openapi" in spec, "Must have openapi version"
        assert spec["openapi"].startswith("3."), "Must use OpenAPI 3.x"
        assert "info" in spec, "Must have info section"
        assert "paths" in spec, "Must have paths section"
        assert "components" in spec, "Must have components section"
        
        # Required info fields
        info = spec["info"]
        assert "title" in info, "Must have title"
        assert "description" in info, "Must have description"
        assert "version" in info, "Must have version"
        assert "license" in info, "Must have license info"
        
        # Check for key endpoints
        paths = spec["paths"]
        required_endpoints = [
            "/healthz",
            "/auth/login",
            "/notifications",
            "/notifications/{id}",
            "/notifications/{id}/approve",
            "/notifications/{id}/deny"
        ]
        
        for endpoint in required_endpoints:
            assert endpoint in paths, f"OpenAPI spec must include endpoint: {endpoint}"
    
    def test_openapi_hal_examples(self, openapi_path: Path):
        """Test that OpenAPI spec includes HAL examples."""
        with open(openapi_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Must include HAL-specific content
        hal_requirements = [
            "application/hal+json",
            "_links",
            "_embedded",
            "HalLinks",
            "HalLink"
        ]
        
        for requirement in hal_requirements:
            assert requirement in content, f"OpenAPI spec must include HAL concept: {requirement}"
    
    def test_adr_documents_exist(self, project_root: Path):
        """Test that Architecture Decision Records exist."""
        adr_dir = project_root / "docs" / "ADRs"
        assert adr_dir.exists(), "ADRs directory must exist"
        
        # Required ADRs
        required_adrs = [
            "ADR-001-hal-hypermedia-api.md",
            "ADR-002-functional-programming-patterns.md", 
            "ADR-003-multi-tenant-architecture.md",
            "ADR-004-opentelemetry-observability.md"
        ]
        
        for adr in required_adrs:
            adr_path = adr_dir / adr
            assert adr_path.exists(), f"ADR must exist: {adr}"
            
            # Check ADR format
            content = adr_path.read_text(encoding='utf-8')
            assert "## Status" in content, f"ADR {adr} must have Status section"
            assert "## Context" in content, f"ADR {adr} must have Context section"
            assert "## Decision" in content, f"ADR {adr} must have Decision section"
            assert "## Consequences" in content, f"ADR {adr} must have Consequences section"
    
    def test_api_documentation_complete(self, project_root: Path):
        """Test that API documentation is complete."""
        api_docs_path = project_root / "docs" / "API" / "README.md"
        assert api_docs_path.exists(), "API documentation README must exist"
        
        content = api_docs_path.read_text(encoding='utf-8')
        
        # Required API doc sections
        required_sections = [
            "# S.O.S Cidadão API Documentation",
            "## 🔐 Authentication",
            "## 🔗 HAL Format", 
            "## ❌ Error Handling",
            "## 🚦 Rate Limiting",
            "## 📝 Examples"
        ]
        
        for section in required_sections:
            assert section in content, f"API docs must contain section: {section}"
    
    def test_license_compliance_documentation(self, project_root: Path):
        """Test that license compliance documentation exists."""
        license_compliance_path = project_root / "docs" / "LICENSE-COMPLIANCE.md"
        assert license_compliance_path.exists(), "License compliance documentation must exist"
        
        content = license_compliance_path.read_text(encoding='utf-8')
        
        # Required sections
        required_sections = [
            "# License Compliance Documentation",
            "## Project License",
            "## SPDX License Identifiers",
            "## Third-Party Dependencies",
            "## License Compatibility Matrix"
        ]
        
        for section in required_sections:
            assert section in content, f"License compliance docs must contain: {section}"
    
    def test_release_process_documentation(self, project_root: Path):
        """Test that release process documentation exists."""
        release_docs_path = project_root / "docs" / "RELEASE-PROCESS.md"
        assert release_docs_path.exists(), "Release process documentation must exist"
        
        content = release_docs_path.read_text(encoding='utf-8')
        
        # Required sections
        required_sections = [
            "# Release Process Documentation",
            "## 🏷️ Version Numbering",
            "## 🔄 Release Types",
            "## 🤖 Automated Release Workflow",
            "## 📝 Changelog Management"
        ]
        
        for section in required_sections:
            assert section in content, f"Release docs must contain: {section}"
    
    def test_changelog_format(self, project_root: Path):
        """Test that CHANGELOG.md follows Keep a Changelog format."""
        changelog_path = project_root / "CHANGELOG.md"
        assert changelog_path.exists(), "CHANGELOG.md must exist"
        
        content = changelog_path.read_text(encoding='utf-8')
        
        # Required changelog elements
        assert "# Changelog" in content, "Must have Changelog header"
        assert "Keep a Changelog" in content, "Must reference Keep a Changelog"
        assert "Semantic Versioning" in content, "Must reference Semantic Versioning"
        assert "## [Unreleased]" in content, "Must have Unreleased section"
    
    def test_docker_compose_documented(self, project_root: Path, readme_path: Path):
        """Test that Docker Compose setup is documented."""
        docker_compose_path = project_root / "docker-compose.yml"
        assert docker_compose_path.exists(), "docker-compose.yml must exist"
        
        readme_content = readme_path.read_text(encoding='utf-8')
        assert "docker-compose up" in readme_content, "README must document Docker Compose usage"
    
    def test_environment_example_file(self, project_root: Path):
        """Test for environment example file or documentation."""
        readme_content = (project_root / "README.md").read_text(encoding='utf-8')
        
        # Should document environment variables
        env_vars_documented = any([
            "Environment Variables" in readme_content,
            ".env" in readme_content,
            "MONGODB_URI" in readme_content
        ])
        
        assert env_vars_documented, "Environment variables must be documented"
    
    def test_github_workflows_documented(self, project_root: Path):
        """Test that GitHub workflows are documented."""
        workflows_dir = project_root / ".github" / "workflows"
        
        if workflows_dir.exists():
            workflow_files = list(workflows_dir.glob("*.yml"))
            assert len(workflow_files) > 0, "Should have GitHub workflow files"
            
            # Check if CI/CD is mentioned in README
            readme_content = (project_root / "README.md").read_text(encoding='utf-8')
            assert any([
                "GitHub Actions" in readme_content,
                "CI/CD" in readme_content,
                "workflow" in readme_content.lower()
            ]), "CI/CD should be documented in README"
    
    def test_spdx_license_identifiers(self, project_root: Path):
        """Test that source files have SPDX license identifiers."""
        # Check key Python files
        python_files = [
            "api/app.py",
            "api/domain/notifications.py"
        ]
        
        for file_path in python_files:
            full_path = project_root / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                assert "SPDX-License-Identifier: Apache-2.0" in content, \
                    f"File {file_path} must have SPDX license identifier"
        
        # Check key TypeScript files
        ts_files = [
            "frontend/src/main.ts"
        ]
        
        for file_path in ts_files:
            full_path = project_root / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                assert "SPDX-License-Identifier: Apache-2.0" in content, \
                    f"File {file_path} must have SPDX license identifier"
    
    def test_documentation_links_valid(self, project_root: Path):
        """Test that documentation contains valid internal links."""
        readme_path = project_root / "README.md"
        content = readme_path.read_text(encoding='utf-8')
        
        # Find markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)
        
        for link_text, link_url in links:
            # Check internal file links
            if not link_url.startswith(('http://', 'https://', '#')):
                # Resolve relative path
                if link_url.startswith('./'):
                    link_url = link_url[2:]
                
                target_path = project_root / link_url
                assert target_path.exists(), f"Link target must exist: {link_url} (referenced as '{link_text}')"
    
    def test_project_structure_documented(self, readme_path: Path):
        """Test that project structure is documented in README."""
        content = readme_path.read_text(encoding='utf-8')
        
        # Should document key directories
        key_directories = [
            "api/",
            "frontend/",
            "docs/",
            ".github/"
        ]
        
        for directory in key_directories:
            assert directory in content, f"README should document directory: {directory}"


class TestDocumentationAccuracy:
    """Test suite for documentation accuracy against actual implementation."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_package_json_matches_documentation(self, project_root: Path):
        """Test that package.json dependencies match documentation."""
        package_json_path = project_root / "frontend" / "package.json"
        
        if package_json_path.exists():
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # Check key dependencies mentioned in README
            readme_content = (project_root / "README.md").read_text(encoding='utf-8')
            
            key_deps = ["vue", "vuetify", "pinia", "typescript"]
            for dep in key_deps:
                if dep in package_data.get("dependencies", {}):
                    assert dep.lower() in readme_content.lower(), \
                        f"Dependency {dep} should be documented in README"
    
    def test_requirements_txt_matches_documentation(self, project_root: Path):
        """Test that requirements.txt matches documentation."""
        requirements_path = project_root / "api" / "requirements.txt"
        
        if requirements_path.exists():
            requirements_content = requirements_path.read_text(encoding='utf-8')
            readme_content = (project_root / "README.md").read_text(encoding='utf-8')
            
            # Check key dependencies
            key_deps = ["Flask", "PyJWT", "pymongo", "redis", "opentelemetry"]
            for dep in key_deps:
                if dep in requirements_content:
                    assert dep in readme_content, \
                        f"Dependency {dep} should be documented in README"
    
    def test_docker_compose_services_documented(self, project_root: Path):
        """Test that Docker Compose services are documented."""
        docker_compose_path = project_root / "docker-compose.yml"
        
        if docker_compose_path.exists():
            with open(docker_compose_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
            
            readme_content = (project_root / "README.md").read_text(encoding='utf-8')
            
            # Check that services are mentioned
            if "services" in compose_data:
                for service_name in compose_data["services"].keys():
                    # Some flexibility in naming (mongodb vs mongo, etc.)
                    service_mentioned = any([
                        service_name.lower() in readme_content.lower(),
                        service_name.replace("-", "").lower() in readme_content.lower()
                    ])
                    
                    if not service_mentioned:
                        # Allow some common variations
                        variations = {
                            "mongodb": ["mongo"],
                            "redis": ["redis"],
                            "lavinmq": ["amqp", "rabbitmq", "message queue"]
                        }
                        
                        if service_name.lower() in variations:
                            service_mentioned = any(
                                var in readme_content.lower() 
                                for var in variations[service_name.lower()]
                            )
                    
                    assert service_mentioned, \
                        f"Docker service {service_name} should be documented in README"


class TestSetupInstructions:
    """Test suite to validate setup instructions work."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_required_files_exist(self, project_root: Path):
        """Test that files mentioned in setup instructions exist."""
        required_files = [
            "docker-compose.yml",
            "api/requirements.txt",
            "frontend/package.json"
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Setup requires file: {file_path}"
    
    def test_python_requirements_installable(self, project_root: Path):
        """Test that Python requirements can be parsed."""
        requirements_path = project_root / "api" / "requirements.txt"
        
        if requirements_path.exists():
            content = requirements_path.read_text(encoding='utf-8')
            
            # Basic validation - should not have syntax errors
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
            
            for line in lines:
                # Should be valid package specification
                assert re.match(r'^[a-zA-Z0-9_-]+[>=<!=]*[0-9.]*', line), \
                    f"Invalid requirement format: {line}"
    
    def test_npm_package_json_valid(self, project_root: Path):
        """Test that package.json is valid JSON."""
        package_json_path = project_root / "frontend" / "package.json"
        
        if package_json_path.exists():
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)  # Will raise if invalid JSON
            
            # Should have required fields
            assert "name" in package_data, "package.json must have name"
            assert "scripts" in package_data, "package.json must have scripts"
            assert "dependencies" in package_data, "package.json must have dependencies"
    
    def test_docker_compose_valid(self, project_root: Path):
        """Test that docker-compose.yml is valid."""
        docker_compose_path = project_root / "docker-compose.yml"
        
        if docker_compose_path.exists():
            with open(docker_compose_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)  # Will raise if invalid YAML
            
            # Should have services
            assert "services" in compose_data, "docker-compose.yml must have services"
            assert len(compose_data["services"]) > 0, "Must have at least one service"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
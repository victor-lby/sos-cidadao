#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 S.O.S Cidadão Contributors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate markdown files
validate_markdown() {
    print_status "Validating Markdown files..."
    
    local markdown_files=(
        "README.md"
        "CONTRIBUTING.md"
        "CODE_OF_CONDUCT.md"
        "CHANGELOG.md"
        "docs/API/README.md"
        "docs/LICENSE-COMPLIANCE.md"
        "docs/RELEASE-PROCESS.md"
    )
    
    for file in "${markdown_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_success "✓ $file exists"
            
            # Check for basic markdown structure
            if grep -q "^# " "$file"; then
                print_success "✓ $file has proper heading structure"
            else
                print_warning "⚠ $file may be missing main heading"
            fi
        else
            print_error "✗ $file is missing"
            return 1
        fi
    done
}

# Function to validate OpenAPI specification
validate_openapi() {
    print_status "Validating OpenAPI specification..."
    
    local openapi_file="docs/API/openapi.yaml"
    
    if [[ ! -f "$openapi_file" ]]; then
        print_error "OpenAPI specification not found: $openapi_file"
        return 1
    fi
    
    # Check YAML syntax
    if command_exists python3; then
        python3 -c "import yaml; yaml.safe_load(open('$openapi_file'))" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            print_success "✓ OpenAPI YAML syntax is valid"
        else
            print_error "✗ OpenAPI YAML syntax is invalid"
            return 1
        fi
    fi
    
    # Validate with Redocly CLI if available
    if command_exists npx; then
        print_status "Running Redocly validation..."
        if npx @redocly/cli lint "$openapi_file" --skip-rule=no-unused-components; then
            print_success "✓ OpenAPI specification is valid"
        else
            print_error "✗ OpenAPI specification validation failed"
            return 1
        fi
    else
        print_warning "⚠ Redocly CLI not available, skipping detailed validation"
    fi
}

# Function to validate ADR documents
validate_adrs() {
    print_status "Validating Architecture Decision Records..."
    
    local adr_dir="docs/ADRs"
    
    if [[ ! -d "$adr_dir" ]]; then
        print_error "ADRs directory not found: $adr_dir"
        return 1
    fi
    
    local required_adrs=(
        "ADR-001-hal-hypermedia-api.md"
        "ADR-002-functional-programming-patterns.md"
        "ADR-003-multi-tenant-architecture.md"
        "ADR-004-opentelemetry-observability.md"
    )
    
    for adr in "${required_adrs[@]}"; do
        local adr_path="$adr_dir/$adr"
        if [[ -f "$adr_path" ]]; then
            print_success "✓ $adr exists"
            
            # Check ADR structure
            local required_sections=("## Status" "## Context" "## Decision" "## Consequences")
            for section in "${required_sections[@]}"; do
                if grep -q "$section" "$adr_path"; then
                    print_success "✓ $adr has $section section"
                else
                    print_warning "⚠ $adr missing $section section"
                fi
            done
        else
            print_error "✗ $adr is missing"
            return 1
        fi
    done
}

# Function to validate license compliance
validate_license_compliance() {
    print_status "Validating license compliance..."
    
    # Check LICENSE file
    if [[ -f "LICENSE" ]]; then
        if grep -q "Apache License" LICENSE && grep -q "Version 2.0" LICENSE; then
            print_success "✓ LICENSE file contains Apache 2.0 license"
        else
            print_error "✗ LICENSE file does not contain Apache 2.0 license"
            return 1
        fi
    else
        print_error "✗ LICENSE file is missing"
        return 1
    fi
    
    # Check SPDX identifiers in key files
    local key_files=(
        "api/app.py"
        "frontend/src/main.ts"
        "scripts/release.sh"
    )
    
    for file in "${key_files[@]}"; do
        if [[ -f "$file" ]]; then
            if grep -q "SPDX-License-Identifier: Apache-2.0" "$file"; then
                print_success "✓ $file has SPDX license identifier"
            else
                print_warning "⚠ $file missing SPDX license identifier"
            fi
        fi
    done
}

# Function to validate setup instructions
validate_setup_instructions() {
    print_status "Validating setup instructions..."
    
    # Check required files exist
    local required_files=(
        "docker-compose.yml"
        "api/requirements.txt"
        "frontend/package.json"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_success "✓ $file exists (required for setup)"
        else
            print_error "✗ $file is missing (required for setup)"
            return 1
        fi
    done
    
    # Validate Python requirements syntax
    if [[ -f "api/requirements.txt" ]]; then
        if python3 -c "
import re
with open('api/requirements.txt') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if line and not line.startswith('#'):
            if not re.match(r'^[a-zA-Z0-9_-]+[>=<!=]*[0-9.]*', line):
                print(f'Invalid requirement at line {line_num}: {line}')
                exit(1)
print('Requirements syntax is valid')
"; then
            print_success "✓ Python requirements syntax is valid"
        else
            print_error "✗ Python requirements syntax is invalid"
            return 1
        fi
    fi
    
    # Validate package.json syntax
    if [[ -f "frontend/package.json" ]]; then
        if python3 -c "import json; json.load(open('frontend/package.json'))" 2>/dev/null; then
            print_success "✓ package.json syntax is valid"
        else
            print_error "✗ package.json syntax is invalid"
            return 1
        fi
    fi
    
    # Validate docker-compose.yml syntax
    if [[ -f "docker-compose.yml" ]]; then
        if python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" 2>/dev/null; then
            print_success "✓ docker-compose.yml syntax is valid"
        else
            print_error "✗ docker-compose.yml syntax is invalid"
            return 1
        fi
    fi
}

# Function to validate documentation links
validate_links() {
    print_status "Validating documentation links..."
    
    # Check internal links in README
    if [[ -f "README.md" ]]; then
        # Extract markdown links
        local links=$(grep -oE '\[([^\]]+)\]\(([^)]+)\)' README.md | grep -oE '\(([^)]+)\)' | tr -d '()')
        
        for link in $links; do
            # Skip external links and anchors
            if [[ "$link" =~ ^https?:// ]] || [[ "$link" =~ ^# ]]; then
                continue
            fi
            
            # Remove leading ./
            link=${link#./}
            
            if [[ -f "$link" ]] || [[ -d "$link" ]]; then
                print_success "✓ Link target exists: $link"
            else
                print_warning "⚠ Link target may not exist: $link"
            fi
        done
    fi
}

# Function to run documentation tests
run_documentation_tests() {
    print_status "Running documentation validation tests..."
    
    if [[ -f "tests/integration/test_documentation.py" ]]; then
        if command_exists python3 && python3 -c "import pytest" 2>/dev/null; then
            if python3 -m pytest tests/integration/test_documentation.py -v; then
                print_success "✓ Documentation tests passed"
            else
                print_error "✗ Documentation tests failed"
                return 1
            fi
        else
            print_warning "⚠ pytest not available, skipping documentation tests"
        fi
    else
        print_warning "⚠ Documentation tests not found"
    fi
}

# Function to check documentation completeness
check_completeness() {
    print_status "Checking documentation completeness..."
    
    local readme_content
    if [[ -f "README.md" ]]; then
        readme_content=$(cat README.md)
        
        # Check for required sections
        local required_sections=(
            "Features"
            "Architecture"
            "Development Setup"
            "Testing"
            "Deployment"
            "API Documentation"
            "Contributing"
            "License"
        )
        
        for section in "${required_sections[@]}"; do
            if echo "$readme_content" | grep -qi "$section"; then
                print_success "✓ README contains $section section"
            else
                print_warning "⚠ README may be missing $section section"
            fi
        done
        
        # Check for environment variables documentation
        local env_vars=(
            "MONGODB_URI"
            "REDIS_URL"
            "JWT_SECRET"
            "AMQP_URL"
        )
        
        for var in "${env_vars[@]}"; do
            if echo "$readme_content" | grep -q "$var"; then
                print_success "✓ README documents $var"
            else
                print_warning "⚠ README may not document $var"
            fi
        done
    fi
}

# Main function
main() {
    print_status "Starting documentation validation..."
    echo
    
    local exit_code=0
    
    # Run all validation functions
    validate_markdown || exit_code=1
    echo
    
    validate_openapi || exit_code=1
    echo
    
    validate_adrs || exit_code=1
    echo
    
    validate_license_compliance || exit_code=1
    echo
    
    validate_setup_instructions || exit_code=1
    echo
    
    validate_links || exit_code=1
    echo
    
    check_completeness || exit_code=1
    echo
    
    run_documentation_tests || exit_code=1
    echo
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "🎉 All documentation validation checks passed!"
    else
        print_error "❌ Some documentation validation checks failed"
        echo
        print_status "To fix issues:"
        echo "1. Review the error messages above"
        echo "2. Update the relevant documentation files"
        echo "3. Run this script again to verify fixes"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"
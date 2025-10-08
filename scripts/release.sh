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

# Function to validate version format
validate_version() {
    local version=$1
    if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$ ]]; then
        print_error "Invalid version format: $version"
        print_error "Expected format: v1.2.3 or v1.2.3-alpha.1"
        exit 1
    fi
}

# Function to check if tag already exists
check_tag_exists() {
    local version=$1
    if git rev-parse "$version" >/dev/null 2>&1; then
        print_error "Tag $version already exists"
        exit 1
    fi
}

# Function to check if working directory is clean
check_clean_working_dir() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes."
        git status --short
        exit 1
    fi
}

# Function to check if on main branch
check_main_branch() {
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        print_warning "You are not on the main branch (current: $current_branch)"
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Release cancelled"
            exit 1
        fi
    fi
}

# Function to update version in files
update_version_files() {
    local version=$1
    local version_number=${version#v}  # Remove 'v' prefix
    
    print_status "Updating version in project files..."
    
    # Update frontend package.json
    if [[ -f "frontend/package.json" ]]; then
        cd frontend
        npm version "$version_number" --no-git-tag-version
        cd ..
        print_success "Updated frontend/package.json"
    fi
    
    # Update OpenAPI spec version
    if [[ -f "docs/API/openapi.yaml" ]]; then
        sed -i.bak "s/version: [0-9]\+\.[0-9]\+\.[0-9]\+.*/version: $version_number/" docs/API/openapi.yaml
        rm docs/API/openapi.yaml.bak 2>/dev/null || true
        print_success "Updated OpenAPI specification version"
    fi
    
    # Update Python version if pyproject.toml exists
    if [[ -f "api/pyproject.toml" ]]; then
        sed -i.bak "s/version = \"[^\"]*\"/version = \"$version_number\"/" api/pyproject.toml
        rm api/pyproject.toml.bak 2>/dev/null || true
        print_success "Updated Python project version"
    fi
}

# Function to generate changelog
generate_changelog() {
    local version=$1
    
    print_status "Generating changelog..."
    
    # Check if conventional-changelog-cli is installed
    if ! command -v conventional-changelog &> /dev/null; then
        print_warning "conventional-changelog-cli not found. Installing..."
        npm install -g conventional-changelog-cli
    fi
    
    # Generate changelog
    conventional-changelog -p angular -i CHANGELOG.md -s
    
    print_success "Changelog generated"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Backend tests
    if [[ -f "api/requirements.txt" ]]; then
        print_status "Running backend tests..."
        cd api
        if [[ -f "pytest.ini" ]]; then
            python -m pytest --tb=short
        else
            print_warning "No pytest configuration found, skipping backend tests"
        fi
        cd ..
    fi
    
    # Frontend tests
    if [[ -f "frontend/package.json" ]]; then
        print_status "Running frontend tests..."
        cd frontend
        if npm run test --if-present; then
            print_success "Frontend tests passed"
        else
            print_warning "Frontend tests failed or not configured"
        fi
        cd ..
    fi
    
    print_success "Tests completed"
}

# Function to validate OpenAPI spec
validate_openapi() {
    print_status "Validating OpenAPI specification..."
    
    if command -v npx &> /dev/null && [[ -f "docs/API/openapi.yaml" ]]; then
        if npx @redocly/cli lint docs/API/openapi.yaml; then
            print_success "OpenAPI specification is valid"
        else
            print_error "OpenAPI specification validation failed"
            exit 1
        fi
    else
        print_warning "Redocly CLI not available, skipping OpenAPI validation"
    fi
}

# Function to create and push tag
create_tag() {
    local version=$1
    
    print_status "Creating git tag $version..."
    
    # Add updated files to git
    git add .
    
    # Check if there are changes to commit
    if [[ -n $(git diff --cached --name-only) ]]; then
        git commit -m "chore: prepare release $version"
        print_success "Committed version updates"
    fi
    
    # Create annotated tag
    git tag -a "$version" -m "Release $version"
    
    # Push tag
    git push origin "$version"
    
    print_success "Tag $version created and pushed"
}

# Function to show release information
show_release_info() {
    local version=$1
    
    echo
    print_success "Release $version has been initiated!"
    echo
    echo "Next steps:"
    echo "1. Monitor GitHub Actions workflow: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\).*/\1/' | sed 's/\.git$//')/actions"
    echo "2. Review the generated release notes"
    echo "3. Verify the deployment to production"
    echo "4. Announce the release to users"
    echo
}

# Main function
main() {
    local version=$1
    
    # Show usage if no version provided
    if [[ -z "$version" ]]; then
        echo "Usage: $0 <version>"
        echo
        echo "Examples:"
        echo "  $0 v1.0.0        # Stable release"
        echo "  $0 v1.1.0-beta.1 # Pre-release"
        echo "  $0 v2.0.0-rc.1   # Release candidate"
        echo
        echo "Version format: vMAJOR.MINOR.PATCH[-PRERELEASE]"
        exit 1
    fi
    
    print_status "Starting release process for $version"
    
    # Validation checks
    validate_version "$version"
    check_tag_exists "$version"
    check_clean_working_dir
    check_main_branch
    
    # Pre-release steps
    print_status "Running pre-release checks..."
    run_tests
    validate_openapi
    
    # Update version files
    update_version_files "$version"
    
    # Generate changelog
    generate_changelog "$version"
    
    # Create and push tag
    create_tag "$version"
    
    # Show completion info
    show_release_info "$version"
}

# Run main function with all arguments
main "$@"
#!/bin/bash

# MVP Release Validation Script for S.O.S Cidadão Platform
# Comprehensive validation before tagging and releasing v1.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RELEASE_VERSION="1.0.0"
RELEASE_BRANCH="main"
CURRENT_BRANCH=$(git branch --show-current)

# Validation results tracking
TOTAL_VALIDATIONS=0
PASSED_VALIDATIONS=0
FAILED_VALIDATIONS=0
FAILED_VALIDATION_NAMES=()

# Function to log messages
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to run validation
run_validation() {
    local validation_name=$1
    local validation_function=$2
    
    echo -e "\n${BLUE}🔍 Validating: $validation_name${NC}"
    echo "----------------------------------------"
    
    ((TOTAL_VALIDATIONS++))
    
    if $validation_function; then
        log_success "$validation_name: PASSED"
        ((PASSED_VALIDATIONS++))
    else
        log_error "$validation_name: FAILED"
        ((FAILED_VALIDATIONS++))
        FAILED_VALIDATION_NAMES+=("$validation_name")
    fi
}

# Validation 1: Git repository status
validate_git_status() {
    log_info "Checking git repository status..."
    
    # Check if we're on the correct branch
    if [ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]; then
        log_error "Not on release branch. Current: $CURRENT_BRANCH, Expected: $RELEASE_BRANCH"
        return 1
    fi
    
    # Check for uncommitted changes
    if ! git diff --quiet; then
        log_error "Uncommitted changes detected"
        git status --porcelain
        return 1
    fi
    
    # Check for untracked files that should be committed
    local untracked_files=$(git ls-files --others --exclude-standard)
    if [ ! -z "$untracked_files" ]; then
        log_warning "Untracked files detected:"
        echo "$untracked_files"
        # This is a warning, not a failure
    fi
    
    log_success "Git repository is clean and ready for release"
    return 0
}

# Validation 2: Required files exist
validate_required_files() {
    log_info "Checking required files exist..."
    
    local required_files=(
        "README.md"
        "LICENSE"
        "CONTRIBUTING.md"
        "CODE_OF_CONDUCT.md"
        "vercel.json"
        "docker-compose.yml"
        ".env.example"
        "api/app.py"
        "api/requirements.txt"
        "frontend/package.json"
        "frontend/src/main.ts"
        "docs/API/README.md"
        "docs/DEPLOYMENT-CHECKLIST.md"
        "RELEASE-NOTES-v1.0.0.md"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
    
    log_success "All required files are present"
    return 0
}

# Validation 3: Version consistency
validate_version_consistency() {
    log_info "Checking version consistency across files..."
    
    local version_files=(
        "frontend/package.json"
        "api/app.py"
    )
    
    local version_mismatches=()
    
    # Check package.json version
    if [ -f "frontend/package.json" ]; then
        local package_version=$(grep '"version"' frontend/package.json | sed 's/.*"version": "\([^"]*\)".*/\1/')
        if [ "$package_version" != "$RELEASE_VERSION" ]; then
            version_mismatches+=("frontend/package.json: $package_version (expected: $RELEASE_VERSION)")
        fi
    fi
    
    # Check if version is referenced in app.py
    if [ -f "api/app.py" ]; then
        if ! grep -q "$RELEASE_VERSION" api/app.py; then
            version_mismatches+=("api/app.py: version $RELEASE_VERSION not found")
        fi
    fi
    
    if [ ${#version_mismatches[@]} -gt 0 ]; then
        log_error "Version mismatches detected:"
        for mismatch in "${version_mismatches[@]}"; do
            echo "  - $mismatch"
        done
        return 1
    fi
    
    log_success "Version consistency validated"
    return 0
}

# Validation 4: Dependencies and security
validate_dependencies() {
    log_info "Checking dependencies and security..."
    
    # Check Python dependencies
    if [ -f "api/requirements.txt" ]; then
        log_info "Validating Python dependencies..."
        
        # Check for known vulnerable packages (basic check)
        local vulnerable_patterns=("django<" "flask<1.0" "requests<2.20")
        
        for pattern in "${vulnerable_patterns[@]}"; do
            if grep -q "$pattern" api/requirements.txt; then
                log_warning "Potentially vulnerable dependency pattern: $pattern"
            fi
        done
    fi
    
    # Check Node.js dependencies
    if [ -f "frontend/package.json" ]; then
        log_info "Validating Node.js dependencies..."
        
        # Check if package-lock.json exists
        if [ ! -f "frontend/package-lock.json" ]; then
            log_warning "package-lock.json not found - dependency versions not locked"
        fi
    fi
    
    log_success "Dependencies validation completed"
    return 0
}

# Validation 5: Configuration files
validate_configuration_files() {
    log_info "Checking configuration files..."
    
    # Validate vercel.json
    if [ -f "vercel.json" ]; then
        if ! python3 -c "import json; json.load(open('vercel.json'))" 2>/dev/null; then
            log_error "vercel.json is not valid JSON"
            return 1
        fi
        
        # Check for required environment variables
        local required_env_vars=("MONGODB_URI" "REDIS_URL" "JWT_SECRET" "AMQP_URL")
        
        for env_var in "${required_env_vars[@]}"; do
            if ! grep -q "$env_var" vercel.json; then
                log_warning "Environment variable $env_var not found in vercel.json"
            fi
        done
    fi
    
    # Validate docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        if command -v docker-compose >/dev/null 2>&1; then
            if ! docker-compose config >/dev/null 2>&1; then
                log_error "docker-compose.yml is not valid"
                return 1
            fi
        else
            log_warning "docker-compose not available - skipping validation"
        fi
    fi
    
    log_success "Configuration files validation completed"
    return 0
}

# Validation 6: Documentation completeness
validate_documentation() {
    log_info "Checking documentation completeness..."
    
    # Check README.md content
    if [ -f "README.md" ]; then
        local readme_sections=("Installation" "Usage" "API" "Contributing" "License")
        
        for section in "${readme_sections[@]}"; do
            if ! grep -qi "$section" README.md; then
                log_warning "README.md missing section: $section"
            fi
        done
    fi
    
    # Check API documentation
    if [ -f "docs/API/README.md" ]; then
        if [ $(wc -l < docs/API/README.md) -lt 50 ]; then
            log_warning "API documentation seems incomplete (less than 50 lines)"
        fi
    fi
    
    # Check ADRs exist
    if [ -d "docs/ADRs" ]; then
        local adr_count=$(find docs/ADRs -name "*.md" | wc -l)
        if [ $adr_count -lt 3 ]; then
            log_warning "Few ADRs found ($adr_count) - consider documenting more architectural decisions"
        fi
    fi
    
    log_success "Documentation validation completed"
    return 0
}

# Validation 7: Test coverage and quality
validate_test_coverage() {
    log_info "Checking test coverage and quality..."
    
    # Check if test directories exist
    local test_directories=("api/tests" "frontend/tests" "tests/integration" "tests/acceptance")
    local missing_test_dirs=()
    
    for test_dir in "${test_directories[@]}"; do
        if [ ! -d "$test_dir" ]; then
            missing_test_dirs+=("$test_dir")
        fi
    done
    
    if [ ${#missing_test_dirs[@]} -gt 0 ]; then
        log_warning "Missing test directories:"
        for dir in "${missing_test_dirs[@]}"; do
            echo "  - $dir"
        done
    fi
    
    # Count test files
    local test_file_count=0
    for test_dir in "${test_directories[@]}"; do
        if [ -d "$test_dir" ]; then
            local dir_test_count=$(find "$test_dir" -name "test_*.py" -o -name "*_test.py" -o -name "*.spec.ts" | wc -l)
            test_file_count=$((test_file_count + dir_test_count))
        fi
    done
    
    log_info "Found $test_file_count test files"
    
    if [ $test_file_count -lt 10 ]; then
        log_warning "Low test file count ($test_file_count) - consider adding more tests"
    fi
    
    log_success "Test coverage validation completed"
    return 0
}

# Validation 8: Security configuration
validate_security_configuration() {
    log_info "Checking security configuration..."
    
    # Check for sensitive files that shouldn't be committed
    local sensitive_patterns=(".env" "*.key" "*.pem" "secrets.json" "config/production.py")
    local found_sensitive=()
    
    for pattern in "${sensitive_patterns[@]}"; do
        if find . -name "$pattern" -not -path "./.git/*" | grep -q .; then
            found_sensitive+=("$pattern")
        fi
    done
    
    if [ ${#found_sensitive[@]} -gt 0 ]; then
        log_error "Sensitive files found in repository:"
        for file in "${found_sensitive[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
    
    # Check .gitignore exists and has common patterns
    if [ -f ".gitignore" ]; then
        local gitignore_patterns=(".env" "*.key" "node_modules" "__pycache__")
        
        for pattern in "${gitignore_patterns[@]}"; do
            if ! grep -q "$pattern" .gitignore; then
                log_warning ".gitignore missing pattern: $pattern"
            fi
        done
    else
        log_error ".gitignore file not found"
        return 1
    fi
    
    log_success "Security configuration validation completed"
    return 0
}

# Validation 9: Build and deployment readiness
validate_build_readiness() {
    log_info "Checking build and deployment readiness..."
    
    # Check if Python requirements can be installed
    if [ -f "api/requirements.txt" ]; then
        log_info "Validating Python requirements..."
        
        # Create temporary virtual environment for validation
        if command -v python3 >/dev/null 2>&1; then
            local temp_venv=$(mktemp -d)
            python3 -m venv "$temp_venv" >/dev/null 2>&1
            
            if source "$temp_venv/bin/activate" && pip install -r api/requirements.txt >/dev/null 2>&1; then
                log_success "Python requirements can be installed"
            else
                log_error "Python requirements installation failed"
                rm -rf "$temp_venv"
                return 1
            fi
            
            deactivate
            rm -rf "$temp_venv"
        else
            log_warning "Python3 not available - skipping requirements validation"
        fi
    fi
    
    # Check if Node.js dependencies can be installed
    if [ -f "frontend/package.json" ]; then
        log_info "Validating Node.js dependencies..."
        
        if command -v npm >/dev/null 2>&1; then
            # Check if package.json is valid
            if ! node -e "require('./frontend/package.json')" 2>/dev/null; then
                log_error "frontend/package.json is not valid"
                return 1
            fi
        else
            log_warning "npm not available - skipping Node.js validation"
        fi
    fi
    
    log_success "Build readiness validation completed"
    return 0
}

# Validation 10: Release notes and changelog
validate_release_documentation() {
    log_info "Checking release documentation..."
    
    # Check release notes exist
    if [ ! -f "RELEASE-NOTES-v$RELEASE_VERSION.md" ]; then
        log_error "Release notes not found: RELEASE-NOTES-v$RELEASE_VERSION.md"
        return 1
    fi
    
    # Check release notes content
    local release_notes_file="RELEASE-NOTES-v$RELEASE_VERSION.md"
    local required_sections=("Release Overview" "Key Features" "Installation" "Known Issues")
    
    for section in "${required_sections[@]}"; do
        if ! grep -qi "$section" "$release_notes_file"; then
            log_warning "Release notes missing section: $section"
        fi
    done
    
    # Check if CHANGELOG exists
    if [ -f "CHANGELOG.md" ]; then
        if ! grep -q "$RELEASE_VERSION" CHANGELOG.md; then
            log_warning "CHANGELOG.md doesn't mention version $RELEASE_VERSION"
        fi
    else
        log_warning "CHANGELOG.md not found"
    fi
    
    log_success "Release documentation validation completed"
    return 0
}

# Function to generate release validation report
generate_release_validation_report() {
    echo -e "\n${BLUE}📊 MVP Release Validation Report${NC}"
    echo "================================="
    echo -e "Release Version: v$RELEASE_VERSION"
    echo -e "Current Branch: $CURRENT_BRANCH"
    echo -e "Validation Time: $(date)"
    echo -e "Total Validations: $TOTAL_VALIDATIONS"
    echo -e "${GREEN}Passed: $PASSED_VALIDATIONS${NC}"
    echo -e "${RED}Failed: $FAILED_VALIDATIONS${NC}"
    
    if [ $FAILED_VALIDATIONS -gt 0 ]; then
        echo -e "\n${RED}Failed Validations:${NC}"
        for validation_name in "${FAILED_VALIDATION_NAMES[@]}"; do
            echo -e "  - $validation_name"
        done
        
        echo -e "\n${RED}❌ RELEASE NOT READY${NC}"
        echo -e "${RED}Please fix the failed validations before proceeding with the release.${NC}"
    else
        echo -e "\n${GREEN}✅ RELEASE READY${NC}"
        echo -e "${GREEN}All validations passed. The MVP is ready for release!${NC}"
        
        echo -e "\n${BLUE}Next Steps:${NC}"
        echo -e "1. Create and merge pull request to main branch"
        echo -e "2. Tag the release: git tag -a v$RELEASE_VERSION -m 'Release v$RELEASE_VERSION: S.O.S Cidadão MVP'"
        echo -e "3. Push the tag: git push origin v$RELEASE_VERSION"
        echo -e "4. Deploy to production and verify all systems operational"
        echo -e "5. Announce the release to stakeholders"
    fi
    
    # Calculate success rate
    if [ $TOTAL_VALIDATIONS -gt 0 ]; then
        local success_rate=$((PASSED_VALIDATIONS * 100 / TOTAL_VALIDATIONS))
        echo -e "\nValidation Success Rate: $success_rate%"
    fi
}

# Main execution function
main() {
    echo -e "${BLUE}S.O.S Cidadão Platform - MVP Release Validation${NC}"
    echo -e "================================================"
    echo -e "Validating release readiness for v$RELEASE_VERSION"
    echo ""
    
    # Run all validations
    run_validation "Git Repository Status" validate_git_status
    run_validation "Required Files" validate_required_files
    run_validation "Version Consistency" validate_version_consistency
    run_validation "Dependencies and Security" validate_dependencies
    run_validation "Configuration Files" validate_configuration_files
    run_validation "Documentation Completeness" validate_documentation
    run_validation "Test Coverage and Quality" validate_test_coverage
    run_validation "Security Configuration" validate_security_configuration
    run_validation "Build and Deployment Readiness" validate_build_readiness
    run_validation "Release Documentation" validate_release_documentation
    
    # Generate validation report
    generate_release_validation_report
    
    # Exit with appropriate code
    if [ $FAILED_VALIDATIONS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            RELEASE_VERSION="$2"
            shift 2
            ;;
        --branch)
            RELEASE_BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            echo "MVP Release Validation Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --version VERSION         Release version to validate (default: 1.0.0)"
            echo "  --branch BRANCH           Release branch to validate (default: main)"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "This script validates that the repository is ready for MVP release by checking:"
            echo "  - Git repository status and cleanliness"
            echo "  - Required files and documentation"
            echo "  - Version consistency across files"
            echo "  - Dependencies and security configuration"
            echo "  - Build and deployment readiness"
            echo "  - Test coverage and quality"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main
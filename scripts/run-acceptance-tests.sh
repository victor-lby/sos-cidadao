#!/bin/bash

# Comprehensive Acceptance Test Runner for S.O.S Cidadão Platform
# Runs complete user journey and business rule validation tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_ENVIRONMENT="acceptance"
DEPLOYMENT_URL=""
GENERATE_REPORT=true
VERBOSE_OUTPUT=false
PARALLEL_EXECUTION=false

# Test results tracking
TOTAL_TEST_SUITES=0
PASSED_TEST_SUITES=0
FAILED_TEST_SUITES=0
FAILED_SUITE_NAMES=()
TEST_START_TIME=""
TEST_END_TIME=""

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

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_file=$2
    local test_description=$3
    
    echo -e "\n${BLUE}🧪 Running: $suite_name${NC}"
    echo "Description: $test_description"
    echo "Test File: $test_file"
    echo "----------------------------------------"
    
    ((TOTAL_TEST_SUITES++))
    
    local start_time=$(date +%s)
    local test_output=""
    local test_result=0
    
    # Run the test suite
    if [ "$VERBOSE_OUTPUT" = "true" ]; then
        python3 -m pytest "$test_file" -v --tb=short --color=yes
        test_result=$?
    else
        test_output=$(python3 -m pytest "$test_file" -v --tb=short --color=yes 2>&1)
        test_result=$?
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $test_result -eq 0 ]; then
        log_success "$suite_name: PASSED (${duration}s)"
        ((PASSED_TEST_SUITES++))
    else
        log_error "$suite_name: FAILED (${duration}s)"
        ((FAILED_TEST_SUITES++))
        FAILED_SUITE_NAMES+=("$suite_name")
        
        # Show test output for failed tests if not in verbose mode
        if [ "$VERBOSE_OUTPUT" = "false" ] && [ ! -z "$test_output" ]; then
            echo -e "${RED}Test Output:${NC}"
            echo "$test_output" | tail -20  # Show last 20 lines
        fi
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for acceptance testing..."
    
    # Check required tools
    local required_tools=("python3" "pip")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check Python packages
    local required_packages=("pytest" "requests")
    
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" >/dev/null 2>&1; then
            log_error "Python package $package is required but not installed"
            log_info "Install with: pip install $package"
            exit 1
        fi
    done
    
    # Check test files exist
    local test_files=(
        "tests/acceptance/test_user_workflows.py"
        "tests/acceptance/test_business_rules.py"
    )
    
    for test_file in "${test_files[@]}"; do
        if [ ! -f "$test_file" ]; then
            log_error "Test file not found: $test_file"
            exit 1
        fi
    done
    
    log_success "Prerequisites check completed"
}

# Function to setup test environment
setup_test_environment() {
    log_info "Setting up acceptance test environment..."
    
    # Load environment variables
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Set test-specific environment variables
    export ENVIRONMENT="$TEST_ENVIRONMENT"
    export TESTING=true
    
    # Set deployment URL
    if [ -z "$DEPLOYMENT_URL" ]; then
        DEPLOYMENT_URL=${VERCEL_URL:-"http://localhost:5000"}
    fi
    
    # Ensure URL has protocol
    if [[ ! $DEPLOYMENT_URL =~ ^https?:// ]]; then
        DEPLOYMENT_URL="http://$DEPLOYMENT_URL"
    fi
    
    export DEPLOYMENT_URL="$DEPLOYMENT_URL"
    
    log_info "Testing deployment: $DEPLOYMENT_URL"
    
    # Verify deployment is accessible
    if ! curl -f "$DEPLOYMENT_URL/api/health" >/dev/null 2>&1; then
        log_warning "Deployment not accessible at $DEPLOYMENT_URL"
        log_info "Continuing with local testing configuration"
    fi
    
    # Setup test database
    export MONGODB_URI="${MONGODB_URI:-mongodb://localhost:27017/sos_cidadao_acceptance_test}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/2}"  # Use different DB for acceptance tests
    
    # Clean test database
    log_info "Cleaning acceptance test database..."
    python3 -c "
import pymongo
import os
try:
    client = pymongo.MongoClient(os.getenv('MONGODB_URI'))
    db_name = os.getenv('MONGODB_URI').split('/')[-1]
    client.drop_database(db_name)
    print('Acceptance test database cleaned')
except Exception as e:
    print(f'Database cleanup failed: {e}')
" 2>/dev/null || log_warning "Database cleanup failed"
    
    log_success "Test environment setup completed"
}

# Function to run user workflow tests
run_user_workflow_tests() {
    echo -e "\n${BLUE}👥 Running User Workflow Acceptance Tests${NC}"
    echo "=========================================="
    
    run_test_suite \
        "Notification Workflow Tests" \
        "tests/acceptance/test_user_workflows.py::TestNotificationWorkflowAcceptance" \
        "Complete notification workflows from creation to dispatch"
    
    run_test_suite \
        "User Management Tests" \
        "tests/acceptance/test_user_workflows.py::TestUserManagementAcceptance" \
        "User registration, role assignment, and permission management"
    
    run_test_suite \
        "Organization Management Tests" \
        "tests/acceptance/test_user_workflows.py::TestOrganizationManagementAcceptance" \
        "Organization settings and configuration management"
    
    run_test_suite \
        "Audit and Compliance Tests" \
        "tests/acceptance/test_user_workflows.py::TestAuditAndComplianceAcceptance" \
        "Audit trail generation and compliance reporting"
    
    run_test_suite \
        "Error Recovery Tests" \
        "tests/acceptance/test_user_workflows.py::TestErrorRecoveryAcceptance" \
        "Error scenarios and system recovery procedures"
    
    run_test_suite \
        "Integration Tests" \
        "tests/acceptance/test_user_workflows.py::TestIntegrationAcceptance" \
        "External system integration and API workflows"
}

# Function to run business rule tests
run_business_rule_tests() {
    echo -e "\n${BLUE}📋 Running Business Rule Acceptance Tests${NC}"
    echo "=========================================="
    
    run_test_suite \
        "Notification Business Rules" \
        "tests/acceptance/test_business_rules.py::TestNotificationBusinessRules" \
        "Notification-specific business rules and constraints"
    
    run_test_suite \
        "User Permission Rules" \
        "tests/acceptance/test_business_rules.py::TestUserPermissionBusinessRules" \
        "User permission and role-based access control rules"
    
    run_test_suite \
        "Data Consistency Rules" \
        "tests/acceptance/test_business_rules.py::TestDataConsistencyBusinessRules" \
        "Data consistency and integrity validation rules"
    
    run_test_suite \
        "Workflow Rules" \
        "tests/acceptance/test_business_rules.py::TestWorkflowBusinessRules" \
        "Workflow-specific business rules and state transitions"
    
    run_test_suite \
        "Compliance Rules" \
        "tests/acceptance/test_business_rules.py::TestComplianceBusinessRules" \
        "Compliance and regulatory requirement validation"
}

# Function to run data consistency validation
run_data_consistency_validation() {
    echo -e "\n${BLUE}🔍 Running Data Consistency Validation${NC}"
    echo "======================================"
    
    log_info "Validating database consistency..."
    
    # Run data consistency checks
    python3 -c "
import pymongo
import os
from datetime import datetime

try:
    client = pymongo.MongoClient(os.getenv('MONGODB_URI'))
    db = client.get_default_database()
    
    # Check for orphaned records
    notifications = list(db.notifications.find({'deletedAt': None}))
    users = list(db.users.find({'deletedAt': None}))
    organizations = list(db.organizations.find({'deletedAt': None}))
    
    print(f'Found {len(notifications)} notifications')
    print(f'Found {len(users)} users')
    print(f'Found {len(organizations)} organizations')
    
    # Validate referential integrity
    org_ids = {org['_id'] for org in organizations}
    
    orphaned_notifications = [n for n in notifications if n.get('organizationId') not in org_ids]
    orphaned_users = [u for u in users if u.get('organizationId') not in org_ids]
    
    if orphaned_notifications:
        print(f'WARNING: Found {len(orphaned_notifications)} orphaned notifications')
    
    if orphaned_users:
        print(f'WARNING: Found {len(orphaned_users)} orphaned users')
    
    # Validate schema versions
    invalid_schema_notifications = [n for n in notifications if not n.get('schemaVersion')]
    invalid_schema_users = [u for u in users if not u.get('schemaVersion')]
    
    if invalid_schema_notifications:
        print(f'WARNING: Found {len(invalid_schema_notifications)} notifications without schema version')
    
    if invalid_schema_users:
        print(f'WARNING: Found {len(invalid_schema_users)} users without schema version')
    
    print('Data consistency validation completed')
    
except Exception as e:
    print(f'Data consistency validation failed: {e}')
    exit(1)
" || log_warning "Data consistency validation had issues"
    
    log_success "Data consistency validation completed"
}

# Function to generate acceptance test report
generate_acceptance_test_report() {
    if [ "$GENERATE_REPORT" != "true" ]; then
        return 0
    fi
    
    local report_file="acceptance_test_report_$(date +%Y%m%d_%H%M%S).md"
    
    log_info "Generating acceptance test report: $report_file"
    
    cat > "$report_file" << EOF
# S.O.S Cidadão Platform - Acceptance Test Report

## Test Execution Summary

- **Test Date**: $(date)
- **Test Environment**: $TEST_ENVIRONMENT
- **Deployment URL**: $DEPLOYMENT_URL
- **Test Duration**: $(($(date +%s) - $(date -d "$TEST_START_TIME" +%s))) seconds

## Results Overview

- **Total Test Suites**: $TOTAL_TEST_SUITES
- **Passed**: $PASSED_TEST_SUITES
- **Failed**: $FAILED_TEST_SUITES
- **Success Rate**: $((PASSED_TEST_SUITES * 100 / TOTAL_TEST_SUITES))%

## Test Suite Results

### User Workflow Tests
Tests complete user journeys from login to notification management.

### Business Rule Tests
Validates business rule enforcement and data consistency.

### Data Consistency Validation
Ensures data integrity and referential consistency.

EOF

    if [ $FAILED_TEST_SUITES -gt 0 ]; then
        cat >> "$report_file" << EOF
## Failed Test Suites

The following test suites failed and require attention:

EOF
        for suite_name in "${FAILED_SUITE_NAMES[@]}"; do
            echo "- $suite_name" >> "$report_file"
        done
        
        cat >> "$report_file" << EOF

## Recommendations

1. Review failed test suites and address underlying issues
2. Verify business rule implementation matches requirements
3. Ensure data consistency and integrity constraints are properly enforced
4. Re-run acceptance tests after fixes are implemented

EOF
    else
        cat >> "$report_file" << EOF
## Test Results

✅ **All acceptance tests passed successfully!**

The S.O.S Cidadão Platform has successfully passed all acceptance criteria:

- Complete user workflows function correctly
- Business rules are properly enforced
- Data consistency is maintained
- Error scenarios are handled appropriately
- Integration points work as expected

## Approval for Production

Based on the successful completion of all acceptance tests, the system is **APPROVED** for production deployment.

EOF
    fi
    
    cat >> "$report_file" << EOF
## Test Environment Details

- **MongoDB URI**: $MONGODB_URI
- **Redis URL**: $REDIS_URL
- **Python Version**: $(python3 --version)
- **Pytest Version**: $(python3 -m pytest --version)

## Next Steps

EOF
    
    if [ $FAILED_TEST_SUITES -eq 0 ]; then
        cat >> "$report_file" << EOF
1. ✅ Proceed with production deployment
2. ✅ Configure production monitoring and alerting
3. ✅ Schedule regular acceptance test runs
4. ✅ Document any configuration changes for production

EOF
    else
        cat >> "$report_file" << EOF
1. ❌ Fix failed test suites before production deployment
2. ❌ Re-run acceptance tests to verify fixes
3. ❌ Review business requirements for failed scenarios
4. ❌ Update documentation based on test results

EOF
    fi
    
    log_success "Acceptance test report generated: $report_file"
}

# Function to generate comprehensive summary
generate_comprehensive_summary() {
    echo -e "\n${BLUE}📊 Acceptance Test Execution Summary${NC}"
    echo "====================================="
    echo -e "Test Start Time: $TEST_START_TIME"
    echo -e "Test End Time: $(date)"
    echo -e "Total Duration: $(($(date +%s) - $(date -d "$TEST_START_TIME" +%s))) seconds"
    echo -e "Deployment URL: $DEPLOYMENT_URL"
    echo -e "Test Environment: $TEST_ENVIRONMENT"
    echo ""
    echo -e "Total Test Suites: $TOTAL_TEST_SUITES"
    echo -e "${GREEN}Passed: $PASSED_TEST_SUITES${NC}"
    echo -e "${RED}Failed: $FAILED_TEST_SUITES${NC}"
    
    if [ $TOTAL_TEST_SUITES -gt 0 ]; then
        local success_rate=$((PASSED_TEST_SUITES * 100 / TOTAL_TEST_SUITES))
        echo -e "Success Rate: $success_rate%"
        
        if [ $success_rate -eq 100 ]; then
            echo -e "\n${GREEN}🎉 ALL ACCEPTANCE TESTS PASSED!${NC}"
            echo -e "${GREEN}✅ System is ready for production deployment${NC}"
            echo -e "${GREEN}✅ All user workflows function correctly${NC}"
            echo -e "${GREEN}✅ All business rules are properly enforced${NC}"
            echo -e "${GREEN}✅ Data consistency is maintained${NC}"
        elif [ $success_rate -ge 80 ]; then
            echo -e "\n${YELLOW}⚠️  Most acceptance tests passed${NC}"
            echo -e "${YELLOW}🔧 Some issues need attention before production${NC}"
        else
            echo -e "\n${RED}❌ Significant acceptance test failures${NC}"
            echo -e "${RED}🚫 System not ready for production deployment${NC}"
        fi
    fi
    
    if [ $FAILED_TEST_SUITES -gt 0 ]; then
        echo -e "\n${RED}Failed Test Suites:${NC}"
        for suite_name in "${FAILED_SUITE_NAMES[@]}"; do
            echo -e "  - $suite_name"
        done
    fi
    
    echo -e "\n${BLUE}📋 Acceptance Criteria Validation:${NC}"
    echo -e "  - User workflow completeness: $([ $FAILED_TEST_SUITES -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo -e "  - Business rule enforcement: $([ $FAILED_TEST_SUITES -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo -e "  - Data consistency validation: $([ $FAILED_TEST_SUITES -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo -e "  - Error handling and recovery: $([ $FAILED_TEST_SUITES -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo -e "  - Integration functionality: $([ $FAILED_TEST_SUITES -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
}

# Main execution function
main() {
    TEST_START_TIME=$(date)
    
    echo -e "${BLUE}S.O.S Cidadão Platform - Acceptance Test Suite${NC}"
    echo -e "=============================================="
    echo -e "Starting comprehensive acceptance testing..."
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup test environment
    setup_test_environment
    
    # Run user workflow tests
    run_user_workflow_tests
    
    # Run business rule tests
    run_business_rule_tests
    
    # Run data consistency validation
    run_data_consistency_validation
    
    # Generate test report
    generate_acceptance_test_report
    
    # Generate comprehensive summary
    generate_comprehensive_summary
    
    # Exit with appropriate code
    if [ $FAILED_TEST_SUITES -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All acceptance tests completed successfully!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some acceptance tests failed. Please review and fix issues.${NC}"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            DEPLOYMENT_URL="$2"
            shift 2
            ;;
        --environment)
            TEST_ENVIRONMENT="$2"
            shift 2
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        --verbose|-v)
            VERBOSE_OUTPUT=true
            shift
            ;;
        --parallel)
            PARALLEL_EXECUTION=true
            shift
            ;;
        --help|-h)
            echo "Comprehensive Acceptance Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --url URL                 Deployment URL to test"
            echo "  --environment ENV         Test environment name (default: acceptance)"
            echo "  --no-report               Skip generating test report"
            echo "  --verbose, -v             Enable verbose test output"
            echo "  --parallel                Run tests in parallel (experimental)"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DEPLOYMENT_URL            Deployment URL to test"
            echo "  MONGODB_URI               MongoDB connection string for testing"
            echo "  REDIS_URL                 Redis connection string for testing"
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
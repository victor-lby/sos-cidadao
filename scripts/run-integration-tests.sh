#!/bin/bash

# Comprehensive integration test runner for S.O.S Cidadão Platform
# Runs end-to-end tests, multi-tenant isolation tests, and HAL API tests

set -e

echo "🚀 Starting S.O.S Cidadão Platform Integration Tests"
echo "=================================================="

# Load environment variables
source scripts/load-env.sh development

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
FAILED_TEST_NAMES=()

# Function to run test suite
run_test_suite() {
    local test_file=$1
    local test_name=$2
    
    echo -e "\n${BLUE}📋 Running: $test_name${NC}"
    echo "----------------------------------------"
    
    if python -m pytest "$test_file" -v --tb=short --color=yes; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        ((FAILED_TESTS++))
        FAILED_TEST_NAMES+=("$test_name")
    fi
    
    ((TOTAL_TESTS++))
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    
    # Check if required services are running
    if ! docker-compose ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Starting required services...${NC}"
        docker-compose up -d
        sleep 10  # Wait for services to start
    fi
    
    # Check Python dependencies
    if ! python -c "import pytest, flask, pymongo, redis" >/dev/null 2>&1; then
        echo -e "${RED}❌ Missing Python dependencies. Please run: pip install -r api/requirements.txt${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function to setup test environment
setup_test_environment() {
    echo -e "\n${BLUE}🛠️  Setting up test environment...${NC}"
    
    # Set test environment variables
    export ENVIRONMENT=test
    export MONGODB_URI="mongodb://localhost:27017/sos_cidadao_test"
    export REDIS_URL="redis://localhost:6379/1"  # Use different DB for tests
    export JWT_SECRET="test-jwt-secret-key"
    export AMQP_URL="amqp://admin:admin123@localhost:5672/"
    export OTEL_ENABLED=false  # Disable telemetry for tests
    
    # Clean test database
    echo "🧹 Cleaning test database..."
    python -c "
import pymongo
client = pymongo.MongoClient('$MONGODB_URI')
client.drop_database('sos_cidadao_test')
print('Test database cleaned')
"
    
    # Clean test Redis
    echo "🧹 Cleaning test Redis..."
    redis-cli -u "$REDIS_URL" FLUSHDB
    
    echo -e "${GREEN}✅ Test environment setup complete${NC}"
}

# Function to run health checks
run_health_checks() {
    echo -e "\n${BLUE}🏥 Running health checks...${NC}"
    
    # Check API health
    if curl -f http://localhost:5000/api/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Starting API server...${NC}"
        cd api && python app.py &
        API_PID=$!
        sleep 5
        
        if curl -f http://localhost:5000/api/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ API health check passed${NC}"
        else
            echo -e "${RED}❌ API health check failed${NC}"
            kill $API_PID 2>/dev/null || true
            exit 1
        fi
    fi
}

# Function to generate test report
generate_test_report() {
    echo -e "\n${BLUE}📊 Test Results Summary${NC}"
    echo "========================================"
    echo -e "Total Test Suites: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "\n${RED}Failed Test Suites:${NC}"
        for test_name in "${FAILED_TEST_NAMES[@]}"; do
            echo -e "  - $test_name"
        done
    fi
    
    # Calculate success rate
    if [ $TOTAL_TESTS -gt 0 ]; then
        SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo -e "\nSuccess Rate: $SUCCESS_RATE%"
        
        if [ $SUCCESS_RATE -eq 100 ]; then
            echo -e "${GREEN}🎉 All integration tests passed!${NC}"
        elif [ $SUCCESS_RATE -ge 80 ]; then
            echo -e "${YELLOW}⚠️  Most tests passed, but some issues need attention.${NC}"
        else
            echo -e "${RED}❌ Significant test failures detected. Please review and fix.${NC}"
        fi
    fi
}

# Function to cleanup
cleanup() {
    echo -e "\n${BLUE}🧹 Cleaning up...${NC}"
    
    # Kill API server if started
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    
    # Clean test data
    python -c "
import pymongo
try:
    client = pymongo.MongoClient('$MONGODB_URI')
    client.drop_database('sos_cidadao_test')
    print('Test database cleaned')
except:
    pass
" 2>/dev/null || true
    
    redis-cli -u "$REDIS_URL" FLUSHDB 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Trap cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    echo -e "${BLUE}S.O.S Cidadão Platform - Integration Test Suite${NC}"
    echo -e "Environment: ${ENVIRONMENT:-development}"
    echo -e "Timestamp: $(date)"
    echo ""
    
    # Run prerequisite checks
    check_prerequisites
    
    # Setup test environment
    setup_test_environment
    
    # Run health checks
    run_health_checks
    
    # Run integration test suites
    echo -e "\n${BLUE}🧪 Running Integration Test Suites${NC}"
    echo "========================================"
    
    # 1. End-to-end workflow tests
    run_test_suite "tests/integration/test_end_to_end_workflow.py" "End-to-End Workflow Tests"
    
    # 2. Multi-tenant isolation tests
    run_test_suite "tests/integration/test_multi_tenant_isolation.py" "Multi-Tenant Isolation Tests"
    
    # 3. HAL API discoverability tests
    run_test_suite "tests/integration/test_hal_api_discoverability.py" "HAL API Discoverability Tests"
    
    # 4. Authentication and authorization tests
    if [ -f "tests/integration/test_auth_flows.py" ]; then
        run_test_suite "tests/integration/test_auth_flows.py" "Authentication & Authorization Tests"
    fi
    
    # 5. Performance and scalability tests
    if [ -f "tests/integration/test_performance.py" ]; then
        run_test_suite "tests/integration/test_performance.py" "Performance & Scalability Tests"
    fi
    
    # 6. Security validation tests
    if [ -f "tests/integration/test_security.py" ]; then
        run_test_suite "tests/integration/test_security.py" "Security Validation Tests"
    fi
    
    # 7. Deployment and infrastructure tests
    if [ -f "tests/integration/test_deployment.py" ]; then
        run_test_suite "tests/integration/test_deployment.py" "Deployment & Infrastructure Tests"
    fi
    
    # Generate final report
    generate_test_report
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All integration tests completed successfully!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some integration tests failed. Please review and fix issues.${NC}"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "S.O.S Cidadão Platform Integration Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --help, -h          Show this help message"
            echo "  --verbose, -v       Run tests with verbose output"
            echo "  --fast              Skip setup and run tests quickly"
            echo "  --suite SUITE       Run specific test suite only"
            echo ""
            echo "Test Suites:"
            echo "  - end-to-end        End-to-end workflow tests"
            echo "  - multi-tenant      Multi-tenant isolation tests"
            echo "  - hal-api           HAL API discoverability tests"
            echo "  - auth              Authentication & authorization tests"
            echo "  - performance       Performance & scalability tests"
            echo "  - security          Security validation tests"
            echo "  - deployment        Deployment & infrastructure tests"
            exit 0
            ;;
        --verbose|-v)
            set -x
            shift
            ;;
        --fast)
            FAST_MODE=true
            shift
            ;;
        --suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run specific test suite if requested
if [ ! -z "$TEST_SUITE" ]; then
    case $TEST_SUITE in
        end-to-end)
            run_test_suite "tests/integration/test_end_to_end_workflow.py" "End-to-End Workflow Tests"
            ;;
        multi-tenant)
            run_test_suite "tests/integration/test_multi_tenant_isolation.py" "Multi-Tenant Isolation Tests"
            ;;
        hal-api)
            run_test_suite "tests/integration/test_hal_api_discoverability.py" "HAL API Discoverability Tests"
            ;;
        *)
            echo "Unknown test suite: $TEST_SUITE"
            exit 1
            ;;
    esac
    exit 0
fi

# Run main function
main
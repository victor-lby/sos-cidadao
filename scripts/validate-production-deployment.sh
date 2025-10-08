#!/bin/bash

# Production Deployment Validation Script for S.O.S Cidadão Platform
# Validates Vercel deployment with MongoDB Atlas, Upstash Redis, and CloudAMQP LavinMQ

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_URL=""
MONGODB_ATLAS_URI=""
UPSTASH_REDIS_URL=""
UPSTASH_REDIS_TOKEN=""
CLOUDAMQP_URL=""
JWT_SECRET=""
OTEL_ENDPOINT=""

# Test results tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
FAILED_CHECK_NAMES=()

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

# Function to run validation check
run_check() {
    local check_name=$1
    local check_function=$2
    
    echo -e "\n${BLUE}🔍 Running: $check_name${NC}"
    echo "----------------------------------------"
    
    ((TOTAL_CHECKS++))
    
    if $check_function; then
        log_success "$check_name: PASSED"
        ((PASSED_CHECKS++))
    else
        log_error "$check_name: FAILED"
        ((FAILED_CHECKS++))
        FAILED_CHECK_NAMES+=("$check_name")
    fi
}

# Function to load configuration
load_configuration() {
    log_info "Loading production deployment configuration..."
    
    # Try to load from environment variables first
    DEPLOYMENT_URL=${DEPLOYMENT_URL:-$VERCEL_URL}
    MONGODB_ATLAS_URI=${MONGODB_ATLAS_URI:-$MONGODB_URI}
    UPSTASH_REDIS_URL=${UPSTASH_REDIS_URL:-$REDIS_URL}
    UPSTASH_REDIS_TOKEN=${UPSTASH_REDIS_TOKEN:-$REDIS_TOKEN}
    CLOUDAMQP_URL=${CLOUDAMQP_URL:-$AMQP_URL}
    JWT_SECRET=${JWT_SECRET:-$JWT_SECRET}
    OTEL_ENDPOINT=${OTEL_ENDPOINT:-$OTEL_EXPORTER_OTLP_ENDPOINT}
    
    # Validate required configuration
    if [ -z "$DEPLOYMENT_URL" ]; then
        log_error "DEPLOYMENT_URL not set. Please provide the Vercel deployment URL."
        exit 1
    fi
    
    # Ensure URL has protocol
    if [[ ! $DEPLOYMENT_URL =~ ^https?:// ]]; then
        DEPLOYMENT_URL="https://$DEPLOYMENT_URL"
    fi
    
    log_success "Configuration loaded for: $DEPLOYMENT_URL"
}

# Check 1: Vercel deployment accessibility
check_vercel_deployment() {
    log_info "Checking Vercel deployment accessibility..."
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$DEPLOYMENT_URL" || echo "000")
    
    if [ "$response_code" = "200" ] || [ "$response_code" = "301" ] || [ "$response_code" = "302" ]; then
        log_success "Deployment is accessible (HTTP $response_code)"
        return 0
    else
        log_error "Deployment not accessible (HTTP $response_code)"
        return 1
    fi
}

# Check 2: API health endpoint
check_api_health() {
    log_info "Checking API health endpoint..."
    
    local health_url="$DEPLOYMENT_URL/api/health"
    local response
    
    response=$(curl -s "$health_url" || echo "")
    
    if echo "$response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
        log_success "API health check passed"
        
        # Extract and display health information
        local version
        local environment
        version=$(echo "$response" | jq -r '.version // "unknown"')
        environment=$(echo "$response" | jq -r '.environment // "unknown"')
        
        log_info "API Version: $version"
        log_info "Environment: $environment"
        
        return 0
    else
        log_error "API health check failed"
        log_error "Response: $response"
        return 1
    fi
}

# Check 3: MongoDB Atlas connectivity
check_mongodb_atlas() {
    log_info "Checking MongoDB Atlas connectivity..."
    
    if [ -z "$MONGODB_ATLAS_URI" ]; then
        log_warning "MongoDB Atlas URI not provided, skipping check"
        return 0
    fi
    
    # Test MongoDB connection using Python
    python3 -c "
import pymongo
import sys
try:
    client = pymongo.MongoClient('$MONGODB_ATLAS_URI', serverSelectionTimeoutMS=5000)
    client.server_info()
    print('MongoDB Atlas connection successful')
    sys.exit(0)
except Exception as e:
    print(f'MongoDB Atlas connection failed: {e}')
    sys.exit(1)
" && return 0 || return 1
}

# Check 4: Upstash Redis connectivity
check_upstash_redis() {
    log_info "Checking Upstash Redis connectivity..."
    
    if [ -z "$UPSTASH_REDIS_URL" ]; then
        log_warning "Upstash Redis URL not provided, skipping check"
        return 0
    fi
    
    # Test Redis connection using HTTP API
    local redis_test_url="$UPSTASH_REDIS_URL/ping"
    local auth_header=""
    
    if [ ! -z "$UPSTASH_REDIS_TOKEN" ]; then
        auth_header="Authorization: Bearer $UPSTASH_REDIS_TOKEN"
    fi
    
    local response
    if [ ! -z "$auth_header" ]; then
        response=$(curl -s -H "$auth_header" "$redis_test_url" || echo "")
    else
        response=$(curl -s "$redis_test_url" || echo "")
    fi
    
    if echo "$response" | grep -q "PONG"; then
        log_success "Upstash Redis connection successful"
        return 0
    else
        log_error "Upstash Redis connection failed"
        log_error "Response: $response"
        return 1
    fi
}

# Check 5: CloudAMQP LavinMQ connectivity
check_cloudamqp_lavinmq() {
    log_info "Checking CloudAMQP LavinMQ connectivity..."
    
    if [ -z "$CLOUDAMQP_URL" ]; then
        log_warning "CloudAMQP URL not provided, skipping check"
        return 0
    fi
    
    # Test AMQP connection using Python
    python3 -c "
import pika
import sys
import urllib.parse
try:
    connection = pika.BlockingConnection(pika.URLParameters('$CLOUDAMQP_URL'))
    channel = connection.channel()
    connection.close()
    print('CloudAMQP LavinMQ connection successful')
    sys.exit(0)
except Exception as e:
    print(f'CloudAMQP LavinMQ connection failed: {e}')
    sys.exit(1)
" && return 0 || return 1
}

# Check 6: OpenTelemetry observability
check_opentelemetry_observability() {
    log_info "Checking OpenTelemetry observability configuration..."
    
    local health_url="$DEPLOYMENT_URL/api/health"
    local response
    
    response=$(curl -s "$health_url" || echo "")
    
    if echo "$response" | jq -e '.observability.otel_enabled == true' >/dev/null 2>&1; then
        log_success "OpenTelemetry is enabled"
        
        # Check if OTLP endpoint is configured
        if [ ! -z "$OTEL_ENDPOINT" ]; then
            log_success "OTLP endpoint configured: $OTEL_ENDPOINT"
        else
            log_warning "OTLP endpoint not configured"
        fi
        
        return 0
    else
        log_warning "OpenTelemetry not enabled or not reporting status"
        return 0  # Not a failure, might be intentionally disabled
    fi
}

# Check 7: Environment variables and secrets
check_environment_configuration() {
    log_info "Checking environment configuration..."
    
    local config_url="$DEPLOYMENT_URL/api/health"
    local response
    
    response=$(curl -s "$config_url" || echo "")
    
    local config_status
    config_status=$(echo "$response" | jq -r '.configuration // {}')
    
    if [ "$config_status" = "{}" ]; then
        log_warning "Configuration status not available in health endpoint"
        return 0
    fi
    
    # Check individual configuration items
    local mongodb_configured
    local redis_configured
    local amqp_configured
    local jwt_configured
    
    mongodb_configured=$(echo "$response" | jq -r '.configuration.mongodb_uri_configured // false')
    redis_configured=$(echo "$response" | jq -r '.configuration.redis_configured // false')
    amqp_configured=$(echo "$response" | jq -r '.configuration.amqp_configured // false')
    jwt_configured=$(echo "$response" | jq -r '.configuration.jwt_secret_configured // false')
    
    local all_configured=true
    
    if [ "$mongodb_configured" = "true" ]; then
        log_success "MongoDB URI configured"
    else
        log_error "MongoDB URI not configured"
        all_configured=false
    fi
    
    if [ "$redis_configured" = "true" ]; then
        log_success "Redis configured"
    else
        log_error "Redis not configured"
        all_configured=false
    fi
    
    if [ "$amqp_configured" = "true" ]; then
        log_success "AMQP configured"
    else
        log_error "AMQP not configured"
        all_configured=false
    fi
    
    if [ "$jwt_configured" = "true" ]; then
        log_success "JWT secret configured"
    else
        log_error "JWT secret not configured"
        all_configured=false
    fi
    
    if [ "$all_configured" = "true" ]; then
        return 0
    else
        return 1
    fi
}

# Check 8: API endpoints functionality
check_api_endpoints() {
    log_info "Checking API endpoints functionality..."
    
    # Test API root endpoint
    local api_root_url="$DEPLOYMENT_URL/api"
    local response
    
    response=$(curl -s "$api_root_url" || echo "")
    
    if echo "$response" | jq -e '._links' >/dev/null 2>&1; then
        log_success "API root endpoint returns HAL structure"
    else
        log_error "API root endpoint not returning proper HAL structure"
        return 1
    fi
    
    # Test OpenAPI documentation (if enabled)
    local docs_url="$DEPLOYMENT_URL/api/docs"
    local docs_response_code
    docs_response_code=$(curl -s -o /dev/null -w "%{http_code}" "$docs_url" || echo "000")
    
    if [ "$docs_response_code" = "200" ]; then
        log_success "API documentation accessible"
    elif [ "$docs_response_code" = "404" ]; then
        log_info "API documentation disabled (expected in production)"
    else
        log_warning "API documentation endpoint returned HTTP $docs_response_code"
    fi
    
    return 0
}

# Check 9: Security headers and HTTPS
check_security_configuration() {
    log_info "Checking security configuration..."
    
    local headers
    headers=$(curl -s -I "$DEPLOYMENT_URL" || echo "")
    
    local security_score=0
    local total_security_checks=5
    
    # Check HTTPS
    if [[ $DEPLOYMENT_URL =~ ^https:// ]]; then
        log_success "HTTPS enabled"
        ((security_score++))
    else
        log_error "HTTPS not enabled"
    fi
    
    # Check security headers
    if echo "$headers" | grep -i "strict-transport-security" >/dev/null; then
        log_success "HSTS header present"
        ((security_score++))
    else
        log_warning "HSTS header missing"
    fi
    
    if echo "$headers" | grep -i "x-content-type-options" >/dev/null; then
        log_success "X-Content-Type-Options header present"
        ((security_score++))
    else
        log_warning "X-Content-Type-Options header missing"
    fi
    
    if echo "$headers" | grep -i "x-frame-options" >/dev/null; then
        log_success "X-Frame-Options header present"
        ((security_score++))
    else
        log_warning "X-Frame-Options header missing"
    fi
    
    if echo "$headers" | grep -i "content-security-policy" >/dev/null; then
        log_success "Content-Security-Policy header present"
        ((security_score++))
    else
        log_warning "Content-Security-Policy header missing"
    fi
    
    # Calculate security score
    local security_percentage=$((security_score * 100 / total_security_checks))
    log_info "Security score: $security_score/$total_security_checks ($security_percentage%)"
    
    if [ $security_score -ge 4 ]; then
        return 0
    else
        return 1
    fi
}

# Check 10: Performance and response times
check_performance() {
    log_info "Checking performance and response times..."
    
    local health_url="$DEPLOYMENT_URL/api/health"
    local start_time
    local end_time
    local response_time
    
    start_time=$(date +%s%N)
    curl -s "$health_url" >/dev/null
    end_time=$(date +%s%N)
    
    response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    
    log_info "Health endpoint response time: ${response_time}ms"
    
    if [ $response_time -lt 2000 ]; then
        log_success "Response time acceptable (< 2s)"
        return 0
    elif [ $response_time -lt 5000 ]; then
        log_warning "Response time slow but acceptable (< 5s)"
        return 0
    else
        log_error "Response time too slow (> 5s)"
        return 1
    fi
}

# Function to generate validation report
generate_validation_report() {
    echo -e "\n${BLUE}📊 Production Deployment Validation Report${NC}"
    echo "=============================================="
    echo -e "Deployment URL: $DEPLOYMENT_URL"
    echo -e "Validation Time: $(date)"
    echo -e "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "\n${RED}Failed Checks:${NC}"
        for check_name in "${FAILED_CHECK_NAMES[@]}"; do
            echo -e "  - $check_name"
        done
    fi
    
    # Calculate success rate
    if [ $TOTAL_CHECKS -gt 0 ]; then
        local success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo -e "\nSuccess Rate: $success_rate%"
        
        if [ $success_rate -eq 100 ]; then
            echo -e "${GREEN}🎉 Production deployment validation passed!${NC}"
            echo -e "${GREEN}✅ All systems operational and ready for production use.${NC}"
        elif [ $success_rate -ge 80 ]; then
            echo -e "${YELLOW}⚠️  Most checks passed, but some issues need attention.${NC}"
            echo -e "${YELLOW}🔧 Please review failed checks before full production deployment.${NC}"
        else
            echo -e "${RED}❌ Significant validation failures detected.${NC}"
            echo -e "${RED}🚫 Production deployment not recommended until issues are resolved.${NC}"
        fi
    fi
}

# Main execution function
main() {
    echo -e "${BLUE}S.O.S Cidadão Platform - Production Deployment Validation${NC}"
    echo -e "=========================================================="
    echo ""
    
    # Load configuration
    load_configuration
    
    # Run validation checks
    echo -e "\n${BLUE}🔍 Running Production Deployment Validation Checks${NC}"
    echo "===================================================="
    
    run_check "Vercel Deployment Accessibility" check_vercel_deployment
    run_check "API Health Endpoint" check_api_health
    run_check "MongoDB Atlas Connectivity" check_mongodb_atlas
    run_check "Upstash Redis Connectivity" check_upstash_redis
    run_check "CloudAMQP LavinMQ Connectivity" check_cloudamqp_lavinmq
    run_check "OpenTelemetry Observability" check_opentelemetry_observability
    run_check "Environment Configuration" check_environment_configuration
    run_check "API Endpoints Functionality" check_api_endpoints
    run_check "Security Configuration" check_security_configuration
    run_check "Performance and Response Times" check_performance
    
    # Generate validation report
    generate_validation_report
    
    # Exit with appropriate code
    if [ $FAILED_CHECKS -eq 0 ]; then
        exit 0
    else
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
        --mongodb-uri)
            MONGODB_ATLAS_URI="$2"
            shift 2
            ;;
        --redis-url)
            UPSTASH_REDIS_URL="$2"
            shift 2
            ;;
        --redis-token)
            UPSTASH_REDIS_TOKEN="$2"
            shift 2
            ;;
        --amqp-url)
            CLOUDAMQP_URL="$2"
            shift 2
            ;;
        --jwt-secret)
            JWT_SECRET="$2"
            shift 2
            ;;
        --otel-endpoint)
            OTEL_ENDPOINT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Production Deployment Validation Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --url URL                 Vercel deployment URL"
            echo "  --mongodb-uri URI         MongoDB Atlas connection URI"
            echo "  --redis-url URL           Upstash Redis URL"
            echo "  --redis-token TOKEN       Upstash Redis authentication token"
            echo "  --amqp-url URL            CloudAMQP LavinMQ URL"
            echo "  --jwt-secret SECRET       JWT secret key"
            echo "  --otel-endpoint URL       OpenTelemetry OTLP endpoint"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  VERCEL_URL                Vercel deployment URL"
            echo "  MONGODB_URI               MongoDB Atlas connection URI"
            echo "  REDIS_URL                 Upstash Redis URL"
            echo "  REDIS_TOKEN               Upstash Redis token"
            echo "  AMQP_URL                  CloudAMQP LavinMQ URL"
            echo "  JWT_SECRET                JWT secret key"
            echo "  OTEL_EXPORTER_OTLP_ENDPOINT  OpenTelemetry endpoint"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check for required dependencies
if ! command -v curl >/dev/null 2>&1; then
    log_error "curl is required but not installed"
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    log_error "jq is required but not installed"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    log_error "python3 is required but not installed"
    exit 1
fi

# Run main function
main
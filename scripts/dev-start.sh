#!/bin/bash

# S.O.S Cidadão Development Startup Script
# This script starts the complete development environment using Docker Compose

set -e

echo "🚀 Starting S.O.S Cidadão Development Environment"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose is not available. Please install Docker Compose and try again."
    exit 1
fi

# Use docker compose (newer) or docker-compose (legacy)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "📦 Building and starting all services..."
echo "This may take a few minutes on first run..."

# Build and start all services
$DOCKER_COMPOSE_CMD up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."

# Wait for services to be healthy
timeout=300  # 5 minutes timeout
elapsed=0
interval=5

while [ $elapsed -lt $timeout ]; do
    if $DOCKER_COMPOSE_CMD ps --format json | jq -r '.[].Health' | grep -q "unhealthy"; then
        echo "⚠️  Some services are unhealthy, continuing to wait..."
    elif $DOCKER_COMPOSE_CMD ps --format json | jq -r '.[].Health' | grep -qv "healthy\|"; then
        echo "⏳ Services still starting... (${elapsed}s elapsed)"
    else
        echo "✅ All services are healthy!"
        break
    fi
    
    sleep $interval
    elapsed=$((elapsed + interval))
done

if [ $elapsed -ge $timeout ]; then
    echo "⚠️  Timeout waiting for services to be healthy. Checking status..."
    $DOCKER_COMPOSE_CMD ps
    echo ""
    echo "You can check logs with: $DOCKER_COMPOSE_CMD logs [service-name]"
else
    echo ""
    echo "🎉 S.O.S Cidadão Development Environment is ready!"
    echo ""
    echo "📱 Frontend:              http://localhost:3000"
    echo "🔧 Backend API:           http://localhost:5000"
    echo "📚 API Documentation:     http://localhost:5000/openapi/swagger"
    echo "🐰 RabbitMQ Management:   http://localhost:15672 (admin/admin123)"
    echo "🔍 Jaeger Tracing:        http://localhost:16686"
    echo "🗄️  MongoDB:               mongodb://localhost:27017"
    echo "🔴 Redis:                 redis://localhost:6379"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs:              $DOCKER_COMPOSE_CMD logs -f [service-name]"
    echo "  Stop services:          $DOCKER_COMPOSE_CMD down"
    echo "  Restart service:        $DOCKER_COMPOSE_CMD restart [service-name]"
    echo "  View status:            $DOCKER_COMPOSE_CMD ps"
    echo ""
    echo "🔧 Development workflow:"
    echo "  - Code changes in ./api and ./frontend are automatically reloaded"
    echo "  - Backend logs: $DOCKER_COMPOSE_CMD logs -f api"
    echo "  - Frontend logs: $DOCKER_COMPOSE_CMD logs -f frontend"
fi
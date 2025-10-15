#!/bin/bash

# S.O.S Cidadão Development Stop Script
# This script stops the complete development environment

set -e

echo "🛑 Stopping S.O.S Cidadão Development Environment"
echo "==============================================="

# Use docker compose (newer) or docker-compose (legacy)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "📦 Stopping all services..."
$DOCKER_COMPOSE_CMD down

echo ""
echo "🧹 Cleaning up..."

# Optional: Remove volumes (uncomment if you want to reset data)
# echo "🗑️  Removing volumes..."
# $DOCKER_COMPOSE_CMD down -v

echo ""
echo "✅ Development environment stopped successfully!"
echo ""
echo "💡 To start again, run: ./scripts/dev-start.sh"
echo "💡 To remove all data, run: $DOCKER_COMPOSE_CMD down -v"
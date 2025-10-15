#!/bin/bash

# Test script to verify the Docker Compose setup
set -e

echo "🧪 Testing S.O.S Cidadão Docker Compose Setup"
echo "============================================="

# Use docker compose (newer) or docker-compose (legacy)
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "📋 Validating docker-compose.yml..."
$DOCKER_COMPOSE_CMD config --quiet

echo "✅ Docker Compose configuration is valid!"

echo ""
echo "🔍 Checking required files..."

required_files=(
    "api/Dockerfile"
    "frontend/Dockerfile"
    "api/.dockerignore"
    "frontend/.dockerignore"
    ".env.development"
    "docker-compose.override.yml"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

echo ""
echo "🎉 All setup files are present and valid!"
echo ""
echo "🚀 Ready to start development environment with:"
echo "   ./scripts/dev-start.sh"
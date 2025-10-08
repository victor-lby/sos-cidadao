#!/bin/bash

# Load environment variables for S.O.S Cidadão Platform
# Usage: source scripts/load-env.sh [environment]

set -e

ENVIRONMENT=${1:-development}
ENV_FILE=""

case $ENVIRONMENT in
    "development"|"dev")
        ENV_FILE=".env"
        ;;
    "staging"|"stage")
        ENV_FILE=".env.staging"
        ;;
    "production"|"prod")
        ENV_FILE=".env.production"
        ;;
    "test")
        ENV_FILE=".env.test"
        ;;
    *)
        echo "Unknown environment: $ENVIRONMENT"
        echo "Usage: source scripts/load-env.sh [development|staging|production|test]"
        exit 1
        ;;
esac

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Environment file $ENV_FILE not found!"
    
    if [ "$ENV_FILE" = ".env" ]; then
        echo "Creating .env from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "Created .env file. Please update with your actual values."
        else
            echo "No .env.example found. Please create .env manually."
            exit 1
        fi
    else
        echo "Please create $ENV_FILE or use 'development' environment."
        exit 1
    fi
fi

# Load environment variables
echo "Loading environment variables from $ENV_FILE..."
export $(grep -v '^#' $ENV_FILE | grep -v '^$' | xargs)

# Validate required variables
REQUIRED_VARS=(
    "ENVIRONMENT"
    "MONGODB_URI"
    "REDIS_URL"
    "JWT_SECRET"
    "AMQP_URL"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "ERROR: Missing required environment variables:"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo "Please update $ENV_FILE with the required values."
    exit 1
fi

echo "Environment loaded successfully for: $ENVIRONMENT"
echo "MongoDB URI: ${MONGODB_URI}"
echo "Redis URL: ${REDIS_URL}"
echo "AMQP URL: ${AMQP_URL}"
echo "OpenTelemetry enabled: ${OTEL_ENABLED:-true}"
echo "Docs enabled: ${DOCS_ENABLED:-true}"
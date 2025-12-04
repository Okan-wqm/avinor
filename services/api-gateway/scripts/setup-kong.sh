#!/bin/bash
# services/api-gateway/scripts/setup-kong.sh
# Setup Kong API Gateway

set -e

echo "=========================================="
echo "Kong API Gateway Setup"
echo "=========================================="

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Create external network if not exists
echo "Creating Docker network..."
docker network create avinor_network 2>/dev/null || true

# Navigate to api-gateway directory
cd "$(dirname "$0")/.."

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your settings before continuing."
    exit 1
fi

# Generate JWT keys if not exist
if [ ! -f kong/jwt-keys/private.pem ]; then
    echo "Generating JWT keys..."
    ./scripts/generate-jwt-keys.sh
fi

# Start Kong database first
echo "Starting Kong database..."
docker-compose up -d kong-database

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Run migrations
echo "Running Kong migrations..."
docker-compose up kong-migration

# Start Kong
echo "Starting Kong..."
docker-compose up -d kong

# Wait for Kong to be ready
echo "Waiting for Kong to be ready..."
sleep 10

# Verify Kong is running
if curl -s http://localhost:8001/status > /dev/null; then
    echo "=========================================="
    echo "Kong is running!"
    echo "=========================================="
    echo ""
    echo "Proxy:     http://localhost:80"
    echo "Admin API: http://localhost:8001"
    echo ""
    echo "To start Konga (Admin UI):"
    echo "  docker-compose --profile dev up -d konga"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f kong"
else
    echo "Error: Kong failed to start"
    docker-compose logs kong
    exit 1
fi

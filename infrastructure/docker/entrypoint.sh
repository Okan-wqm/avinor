#!/bin/bash
set -e

# =============================================================================
# Service Entrypoint Script
# =============================================================================

echo "Starting ${SERVICE_NAME:-service}..."

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=${4:-30}
    local attempt=1

    echo "Waiting for $service_name at $host:$port..."

    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: $service_name at $host:$port is not available after $max_attempts attempts"
            exit 1
        fi
        echo "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "$service_name is ready!"
}

# Wait for database
if [ -n "$DB_HOST" ]; then
    wait_for_service "$DB_HOST" "${DB_PORT:-5432}" "PostgreSQL"
fi

# Wait for Redis (if configured)
if [ -n "$REDIS_HOST" ]; then
    wait_for_service "$REDIS_HOST" "${REDIS_PORT:-6379}" "Redis"
fi

# Wait for RabbitMQ (if configured)
if [ -n "$RABBITMQ_HOST" ]; then
    wait_for_service "$RABBITMQ_HOST" "${RABBITMQ_PORT:-5672}" "RabbitMQ"
fi

# Run database migrations (if enabled)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput
fi

# Collect static files (if enabled)
if [ "${COLLECT_STATIC:-false}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

# Create superuser (if enabled and doesn't exist)
if [ "${CREATE_SUPERUSER:-false}" = "true" ]; then
    echo "Creating superuser if not exists..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='${SUPERUSER_EMAIL:-admin@example.com}').exists():
    User.objects.create_superuser(
        email='${SUPERUSER_EMAIL:-admin@example.com}',
        password='${SUPERUSER_PASSWORD:-admin123}',
        username='${SUPERUSER_USERNAME:-admin}'
    )
    print('Superuser created')
else:
    print('Superuser already exists')
EOF
fi

# Execute the main command
echo "Starting application with command: $@"
exec "$@"

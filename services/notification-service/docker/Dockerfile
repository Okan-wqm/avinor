# Notification Service Dockerfile
FROM python:3.11-slim-bookworm

# Build arguments
ARG SERVICE_NAME=notification-service
ARG SERVICE_PORT=8013

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVICE_NAME=${SERVICE_NAME} \
    SERVICE_PORT=${SERVICE_PORT}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy requirements and install
COPY requirements/ /app/requirements/
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /app/requirements/base.txt

# Copy shared library
COPY shared/ /app/shared/

# Copy service code
COPY services/notification-service/src/ /app/

# Copy entrypoint
COPY infrastructure/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Change ownership
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE ${SERVICE_PORT}

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8013"]

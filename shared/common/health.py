"""
Health Check Module.

Provides health check endpoints for all microservices.
"""
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from django.db import connection
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# =============================================================================
# HEALTH CHECK STATUS
# =============================================================================

class HealthStatus:
    """Health check status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency = (time.time() - start) * 1000
        return {
            "name": "database",
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "name": "database",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_cache() -> Dict[str, Any]:
    """Check cache connectivity."""
    start = time.time()
    try:
        cache_key = f"health_check_{time.time()}"
        cache.set(cache_key, "OK", 10)
        value = cache.get(cache_key)
        cache.delete(cache_key)

        if value != "OK":
            raise Exception("Cache read/write mismatch")

        latency = (time.time() - start) * 1000
        return {
            "name": "cache",
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "name": "cache",
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
        }


def check_nats() -> Dict[str, Any]:
    """Check NATS connectivity."""
    start = time.time()
    try:
        import nats
        import asyncio

        async def _check():
            nc = await nats.connect(
                servers=getattr(settings, 'NATS_SERVERS', ['nats://localhost:4222']),
                connect_timeout=5,
            )
            await nc.close()

        asyncio.get_event_loop().run_until_complete(_check())
        latency = (time.time() - start) * 1000

        return {
            "name": "nats",
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.warning(f"NATS health check failed: {e}")
        return {
            "name": "nats",
            "status": HealthStatus.DEGRADED,
            "error": str(e),
        }


def check_celery() -> Dict[str, Any]:
    """Check Celery worker connectivity."""
    try:
        from celery import current_app

        inspect = current_app.control.inspect()
        active = inspect.active()

        if active:
            worker_count = len(active)
            return {
                "name": "celery",
                "status": HealthStatus.HEALTHY,
                "workers": worker_count,
            }
        else:
            return {
                "name": "celery",
                "status": HealthStatus.DEGRADED,
                "workers": 0,
            }
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        return {
            "name": "celery",
            "status": HealthStatus.DEGRADED,
            "error": str(e),
        }


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        import shutil

        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100

        status = HealthStatus.HEALTHY
        if free_percent < 10:
            status = HealthStatus.UNHEALTHY
        elif free_percent < 20:
            status = HealthStatus.DEGRADED

        return {
            "name": "disk",
            "status": status,
            "free_percent": round(free_percent, 2),
            "free_gb": round(free / (1024**3), 2),
        }
    except Exception as e:
        logger.warning(f"Disk space check failed: {e}")
        return {
            "name": "disk",
            "status": HealthStatus.DEGRADED,
            "error": str(e),
        }


def check_memory() -> Dict[str, Any]:
    """Check available memory."""
    try:
        import psutil

        memory = psutil.virtual_memory()
        available_percent = memory.available / memory.total * 100

        status = HealthStatus.HEALTHY
        if available_percent < 10:
            status = HealthStatus.UNHEALTHY
        elif available_percent < 20:
            status = HealthStatus.DEGRADED

        return {
            "name": "memory",
            "status": status,
            "available_percent": round(available_percent, 2),
            "available_mb": round(memory.available / (1024**2), 2),
        }
    except ImportError:
        return {
            "name": "memory",
            "status": HealthStatus.HEALTHY,
            "note": "psutil not installed",
        }
    except Exception as e:
        logger.warning(f"Memory check failed: {e}")
        return {
            "name": "memory",
            "status": HealthStatus.DEGRADED,
            "error": str(e),
        }


# =============================================================================
# HEALTH CHECK VIEWS
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint.

    Returns 200 if the service is running.
    Used by load balancers and orchestrators.
    """
    return Response({
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.utcnow().isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the service is alive.
    Failures will trigger container restart.
    """
    return Response({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Checks critical dependencies (database, cache).
    """
    checks = [
        check_database(),
        check_cache(),
    ]

    # Determine overall status
    statuses = [c["status"] for c in checks]
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
        status_code = 503
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
        status_code = 200
    else:
        overall_status = HealthStatus.HEALTHY
        status_code = 200

    return Response(
        {
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        },
        status=status_code
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def detailed_health_check(request):
    """
    Detailed health check endpoint.

    Returns comprehensive health status of all dependencies.
    Use for monitoring dashboards and troubleshooting.
    """
    checks = [
        check_database(),
        check_cache(),
        check_nats(),
        check_celery(),
        check_disk_space(),
        check_memory(),
    ]

    # Determine overall status
    statuses = [c["status"] for c in checks]
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    return Response({
        "status": overall_status,
        "service": getattr(settings, 'SERVICE_NAME', 'unknown'),
        "version": getattr(settings, 'VERSION', '1.0.0'),
        "environment": getattr(settings, 'ENVIRONMENT', 'development'),
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    })


# =============================================================================
# URL PATTERNS
# =============================================================================

def get_health_urlpatterns():
    """
    Returns URL patterns for health check endpoints.

    Usage in urls.py:
        from shared.common.health import get_health_urlpatterns
        urlpatterns += get_health_urlpatterns()
    """
    from django.urls import path

    return [
        path('health/', health_check, name='health'),
        path('health/live/', liveness_check, name='liveness'),
        path('health/ready/', readiness_check, name='readiness'),
        path('health/detailed/', detailed_health_check, name='health_detailed'),
    ]

# shared/common/metrics.py
"""
Prometheus Metrics and Monitoring Utilities
"""

import time
import logging
from functools import wraps
from typing import Callable, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import prometheus_client, gracefully handle if not installed
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics will be disabled")


# =============================================================================
# METRIC DEFINITIONS
# =============================================================================

if PROMETHEUS_AVAILABLE:
    SERVICE_NAME = getattr(settings, 'SERVICE_NAME', 'unknown')

    # HTTP Metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code', 'service']
    )

    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint', 'service'],
        buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
    )

    http_requests_in_progress = Gauge(
        'http_requests_in_progress',
        'HTTP requests currently in progress',
        ['method', 'service']
    )

    # Database Metrics
    database_query_duration_seconds = Histogram(
        'database_query_duration_seconds',
        'Database query duration in seconds',
        ['query_type', 'table', 'service'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    )

    database_connections_total = Gauge(
        'database_connections_total',
        'Total database connections',
        ['service', 'database']
    )

    # Cache Metrics
    cache_hits_total = Counter(
        'cache_hits_total',
        'Total cache hits',
        ['cache_name', 'service']
    )

    cache_misses_total = Counter(
        'cache_misses_total',
        'Total cache misses',
        ['cache_name', 'service']
    )

    cache_operation_duration_seconds = Histogram(
        'cache_operation_duration_seconds',
        'Cache operation duration in seconds',
        ['operation', 'cache_name', 'service'],
        buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1]
    )

    # Event Metrics
    events_published_total = Counter(
        'events_published_total',
        'Total events published',
        ['event_type', 'service']
    )

    events_consumed_total = Counter(
        'events_consumed_total',
        'Total events consumed',
        ['event_type', 'service', 'status']
    )

    event_processing_duration_seconds = Histogram(
        'event_processing_duration_seconds',
        'Event processing duration in seconds',
        ['event_type', 'service'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
    )

    # External Service Metrics
    external_request_duration_seconds = Histogram(
        'external_request_duration_seconds',
        'External service request duration in seconds',
        ['target_service', 'method', 'source_service'],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )

    external_request_errors_total = Counter(
        'external_request_errors_total',
        'Total external service request errors',
        ['target_service', 'error_type', 'source_service']
    )

    circuit_breaker_state = Gauge(
        'circuit_breaker_state',
        'Circuit breaker state (0=closed, 1=open, 2=half_open)',
        ['target_service', 'source_service']
    )

    # Business Metrics
    active_users = Gauge(
        'active_users',
        'Number of active users',
        ['service', 'organization']
    )

    # Task/Celery Metrics
    celery_task_duration_seconds = Histogram(
        'celery_task_duration_seconds',
        'Celery task duration in seconds',
        ['task_name', 'service'],
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
    )

    celery_tasks_total = Counter(
        'celery_tasks_total',
        'Total Celery tasks',
        ['task_name', 'status', 'service']
    )

    # Service Info
    service_info = Info(
        'service',
        'Service information'
    )


# =============================================================================
# DECORATORS
# =============================================================================

def track_request_metrics(view_func: Callable) -> Callable:
    """
    Decorator to track HTTP request metrics for views.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not PROMETHEUS_AVAILABLE:
            return view_func(request, *args, **kwargs)

        service = getattr(settings, 'SERVICE_NAME', 'unknown')
        method = request.method
        endpoint = request.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, service=service).inc()

        start_time = time.time()
        try:
            response = view_func(request, *args, **kwargs)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                service=service
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                service=service
            ).observe(duration)

            http_requests_in_progress.labels(method=method, service=service).dec()

    return wrapper


def track_db_query(query_type: str, table: str):
    """
    Decorator to track database query metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            service = getattr(settings, 'SERVICE_NAME', 'unknown')
            start_time = time.time()

            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                database_query_duration_seconds.labels(
                    query_type=query_type,
                    table=table,
                    service=service
                ).observe(duration)

        return wrapper
    return decorator


def track_cache_operation(cache_name: str = 'default'):
    """
    Decorator to track cache operation metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            service = getattr(settings, 'SERVICE_NAME', 'unknown')
            operation = func.__name__
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Track hits/misses for get operations
                if operation in ['get', 'get_many']:
                    if result is not None:
                        cache_hits_total.labels(cache_name=cache_name, service=service).inc()
                    else:
                        cache_misses_total.labels(cache_name=cache_name, service=service).inc()

                return result
            finally:
                duration = time.time() - start_time
                cache_operation_duration_seconds.labels(
                    operation=operation,
                    cache_name=cache_name,
                    service=service
                ).observe(duration)

        return wrapper
    return decorator


def track_external_request(target_service: str):
    """
    Decorator to track external service request metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return await func(*args, **kwargs)

            source_service = getattr(settings, 'SERVICE_NAME', 'unknown')
            method = func.__name__.upper()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                external_request_errors_total.labels(
                    target_service=target_service,
                    error_type=type(e).__name__,
                    source_service=source_service
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                external_request_duration_seconds.labels(
                    target_service=target_service,
                    method=method,
                    source_service=source_service
                ).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            source_service = getattr(settings, 'SERVICE_NAME', 'unknown')
            method = func.__name__.upper()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                external_request_errors_total.labels(
                    target_service=target_service,
                    error_type=type(e).__name__,
                    source_service=source_service
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                external_request_duration_seconds.labels(
                    target_service=target_service,
                    method=method,
                    source_service=source_service
                ).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def track_celery_task(task_name: str):
    """
    Decorator to track Celery task metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not PROMETHEUS_AVAILABLE:
                return func(*args, **kwargs)

            service = getattr(settings, 'SERVICE_NAME', 'unknown')
            start_time = time.time()
            status = 'success'

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failure'
                raise
            finally:
                duration = time.time() - start_time
                celery_task_duration_seconds.labels(
                    task_name=task_name,
                    service=service
                ).observe(duration)
                celery_tasks_total.labels(
                    task_name=task_name,
                    status=status,
                    service=service
                ).inc()

        return wrapper
    return decorator


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_metrics():
    """Get Prometheus metrics in text format"""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not installed", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


def set_service_info(version: str, environment: str):
    """Set service info metric"""
    if not PROMETHEUS_AVAILABLE:
        return

    service_info.info({
        'name': getattr(settings, 'SERVICE_NAME', 'unknown'),
        'version': version,
        'environment': environment
    })


def update_circuit_breaker_state(target_service: str, state: str):
    """Update circuit breaker state metric"""
    if not PROMETHEUS_AVAILABLE:
        return

    state_map = {'closed': 0, 'open': 1, 'half_open': 2}
    circuit_breaker_state.labels(
        target_service=target_service,
        source_service=getattr(settings, 'SERVICE_NAME', 'unknown')
    ).set(state_map.get(state, 0))


def record_event_published(event_type: str):
    """Record event published metric"""
    if not PROMETHEUS_AVAILABLE:
        return

    events_published_total.labels(
        event_type=event_type,
        service=getattr(settings, 'SERVICE_NAME', 'unknown')
    ).inc()


def record_event_consumed(event_type: str, success: bool = True):
    """Record event consumed metric"""
    if not PROMETHEUS_AVAILABLE:
        return

    events_consumed_total.labels(
        event_type=event_type,
        service=getattr(settings, 'SERVICE_NAME', 'unknown'),
        status='success' if success else 'failure'
    ).inc()


class MetricsTimer:
    """Context manager for timing operations"""

    def __init__(self, histogram, labels: dict):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if PROMETHEUS_AVAILABLE and self.histogram:
            duration = time.time() - self.start_time
            self.histogram.labels(**self.labels).observe(duration)

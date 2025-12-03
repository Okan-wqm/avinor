# shared/common/middleware.py
"""
Custom Middleware Classes
"""

import uuid
import time
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """
    Middleware that adds a unique request ID to each request.
    The ID is used for request tracing across services.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get request ID from header or generate new one
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())

        # Attach to request object
        request.request_id = request_id

        # Process request
        response = self.get_response(request)

        # Add to response headers
        response['X-Request-ID'] = request_id

        return response


class LoggingMiddleware:
    """
    Middleware that logs request/response information.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip health check endpoints
        if request.path in ['/health/', '/health/ready/', '/health/live/']:
            return self.get_response(request)

        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': getattr(request, 'request_id', None),
                'method': request.method,
                'path': request.path,
                'user_id': str(getattr(request.user, 'id', None)),
                'ip_address': self.get_client_ip(request),
            }
        )

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        log_method = logger.warning if response.status_code >= 400 else logger.info
        log_method(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'request_id': getattr(request, 'request_id', None),
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'user_id': str(getattr(request.user, 'id', None)),
            }
        )

        # Add timing header
        response['X-Response-Time'] = f"{duration * 1000:.2f}ms"

        return response

    def get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class TenantMiddleware:
    """
    Middleware for multi-tenant support.
    Extracts organization ID from request and makes it available.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get organization ID from header or user
        org_id = request.headers.get('X-Organization-ID')

        if not org_id and hasattr(request, 'user'):
            org_id = getattr(request.user, 'organization_id', None)

        # Attach to request
        request.organization_id = org_id

        return self.get_response(request)


class CORSMiddleware:
    """
    Custom CORS middleware with fine-grained control.
    Note: Usually django-cors-headers is preferred, but this is for custom needs.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = HttpResponse()
            response['Content-Length'] = '0'
            response['Content-Type'] = 'text/plain'
        else:
            response = self.get_response(request)

        # Add CORS headers
        origin = request.headers.get('Origin', '')
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])

        if origin in allowed_origins or '*' in allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = ', '.join([
                'Accept',
                'Accept-Language',
                'Content-Type',
                'Authorization',
                'X-Request-ID',
                'X-Organization-ID',
            ])
            response['Access-Control-Max-Age'] = '86400'

        return response


class SecurityHeadersMiddleware:
    """
    Middleware that adds security headers to responses.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # HSTS for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy (basic)
        response['Content-Security-Policy'] = "default-src 'self'"

        return response


class RateLimitMiddleware:
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.cache = {}
        self.rate_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 100)
        self.window = 60  # 1 minute

    def __call__(self, request: HttpRequest) -> HttpResponse:
        client_ip = self.get_client_ip(request)
        current_time = time.time()

        # Clean old entries
        self.cache = {
            k: v for k, v in self.cache.items()
            if current_time - v['timestamp'] < self.window
        }

        # Check rate limit
        if client_ip in self.cache:
            entry = self.cache[client_ip]
            if entry['count'] >= self.rate_limit:
                response = HttpResponse(
                    '{"error": "Rate limit exceeded"}',
                    content_type='application/json',
                    status=429
                )
                response['Retry-After'] = str(
                    int(self.window - (current_time - entry['timestamp']))
                )
                return response
            entry['count'] += 1
        else:
            self.cache[client_ip] = {
                'count': 1,
                'timestamp': current_time
            }

        response = self.get_response(request)

        # Add rate limit headers
        remaining = self.rate_limit - self.cache[client_ip]['count']
        response['X-RateLimit-Limit'] = str(self.rate_limit)
        response['X-RateLimit-Remaining'] = str(max(0, remaining))

        return response

    def get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class MaintenanceModeMiddleware:
    """
    Middleware to enable maintenance mode.
    Returns 503 for all requests when maintenance mode is enabled.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Check if maintenance mode is enabled
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)

        if maintenance_mode:
            # Allow health checks
            if request.path in ['/health/', '/health/live/']:
                return self.get_response(request)

            # Allow admin access
            admin_ips = getattr(settings, 'MAINTENANCE_ADMIN_IPS', [])
            client_ip = self.get_client_ip(request)
            if client_ip in admin_ips:
                return self.get_response(request)

            return HttpResponse(
                '{"error": "Service is under maintenance"}',
                content_type='application/json',
                status=503
            )

        return self.get_response(request)

    def get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

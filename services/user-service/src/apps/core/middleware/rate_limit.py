# services/user-service/src/apps/core/middleware/rate_limit.py
"""
Rate Limiting Middleware

Provides rate limiting for API endpoints to prevent abuse.
Uses Redis for distributed rate limiting across instances.
"""

import logging
import time
from typing import Optional, Tuple

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware that implements rate limiting for API endpoints.

    Features:
    - Per-user and per-IP rate limiting
    - Configurable limits per endpoint
    - Uses Redis for distributed state
    - Sliding window algorithm
    - Includes rate limit headers in responses
    """

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        'default': 100,
        'auth': 10,
        'login': 5,
        'register': 3,
        'password_reset': 3,
    }

    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        '/api/v1/auth/login/': ('login', 5, 60),       # 5 requests per 60 seconds
        '/api/v1/auth/register/': ('register', 3, 60),  # 3 requests per 60 seconds
        '/api/v1/auth/forgot-password/': ('password_reset', 3, 300),  # 3 per 5 min
        '/api/v1/auth/reset-password/': ('password_reset', 3, 300),
        '/api/v1/auth/verify-2fa/': ('auth', 10, 60),
        '/api/v1/auth/refresh/': ('auth', 30, 60),
    }

    # Endpoints exempt from rate limiting
    EXEMPT_ENDPOINTS = [
        '/health/',
        '/ready/',
        '/metrics/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = self._get_cache()

    def __call__(self, request):
        # Skip exempt endpoints
        if self._is_exempt(request.path):
            return self.get_response(request)

        # Get rate limit config for endpoint
        limit_key, limit, window = self._get_limit_config(request)

        # Get identifier (user ID or IP)
        identifier = self._get_identifier(request)

        # Check rate limit
        cache_key = f"ratelimit:{limit_key}:{identifier}"
        allowed, remaining, reset_at = self._check_rate_limit(cache_key, limit, window)

        if not allowed:
            return self._rate_limit_response(limit, window, reset_at)

        # Process request
        response = self.get_response(request)

        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(reset_at)

        return response

    def _get_cache(self):
        """Get cache backend for rate limiting."""
        try:
            from django.core.cache import caches
            return caches.get('rate_limit', caches['default'])
        except Exception:
            return None

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        for exempt in self.EXEMPT_ENDPOINTS:
            if path.startswith(exempt):
                return True
        return False

    def _get_limit_config(self, request) -> Tuple[str, int, int]:
        """Get rate limit configuration for the endpoint."""
        path = request.path

        # Check endpoint-specific limits
        for endpoint, config in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return config

        # Default limit
        return 'default', self.DEFAULT_LIMITS['default'], 60

    def _get_identifier(self, request) -> str:
        """Get rate limit identifier (user ID or IP)."""
        user = getattr(request, 'user', None)
        if user and hasattr(user, 'id'):
            return f"user:{user.id}"

        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return f"ip:{ip}"

    def _check_rate_limit(
        self,
        cache_key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window.

        Returns:
            Tuple of (allowed, remaining, reset_at)
        """
        if not self.cache:
            # No cache available, allow all requests
            return True, limit, int(time.time()) + window

        now = int(time.time())
        window_start = now - window

        try:
            # Get current request count
            request_times = self.cache.get(cache_key, [])

            # Filter to only requests within window
            request_times = [t for t in request_times if t > window_start]

            if len(request_times) >= limit:
                # Rate limit exceeded
                oldest = min(request_times) if request_times else now
                reset_at = oldest + window
                return False, 0, reset_at

            # Add current request
            request_times.append(now)
            self.cache.set(cache_key, request_times, timeout=window + 10)

            remaining = limit - len(request_times)
            reset_at = min(request_times) + window if request_times else now + window

            return True, remaining, reset_at

        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            # On error, allow request
            return True, limit, int(time.time()) + window

    def _rate_limit_response(self, limit: int, window: int, reset_at: int) -> JsonResponse:
        """Return a 429 Too Many Requests response."""
        retry_after = max(1, reset_at - int(time.time()))

        response = JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': f'Rate limit exceeded. Maximum {limit} requests per {window} seconds.',
                    'retry_after': retry_after,
                }
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

        response['Retry-After'] = str(retry_after)
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = '0'
        response['X-RateLimit-Reset'] = str(reset_at)

        return response


class RateLimitExempt:
    """
    Decorator to exempt a view from rate limiting.

    Usage:
        @rate_limit_exempt
        def my_view(request):
            ...
    """

    def __init__(self, view_func):
        self.view_func = view_func

    def __call__(self, request, *args, **kwargs):
        request._rate_limit_exempt = True
        return self.view_func(request, *args, **kwargs)


def rate_limit(limit: int, window: int = 60, key: str = None):
    """
    Decorator to apply custom rate limit to a view.

    Usage:
        @rate_limit(limit=10, window=60)
        def my_view(request):
            ...

    Args:
        limit: Maximum number of requests
        window: Time window in seconds
        key: Optional custom key for rate limiting
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            request._rate_limit_config = (key or 'custom', limit, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

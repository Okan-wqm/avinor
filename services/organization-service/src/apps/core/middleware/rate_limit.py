# services/organization-service/src/apps/core/middleware/rate_limit.py
"""
Rate Limiting Middleware

Implements rate limiting based on organization subscription plan.
"""

import logging
import time
from typing import Optional, Tuple

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Middleware for API rate limiting based on subscription plan.

    Rate limits are applied per organization and per user.
    Different limits for different subscription tiers.
    """

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        'free': 60,
        'starter': 120,
        'professional': 300,
        'enterprise': 1000,
        'default': 100,
    }

    # Paths exempt from rate limiting
    EXEMPT_PATHS = [
        '/health/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.limits = getattr(settings, 'RATE_LIMITS', self.DEFAULT_LIMITS)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with rate limiting."""
        if not self.enabled or self._is_exempt(request):
            return self.get_response(request)

        # Get rate limit key and limit
        rate_key, limit = self._get_rate_limit_config(request)

        if rate_key and limit:
            # Check rate limit
            allowed, remaining, reset_at = self._check_rate_limit(rate_key, limit)

            if not allowed:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'data': {
                        'limit': limit,
                        'reset_at': reset_at,
                    }
                }, status=429, headers={
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(reset_at),
                    'Retry-After': str(max(0, reset_at - int(time.time()))),
                })

            # Add rate limit headers to response
            response = self.get_response(request)
            response['X-RateLimit-Limit'] = str(limit)
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(reset_at)
            return response

        return self.get_response(request)

    def _is_exempt(self, request: HttpRequest) -> bool:
        """Check if request is exempt from rate limiting."""
        for path in self.EXEMPT_PATHS:
            if request.path.startswith(path):
                return True
        return False

    def _get_rate_limit_config(self, request: HttpRequest) -> Tuple[Optional[str], Optional[int]]:
        """
        Get rate limit key and limit for request.

        Returns:
            Tuple of (rate_key, limit) or (None, None) if not applicable
        """
        # Get organization context
        org_context = getattr(request, 'organization', None)

        if org_context and org_context.organization_id:
            # Organization-level rate limit
            org_id = str(org_context.organization_id)

            # Determine plan tier
            plan_code = self._get_plan_code(org_context)
            limit = self.limits.get(plan_code, self.limits['default'])

            # Key includes organization ID
            rate_key = f"rate_limit:org:{org_id}"

            return rate_key, limit

        # User-level rate limit for non-organization requests
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
            rate_key = f"rate_limit:user:{user_id}"
            return rate_key, self.limits['default']

        # IP-based rate limit for anonymous requests
        client_ip = self._get_client_ip(request)
        rate_key = f"rate_limit:ip:{client_ip}"
        return rate_key, self.limits.get('free', 60)

    def _get_plan_code(self, org_context) -> str:
        """Get plan code from organization context."""
        # Check features for plan info
        if org_context.features:
            plan = org_context.features.get('plan_code')
            if plan:
                return plan.lower()

        # Default based on limits
        max_users = org_context.get_limit('max_users', 0)
        if max_users >= 100:
            return 'enterprise'
        elif max_users >= 25:
            return 'professional'
        elif max_users >= 10:
            return 'starter'
        return 'free'

    def _check_rate_limit(
        self, rate_key: str, limit: int
    ) -> Tuple[bool, int, int]:
        """
        Check and update rate limit counter.

        Uses sliding window algorithm with Redis/cache.

        Returns:
            Tuple of (allowed, remaining, reset_timestamp)
        """
        now = int(time.time())
        window_start = now - 60  # 1-minute window
        window_key = f"{rate_key}:{now // 60}"

        # Get current count
        current = cache.get(window_key, 0)

        if current >= limit:
            # Rate limit exceeded
            reset_at = (now // 60 + 1) * 60
            return False, 0, reset_at

        # Increment counter
        try:
            cache.incr(window_key)
        except ValueError:
            # Key doesn't exist, create it
            cache.set(window_key, 1, timeout=120)

        remaining = max(0, limit - current - 1)
        reset_at = (now // 60 + 1) * 60

        return True, remaining, reset_at

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class ThrottleByAction:
    """
    Per-action throttling for specific expensive operations.

    Usage in views:
        @throttle_action('send_invitation', limit=10, period=3600)
        def send_invitation(self, request):
            ...
    """

    def __init__(self, action: str, limit: int, period: int = 3600):
        """
        Initialize throttle.

        Args:
            action: Action identifier
            limit: Maximum requests allowed
            period: Time window in seconds
        """
        self.action = action
        self.limit = limit
        self.period = period

    def __call__(self, func):
        """Decorator implementation."""
        def wrapper(view_instance, request, *args, **kwargs):
            # Build throttle key
            org_context = getattr(request, 'organization', None)
            if org_context:
                throttle_key = f"throttle:{self.action}:org:{org_context.organization_id}"
            elif hasattr(request, 'user') and request.user.is_authenticated:
                throttle_key = f"throttle:{self.action}:user:{request.user.id}"
            else:
                return func(view_instance, request, *args, **kwargs)

            # Check throttle
            count = cache.get(throttle_key, 0)
            if count >= self.limit:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Action rate limit exceeded. Try again later.',
                    'code': 'ACTION_THROTTLED',
                    'data': {
                        'action': self.action,
                        'limit': self.limit,
                        'period': self.period,
                    }
                }, status=429)

            # Increment counter
            try:
                cache.incr(throttle_key)
            except ValueError:
                cache.set(throttle_key, 1, timeout=self.period)

            return func(view_instance, request, *args, **kwargs)

        return wrapper


# Convenience decorator
def throttle_action(action: str, limit: int, period: int = 3600):
    """Decorator for throttling specific actions."""
    return ThrottleByAction(action, limit, period)

# services/organization-service/src/apps/core/middleware/audit.py
"""
Audit Middleware

Logs API requests for audit trail and debugging purposes.
"""

import json
import logging
import time
import uuid
from typing import Any, Optional

from django.http import HttpRequest, HttpResponse
from django.conf import settings

logger = logging.getLogger('audit')


class AuditMiddleware:
    """
    Middleware for audit logging of API requests.

    Logs:
    - Request method, path, user
    - Response status and timing
    - Organization context
    - Request body (for mutations)
    """

    # Methods that modify data
    MUTATION_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # Paths to exclude from logging
    EXCLUDE_PATHS = [
        '/health/',
        '/admin/jsi18n/',
        '/static/',
    ]

    # Sensitive fields to mask in logs
    SENSITIVE_FIELDS = [
        'password', 'token', 'secret', 'api_key', 'authorization',
        'credit_card', 'cvv', 'ssn',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'AUDIT_LOGGING_ENABLED', True)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with audit logging."""
        if not self.enabled or self._should_exclude(request.path):
            return self.get_response(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.audit_request_id = request_id

        # Start timing
        start_time = time.time()

        # Capture request data for mutations
        request_body = None
        if request.method in self.MUTATION_METHODS:
            request_body = self._capture_request_body(request)

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log audit entry
        self._log_audit_entry(
            request=request,
            response=response,
            request_id=request_id,
            duration_ms=duration_ms,
            request_body=request_body,
        )

        # Add request ID to response headers
        response['X-Request-ID'] = request_id

        return response

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from audit logging."""
        for exclude in self.EXCLUDE_PATHS:
            if path.startswith(exclude):
                return True
        return False

    def _capture_request_body(self, request: HttpRequest) -> Optional[dict]:
        """Capture and sanitize request body."""
        try:
            if request.content_type == 'application/json':
                body = json.loads(request.body.decode('utf-8'))
                return self._mask_sensitive_data(body)
        except Exception:
            pass
        return None

    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive fields in data."""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    masked[key] = '***MASKED***'
                else:
                    masked[key] = self._mask_sensitive_data(value)
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data

    def _log_audit_entry(
        self,
        request: HttpRequest,
        response: HttpResponse,
        request_id: str,
        duration_ms: float,
        request_body: Optional[dict] = None
    ) -> None:
        """Log audit entry."""
        # Get user info
        user_id = None
        user_email = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(getattr(request.user, 'id', None))
            user_email = getattr(request.user, 'email', None)

        # Get organization info
        org_id = None
        if hasattr(request, 'organization') and request.organization:
            org_id = str(request.organization.organization_id)

        # Build audit entry
        audit_entry = {
            'request_id': request_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'user_id': user_id,
            'user_email': user_email,
            'organization_id': org_id,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
        }

        # Add request body for mutations
        if request_body:
            audit_entry['request_body'] = request_body

        # Log level based on status
        if response.status_code >= 500:
            logger.error(json.dumps(audit_entry))
        elif response.status_code >= 400:
            logger.warning(json.dumps(audit_entry))
        else:
            logger.info(json.dumps(audit_entry))

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

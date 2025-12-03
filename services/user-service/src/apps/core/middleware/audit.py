# services/user-service/src/apps/core/middleware/audit.py
"""
Audit Middleware

Automatically logs API requests for audit trail.
Captures request/response details for security and compliance.
"""

import json
import logging
import uuid
from typing import Optional

from django.conf import settings
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware that logs API requests to the audit log.

    Features:
    - Logs all modifying requests (POST, PUT, PATCH, DELETE)
    - Captures request metadata (IP, user agent, etc.)
    - Assigns risk levels based on action sensitivity
    - Excludes configured endpoints from logging
    - Adds request_id for tracing
    """

    # HTTP methods that should be audited
    AUDITED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # Endpoints to exclude from audit logging
    EXCLUDED_ENDPOINTS = [
        '/health/',
        '/ready/',
        '/metrics/',
        '/api/v1/auth/refresh/',
    ]

    # Endpoints with sensitive data that shouldn't be logged
    SENSITIVE_ENDPOINTS = [
        '/api/v1/auth/login/',
        '/api/v1/auth/register/',
        '/api/v1/auth/reset-password/',
        '/api/v1/auth/change-password/',
        '/api/v1/auth/2fa/',
    ]

    # Mapping of endpoints to audit actions
    ACTION_MAP = {
        '/api/v1/auth/login/': 'user.login',
        '/api/v1/auth/logout/': 'user.logout',
        '/api/v1/auth/register/': 'user.register',
        '/api/v1/users/': 'user',
        '/api/v1/roles/': 'role',
        '/api/v1/permissions/': 'permission',
    }

    # High-risk actions
    HIGH_RISK_PATTERNS = [
        'delete',
        'bulk',
        'permission',
        'role/assign',
        'role/revoke',
        'suspend',
        'deactivate',
        '2fa/disable',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        # Add request ID to response headers
        response = self.get_response(request)
        response['X-Request-ID'] = request_id

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Called before the view is executed."""
        # Only audit modifying methods
        if request.method not in self.AUDITED_METHODS:
            return None

        # Skip excluded endpoints
        if self._is_excluded(request.path):
            return None

        # Store request info for post-processing
        request._audit_start_time = timezone.now()
        request._audit_request_body = self._get_safe_request_body(request)

        return None

    def process_response(self, request, response):
        """Called after the view is executed."""
        # Check if we should audit this request
        if not hasattr(request, '_audit_start_time'):
            return response

        if request.method not in self.AUDITED_METHODS:
            return response

        try:
            self._create_audit_log(request, response)
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

        return response

    def _is_excluded(self, path: str) -> bool:
        """Check if path should be excluded from auditing."""
        for excluded in self.EXCLUDED_ENDPOINTS:
            if path.startswith(excluded):
                return True
        return False

    def _is_sensitive(self, path: str) -> bool:
        """Check if endpoint contains sensitive data."""
        for sensitive in self.SENSITIVE_ENDPOINTS:
            if path.startswith(sensitive):
                return True
        return False

    def _get_safe_request_body(self, request) -> Optional[dict]:
        """Get request body with sensitive data redacted."""
        if self._is_sensitive(request.path):
            return {'_redacted': True}

        try:
            if request.content_type == 'application/json':
                body = json.loads(request.body.decode('utf-8'))
                return self._redact_sensitive_fields(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        return None

    def _redact_sensitive_fields(self, data: dict) -> dict:
        """Redact sensitive fields from data."""
        sensitive_fields = [
            'password', 'new_password', 'old_password', 'current_password',
            'token', 'access_token', 'refresh_token', 'secret', 'otp',
            'backup_code', 'credit_card', 'ssn', 'api_key',
        ]

        redacted = {}
        for key, value in data.items():
            if any(sf in key.lower() for sf in sensitive_fields):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_fields(value)
            else:
                redacted[key] = value

        return redacted

    def _get_action(self, request) -> str:
        """Determine the audit action from the request."""
        path = request.path

        # Check action map first
        for endpoint, action in self.ACTION_MAP.items():
            if path.startswith(endpoint):
                method_suffix = {
                    'POST': '.create',
                    'PUT': '.update',
                    'PATCH': '.update',
                    'DELETE': '.delete',
                }.get(request.method, '')
                return f"{action}{method_suffix}"

        # Fall back to method + path
        return f"{request.method.lower()}:{path}"

    def _get_risk_level(self, request, action: str) -> str:
        """Determine risk level based on action."""
        path_lower = request.path.lower()
        action_lower = action.lower()

        # Check for high-risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if pattern in path_lower or pattern in action_lower:
                return AuditLog.RiskLevel.HIGH

        # Method-based risk levels
        if request.method == 'DELETE':
            return AuditLog.RiskLevel.HIGH
        elif request.method in ['PUT', 'PATCH']:
            return AuditLog.RiskLevel.MEDIUM
        elif request.method == 'POST':
            return AuditLog.RiskLevel.LOW

        return AuditLog.RiskLevel.LOW

    def _get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _create_audit_log(self, request, response) -> None:
        """Create an audit log entry."""
        user = getattr(request, 'user', None)
        if not user or not hasattr(user, 'id'):
            user = None

        action = self._get_action(request)
        risk_level = self._get_risk_level(request, action)

        # Determine entity info from path
        entity_type, entity_id = self._extract_entity_info(request)

        # Get response data if available
        response_data = None
        if hasattr(response, 'data'):
            response_data = self._redact_sensitive_fields(
                response.data if isinstance(response.data, dict) else {}
            )

        # Create audit log
        AuditLog.objects.create(
            organization_id=getattr(user, 'organization_id', None) if user else None,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_name=getattr(user, 'full_name', None) if user else None,
            impersonated_by=getattr(request, 'impersonated_by', None),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=None,  # Could be populated by view
            new_values=response_data,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            request_id=getattr(request, 'request_id', None),
            session_id=str(getattr(request, 'session_info', {}).get('id', '')) or None,
            risk_level=risk_level,
            metadata={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': (
                    (timezone.now() - request._audit_start_time).total_seconds() * 1000
                    if hasattr(request, '_audit_start_time') else None
                ),
            }
        )

    def _extract_entity_info(self, request) -> tuple:
        """Extract entity type and ID from request path."""
        path_parts = request.path.strip('/').split('/')

        entity_type = None
        entity_id = None

        # Try to find entity type and ID from URL pattern
        # Pattern: /api/v1/{entity_type}/{entity_id}/...
        if len(path_parts) >= 3:
            entity_type = path_parts[2].rstrip('s')  # Remove plural 's'

        if len(path_parts) >= 4:
            potential_id = path_parts[3]
            try:
                # Validate UUID
                uuid.UUID(potential_id)
                entity_id = potential_id
            except ValueError:
                pass

        return entity_type, entity_id

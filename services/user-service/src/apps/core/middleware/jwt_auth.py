# services/user-service/src/apps/core/middleware/jwt_auth.py
"""
JWT Authentication Middleware

Provides JWT-based authentication for the User Service API.
Validates access tokens and attaches user info to requests.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

from apps.core.models import User, UserSession

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware that authenticates requests using JWT tokens.

    Features:
    - Validates JWT access tokens from Authorization header
    - Attaches user and session info to request
    - Supports token blacklist checking
    - Handles expired and invalid tokens gracefully
    - Exempts configured public endpoints
    """

    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        '/api/v1/auth/login/',
        '/api/v1/auth/register/',
        '/api/v1/auth/forgot-password/',
        '/api/v1/auth/reset-password/',
        '/api/v1/auth/verify-email/',
        '/api/v1/auth/resend-verification/',
        '/api/v1/auth/refresh/',
        '/api/v1/auth/verify-2fa/',
        '/health/',
        '/ready/',
        '/metrics/',
    ]

    # Endpoints that allow optional authentication
    OPTIONAL_AUTH_ENDPOINTS = [
        '/api/v1/',  # API root
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
        self.jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

    def __call__(self, request):
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.path):
            return self.get_response(request)

        # Check for Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            if self._is_optional_auth_endpoint(request.path):
                return self.get_response(request)
            return self._unauthorized_response('Authorization header missing')

        # Parse Bearer token
        token = self._extract_token(auth_header)
        if not token:
            return self._unauthorized_response('Invalid authorization header format')

        # Validate token and get user
        user, session, error = self._validate_token(token)
        if error:
            return self._unauthorized_response(error)

        # Attach user and session to request
        request.user = user
        request.auth_token = token
        request.session_info = session
        request.jwt_payload = self._decode_token(token)

        # Update session last activity
        if session:
            self._update_session_activity(session, request)

        return self.get_response(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the endpoint is public (no auth required)."""
        for endpoint in self.PUBLIC_ENDPOINTS:
            if path.startswith(endpoint) or path == endpoint.rstrip('/'):
                return True
        return False

    def _is_optional_auth_endpoint(self, path: str) -> bool:
        """Check if the endpoint allows optional authentication."""
        for endpoint in self.OPTIONAL_AUTH_ENDPOINTS:
            if path.startswith(endpoint):
                return True
        return False

    def _extract_token(self, auth_header: str) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        parts = auth_header.split()

        if len(parts) != 2:
            return None

        scheme, token = parts

        if scheme.lower() != 'bearer':
            return None

        return token

    def _decode_token(self, token: str) -> Optional[dict]:
        """Decode JWT token without validation."""
        try:
            return jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={'verify_exp': False}
            )
        except jwt.DecodeError:
            return None

    def _validate_token(self, token: str) -> Tuple[Optional[User], Optional[UserSession], Optional[str]]:
        """
        Validate JWT token and return user and session.

        Returns:
            Tuple of (user, session, error_message)
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            return None, None, 'Token has expired'
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None, None, 'Invalid token'

        # Validate token type
        if payload.get('type') != 'access':
            return None, None, 'Invalid token type'

        # Get user
        user_id = payload.get('user_id')
        if not user_id:
            return None, None, 'Invalid token payload'

        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            return None, None, 'User not found'

        # Check user status
        if user.status != 'active':
            return None, None, f'Account is {user.status}'

        # Check if email is verified (if required)
        if getattr(settings, 'REQUIRE_EMAIL_VERIFICATION', True):
            if not user.email_verified:
                return None, None, 'Email not verified'

        # Get session if session_id in token
        session = None
        session_id = payload.get('session_id')
        if session_id:
            try:
                session = UserSession.objects.get(
                    id=session_id,
                    user=user,
                    is_active=True,
                    revoked_at__isnull=True
                )

                # Check if session is expired
                if session.expires_at and session.expires_at < timezone.now():
                    session.is_active = False
                    session.save(update_fields=['is_active'])
                    return None, None, 'Session has expired'

            except UserSession.DoesNotExist:
                return None, None, 'Session not found or revoked'

        # Check token blacklist (if implemented)
        if self._is_token_blacklisted(payload.get('jti')):
            return None, None, 'Token has been revoked'

        return user, session, None

    def _is_token_blacklisted(self, jti: Optional[str]) -> bool:
        """Check if token is blacklisted."""
        if not jti:
            return False

        # Check Redis cache for blacklisted token
        try:
            from django.core.cache import cache
            return cache.get(f'blacklisted_token:{jti}') is not None
        except Exception:
            return False

    def _update_session_activity(self, session: UserSession, request) -> None:
        """Update session's last activity timestamp."""
        try:
            now = timezone.now()
            # Only update if more than 1 minute since last update
            if not session.last_activity or (now - session.last_activity).seconds > 60:
                session.last_activity = now
                session.save(update_fields=['last_activity'])
        except Exception as e:
            logger.warning(f"Failed to update session activity: {e}")

    def _unauthorized_response(self, message: str) -> JsonResponse:
        """Return a 401 Unauthorized response."""
        return JsonResponse(
            {
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': message,
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )


class JWTAuthentication:
    """
    DRF Authentication class for JWT tokens.

    Use this in your ViewSet authentication_classes for DRF integration.
    """

    def __init__(self):
        self.jwt_secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
        self.jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

    def authenticate(self, request):
        """
        Authenticate the request using JWT token.

        Returns:
            Tuple of (user, auth_info) or None
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid token')

        if payload.get('type') != 'access':
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid token type')

        user_id = payload.get('user_id')
        if not user_id:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid token payload')

        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('User not found')

        if user.status != 'active':
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed(f'Account is {user.status}')

        return (user, payload)

    def authenticate_header(self, request):
        """Return the WWW-Authenticate header value."""
        return 'Bearer'

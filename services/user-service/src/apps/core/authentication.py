# services/user-service/src/apps/core/authentication.py
"""
DRF Authentication Backends

Custom authentication classes for Django REST Framework.
"""

import logging
from typing import Optional, Tuple

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from apps.core.models import User, UserSession

logger = logging.getLogger(__name__)


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT Authentication for Django REST Framework.

    Validates JWT tokens from the Authorization header and returns
    the authenticated user.

    Usage in ViewSet:
        authentication_classes = [JWTAuthentication]
    """

    keyword = 'Bearer'

    def __init__(self):
        self.jwt_secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
        self.jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

    def authenticate(self, request) -> Optional[Tuple[User, dict]]:
        """
        Authenticate the request using JWT token.

        Returns:
            Tuple of (user, auth_info) or None if no auth provided
        """
        auth_header = authentication.get_authorization_header(request)

        if not auth_header:
            return None

        auth_header = auth_header.decode('utf-8')
        auth_parts = auth_header.split()

        if len(auth_parts) != 2:
            return None

        scheme, token = auth_parts

        if scheme.lower() != self.keyword.lower():
            return None

        return self._authenticate_token(token, request)

    def _authenticate_token(self, token: str, request) -> Tuple[User, dict]:
        """Validate JWT token and return user."""
        # Decode token
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise exceptions.AuthenticationFailed('Invalid token')

        # Validate token type
        if payload.get('type') != 'access':
            raise exceptions.AuthenticationFailed('Invalid token type')

        # Get user
        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Invalid token payload')

        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        # Check user status
        if user.status != 'active':
            raise exceptions.AuthenticationFailed(f'Account is {user.status}')

        # Check email verification if required
        if getattr(settings, 'REQUIRE_EMAIL_VERIFICATION', True):
            if not user.email_verified:
                raise exceptions.AuthenticationFailed('Email not verified')

        # Validate session if session_id in token
        session = None
        session_id = payload.get('session_id')
        if session_id:
            session = self._validate_session(session_id, user)
            if session:
                request.session_info = session

        # Check token blacklist
        if self._is_token_blacklisted(payload.get('jti')):
            raise exceptions.AuthenticationFailed('Token has been revoked')

        # Store token payload in request
        request.jwt_payload = payload
        request.auth_token = token

        return (user, payload)

    def _validate_session(self, session_id: str, user: User) -> Optional[UserSession]:
        """Validate user session."""
        from django.utils import timezone

        try:
            session = UserSession.objects.get(
                id=session_id,
                user=user,
                is_active=True,
                revoked_at__isnull=True
            )

            # Check expiration
            if session.expires_at and session.expires_at < timezone.now():
                session.is_active = False
                session.save(update_fields=['is_active'])
                raise exceptions.AuthenticationFailed('Session has expired')

            return session

        except UserSession.DoesNotExist:
            raise exceptions.AuthenticationFailed('Session not found or revoked')

    def _is_token_blacklisted(self, jti: Optional[str]) -> bool:
        """Check if token is blacklisted."""
        if not jti:
            return False

        try:
            from django.core.cache import cache
            return cache.get(f'blacklisted_token:{jti}') is not None
        except Exception:
            return False

    def authenticate_header(self, request) -> str:
        """Return the WWW-Authenticate header value."""
        return self.keyword


class ServiceAuthentication(authentication.BaseAuthentication):
    """
    Service-to-Service Authentication.

    Validates internal service tokens for microservice communication.
    """

    keyword = 'Service'

    def __init__(self):
        self.service_secret = getattr(settings, 'SERVICE_SECRET_KEY', None)

    def authenticate(self, request) -> Optional[Tuple[None, dict]]:
        """
        Authenticate service-to-service requests.

        Returns:
            Tuple of (None, service_info) or None if no auth provided
        """
        if not self.service_secret:
            return None

        auth_header = authentication.get_authorization_header(request)

        if not auth_header:
            return None

        auth_header = auth_header.decode('utf-8')
        auth_parts = auth_header.split()

        if len(auth_parts) != 2:
            return None

        scheme, token = auth_parts

        if scheme.lower() != self.keyword.lower():
            return None

        return self._authenticate_service(token)

    def _authenticate_service(self, token: str) -> Tuple[None, dict]:
        """Validate service token."""
        try:
            payload = jwt.decode(
                token,
                self.service_secret,
                algorithms=['HS256']
            )
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid service token')

        if payload.get('type') != 'service':
            raise exceptions.AuthenticationFailed('Invalid token type')

        service_name = payload.get('service')
        if not service_name:
            raise exceptions.AuthenticationFailed('Invalid service token')

        return (None, {'service': service_name, 'payload': payload})

    def authenticate_header(self, request) -> str:
        """Return the WWW-Authenticate header value."""
        return self.keyword


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key Authentication.

    Validates API keys for external integrations.
    """

    keyword = 'ApiKey'

    def authenticate(self, request) -> Optional[Tuple[User, dict]]:
        """
        Authenticate using API key.

        Returns:
            Tuple of (user, api_key_info) or None if no auth provided
        """
        # Check header first
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            # Check Authorization header
            auth_header = authentication.get_authorization_header(request)
            if auth_header:
                auth_header = auth_header.decode('utf-8')
                auth_parts = auth_header.split()
                if len(auth_parts) == 2 and auth_parts[0].lower() == self.keyword.lower():
                    api_key = auth_parts[1]

        if not api_key:
            return None

        return self._authenticate_api_key(api_key)

    def _authenticate_api_key(self, api_key: str) -> Tuple[User, dict]:
        """Validate API key and return associated user."""
        from django.core.cache import cache

        # Check cache first
        cache_key = f'api_key:{api_key[:16]}'
        cached = cache.get(cache_key)

        if cached:
            try:
                user = User.objects.get(id=cached['user_id'])
                return (user, cached)
            except User.DoesNotExist:
                cache.delete(cache_key)

        # Look up API key in database
        # Note: You would need an APIKey model for this
        # This is a placeholder implementation
        raise exceptions.AuthenticationFailed('Invalid API key')

    def authenticate_header(self, request) -> str:
        """Return the WWW-Authenticate header value."""
        return self.keyword

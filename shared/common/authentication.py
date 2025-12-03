# shared/common/authentication.py
"""
JWT Authentication and Service-to-Service Authentication
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.request import Request

logger = logging.getLogger(__name__)


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT Token Authentication for API requests.
    Uses RS256 algorithm with public/private key pair.
    """

    keyword = 'Bearer'

    def authenticate(self, request: Request) -> Optional[Tuple[Any, Dict]]:
        auth_header = authentication.get_authorization_header(request)

        if not auth_header:
            return None

        try:
            auth_parts = auth_header.decode('utf-8').split()
        except UnicodeDecodeError:
            raise exceptions.AuthenticationFailed('Invalid token header encoding')

        if len(auth_parts) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header format')

        if auth_parts[0].lower() != self.keyword.lower():
            return None

        token = auth_parts[1]
        return self.authenticate_token(token)

    def authenticate_token(self, token: str) -> Tuple[Any, Dict]:
        """Validate and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SETTINGS['VERIFYING_KEY'],
                algorithms=[settings.JWT_SETTINGS['ALGORITHM']],
                issuer=settings.JWT_SETTINGS['ISSUER'],
                options={
                    'require': ['exp', 'iat', 'sub', 'iss'],
                    'verify_exp': True,
                    'verify_iat': True,
                    'verify_iss': True,
                }
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise exceptions.AuthenticationFailed('Invalid token')

        user = self._get_user_from_payload(payload)
        return (user, payload)

    def _get_user_from_payload(self, payload: Dict) -> 'TokenUser':
        """Create a user object from JWT payload"""
        return TokenUser(payload)

    def authenticate_header(self, request: Request) -> str:
        return self.keyword


class ServiceAuthentication(authentication.BaseAuthentication):
    """
    Service-to-Service Authentication using shared secret token.
    Used for internal microservice communication.
    """

    keyword = 'Service'

    def authenticate(self, request: Request) -> Optional[Tuple[Any, Dict]]:
        service_token = request.headers.get('X-Service-Auth')

        if not service_token:
            return None

        if service_token != settings.SERVICE_AUTH_TOKEN:
            raise exceptions.AuthenticationFailed('Invalid service token')

        source_service = request.headers.get('X-Source-Service', 'unknown')

        return (ServiceUser(source_service), {'service': source_service})

    def authenticate_header(self, request: Request) -> str:
        return self.keyword


class TokenUser:
    """
    User object created from JWT token payload.
    Provides a consistent interface for accessing user data.
    """

    def __init__(self, payload: Dict):
        self.payload = payload
        self.id = payload.get('sub')
        self.user_id = payload.get('sub')
        self.email = payload.get('email')
        self.username = payload.get('username')
        self.organization_id = payload.get('organization_id')
        self.roles = payload.get('roles', [])
        self.permissions = payload.get('permissions', [])
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False

    def __str__(self) -> str:
        return f"TokenUser({self.email})"

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions or 'admin' in self.roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        return bool(set(self.roles) & set(roles))

    def has_all_roles(self, roles: list) -> bool:
        """Check if user has all of the specified roles"""
        return set(roles).issubset(set(self.roles))


class ServiceUser:
    """
    User object for service-to-service authentication.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.id = f"service:{service_name}"
        self.is_service = True
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False

    def __str__(self) -> str:
        return f"ServiceUser({self.service_name})"


class JWTTokenGenerator:
    """
    Generate JWT tokens for authentication.
    """

    @staticmethod
    def generate_access_token(
        user_id: str,
        email: str,
        username: str,
        organization_id: str,
        roles: list,
        permissions: list,
        extra_claims: Dict = None
    ) -> str:
        """Generate an access token"""
        now = datetime.utcnow()

        payload = {
            'sub': user_id,
            'email': email,
            'username': username,
            'organization_id': organization_id,
            'roles': roles,
            'permissions': permissions,
            'iat': now,
            'exp': now + settings.JWT_SETTINGS['ACCESS_TOKEN_LIFETIME'],
            'iss': settings.JWT_SETTINGS['ISSUER'],
            'type': 'access',
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(
            payload,
            settings.JWT_SETTINGS['SIGNING_KEY'],
            algorithm=settings.JWT_SETTINGS['ALGORITHM']
        )

    @staticmethod
    def generate_refresh_token(user_id: str, token_id: str = None) -> str:
        """Generate a refresh token"""
        import uuid
        now = datetime.utcnow()

        payload = {
            'sub': user_id,
            'jti': token_id or str(uuid.uuid4()),
            'iat': now,
            'exp': now + settings.JWT_SETTINGS['REFRESH_TOKEN_LIFETIME'],
            'iss': settings.JWT_SETTINGS['ISSUER'],
            'type': 'refresh',
        }

        return jwt.encode(
            payload,
            settings.JWT_SETTINGS['SIGNING_KEY'],
            algorithm=settings.JWT_SETTINGS['ALGORITHM']
        )

    @staticmethod
    def decode_token(token: str, verify_exp: bool = True) -> Dict:
        """Decode and verify a token"""
        return jwt.decode(
            token,
            settings.JWT_SETTINGS['VERIFYING_KEY'],
            algorithms=[settings.JWT_SETTINGS['ALGORITHM']],
            issuer=settings.JWT_SETTINGS['ISSUER'],
            options={'verify_exp': verify_exp}
        )

    @staticmethod
    def refresh_access_token(refresh_token: str, user_data: Dict) -> Tuple[str, str]:
        """
        Generate new access and refresh tokens using a valid refresh token.
        Returns: (new_access_token, new_refresh_token)
        """
        payload = JWTTokenGenerator.decode_token(refresh_token)

        if payload.get('type') != 'refresh':
            raise ValueError('Invalid token type')

        new_access_token = JWTTokenGenerator.generate_access_token(
            user_id=payload['sub'],
            email=user_data['email'],
            username=user_data['username'],
            organization_id=user_data['organization_id'],
            roles=user_data['roles'],
            permissions=user_data['permissions']
        )

        new_refresh_token = JWTTokenGenerator.generate_refresh_token(
            user_id=payload['sub']
        )

        return new_access_token, new_refresh_token

# services/user-service/src/apps/core/services/__init__.py
"""
User Service - Business Logic Layer

This module exports all service classes for the User Service including:
- AuthService: Authentication and token management
- UserService: User CRUD and management
- PermissionService: RBAC/ABAC authorization
"""

from .auth_service import (
    AuthService,
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountInactiveError,
    TwoFactorRequiredError,
    InvalidTokenError,
    PasswordPolicyError,
)

from .user_service import (
    UserService,
    UserServiceError,
    UserNotFoundError,
    UserExistsError,
)

from .permission_service import (
    PermissionService,
    PermissionDeniedError,
    RoleNotFoundError,
)

__all__ = [
    # Auth Service
    'AuthService',
    'AuthenticationError',
    'InvalidCredentialsError',
    'AccountLockedError',
    'AccountInactiveError',
    'TwoFactorRequiredError',
    'InvalidTokenError',
    'PasswordPolicyError',

    # User Service
    'UserService',
    'UserServiceError',
    'UserNotFoundError',
    'UserExistsError',

    # Permission Service
    'PermissionService',
    'PermissionDeniedError',
    'RoleNotFoundError',
]

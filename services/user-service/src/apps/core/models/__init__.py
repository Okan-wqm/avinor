# services/user-service/src/apps/core/models/__init__.py
"""
User Service Models

This module exports all models for the User Service including:
- User management (User, UserSession)
- RBAC (Role, Permission, RolePermission, UserRole)
- Token management (RefreshToken, PasswordResetToken, EmailVerificationToken)
- Audit logging (AuditLog)
- Event outbox (EventOutbox)
"""

from .user import User, UserSession
from .role import Role, Permission, RolePermission, UserRole, AuditLog
from .token import RefreshToken, PasswordResetToken, EmailVerificationToken
from .outbox import EventOutbox

__all__ = [
    # User models
    'User',
    'UserSession',

    # RBAC models
    'Role',
    'Permission',
    'RolePermission',
    'UserRole',

    # Token models
    'RefreshToken',
    'PasswordResetToken',
    'EmailVerificationToken',

    # Audit
    'AuditLog',

    # Event outbox
    'EventOutbox',
]

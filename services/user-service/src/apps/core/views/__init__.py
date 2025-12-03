# services/user-service/src/apps/core/views/__init__.py
"""
User Service Views

This module exports all ViewSets for the User Service API.
"""

from .user import UserViewSet
from .auth import AuthViewSet
from .role import RoleViewSet, PermissionViewSet, AuditLogViewSet

__all__ = [
    'UserViewSet',
    'AuthViewSet',
    'RoleViewSet',
    'PermissionViewSet',
    'AuditLogViewSet',
]

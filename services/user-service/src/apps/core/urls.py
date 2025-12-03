# services/user-service/src/apps/core/urls.py
"""
URL configuration for User Service API

Endpoints:
    /api/v1/users/          - User management (CRUD, search, bulk operations)
    /api/v1/auth/           - Authentication (login, register, 2FA, sessions)
    /api/v1/roles/          - Role management (CRUD, permissions, assignments)
    /api/v1/permissions/    - Permission management (CRUD, modules)
    /api/v1/audit-logs/     - Audit log viewing (read-only)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.core.views import (
    UserViewSet,
    AuthViewSet,
    RoleViewSet,
    PermissionViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]

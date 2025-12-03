# services/user-service/src/apps/core/permissions.py
"""
DRF Permission Classes

Custom permission classes for Django REST Framework.
Integrates with the RBAC/ABAC permission system.
"""

import logging
from typing import Optional

from django.conf import settings
from rest_framework import permissions

from apps.core.services import PermissionService

logger = logging.getLogger(__name__)


class IsAuthenticated(permissions.BasePermission):
    """
    Permission class that requires authentication.

    Same as DRF's IsAuthenticated but with custom error messages.
    """

    message = 'Authentication required'

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and
            hasattr(request.user, 'id') and
            request.user.status == 'active'
        )


class IsEmailVerified(permissions.BasePermission):
    """
    Permission class that requires email verification.
    """

    message = 'Email verification required'

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False
        return request.user.email_verified


class HasPermission(permissions.BasePermission):
    """
    Permission class that checks for a specific permission.

    Usage:
        permission_classes = [HasPermission]
        required_permissions = ['users.read']

    Or in the view:
        def get_permissions(self):
            if self.action == 'create':
                return [HasPermission('users.create')]
            return [HasPermission('users.read')]
    """

    message = 'You do not have permission to perform this action'

    def __init__(self, permission_code: Optional[str] = None):
        self.permission_code = permission_code
        self._permission_service = None

    @property
    def permission_service(self) -> PermissionService:
        if self._permission_service is None:
            self._permission_service = PermissionService()
        return self._permission_service

    def has_permission(self, request, view) -> bool:
        # Must be authenticated
        if not request.user or not hasattr(request.user, 'id'):
            return False

        # Get permission code
        permission_code = self._get_permission_code(request, view)
        if not permission_code:
            return True  # No permission required

        # Build context for ABAC
        context = self._build_context(request, view)

        # Check permission
        return self.permission_service.has_permission(
            user=request.user,
            permission_code=permission_code,
            context=context
        )

    def has_object_permission(self, request, view, obj) -> bool:
        """Check object-level permission."""
        if not request.user or not hasattr(request.user, 'id'):
            return False

        permission_code = self._get_permission_code(request, view)
        if not permission_code:
            return True

        # Build context with object info
        context = self._build_context(request, view, obj)

        return self.permission_service.has_permission(
            user=request.user,
            permission_code=permission_code,
            context=context
        )

    def _get_permission_code(self, request, view) -> Optional[str]:
        """Get the required permission code."""
        # Use instance permission if set
        if self.permission_code:
            return self.permission_code

        # Check view for permission mapping
        if hasattr(view, 'permission_map'):
            action = getattr(view, 'action', None) or request.method.lower()
            return view.permission_map.get(action)

        # Check view for required_permissions
        if hasattr(view, 'required_permissions'):
            perms = view.required_permissions
            if isinstance(perms, str):
                return perms
            elif isinstance(perms, list) and len(perms) > 0:
                return perms[0]

        return None

    def _build_context(self, request, view, obj=None) -> dict:
        """Build ABAC context for permission checking."""
        context = {
            'request': request,
            'view': view,
            'method': request.method,
            'action': getattr(view, 'action', None),
            'ip_address': self._get_client_ip(request),
        }

        if obj:
            context['object'] = obj
            context['object_id'] = str(getattr(obj, 'id', None))
            context['object_type'] = obj.__class__.__name__

            # Check if object belongs to same organization
            if hasattr(obj, 'organization_id') and hasattr(request.user, 'organization_id'):
                context['same_organization'] = (
                    obj.organization_id == request.user.organization_id
                )

        return context

    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class HasAnyPermission(permissions.BasePermission):
    """
    Permission class that requires any of the specified permissions.

    Usage:
        class MyViewSet(ViewSet):
            permission_classes = [HasAnyPermission]
            required_permissions = ['users.read', 'users.list']
    """

    message = 'You do not have permission to perform this action'

    def __init__(self, *permission_codes):
        self.permission_codes = permission_codes
        self._permission_service = None

    @property
    def permission_service(self) -> PermissionService:
        if self._permission_service is None:
            self._permission_service = PermissionService()
        return self._permission_service

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False

        # Get permission codes
        permission_codes = self._get_permission_codes(view)
        if not permission_codes:
            return True

        context = {'request': request, 'view': view}

        # Check if user has any of the permissions
        for code in permission_codes:
            if self.permission_service.has_permission(
                user=request.user,
                permission_code=code,
                context=context
            ):
                return True

        return False

    def _get_permission_codes(self, view) -> list:
        if self.permission_codes:
            return list(self.permission_codes)

        if hasattr(view, 'required_permissions'):
            perms = view.required_permissions
            if isinstance(perms, list):
                return perms
            return [perms]

        return []


class HasAllPermissions(permissions.BasePermission):
    """
    Permission class that requires all of the specified permissions.

    Usage:
        class MyViewSet(ViewSet):
            permission_classes = [HasAllPermissions]
            required_permissions = ['users.read', 'users.update']
    """

    message = 'You do not have all required permissions'

    def __init__(self, *permission_codes):
        self.permission_codes = permission_codes
        self._permission_service = None

    @property
    def permission_service(self) -> PermissionService:
        if self._permission_service is None:
            self._permission_service = PermissionService()
        return self._permission_service

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False

        permission_codes = self._get_permission_codes(view)
        if not permission_codes:
            return True

        context = {'request': request, 'view': view}

        # Check if user has all permissions
        for code in permission_codes:
            if not self.permission_service.has_permission(
                user=request.user,
                permission_code=code,
                context=context
            ):
                return False

        return True

    def _get_permission_codes(self, view) -> list:
        if self.permission_codes:
            return list(self.permission_codes)

        if hasattr(view, 'required_permissions'):
            perms = view.required_permissions
            if isinstance(perms, list):
                return perms
            return [perms]

        return []


class IsOwnerOrHasPermission(permissions.BasePermission):
    """
    Permission class that allows access if user owns the object
    or has the required permission.

    Usage:
        class UserViewSet(ViewSet):
            permission_classes = [IsOwnerOrHasPermission]
            required_permissions = ['users.read']
            owner_field = 'id'  # or 'user', 'created_by', etc.
    """

    message = 'You do not have permission to access this resource'

    def __init__(self, permission_code: Optional[str] = None, owner_field: str = 'id'):
        self.permission_code = permission_code
        self.owner_field = owner_field
        self._permission_service = None

    @property
    def permission_service(self) -> PermissionService:
        if self._permission_service is None:
            self._permission_service = PermissionService()
        return self._permission_service

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False

        # Check if user owns the object
        owner_field = getattr(view, 'owner_field', self.owner_field)
        owner_value = getattr(obj, owner_field, None)

        if owner_value:
            # Handle both direct ID and related object
            if hasattr(owner_value, 'id'):
                owner_id = owner_value.id
            else:
                owner_id = owner_value

            if str(owner_id) == str(request.user.id):
                return True

        # Check permission
        permission_code = self.permission_code
        if not permission_code and hasattr(view, 'required_permissions'):
            perms = view.required_permissions
            permission_code = perms[0] if isinstance(perms, list) else perms

        if permission_code:
            return self.permission_service.has_permission(
                user=request.user,
                permission_code=permission_code,
                context={'object': obj}
            )

        return False


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class that only allows super administrators.
    """

    message = 'Super administrator access required'

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False
        return request.user.is_superuser


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission class that allows organization administrators.
    """

    message = 'Organization administrator access required'

    def __init__(self):
        self._permission_service = None

    @property
    def permission_service(self) -> PermissionService:
        if self._permission_service is None:
            self._permission_service = PermissionService()
        return self._permission_service

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False

        # Super admin always has access
        if request.user.is_superuser:
            return True

        # Check for org admin role
        return self.permission_service.has_permission(
            user=request.user,
            permission_code='organization.admin'
        )


class Requires2FA(permissions.BasePermission):
    """
    Permission class that requires 2FA verification for the current session.
    """

    message = 'Two-factor authentication required for this action'

    def has_permission(self, request, view) -> bool:
        if not request.user or not hasattr(request.user, 'id'):
            return False

        # Check if session has 2FA verified
        session_info = getattr(request, 'session_info', None)
        if session_info and hasattr(session_info, 'two_factor_verified'):
            return session_info.two_factor_verified

        # Check JWT payload
        jwt_payload = getattr(request, 'jwt_payload', {})
        return jwt_payload.get('two_factor_verified', False)


class ReadOnly(permissions.BasePermission):
    """
    Permission class that only allows read operations.
    """

    message = 'Write operations not allowed'

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view) -> bool:
        return request.method in self.SAFE_METHODS

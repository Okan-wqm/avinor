# shared/common/permissions.py
"""
Custom Permission Classes for Role-Based Access Control (RBAC)
"""

from typing import List, Optional
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
import logging

logger = logging.getLogger(__name__)


class BasePermission(permissions.BasePermission):
    """Base permission class with utility methods"""

    def get_user_permissions(self, request: Request) -> List[str]:
        """Get permissions from user object or JWT payload"""
        if hasattr(request.user, 'permissions'):
            return request.user.permissions
        if hasattr(request, 'auth') and isinstance(request.auth, dict):
            return request.auth.get('permissions', [])
        return []

    def get_user_roles(self, request: Request) -> List[str]:
        """Get roles from user object or JWT payload"""
        if hasattr(request.user, 'roles'):
            return request.user.roles
        if hasattr(request, 'auth') and isinstance(request.auth, dict):
            return request.auth.get('roles', [])
        return []

    def get_organization_id(self, request: Request) -> Optional[str]:
        """Get organization ID from user or header"""
        if hasattr(request.user, 'organization_id'):
            return request.user.organization_id
        return request.headers.get('X-Organization-ID')


class IsAuthenticated(BasePermission):
    """Verify that user is authenticated"""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user and
            hasattr(request.user, 'is_authenticated') and
            request.user.is_authenticated
        )


class IsServiceRequest(BasePermission):
    """Allow only service-to-service requests"""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            hasattr(request.user, 'is_service') and
            request.user.is_service
        )


class HasRole(BasePermission):
    """Check if user has required role(s)"""

    required_roles: List[str] = []
    require_all: bool = False  # If True, user must have ALL roles

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        user_roles = self.get_user_roles(request)

        if self.require_all:
            return set(self.required_roles).issubset(set(user_roles))
        return bool(set(self.required_roles) & set(user_roles))


class HasPermission(BasePermission):
    """Check if user has required permission(s)"""

    required_permissions: List[str] = []
    require_all: bool = True  # If True, user must have ALL permissions

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        user_permissions = self.get_user_permissions(request)

        # Admin has all permissions
        if 'admin' in self.get_user_roles(request):
            return True

        if self.require_all:
            return set(self.required_permissions).issubset(set(user_permissions))
        return bool(set(self.required_permissions) & set(user_permissions))


class IsSameOrganization(BasePermission):
    """Verify user belongs to the same organization as the resource"""

    organization_field: str = 'organization_id'

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        user_org = self.get_organization_id(request)
        if not user_org:
            return False

        obj_org = getattr(obj, self.organization_field, None)
        return str(user_org) == str(obj_org)


class IsOwner(BasePermission):
    """Verify user is the owner of the resource"""

    owner_field: str = 'user_id'

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        owner_id = getattr(obj, self.owner_field, None)
        return str(request.user.id) == str(owner_id)


class IsOwnerOrReadOnly(BasePermission):
    """
    Allow read access to any authenticated user,
    but write access only to the owner.
    """

    owner_field: str = 'user_id'

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        owner_id = getattr(obj, self.owner_field, None)
        return str(request.user.id) == str(owner_id)


# =============================================================================
# ROLE-SPECIFIC PERMISSIONS
# =============================================================================

class IsAdmin(HasRole):
    """Only system administrators"""
    required_roles = ['admin', 'system_admin']


class IsOrganizationAdmin(HasRole):
    """Organization administrators"""
    required_roles = ['admin', 'organization_admin', 'system_admin']


class IsInstructor(HasRole):
    """Flight instructors"""
    required_roles = ['instructor', 'chief_instructor', 'admin']


class IsChiefInstructor(HasRole):
    """Chief flight instructors only"""
    required_roles = ['chief_instructor', 'admin']


class IsStudent(HasRole):
    """Students"""
    required_roles = ['student', 'instructor', 'admin']


class IsPilot(HasRole):
    """Licensed pilots"""
    required_roles = ['pilot', 'instructor', 'chief_instructor', 'admin']


class IsDispatcher(HasRole):
    """Dispatchers and schedulers"""
    required_roles = ['dispatcher', 'organization_admin', 'admin']


class IsMaintenance(HasRole):
    """Maintenance personnel"""
    required_roles = ['maintenance', 'maintenance_manager', 'admin']


class IsFinance(HasRole):
    """Finance personnel"""
    required_roles = ['finance', 'finance_manager', 'admin']


# =============================================================================
# COMBINED PERMISSIONS
# =============================================================================

class IsAdminOrReadOnly(BasePermission):
    """
    Full access for admins, read-only for others.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        user_roles = self.get_user_roles(request)
        return 'admin' in user_roles or 'system_admin' in user_roles


class IsInstructorOrStudent(BasePermission):
    """
    Permission for both instructors and students.
    Instructors can modify, students can only read.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        user_roles = self.get_user_roles(request)
        allowed_roles = {'instructor', 'chief_instructor', 'student', 'admin'}

        return bool(set(user_roles) & allowed_roles)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        user_roles = self.get_user_roles(request)

        # Instructors and admins can modify
        if set(user_roles) & {'instructor', 'chief_instructor', 'admin'}:
            return True

        # Students can only read
        if 'student' in user_roles and request.method in permissions.SAFE_METHODS:
            return True

        return False


# =============================================================================
# DYNAMIC PERMISSION FACTORY
# =============================================================================

def create_role_permission(*roles: str, require_all: bool = False):
    """
    Factory function to create role-based permission classes dynamically.

    Usage:
        permission_classes = [create_role_permission('instructor', 'admin')]
    """

    class DynamicRolePermission(HasRole):
        required_roles = list(roles)

    DynamicRolePermission.require_all = require_all
    return DynamicRolePermission


def create_permission_check(*perms: str, require_all: bool = True):
    """
    Factory function to create permission-based permission classes dynamically.

    Usage:
        permission_classes = [create_permission_check('booking.create', 'booking.view')]
    """

    class DynamicPermission(HasPermission):
        required_permissions = list(perms)

    DynamicPermission.require_all = require_all
    return DynamicPermission


# =============================================================================
# PERMISSION CONSTANTS
# =============================================================================

class Permissions:
    """
    Permission constants for the system.
    Use these constants instead of magic strings.
    """

    # User permissions
    USER_VIEW = 'user.view'
    USER_CREATE = 'user.create'
    USER_UPDATE = 'user.update'
    USER_DELETE = 'user.delete'

    # Organization permissions
    ORGANIZATION_VIEW = 'organization.view'
    ORGANIZATION_CREATE = 'organization.create'
    ORGANIZATION_UPDATE = 'organization.update'
    ORGANIZATION_DELETE = 'organization.delete'

    # Aircraft permissions
    AIRCRAFT_VIEW = 'aircraft.view'
    AIRCRAFT_CREATE = 'aircraft.create'
    AIRCRAFT_UPDATE = 'aircraft.update'
    AIRCRAFT_DELETE = 'aircraft.delete'
    AIRCRAFT_GROUND = 'aircraft.ground'

    # Booking permissions
    BOOKING_VIEW = 'booking.view'
    BOOKING_CREATE = 'booking.create'
    BOOKING_UPDATE = 'booking.update'
    BOOKING_DELETE = 'booking.delete'
    BOOKING_APPROVE = 'booking.approve'

    # Flight permissions
    FLIGHT_VIEW = 'flight.view'
    FLIGHT_CREATE = 'flight.create'
    FLIGHT_UPDATE = 'flight.update'
    FLIGHT_DELETE = 'flight.delete'
    FLIGHT_APPROVE = 'flight.approve'

    # Training permissions
    TRAINING_VIEW = 'training.view'
    TRAINING_CREATE = 'training.create'
    TRAINING_UPDATE = 'training.update'
    TRAINING_EVALUATE = 'training.evaluate'

    # Finance permissions
    FINANCE_VIEW = 'finance.view'
    FINANCE_CREATE = 'finance.create'
    FINANCE_UPDATE = 'finance.update'
    FINANCE_REFUND = 'finance.refund'

    # Maintenance permissions
    MAINTENANCE_VIEW = 'maintenance.view'
    MAINTENANCE_CREATE = 'maintenance.create'
    MAINTENANCE_UPDATE = 'maintenance.update'
    MAINTENANCE_COMPLETE = 'maintenance.complete'

    # Report permissions
    REPORT_VIEW = 'report.view'
    REPORT_EXPORT = 'report.export'
    REPORT_CREATE = 'report.create'


class Roles:
    """
    Role constants for the system.
    """

    SYSTEM_ADMIN = 'system_admin'
    ADMIN = 'admin'
    ORGANIZATION_ADMIN = 'organization_admin'
    CHIEF_INSTRUCTOR = 'chief_instructor'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'
    PILOT = 'pilot'
    DISPATCHER = 'dispatcher'
    MAINTENANCE = 'maintenance'
    MAINTENANCE_MANAGER = 'maintenance_manager'
    FINANCE = 'finance'
    FINANCE_MANAGER = 'finance_manager'
    EXAMINER = 'examiner'
    STAFF = 'staff'

# services/user-service/src/apps/core/services/permission_service.py
"""
Permission Service - Comprehensive RBAC/ABAC Authorization Layer

Handles all authorization operations including:
- Permission checking with caching
- Role management (system and organization roles)
- User role assignments with time/location constraints
- Conditional permissions (ABAC)
- Permission inheritance and hierarchy
- Audit logging for security operations
"""

import logging
from typing import Dict, List, Optional, Set, Any
from functools import lru_cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from apps.core.models import (
    User, Role, Permission, RolePermission, UserRole, AuditLog
)

logger = logging.getLogger(__name__)


class PermissionDeniedError(Exception):
    """Permission check failed"""
    def __init__(self, message: str = "Permission denied", permission: str = None, details: Dict = None):
        self.message = message
        self.permission = permission
        self.details = details or {}
        super().__init__(message)


class RoleNotFoundError(Exception):
    """Role not found"""
    pass


class PermissionService:
    """
    Comprehensive permission service implementing RBAC with ABAC extensions.

    Features:
    - Role-based access control (RBAC)
    - Attribute-based access control (ABAC) conditions
    - Permission caching for performance
    - Time-based role validity
    - Location-based role constraints
    - Role priority for conflict resolution
    - Organization-specific roles
    - System roles available to all organizations
    """

    # Cache settings
    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'perm:'

    def __init__(self):
        self.cache_enabled = True

    # ==================== PERMISSION CHECKING ====================

    def has_permission(
        self,
        user: User,
        permission_code: str,
        resource: Any = None,
        context: Dict = None
    ) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user: User object to check
            permission_code: Permission code (e.g., 'users.create', 'bookings.approve')
            resource: Optional resource for ABAC checks
            context: Optional additional context for ABAC

        Returns:
            True if user has permission, False otherwise
        """
        if not user or not user.is_active:
            return False

        # Superadmins have all permissions
        if user.is_superuser:
            return True

        # Check cache
        cache_key = self._get_permission_cache_key(user.id, permission_code)
        if self.cache_enabled:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                # Cache hit - but still need to evaluate ABAC conditions
                if cached_result is True and (resource or context):
                    return self._evaluate_conditions(user, permission_code, resource, context)
                return cached_result

        # Get user's effective permissions
        permissions = self.get_user_permissions(user)

        # Check direct permission match
        if permission_code in permissions:
            # Cache the result
            if self.cache_enabled:
                cache.set(cache_key, True, self.CACHE_TTL)

            # Evaluate ABAC conditions if resource provided
            if resource or context:
                return self._evaluate_conditions(user, permission_code, resource, context)
            return True

        # Check wildcard permissions (e.g., 'users.*' or '*.*')
        module = permission_code.split('.')[0] if '.' in permission_code else permission_code
        if f"{module}.*" in permissions or '*.*' in permissions:
            if self.cache_enabled:
                cache.set(cache_key, True, self.CACHE_TTL)
            if resource or context:
                return self._evaluate_conditions(user, permission_code, resource, context)
            return True

        # No permission found
        if self.cache_enabled:
            cache.set(cache_key, False, self.CACHE_TTL)
        return False

    def check_permission(
        self,
        user: User,
        permission_code: str,
        resource: Any = None,
        context: Dict = None
    ) -> None:
        """
        Check permission and raise exception if denied.

        Args:
            user: User to check
            permission_code: Required permission
            resource: Optional resource for ABAC
            context: Optional context

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        if not self.has_permission(user, permission_code, resource, context):
            raise PermissionDeniedError(
                f"Permission '{permission_code}' required",
                permission=permission_code
            )

    def has_any_permission(
        self,
        user: User,
        permission_codes: List[str]
    ) -> bool:
        """Check if user has any of the specified permissions."""
        return any(
            self.has_permission(user, code)
            for code in permission_codes
        )

    def has_all_permissions(
        self,
        user: User,
        permission_codes: List[str]
    ) -> bool:
        """Check if user has all specified permissions."""
        return all(
            self.has_permission(user, code)
            for code in permission_codes
        )

    def get_user_permissions(
        self,
        user: User,
        include_conditions: bool = False
    ) -> Set[str]:
        """
        Get all effective permissions for a user.

        Combines permissions from all active roles.

        Args:
            user: User object
            include_conditions: If True, return dict with conditions

        Returns:
            Set of permission codes, or dict with conditions
        """
        if not user or not user.is_active:
            return set() if not include_conditions else {}

        # Check cache
        cache_key = f"{self.CACHE_PREFIX}user:{user.id}:all"
        if self.cache_enabled:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached if not include_conditions else self._get_conditions_for_permissions(user)

        # Get all active role assignments
        now = timezone.now()
        user_roles = UserRole.objects.filter(
            user=user,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).select_related('role').order_by('-role__priority')

        permissions = set()
        permission_conditions = {}

        for user_role in user_roles:
            role = user_role.role

            # Get role permissions with conditions
            role_permissions = RolePermission.objects.filter(
                role=role
            ).select_related('permission')

            for rp in role_permissions:
                perm_code = rp.permission.code
                permissions.add(perm_code)

                # Store conditions (higher priority role takes precedence)
                if perm_code not in permission_conditions and rp.conditions:
                    permission_conditions[perm_code] = {
                        'conditions': rp.conditions,
                        'user_role_conditions': user_role.conditions,
                        'location_id': user_role.location_id
                    }

        # Cache the result
        if self.cache_enabled:
            cache.set(cache_key, permissions, self.CACHE_TTL)
            cache.set(f"{cache_key}:conditions", permission_conditions, self.CACHE_TTL)

        if include_conditions:
            return permission_conditions
        return permissions

    def _get_conditions_for_permissions(self, user: User) -> Dict:
        """Get cached conditions for user permissions."""
        cache_key = f"{self.CACHE_PREFIX}user:{user.id}:all:conditions"
        return cache.get(cache_key) or {}

    def _evaluate_conditions(
        self,
        user: User,
        permission_code: str,
        resource: Any = None,
        context: Dict = None
    ) -> bool:
        """
        Evaluate ABAC conditions for a permission.

        Args:
            user: User object
            permission_code: Permission being checked
            resource: Resource being accessed
            context: Additional context

        Returns:
            True if conditions are satisfied
        """
        conditions = self._get_conditions_for_permissions(user).get(permission_code)
        if not conditions:
            return True  # No conditions to evaluate

        role_conditions = conditions.get('conditions', {})
        user_role_conditions = conditions.get('user_role_conditions', {})
        location_constraint = conditions.get('location_id')

        context = context or {}

        # Check 'own_records_only' condition
        if role_conditions.get('own_records_only'):
            if resource and hasattr(resource, 'user_id'):
                if str(resource.user_id) != str(user.id):
                    return False
            elif context.get('user_id') and str(context['user_id']) != str(user.id):
                return False

        # Check 'same_organization' condition
        if role_conditions.get('same_organization'):
            resource_org = None
            if resource and hasattr(resource, 'organization_id'):
                resource_org = resource.organization_id
            elif context.get('organization_id'):
                resource_org = context['organization_id']

            if resource_org and str(resource_org) != str(user.organization_id):
                return False

        # Check 'same_location' condition
        if role_conditions.get('same_location') or location_constraint:
            resource_location = None
            if resource and hasattr(resource, 'location_id'):
                resource_location = resource.location_id
            elif context.get('location_id'):
                resource_location = context['location_id']

            if location_constraint:
                if resource_location and str(resource_location) != str(location_constraint):
                    return False

        # Check custom conditions in user role
        if user_role_conditions:
            for key, value in user_role_conditions.items():
                if key in context and context[key] != value:
                    return False

        return True

    # ==================== ROLE MANAGEMENT ====================

    @transaction.atomic
    def create_role(
        self,
        name: str,
        code: str,
        organization_id: str = None,
        description: str = '',
        permissions: List[str] = None,
        is_system_role: bool = False,
        is_default: bool = False,
        priority: int = 0,
        color: str = None,
        created_by: User = None
    ) -> Role:
        """
        Create a new role.

        Args:
            name: Role display name
            code: Unique role code
            organization_id: Organization scope (None for system roles)
            description: Role description
            permissions: List of permission codes to assign
            is_system_role: Whether this is a system-level role
            is_default: Whether to auto-assign to new users
            priority: Role priority for conflict resolution
            color: Display color (hex)
            created_by: User creating the role

        Returns:
            Created Role object
        """
        # Validate code uniqueness within organization scope
        if Role.objects.filter(
            code=code,
            organization_id=organization_id
        ).exists():
            raise ValueError(f"Role with code '{code}' already exists")

        role = Role.objects.create(
            name=name,
            code=code,
            organization_id=organization_id,
            description=description,
            is_system_role=is_system_role,
            is_default=is_default,
            priority=priority,
            color=color,
            created_by=created_by.id if created_by else None
        )

        # Assign permissions
        if permissions:
            self._assign_permissions_to_role(role, permissions)

        # Audit log
        AuditLog.log(
            action='create',
            entity_type='role',
            entity_id=role.id,
            entity_name=role.name,
            user=created_by,
            organization_id=organization_id,
            risk_level='medium',
            metadata={'permissions': permissions}
        )

        logger.info(f"Role created: {role.name}")
        return role

    @transaction.atomic
    def update_role(
        self,
        role: Role,
        updated_by: User = None,
        **kwargs
    ) -> Role:
        """
        Update role properties.

        Args:
            role: Role to update
            updated_by: User making the update
            **kwargs: Fields to update

        Returns:
            Updated Role object
        """
        if role.is_system_role and not (updated_by and updated_by.is_superuser):
            raise PermissionDeniedError("System roles cannot be modified")

        old_values = {}
        changed_fields = []

        allowed_fields = ['name', 'description', 'priority', 'color', 'icon', 'is_default']

        for field in allowed_fields:
            if field in kwargs:
                old_value = getattr(role, field)
                new_value = kwargs[field]
                if old_value != new_value:
                    old_values[field] = old_value
                    setattr(role, field, new_value)
                    changed_fields.append(field)

        if changed_fields:
            role.save(update_fields=changed_fields + ['updated_at'])

            # Invalidate caches for users with this role
            self._invalidate_role_caches(role)

            # Audit log
            AuditLog.log(
                action='update',
                entity_type='role',
                entity_id=role.id,
                entity_name=role.name,
                user=updated_by,
                old_values=old_values,
                new_values={k: kwargs[k] for k in changed_fields},
                changed_fields=changed_fields,
                risk_level='medium'
            )

        return role

    @transaction.atomic
    def delete_role(self, role: Role, deleted_by: User = None) -> None:
        """
        Delete a role.

        Args:
            role: Role to delete
            deleted_by: User performing deletion
        """
        if role.is_system_role:
            raise PermissionDeniedError("System roles cannot be deleted")

        # Check if role is assigned to users
        if UserRole.objects.filter(role=role, revoked_at__isnull=True).exists():
            raise ValueError("Cannot delete role that is assigned to users")

        role_name = role.name
        role_id = role.id

        # Delete role permissions first
        RolePermission.objects.filter(role=role).delete()

        # Delete the role
        role.delete()

        # Audit log
        AuditLog.log(
            action='delete',
            entity_type='role',
            entity_id=role_id,
            entity_name=role_name,
            user=deleted_by,
            risk_level='high'
        )

        logger.info(f"Role deleted: {role_name}")

    def get_role(self, role_id: str = None, code: str = None, organization_id: str = None) -> Optional[Role]:
        """Get role by ID or code."""
        try:
            if role_id:
                return Role.objects.get(id=role_id)
            elif code:
                return Role.objects.get(
                    code=code,
                    organization_id=organization_id
                )
        except Role.DoesNotExist:
            return None

    def get_available_roles(
        self,
        organization_id: str = None,
        include_system_roles: bool = True
    ) -> List[Role]:
        """
        Get roles available to an organization.

        Args:
            organization_id: Organization ID
            include_system_roles: Include system-wide roles

        Returns:
            List of available roles
        """
        query = Q()

        if organization_id:
            query |= Q(organization_id=organization_id)

        if include_system_roles:
            query |= Q(is_system_role=True)

        return list(
            Role.objects.filter(query).order_by('-priority', 'name')
        )

    # ==================== PERMISSION MANAGEMENT ====================

    @transaction.atomic
    def create_permission(
        self,
        code: str,
        name: str,
        module: str,
        action: str,
        description: str = '',
        is_sensitive: bool = False,
        requires_2fa: bool = False,
        created_by: User = None
    ) -> Permission:
        """
        Create a new permission.

        Args:
            code: Unique permission code
            name: Human-readable name
            module: Module/resource name
            action: Action type
            description: Permission description
            is_sensitive: Requires additional audit
            requires_2fa: Requires 2FA verification
            created_by: User creating permission

        Returns:
            Created Permission object
        """
        if Permission.objects.filter(code=code).exists():
            raise ValueError(f"Permission with code '{code}' already exists")

        permission = Permission.objects.create(
            code=code,
            name=name,
            module=module,
            action=action,
            description=description,
            is_sensitive=is_sensitive,
            requires_2fa=requires_2fa
        )

        # Audit log
        AuditLog.log(
            action='create',
            entity_type='permission',
            entity_id=permission.id,
            entity_name=permission.code,
            user=created_by,
            risk_level='high' if is_sensitive else 'medium'
        )

        logger.info(f"Permission created: {permission.code}")
        return permission

    def get_permission(self, code: str) -> Optional[Permission]:
        """Get permission by code."""
        try:
            return Permission.objects.get(code=code)
        except Permission.DoesNotExist:
            return None

    def get_all_permissions(self, module: str = None) -> List[Permission]:
        """Get all permissions, optionally filtered by module."""
        query = Permission.objects.all()
        if module:
            query = query.filter(module=module)
        return list(query.order_by('module', 'action', 'code'))

    def get_permission_modules(self) -> List[str]:
        """Get list of unique permission modules."""
        return list(
            Permission.objects.values_list('module', flat=True).distinct()
        )

    @transaction.atomic
    def assign_permission_to_role(
        self,
        role: Role,
        permission_code: str,
        conditions: Dict = None,
        assigned_by: User = None
    ) -> RolePermission:
        """
        Assign a permission to a role.

        Args:
            role: Role to assign to
            permission_code: Permission code
            conditions: Optional ABAC conditions
            assigned_by: User making assignment

        Returns:
            Created RolePermission object
        """
        permission = self.get_permission(permission_code)
        if not permission:
            raise ValueError(f"Permission '{permission_code}' not found")

        if role.is_system_role and not (assigned_by and assigned_by.is_superuser):
            raise PermissionDeniedError("Cannot modify system role permissions")

        rp, created = RolePermission.objects.get_or_create(
            role=role,
            permission=permission,
            defaults={
                'conditions': conditions,
                'created_by': assigned_by.id if assigned_by else None
            }
        )

        if not created and conditions != rp.conditions:
            rp.conditions = conditions
            rp.save(update_fields=['conditions'])

        # Invalidate caches
        self._invalidate_role_caches(role)

        # Audit log
        AuditLog.log(
            action='assign_permission',
            entity_type='role',
            entity_id=role.id,
            entity_name=role.name,
            user=assigned_by,
            risk_level='medium',
            metadata={
                'permission': permission_code,
                'conditions': conditions
            }
        )

        return rp

    @transaction.atomic
    def revoke_permission_from_role(
        self,
        role: Role,
        permission_code: str,
        revoked_by: User = None
    ) -> None:
        """
        Remove a permission from a role.

        Args:
            role: Role to modify
            permission_code: Permission code to remove
            revoked_by: User making the change
        """
        if role.is_system_role and not (revoked_by and revoked_by.is_superuser):
            raise PermissionDeniedError("Cannot modify system role permissions")

        deleted_count = RolePermission.objects.filter(
            role=role,
            permission__code=permission_code
        ).delete()[0]

        if deleted_count > 0:
            # Invalidate caches
            self._invalidate_role_caches(role)

            # Audit log
            AuditLog.log(
                action='revoke_permission',
                entity_type='role',
                entity_id=role.id,
                entity_name=role.name,
                user=revoked_by,
                risk_level='medium',
                metadata={'permission': permission_code}
            )

    def _assign_permissions_to_role(self, role: Role, permission_codes: List[str]) -> None:
        """Bulk assign permissions to a role."""
        permissions = Permission.objects.filter(code__in=permission_codes)

        for permission in permissions:
            RolePermission.objects.get_or_create(
                role=role,
                permission=permission
            )

    def get_role_permissions(self, role: Role) -> List[Dict]:
        """
        Get all permissions for a role.

        Returns:
            List of permission dicts with conditions
        """
        role_permissions = RolePermission.objects.filter(
            role=role
        ).select_related('permission')

        return [
            {
                'code': rp.permission.code,
                'name': rp.permission.name,
                'module': rp.permission.module,
                'action': rp.permission.action,
                'conditions': rp.conditions,
                'is_sensitive': rp.permission.is_sensitive,
                'requires_2fa': rp.permission.requires_2fa
            }
            for rp in role_permissions
        ]

    # ==================== USER ROLE MANAGEMENT ====================

    @transaction.atomic
    def assign_role_to_user(
        self,
        user: User,
        role: Role,
        valid_from: timezone.datetime = None,
        valid_until: timezone.datetime = None,
        location_id: str = None,
        conditions: Dict = None,
        assigned_by: User = None
    ) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user: User to assign role to
            role: Role to assign
            valid_from: Start of validity period
            valid_until: End of validity period
            location_id: Restrict role to specific location
            conditions: Additional ABAC conditions
            assigned_by: User making assignment

        Returns:
            Created UserRole object
        """
        valid_from = valid_from or timezone.now()

        # Check if assignment already exists
        existing = UserRole.objects.filter(
            user=user,
            role=role,
            location_id=location_id,
            revoked_at__isnull=True
        ).first()

        if existing:
            # Update existing assignment
            existing.valid_from = valid_from
            existing.valid_until = valid_until
            existing.conditions = conditions
            existing.save()
            user_role = existing
        else:
            user_role = UserRole.objects.create(
                user=user,
                role=role,
                valid_from=valid_from,
                valid_until=valid_until,
                location_id=location_id,
                conditions=conditions,
                created_by=assigned_by.id if assigned_by else None
            )

        # Invalidate user's permission cache
        self._invalidate_user_caches(user)

        # Audit log
        AuditLog.log(
            action='assign_role',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=assigned_by,
            risk_level='medium',
            metadata={
                'role': role.name,
                'role_id': str(role.id),
                'valid_until': valid_until.isoformat() if valid_until else None,
                'location_id': str(location_id) if location_id else None
            }
        )

        logger.info(f"Role '{role.name}' assigned to user: {user.email}")
        return user_role

    @transaction.atomic
    def revoke_role_from_user(
        self,
        user: User,
        role: Role,
        location_id: str = None,
        revoked_by: User = None
    ) -> None:
        """
        Revoke a role from a user.

        Args:
            user: User to revoke from
            role: Role to revoke
            location_id: Specific location assignment to revoke
            revoked_by: User making the revocation
        """
        user_roles = UserRole.objects.filter(
            user=user,
            role=role,
            revoked_at__isnull=True
        )

        if location_id:
            user_roles = user_roles.filter(location_id=location_id)

        for user_role in user_roles:
            user_role.revoke(revoked_by=revoked_by.id if revoked_by else None)

        # Invalidate caches
        self._invalidate_user_caches(user)

        # Audit log
        AuditLog.log(
            action='revoke_role',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=revoked_by,
            risk_level='medium',
            metadata={
                'role': role.name,
                'role_id': str(role.id),
                'location_id': str(location_id) if location_id else None
            }
        )

        logger.info(f"Role '{role.name}' revoked from user: {user.email}")

    def get_user_roles(
        self,
        user: User,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> List[Dict]:
        """
        Get all roles assigned to a user.

        Args:
            user: User to get roles for
            include_expired: Include expired assignments
            include_revoked: Include revoked assignments

        Returns:
            List of role assignment dicts
        """
        now = timezone.now()
        query = UserRole.objects.filter(user=user)

        if not include_revoked:
            query = query.filter(revoked_at__isnull=True)

        if not include_expired:
            query = query.filter(
                Q(valid_until__isnull=True) | Q(valid_until__gt=now),
                valid_from__lte=now
            )

        user_roles = query.select_related('role').order_by('-role__priority')

        return [
            {
                'id': str(ur.id),
                'role': {
                    'id': str(ur.role.id),
                    'code': ur.role.code,
                    'name': ur.role.name,
                    'priority': ur.role.priority,
                    'is_system_role': ur.role.is_system_role,
                    'color': ur.role.color
                },
                'valid_from': ur.valid_from.isoformat() if ur.valid_from else None,
                'valid_until': ur.valid_until.isoformat() if ur.valid_until else None,
                'location_id': str(ur.location_id) if ur.location_id else None,
                'conditions': ur.conditions,
                'is_valid': ur.is_valid,
                'created_at': ur.created_at.isoformat()
            }
            for ur in user_roles
        ]

    def get_users_with_role(
        self,
        role: Role,
        organization_id: str = None
    ) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role: Role to search for
            organization_id: Filter by organization

        Returns:
            List of User objects
        """
        now = timezone.now()
        user_ids = UserRole.objects.filter(
            role=role,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).values_list('user_id', flat=True)

        query = User.objects.filter(id__in=user_ids, is_active=True)

        if organization_id:
            query = query.filter(organization_id=organization_id)

        return list(query)

    def get_users_with_permission(
        self,
        permission_code: str,
        organization_id: str = None
    ) -> List[User]:
        """
        Get all users with a specific permission.

        Args:
            permission_code: Permission code
            organization_id: Filter by organization

        Returns:
            List of User objects
        """
        # Get roles that have this permission
        role_ids = RolePermission.objects.filter(
            permission__code=permission_code
        ).values_list('role_id', flat=True)

        # Get users with those roles
        now = timezone.now()
        user_ids = UserRole.objects.filter(
            role_id__in=role_ids,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).values_list('user_id', flat=True)

        query = User.objects.filter(id__in=user_ids, is_active=True)

        if organization_id:
            query = query.filter(organization_id=organization_id)

        return list(query)

    # ==================== CACHE MANAGEMENT ====================

    def _get_permission_cache_key(self, user_id: str, permission_code: str) -> str:
        """Generate cache key for permission check."""
        return f"{self.CACHE_PREFIX}user:{user_id}:perm:{permission_code}"

    def _invalidate_user_caches(self, user: User) -> None:
        """Invalidate all permission caches for a user."""
        cache.delete_pattern(f"{self.CACHE_PREFIX}user:{user.id}:*")

    def _invalidate_role_caches(self, role: Role) -> None:
        """Invalidate caches for all users with a role."""
        user_ids = UserRole.objects.filter(
            role=role,
            revoked_at__isnull=True
        ).values_list('user_id', flat=True)

        for user_id in user_ids:
            cache.delete_pattern(f"{self.CACHE_PREFIX}user:{user_id}:*")

    def invalidate_all_caches(self) -> None:
        """Clear all permission caches."""
        cache.delete_pattern(f"{self.CACHE_PREFIX}*")
        logger.info("All permission caches invalidated")

    # ==================== SEEDING ====================

    @transaction.atomic
    def seed_default_permissions(self) -> List[Permission]:
        """
        Create default system permissions.

        Returns:
            List of created permissions
        """
        default_permissions = [
            # User management
            ('users.create', 'Create Users', 'users', 'create'),
            ('users.read', 'View Users', 'users', 'read'),
            ('users.update', 'Update Users', 'users', 'update'),
            ('users.delete', 'Delete Users', 'users', 'delete'),
            ('users.manage', 'Manage Users', 'users', 'manage'),

            # Role management
            ('roles.create', 'Create Roles', 'roles', 'create'),
            ('roles.read', 'View Roles', 'roles', 'read'),
            ('roles.update', 'Update Roles', 'roles', 'update'),
            ('roles.delete', 'Delete Roles', 'roles', 'delete'),
            ('roles.assign', 'Assign Roles', 'roles', 'manage'),

            # Organization management
            ('organizations.create', 'Create Organizations', 'organizations', 'create'),
            ('organizations.read', 'View Organizations', 'organizations', 'read'),
            ('organizations.update', 'Update Organizations', 'organizations', 'update'),
            ('organizations.delete', 'Delete Organizations', 'organizations', 'delete'),

            # Booking management
            ('bookings.create', 'Create Bookings', 'bookings', 'create'),
            ('bookings.read', 'View Bookings', 'bookings', 'read'),
            ('bookings.update', 'Update Bookings', 'bookings', 'update'),
            ('bookings.delete', 'Delete Bookings', 'bookings', 'delete'),
            ('bookings.approve', 'Approve Bookings', 'bookings', 'manage'),
            ('bookings.cancel', 'Cancel Bookings', 'bookings', 'manage'),

            # Flight management
            ('flights.create', 'Create Flights', 'flights', 'create'),
            ('flights.read', 'View Flights', 'flights', 'read'),
            ('flights.update', 'Update Flights', 'flights', 'update'),
            ('flights.delete', 'Delete Flights', 'flights', 'delete'),

            # Reports
            ('reports.view', 'View Reports', 'reports', 'read'),
            ('reports.export', 'Export Reports', 'reports', 'manage'),

            # Audit
            ('audit.view', 'View Audit Logs', 'audit', 'read'),

            # System
            ('system.settings', 'Manage System Settings', 'system', 'manage'),
            ('system.maintenance', 'System Maintenance', 'system', 'manage'),
        ]

        created = []
        for code, name, module, action in default_permissions:
            permission, was_created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'module': module,
                    'action': action,
                    'is_sensitive': module in ['audit', 'system'],
                    'requires_2fa': action == 'delete' and module in ['users', 'organizations']
                }
            )
            if was_created:
                created.append(permission)

        logger.info(f"Seeded {len(created)} default permissions")
        return created

    @transaction.atomic
    def seed_default_roles(self) -> List[Role]:
        """
        Create default system roles.

        Returns:
            List of created roles
        """
        default_roles = [
            {
                'code': 'super_admin',
                'name': 'Super Administrator',
                'description': 'Full system access',
                'is_system_role': True,
                'priority': 100,
                'permissions': ['*.*']  # All permissions
            },
            {
                'code': 'admin',
                'name': 'Administrator',
                'description': 'Organization administrator',
                'is_system_role': True,
                'priority': 90,
                'permissions': [
                    'users.create', 'users.read', 'users.update', 'users.delete',
                    'roles.read', 'roles.assign',
                    'bookings.*', 'flights.*', 'reports.*'
                ]
            },
            {
                'code': 'instructor',
                'name': 'Instructor',
                'description': 'Flight instructor',
                'is_system_role': True,
                'priority': 50,
                'permissions': [
                    'users.read',
                    'bookings.create', 'bookings.read', 'bookings.update',
                    'flights.read', 'flights.update',
                    'reports.view'
                ]
            },
            {
                'code': 'student',
                'name': 'Student',
                'description': 'Student pilot',
                'is_system_role': True,
                'is_default': True,
                'priority': 10,
                'permissions': [
                    'bookings.create', 'bookings.read',
                    'flights.read'
                ]
            },
        ]

        created = []
        for role_data in default_roles:
            permissions = role_data.pop('permissions', [])

            role, was_created = Role.objects.get_or_create(
                code=role_data['code'],
                organization_id=None,  # System roles
                defaults=role_data
            )

            if was_created:
                # Assign permissions
                for perm_code in permissions:
                    if perm_code == '*.*':
                        # All permissions
                        for perm in Permission.objects.all():
                            RolePermission.objects.get_or_create(
                                role=role,
                                permission=perm
                            )
                    elif perm_code.endswith('.*'):
                        # Module wildcard
                        module = perm_code.replace('.*', '')
                        for perm in Permission.objects.filter(module=module):
                            RolePermission.objects.get_or_create(
                                role=role,
                                permission=perm
                            )
                    else:
                        perm = Permission.objects.filter(code=perm_code).first()
                        if perm:
                            RolePermission.objects.get_or_create(
                                role=role,
                                permission=perm
                            )

                created.append(role)

        logger.info(f"Seeded {len(created)} default roles")
        return created

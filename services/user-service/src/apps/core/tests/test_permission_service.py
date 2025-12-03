# services/user-service/src/apps/core/tests/test_permission_service.py
"""
Tests for PermissionService

Tests RBAC/ABAC functionality including:
- Permission checking
- Role management
- User-role assignments
- Conditional permissions
"""

import pytest
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from apps.core.models import Role, Permission, RolePermission, UserRole
from apps.core.services import PermissionService


pytestmark = pytest.mark.django_db


class TestPermissionChecking:
    """Tests for permission checking."""

    def test_has_permission_with_role(
        self, permission_service, active_user, admin_role, basic_permissions
    ):
        """Test user has permission through role."""
        # Assign role to user
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )

        assert permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

    def test_has_permission_without_role(
        self, permission_service, active_user, basic_permissions
    ):
        """Test user without role has no permissions."""
        assert not permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

    def test_has_permission_superuser(self, permission_service, admin_user):
        """Test superuser has all permissions."""
        assert permission_service.has_permission(
            user=admin_user,
            permission_code='any.permission'
        )

    def test_has_permission_expired_role(
        self, permission_service, active_user, admin_role, basic_permissions
    ):
        """Test user with expired role assignment has no permissions."""
        # Assign role with expired validity
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now() - timedelta(days=30),
            valid_until=timezone.now() - timedelta(days=1)  # Expired
        )

        assert not permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

    def test_has_permission_future_role(
        self, permission_service, active_user, admin_role, basic_permissions
    ):
        """Test user with future role assignment has no permissions yet."""
        # Assign role starting in the future
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now() + timedelta(days=1)
        )

        assert not permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

    def test_has_permission_revoked_role(
        self, permission_service, active_user, admin_role, basic_permissions
    ):
        """Test user with revoked role assignment has no permissions."""
        # Assign and revoke role
        user_role = UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )
        user_role.revoked_at = timezone.now()
        user_role.save()

        assert not permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )


class TestConditionalPermissions:
    """Tests for conditional (ABAC) permissions."""

    def test_permission_with_location_condition(
        self, permission_service, active_user, create_role, create_permission
    ):
        """Test permission with location condition."""
        location_id = uuid4()

        # Create role with location-restricted permission
        role = create_role(code='location_manager')
        permission = create_permission(code='resources.manage')

        RolePermission.objects.create(
            role=role,
            permission=permission,
            conditions={'location_ids': [str(location_id)]}
        )

        UserRole.objects.create(
            user=active_user,
            role=role,
            valid_from=timezone.now(),
            location_id=location_id
        )

        # Should have permission for the assigned location
        assert permission_service.has_permission(
            user=active_user,
            permission_code='resources.manage',
            context={'location_id': str(location_id)}
        )

    def test_permission_without_matching_condition(
        self, permission_service, active_user, create_role, create_permission
    ):
        """Test permission denied when condition doesn't match."""
        location_id = uuid4()
        other_location_id = uuid4()

        role = create_role(code='location_manager')
        permission = create_permission(code='resources.manage')

        RolePermission.objects.create(
            role=role,
            permission=permission,
            conditions={'location_ids': [str(location_id)]}
        )

        UserRole.objects.create(
            user=active_user,
            role=role,
            valid_from=timezone.now(),
            location_id=location_id
        )

        # Should not have permission for a different location
        assert not permission_service.has_permission(
            user=active_user,
            permission_code='resources.manage',
            context={'location_id': str(other_location_id)}
        )


class TestGetUserPermissions:
    """Tests for getting user permissions."""

    def test_get_all_permissions(
        self, permission_service, active_user, admin_role, basic_permissions
    ):
        """Test getting all user permissions."""
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )

        permissions = permission_service.get_user_permissions(user=active_user)

        assert len(permissions) >= len(basic_permissions)
        assert 'users.read' in [p['code'] for p in permissions]

    def test_get_permissions_from_multiple_roles(
        self, permission_service, active_user, admin_role, viewer_role, basic_permissions
    ):
        """Test permissions from multiple roles are combined."""
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )
        UserRole.objects.create(
            user=active_user,
            role=viewer_role,
            valid_from=timezone.now()
        )

        permissions = permission_service.get_user_permissions(user=active_user)

        # Should have combined permissions (no duplicates)
        permission_codes = [p['code'] for p in permissions]
        assert len(permission_codes) == len(set(permission_codes))


class TestRoleManagement:
    """Tests for role management."""

    def test_create_role(self, permission_service, organization_id):
        """Test creating a new role."""
        role = permission_service.create_role(
            code='new_role',
            name='New Role',
            description='Test role',
            organization_id=organization_id
        )

        assert role.code == 'new_role'
        assert role.organization_id == organization_id

    def test_create_duplicate_role(self, permission_service, admin_role):
        """Test cannot create role with duplicate code."""
        with pytest.raises(Exception):  # Adjust exception type as needed
            permission_service.create_role(
                code=admin_role.code,
                name='Duplicate Role'
            )

    def test_update_role(self, permission_service, viewer_role):
        """Test updating a role."""
        updated = permission_service.update_role(
            role=viewer_role,
            name='Updated Viewer',
            description='Updated description'
        )

        assert updated.name == 'Updated Viewer'
        assert updated.description == 'Updated description'

    def test_delete_role(self, permission_service, viewer_role):
        """Test deleting a role."""
        role_id = viewer_role.id

        permission_service.delete_role(role=viewer_role)

        assert not Role.objects.filter(id=role_id).exists()

    def test_cannot_delete_system_role(self, permission_service, admin_role):
        """Test cannot delete system role."""
        with pytest.raises(Exception):  # Adjust exception type as needed
            permission_service.delete_role(role=admin_role)


class TestRolePermissionManagement:
    """Tests for role permission management."""

    def test_add_permission_to_role(
        self, permission_service, viewer_role, create_permission
    ):
        """Test adding permission to a role."""
        permission = create_permission(code='reports.view')

        permission_service.add_permission_to_role(
            role=viewer_role,
            permission_code='reports.view'
        )

        assert RolePermission.objects.filter(
            role=viewer_role,
            permission=permission
        ).exists()

    def test_remove_permission_from_role(
        self, permission_service, admin_role, basic_permissions
    ):
        """Test removing permission from a role."""
        permission_service.remove_permission_from_role(
            role=admin_role,
            permission_code='users.delete'
        )

        assert not RolePermission.objects.filter(
            role=admin_role,
            permission=basic_permissions['users.delete']
        ).exists()

    def test_set_role_permissions(
        self, permission_service, viewer_role, basic_permissions
    ):
        """Test setting all permissions for a role."""
        new_permissions = ['users.read', 'users.update']

        permission_service.set_role_permissions(
            role=viewer_role,
            permission_codes=new_permissions
        )

        role_perms = RolePermission.objects.filter(role=viewer_role)
        assert role_perms.count() == 2


class TestUserRoleAssignment:
    """Tests for user-role assignments."""

    def test_assign_role_to_user(self, permission_service, active_user, viewer_role):
        """Test assigning a role to a user."""
        user_role = permission_service.assign_role_to_user(
            user=active_user,
            role=viewer_role
        )

        assert user_role.user == active_user
        assert user_role.role == viewer_role
        assert user_role.is_valid

    def test_assign_role_with_validity(
        self, permission_service, active_user, viewer_role
    ):
        """Test assigning role with validity period."""
        valid_from = timezone.now()
        valid_until = timezone.now() + timedelta(days=30)

        user_role = permission_service.assign_role_to_user(
            user=active_user,
            role=viewer_role,
            valid_from=valid_from,
            valid_until=valid_until
        )

        assert user_role.valid_from == valid_from
        assert user_role.valid_until == valid_until

    def test_assign_role_with_location(
        self, permission_service, active_user, viewer_role
    ):
        """Test assigning role with location restriction."""
        location_id = uuid4()

        user_role = permission_service.assign_role_to_user(
            user=active_user,
            role=viewer_role,
            location_id=location_id
        )

        assert user_role.location_id == location_id

    def test_revoke_role_from_user(
        self, permission_service, active_user, viewer_role
    ):
        """Test revoking a role from a user."""
        # First assign
        user_role = permission_service.assign_role_to_user(
            user=active_user,
            role=viewer_role
        )

        # Then revoke
        permission_service.revoke_role_from_user(
            user=active_user,
            role=viewer_role
        )

        user_role.refresh_from_db()
        assert user_role.revoked_at is not None
        assert not user_role.is_valid

    def test_get_user_roles(self, permission_service, active_user, admin_role, viewer_role):
        """Test getting all roles for a user."""
        permission_service.assign_role_to_user(user=active_user, role=admin_role)
        permission_service.assign_role_to_user(user=active_user, role=viewer_role)

        roles = permission_service.get_user_roles(user=active_user)

        assert len(roles) == 2
        role_codes = [r.role.code for r in roles]
        assert 'admin' in role_codes
        assert 'viewer' in role_codes


class TestPermissionCaching:
    """Tests for permission caching."""

    def test_permissions_are_cached(
        self, permission_service, active_user, admin_role, basic_permissions, clear_cache
    ):
        """Test that permissions are cached."""
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )

        # First call
        result1 = permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

        # Modify database directly (bypass service)
        RolePermission.objects.filter(
            role=admin_role,
            permission__code='users.read'
        ).delete()

        # Second call should still return cached result
        result2 = permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

        assert result1 == result2  # Both should be True due to caching

    def test_cache_invalidation(
        self, permission_service, active_user, admin_role, basic_permissions, clear_cache
    ):
        """Test that cache is invalidated on role change."""
        UserRole.objects.create(
            user=active_user,
            role=admin_role,
            valid_from=timezone.now()
        )

        # First call
        assert permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

        # Invalidate cache
        permission_service.invalidate_user_permissions_cache(active_user)

        # Remove permission
        RolePermission.objects.filter(
            role=admin_role,
            permission__code='users.read'
        ).delete()

        # Should return False now
        assert not permission_service.has_permission(
            user=active_user,
            permission_code='users.read'
        )

# services/user-service/src/apps/core/tests/test_user_service.py
"""
Tests for UserService

Tests user management functionality including:
- User CRUD operations
- Status management
- Bulk operations
- Search and filtering
"""

import pytest
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from apps.core.models import User
from apps.core.services import UserService


pytestmark = pytest.mark.django_db


class TestUserCreation:
    """Tests for user creation."""

    def test_create_user_success(self, user_service):
        """Test successful user creation."""
        user = user_service.create_user(
            email='newuser@test.com',
            first_name='New',
            last_name='User',
            password='SecurePass123!'
        )

        assert user.email == 'newuser@test.com'
        assert user.first_name == 'New'
        assert user.last_name == 'User'

    def test_create_user_with_organization(self, user_service, organization_id):
        """Test user creation with organization."""
        user = user_service.create_user(
            email='orguser@test.com',
            first_name='Org',
            last_name='User',
            organization_id=organization_id,
            password='SecurePass123!'
        )

        assert user.organization_id == organization_id

    def test_create_user_duplicate_email(self, user_service, active_user):
        """Test user creation fails with duplicate email."""
        with pytest.raises(Exception):
            user_service.create_user(
                email=active_user.email,
                first_name='Duplicate',
                last_name='User',
                password='SecurePass123!'
            )

    def test_create_user_with_metadata(self, user_service):
        """Test user creation with metadata."""
        user = user_service.create_user(
            email='metauser@test.com',
            first_name='Meta',
            last_name='User',
            password='SecurePass123!',
            timezone='Europe/Istanbul',
            language='tr',
            phone='+905551234567'
        )

        assert user.timezone == 'Europe/Istanbul'
        assert user.language == 'tr'
        assert user.phone == '+905551234567'


class TestUserRetrieval:
    """Tests for user retrieval."""

    def test_get_user_by_id(self, user_service, active_user):
        """Test getting user by ID."""
        user = user_service.get_user(user_id=active_user.id)

        assert user.id == active_user.id
        assert user.email == active_user.email

    def test_get_user_by_email(self, user_service, active_user):
        """Test getting user by email."""
        user = user_service.get_user_by_email(email=active_user.email)

        assert user.id == active_user.id

    def test_get_nonexistent_user(self, user_service):
        """Test getting nonexistent user returns None or raises."""
        user = user_service.get_user(user_id=uuid4())

        assert user is None

    def test_get_deleted_user(self, user_service, active_user):
        """Test getting soft-deleted user."""
        # Soft delete
        user_service.soft_delete_user(user=active_user)

        # Should not be returned
        user = user_service.get_user(user_id=active_user.id)

        assert user is None


class TestUserUpdate:
    """Tests for user update."""

    def test_update_user_success(self, user_service, active_user):
        """Test successful user update."""
        updated = user_service.update_user(
            user=active_user,
            first_name='Updated',
            last_name='Name'
        )

        assert updated.first_name == 'Updated'
        assert updated.last_name == 'Name'

    def test_update_user_email(self, user_service, active_user):
        """Test updating user email."""
        new_email = 'newemail@test.com'

        updated = user_service.update_user(
            user=active_user,
            email=new_email
        )

        assert updated.email == new_email

    def test_update_user_duplicate_email(self, user_service, active_user, create_user):
        """Test update fails with duplicate email."""
        other_user = create_user(email='other@test.com')

        with pytest.raises(Exception):
            user_service.update_user(
                user=active_user,
                email=other_user.email
            )

    def test_update_user_preserves_unchanged(self, user_service, active_user):
        """Test update preserves unchanged fields."""
        original_email = active_user.email

        updated = user_service.update_user(
            user=active_user,
            first_name='Updated'
        )

        assert updated.email == original_email


class TestUserDeletion:
    """Tests for user deletion."""

    def test_soft_delete_user(self, user_service, active_user):
        """Test soft deleting a user."""
        user_service.soft_delete_user(user=active_user)

        active_user.refresh_from_db()
        assert active_user.deleted_at is not None
        assert active_user.status == 'deleted'

    def test_soft_delete_preserves_data(self, user_service, active_user):
        """Test soft delete preserves user data."""
        original_email = active_user.email

        user_service.soft_delete_user(user=active_user)

        active_user.refresh_from_db()
        # Data should still be there
        assert active_user.email is not None

    def test_hard_delete_user(self, user_service, active_user):
        """Test hard deleting a user."""
        user_id = active_user.id

        user_service.hard_delete_user(user=active_user)

        assert not User.objects.filter(id=user_id).exists()


class TestUserStatusManagement:
    """Tests for user status management."""

    def test_activate_user(self, user_service, inactive_user):
        """Test activating a user."""
        user_service.activate_user(user=inactive_user)

        inactive_user.refresh_from_db()
        assert inactive_user.status == 'active'

    def test_deactivate_user(self, user_service, active_user):
        """Test deactivating a user."""
        user_service.deactivate_user(user=active_user)

        active_user.refresh_from_db()
        assert active_user.status == 'inactive'

    def test_suspend_user(self, user_service, active_user):
        """Test suspending a user."""
        user_service.suspend_user(
            user=active_user,
            reason='Policy violation'
        )

        active_user.refresh_from_db()
        assert active_user.status == 'suspended'

    def test_unsuspend_user(self, user_service, create_user):
        """Test unsuspending a user."""
        suspended_user = create_user(email='suspended@test.com', status='suspended')

        user_service.unsuspend_user(user=suspended_user)

        suspended_user.refresh_from_db()
        assert suspended_user.status == 'active'

    def test_unlock_user(self, user_service, locked_user):
        """Test unlocking a user."""
        user_service.unlock_user(user=locked_user)

        locked_user.refresh_from_db()
        assert locked_user.status == 'active'
        assert locked_user.locked_until is None
        assert locked_user.failed_login_attempts == 0


class TestUserListing:
    """Tests for user listing."""

    def test_list_users(self, user_service, organization_users):
        """Test listing all users."""
        users = user_service.list_users()

        assert len(users) >= len(organization_users)

    def test_list_users_by_organization(self, user_service, organization_users, organization_id):
        """Test listing users by organization."""
        users = user_service.list_users(organization_id=organization_id)

        assert len(users) == len(organization_users)
        for user in users:
            assert user.organization_id == organization_id

    def test_list_users_by_status(self, user_service, active_user, inactive_user):
        """Test listing users by status."""
        users = user_service.list_users(status='active')

        for user in users:
            assert user.status == 'active'

    def test_list_users_pagination(self, user_service, organization_users):
        """Test user listing with pagination."""
        users = user_service.list_users(limit=2, offset=0)

        assert len(users) <= 2


class TestUserSearch:
    """Tests for user search."""

    def test_search_by_email(self, user_service, active_user):
        """Test searching users by email."""
        users = user_service.search_users(query=active_user.email)

        assert len(users) >= 1
        assert active_user.id in [u.id for u in users]

    def test_search_by_name(self, user_service, active_user):
        """Test searching users by name."""
        users = user_service.search_users(query=active_user.first_name)

        assert len(users) >= 1
        assert active_user.id in [u.id for u in users]

    def test_search_partial_match(self, user_service, active_user):
        """Test partial match search."""
        # Search with partial email
        partial = active_user.email[:5]
        users = user_service.search_users(query=partial)

        assert active_user.id in [u.id for u in users]

    def test_search_no_results(self, user_service):
        """Test search with no results."""
        users = user_service.search_users(query='nonexistentemail12345@test.com')

        assert len(users) == 0


class TestBulkOperations:
    """Tests for bulk operations."""

    def test_bulk_update_status(self, user_service, organization_users):
        """Test bulk status update."""
        user_ids = [u.id for u in organization_users[:3]]

        result = user_service.bulk_update_status(
            user_ids=user_ids,
            status='suspended',
            reason='Bulk suspension'
        )

        assert result['updated_count'] == 3

        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            assert user.status == 'suspended'

    def test_bulk_delete(self, user_service, organization_users):
        """Test bulk soft delete."""
        user_ids = [u.id for u in organization_users[:2]]

        result = user_service.bulk_delete(user_ids=user_ids)

        assert result['deleted_count'] == 2

        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            assert user.deleted_at is not None

    def test_bulk_assign_organization(self, user_service, create_user):
        """Test bulk organization assignment."""
        users = [create_user(email=f'bulk{i}@test.com') for i in range(3)]
        user_ids = [u.id for u in users]
        new_org_id = uuid4()

        result = user_service.bulk_update_organization(
            user_ids=user_ids,
            organization_id=new_org_id
        )

        assert result['updated_count'] == 3

        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            assert user.organization_id == new_org_id


class TestUserStatistics:
    """Tests for user statistics."""

    def test_get_user_count(self, user_service, organization_users, organization_id):
        """Test getting user count."""
        count = user_service.get_user_count(organization_id=organization_id)

        assert count == len(organization_users)

    def test_get_user_count_by_status(self, user_service, active_user, inactive_user):
        """Test getting user count by status."""
        stats = user_service.get_user_statistics()

        assert 'by_status' in stats
        assert 'active' in stats['by_status']

    def test_get_recent_registrations(self, user_service, active_user):
        """Test getting recent registrations."""
        recent = user_service.get_recent_registrations(days=7)

        assert len(recent) >= 1


class TestUserValidation:
    """Tests for user validation."""

    def test_validate_email_format(self, user_service):
        """Test email format validation."""
        with pytest.raises(Exception):
            user_service.create_user(
                email='invalid-email',
                first_name='Test',
                last_name='User',
                password='SecurePass123!'
            )

    def test_validate_required_fields(self, user_service):
        """Test required field validation."""
        with pytest.raises(Exception):
            user_service.create_user(
                email='test@test.com',
                first_name='',  # Empty
                last_name='User',
                password='SecurePass123!'
            )

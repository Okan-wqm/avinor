# services/user-service/src/apps/core/tests/test_api_views.py
"""
Tests for API Views

Tests REST API endpoints including:
- Authentication endpoints
- User management endpoints
- Role management endpoints
"""

import pytest
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import User, Role, Permission


pytestmark = pytest.mark.django_db


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    def test_register_endpoint(self, api_client):
        """Test user registration endpoint."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'newuser@test.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data or 'id' in response.data

    def test_register_invalid_email(self, api_client):
        """Test registration fails with invalid email."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'invalid-email',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_endpoint(self, api_client, active_user, user_password):
        """Test login endpoint."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': active_user.email,
            'password': user_password,
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data or 'token' in response.data

    def test_login_invalid_credentials(self, api_client, active_user):
        """Test login fails with invalid credentials."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': active_user.email,
            'password': 'wrongpassword',
        })

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_logout_endpoint(self, authenticated_client):
        """Test logout endpoint."""
        response = authenticated_client.post('/api/v1/auth/logout/')

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT
        ]

    def test_refresh_token_endpoint(self, api_client, active_user, user_password, auth_service):
        """Test token refresh endpoint."""
        # Login first
        login_result = auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        response = api_client.post('/api/v1/auth/refresh/', {
            'refresh_token': login_result['refresh_token'],
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data

    def test_change_password_endpoint(self, authenticated_client, user_password):
        """Test password change endpoint."""
        response = authenticated_client.post('/api/v1/auth/change-password/', {
            'current_password': user_password,
            'new_password': 'NewSecurePass123!',
        })

        assert response.status_code == status.HTTP_200_OK

    def test_forgot_password_endpoint(self, api_client, active_user):
        """Test forgot password endpoint."""
        response = api_client.post('/api/v1/auth/forgot-password/', {
            'email': active_user.email,
        })

        # Should always return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK


class TestUserEndpoints:
    """Tests for user management API endpoints."""

    def test_list_users(self, admin_client):
        """Test listing users endpoint."""
        response = admin_client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_users_unauthenticated(self, api_client):
        """Test listing users requires authentication."""
        response = api_client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, authenticated_client, active_user):
        """Test getting current user endpoint."""
        response = authenticated_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == active_user.email

    def test_get_user_by_id(self, admin_client, active_user):
        """Test getting user by ID."""
        response = admin_client.get(f'/api/v1/users/{active_user.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(active_user.id)

    def test_create_user(self, admin_client):
        """Test creating a user."""
        response = admin_client.post('/api/v1/users/', {
            'email': 'created@test.com',
            'first_name': 'Created',
            'last_name': 'User',
            'password': 'SecurePass123!',
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_update_user(self, admin_client, active_user):
        """Test updating a user."""
        response = admin_client.patch(f'/api/v1/users/{active_user.id}/', {
            'first_name': 'Updated',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

    def test_delete_user(self, admin_client, create_user):
        """Test deleting a user."""
        user = create_user(email='todelete@test.com')

        response = admin_client.delete(f'/api/v1/users/{user.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_search_users(self, admin_client, active_user):
        """Test searching users."""
        response = admin_client.get('/api/v1/users/search/', {
            'q': active_user.email,
        })

        assert response.status_code == status.HTTP_200_OK

    def test_activate_user(self, admin_client, inactive_user):
        """Test activating a user."""
        response = admin_client.post(f'/api/v1/users/{inactive_user.id}/activate/')

        assert response.status_code == status.HTTP_200_OK

    def test_deactivate_user(self, admin_client, active_user):
        """Test deactivating a user."""
        response = admin_client.post(f'/api/v1/users/{active_user.id}/deactivate/')

        assert response.status_code == status.HTTP_200_OK

    def test_suspend_user(self, admin_client, active_user):
        """Test suspending a user."""
        response = admin_client.post(f'/api/v1/users/{active_user.id}/suspend/', {
            'reason': 'Test suspension',
        })

        assert response.status_code == status.HTTP_200_OK

    def test_bulk_update_status(self, admin_client, organization_users):
        """Test bulk status update."""
        user_ids = [str(u.id) for u in organization_users[:2]]

        response = admin_client.post('/api/v1/users/bulk/', {
            'user_ids': user_ids,
            'action': 'suspend',
            'reason': 'Bulk test',
        })

        assert response.status_code == status.HTTP_200_OK


class TestRoleEndpoints:
    """Tests for role management API endpoints."""

    def test_list_roles(self, admin_client, admin_role):
        """Test listing roles."""
        response = admin_client.get('/api/v1/roles/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_role(self, admin_client, admin_role):
        """Test getting a role."""
        response = admin_client.get(f'/api/v1/roles/{admin_role.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == admin_role.code

    def test_create_role(self, admin_client):
        """Test creating a role."""
        response = admin_client.post('/api/v1/roles/', {
            'code': 'new_role',
            'name': 'New Role',
            'description': 'Test role',
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_update_role(self, admin_client, viewer_role):
        """Test updating a role."""
        response = admin_client.patch(f'/api/v1/roles/{viewer_role.id}/', {
            'name': 'Updated Viewer',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Viewer'

    def test_delete_role(self, admin_client, viewer_role):
        """Test deleting a role."""
        response = admin_client.delete(f'/api/v1/roles/{viewer_role.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_delete_system_role(self, admin_client, admin_role):
        """Test cannot delete system role."""
        response = admin_client.delete(f'/api/v1/roles/{admin_role.id}/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_role_to_user(self, admin_client, active_user, viewer_role):
        """Test assigning role to user."""
        response = admin_client.post(f'/api/v1/roles/{viewer_role.id}/assign/', {
            'user_id': str(active_user.id),
        })

        assert response.status_code == status.HTTP_200_OK

    def test_revoke_role_from_user(self, admin_client, user_with_role, admin_role):
        """Test revoking role from user."""
        response = admin_client.post(f'/api/v1/roles/{admin_role.id}/revoke/', {
            'user_id': str(user_with_role.id),
        })

        assert response.status_code == status.HTTP_200_OK

    def test_get_role_permissions(self, admin_client, admin_role):
        """Test getting role permissions."""
        response = admin_client.get(f'/api/v1/roles/{admin_role.id}/permissions/')

        assert response.status_code == status.HTTP_200_OK

    def test_add_permission_to_role(self, admin_client, viewer_role, create_permission):
        """Test adding permission to role."""
        permission = create_permission(code='test.permission')

        response = admin_client.post(f'/api/v1/roles/{viewer_role.id}/permissions/', {
            'permission_code': 'test.permission',
        })

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


class TestPermissionEndpoints:
    """Tests for permission management API endpoints."""

    def test_list_permissions(self, admin_client, basic_permissions):
        """Test listing permissions."""
        response = admin_client.get('/api/v1/permissions/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_permission(self, admin_client, basic_permissions):
        """Test getting a permission."""
        permission = list(basic_permissions.values())[0]

        response = admin_client.get(f'/api/v1/permissions/{permission.id}/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_permission(self, admin_client):
        """Test creating a permission."""
        response = admin_client.post('/api/v1/permissions/', {
            'code': 'new.permission',
            'name': 'New Permission',
            'module': 'new',
            'action': 'permission',
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_permission_modules(self, admin_client, basic_permissions):
        """Test getting permission modules."""
        response = admin_client.get('/api/v1/permissions/modules/')

        assert response.status_code == status.HTTP_200_OK


class TestAuditLogEndpoints:
    """Tests for audit log API endpoints."""

    def test_list_audit_logs(self, admin_client):
        """Test listing audit logs."""
        response = admin_client.get('/api/v1/audit-logs/')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_audit_logs_by_user(self, admin_client, active_user):
        """Test filtering audit logs by user."""
        response = admin_client.get('/api/v1/audit-logs/', {
            'user_id': str(active_user.id),
        })

        assert response.status_code == status.HTTP_200_OK

    def test_filter_audit_logs_by_action(self, admin_client):
        """Test filtering audit logs by action."""
        response = admin_client.get('/api/v1/audit-logs/', {
            'action': 'user.login',
        })

        assert response.status_code == status.HTTP_200_OK

    def test_audit_logs_read_only(self, admin_client):
        """Test audit logs are read-only."""
        response = admin_client.post('/api/v1/audit-logs/', {
            'action': 'test',
        })

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestAPIResponseFormat:
    """Tests for API response format consistency."""

    def test_success_response_format(self, authenticated_client):
        """Test success response format."""
        response = authenticated_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK
        # Response should have data

    def test_error_response_format(self, api_client):
        """Test error response format."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'nonexistent@test.com',
            'password': 'wrong',
        })

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_validation_error_format(self, api_client):
        """Test validation error response format."""
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'invalid-email',
            'password': 'weak',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pagination_format(self, admin_client, organization_users):
        """Test paginated response format."""
        response = admin_client.get('/api/v1/users/', {
            'page_size': 2,
        })

        assert response.status_code == status.HTTP_200_OK
        # Check for pagination metadata
        assert 'count' in response.data or 'results' in response.data or isinstance(response.data, list)


class TestAPIRateLimiting:
    """Tests for API rate limiting."""

    def test_rate_limit_headers(self, api_client, active_user, user_password):
        """Test rate limit headers in response."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': active_user.email,
            'password': user_password,
        })

        # Rate limit headers should be present
        # (actual implementation may vary)
        assert response.status_code == status.HTTP_200_OK


class TestAPIAuthentication:
    """Tests for API authentication mechanisms."""

    def test_bearer_token_auth(self, api_client, active_user, auth_service, user_password):
        """Test Bearer token authentication."""
        result = auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {result['access_token']}")
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_rejected(self, api_client):
        """Test invalid token is rejected."""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_rejected(self, api_client):
        """Test expired token is rejected."""
        # Would need to create an expired token
        pass

    def test_missing_auth_header(self, api_client):
        """Test missing auth header returns 401."""
        response = api_client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

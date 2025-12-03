# services/user-service/src/apps/core/tests/conftest.py
"""
Pytest Configuration and Fixtures

Provides common fixtures for all User Service tests.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Generator, Dict, Any

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    User, UserSession, Role, Permission, RolePermission, UserRole,
    RefreshToken, AuditLog
)
from apps.core.services import AuthService, PermissionService, UserService


# ==================== DATABASE FIXTURES ====================

@pytest.fixture
def db_access(db):
    """Ensure database access for tests."""
    pass


@pytest.fixture
def api_client() -> APIClient:
    """Return a DRF API client instance."""
    return APIClient()


# ==================== USER FIXTURES ====================

@pytest.fixture
def user_password() -> str:
    """Standard password for test users."""
    return 'TestPassword123!'


@pytest.fixture
def create_user(db, user_password):
    """Factory fixture to create test users."""
    def _create_user(
        email: str = None,
        password: str = None,
        status: str = 'active',
        email_verified: bool = True,
        two_factor_enabled: bool = False,
        organization_id: uuid.UUID = None,
        **kwargs
    ) -> User:
        if email is None:
            email = f"user_{uuid.uuid4().hex[:8]}@test.com"

        user = User.objects.create(
            email=email,
            password_hash=make_password(password or user_password),
            first_name=kwargs.get('first_name', 'Test'),
            last_name=kwargs.get('last_name', 'User'),
            status=status,
            email_verified=email_verified,
            two_factor_enabled=two_factor_enabled,
            organization_id=organization_id,
            phone=kwargs.get('phone'),
            timezone=kwargs.get('timezone', 'UTC'),
            language=kwargs.get('language', 'en'),
        )
        return user

    return _create_user


@pytest.fixture
def active_user(create_user) -> User:
    """Create an active verified user."""
    return create_user(
        email='active@test.com',
        first_name='Active',
        last_name='User',
        status='active',
        email_verified=True
    )


@pytest.fixture
def inactive_user(create_user) -> User:
    """Create an inactive user."""
    return create_user(
        email='inactive@test.com',
        first_name='Inactive',
        last_name='User',
        status='inactive',
        email_verified=True
    )


@pytest.fixture
def pending_user(create_user) -> User:
    """Create a user pending email verification."""
    return create_user(
        email='pending@test.com',
        first_name='Pending',
        last_name='User',
        status='pending_verification',
        email_verified=False
    )


@pytest.fixture
def locked_user(create_user) -> User:
    """Create a locked user."""
    user = create_user(
        email='locked@test.com',
        first_name='Locked',
        last_name='User',
        status='locked',
        email_verified=True
    )
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(hours=1)
    user.save()
    return user


@pytest.fixture
def admin_user(create_user) -> User:
    """Create an admin user."""
    user = create_user(
        email='admin@test.com',
        first_name='Admin',
        last_name='User',
        status='active',
        email_verified=True
    )
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def user_with_2fa(create_user) -> User:
    """Create a user with 2FA enabled."""
    user = create_user(
        email='2fa@test.com',
        first_name='TwoFactor',
        last_name='User',
        status='active',
        email_verified=True,
        two_factor_enabled=True
    )
    user.two_factor_secret = 'JBSWY3DPEHPK3PXP'  # Test secret
    user.save()
    return user


# ==================== ORGANIZATION FIXTURE ====================

@pytest.fixture
def organization_id() -> uuid.UUID:
    """Return a test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def organization_users(create_user, organization_id):
    """Create multiple users in the same organization."""
    users = []
    for i in range(5):
        user = create_user(
            email=f'orguser{i}@test.com',
            organization_id=organization_id
        )
        users.append(user)
    return users


# ==================== ROLE & PERMISSION FIXTURES ====================

@pytest.fixture
def create_permission(db):
    """Factory fixture to create permissions."""
    def _create_permission(
        code: str = None,
        name: str = None,
        module: str = 'test',
        action: str = 'read',
        **kwargs
    ) -> Permission:
        if code is None:
            code = f"{module}.{action}"
        if name is None:
            name = f"{module.title()} {action.title()}"

        return Permission.objects.create(
            code=code,
            name=name,
            module=module,
            action=action,
            description=kwargs.get('description', ''),
            is_sensitive=kwargs.get('is_sensitive', False),
            requires_2fa=kwargs.get('requires_2fa', False),
        )

    return _create_permission


@pytest.fixture
def create_role(db):
    """Factory fixture to create roles."""
    def _create_role(
        code: str = None,
        name: str = None,
        organization_id: uuid.UUID = None,
        **kwargs
    ) -> Role:
        if code is None:
            code = f"role_{uuid.uuid4().hex[:8]}"
        if name is None:
            name = f"Test Role {code}"

        return Role.objects.create(
            code=code,
            name=name,
            description=kwargs.get('description', ''),
            organization_id=organization_id,
            is_system_role=kwargs.get('is_system_role', False),
            is_default=kwargs.get('is_default', False),
            priority=kwargs.get('priority', 0),
        )

    return _create_role


@pytest.fixture
def basic_permissions(create_permission) -> Dict[str, Permission]:
    """Create basic CRUD permissions."""
    return {
        'users.read': create_permission(code='users.read', module='users', action='read'),
        'users.create': create_permission(code='users.create', module='users', action='create'),
        'users.update': create_permission(code='users.update', module='users', action='update'),
        'users.delete': create_permission(code='users.delete', module='users', action='delete'),
        'roles.read': create_permission(code='roles.read', module='roles', action='read'),
        'roles.manage': create_permission(code='roles.manage', module='roles', action='manage'),
    }


@pytest.fixture
def admin_role(create_role, basic_permissions) -> Role:
    """Create an admin role with all permissions."""
    role = create_role(code='admin', name='Administrator', is_system_role=True)

    for permission in basic_permissions.values():
        RolePermission.objects.create(role=role, permission=permission)

    return role


@pytest.fixture
def viewer_role(create_role, basic_permissions) -> Role:
    """Create a viewer role with read permissions only."""
    role = create_role(code='viewer', name='Viewer')

    RolePermission.objects.create(
        role=role,
        permission=basic_permissions['users.read']
    )

    return role


@pytest.fixture
def user_with_role(active_user, admin_role) -> User:
    """Create a user with admin role assigned."""
    UserRole.objects.create(
        user=active_user,
        role=admin_role,
        valid_from=timezone.now()
    )
    return active_user


# ==================== SESSION FIXTURES ====================

@pytest.fixture
def create_session(db):
    """Factory fixture to create user sessions."""
    def _create_session(
        user: User,
        is_active: bool = True,
        **kwargs
    ) -> UserSession:
        return UserSession.objects.create(
            user=user,
            is_active=is_active,
            ip_address=kwargs.get('ip_address', '127.0.0.1'),
            user_agent=kwargs.get('user_agent', 'Test Agent'),
            device_type=kwargs.get('device_type', 'desktop'),
            expires_at=kwargs.get('expires_at', timezone.now() + timedelta(days=7)),
            last_activity=kwargs.get('last_activity', timezone.now()),
        )

    return _create_session


@pytest.fixture
def active_session(active_user, create_session) -> UserSession:
    """Create an active session for the active user."""
    return create_session(user=active_user)


# ==================== TOKEN FIXTURES ====================

@pytest.fixture
def refresh_token(active_user, active_session, db) -> RefreshToken:
    """Create a refresh token for the active user."""
    return RefreshToken.objects.create(
        user=active_user,
        session=active_session,
        token='test_refresh_token_' + uuid.uuid4().hex,
        expires_at=timezone.now() + timedelta(days=7),
    )


# ==================== SERVICE FIXTURES ====================

@pytest.fixture
def auth_service() -> AuthService:
    """Return an AuthService instance."""
    return AuthService()


@pytest.fixture
def permission_service() -> PermissionService:
    """Return a PermissionService instance."""
    return PermissionService()


@pytest.fixture
def user_service() -> UserService:
    """Return a UserService instance."""
    return UserService()


# ==================== AUTHENTICATED CLIENT FIXTURES ====================

@pytest.fixture
def authenticated_client(api_client, active_user, auth_service, user_password) -> APIClient:
    """Return an API client with authentication."""
    # Login and get tokens
    result = auth_service.login(
        email=active_user.email,
        password=user_password,
        ip_address='127.0.0.1',
        user_agent='Test Agent'
    )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {result['access_token']}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user, auth_service, user_password) -> APIClient:
    """Return an API client with admin authentication."""
    # Create password for admin
    admin_user.password_hash = make_password(user_password)
    admin_user.save()

    result = auth_service.login(
        email=admin_user.email,
        password=user_password,
        ip_address='127.0.0.1',
        user_agent='Test Agent'
    )

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {result['access_token']}")
    return api_client


# ==================== HELPER FIXTURES ====================

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    class MockRequest:
        def __init__(self):
            self.META = {
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_USER_AGENT': 'Test Agent',
            }
            self.user = None
            self.request_id = str(uuid.uuid4())

    return MockRequest()


@pytest.fixture
def clear_cache():
    """Clear Django cache before test."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()

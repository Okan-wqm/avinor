# services/user-service/src/apps/core/tests/test_auth_service.py
"""
Tests for AuthService

Tests authentication flows including:
- Registration
- Login/Logout
- Password management
- Two-Factor Authentication
- Session management
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.utils import timezone

from apps.core.models import User, UserSession, RefreshToken
from apps.core.services import (
    AuthService,
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    TwoFactorRequiredError,
    PasswordPolicyError,
)


pytestmark = pytest.mark.django_db


class TestRegistration:
    """Tests for user registration."""

    def test_register_success(self, auth_service):
        """Test successful user registration."""
        result = auth_service.register(
            email='newuser@test.com',
            password='SecurePass123!',
            first_name='New',
            last_name='User'
        )

        assert result['user'] is not None
        assert result['user'].email == 'newuser@test.com'
        assert result['user'].status == 'pending_verification'
        assert not result['user'].email_verified

    def test_register_duplicate_email(self, auth_service, active_user):
        """Test registration fails with duplicate email."""
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.register(
                email=active_user.email,
                password='SecurePass123!',
                first_name='Duplicate',
                last_name='User'
            )

        assert 'already registered' in str(exc_info.value).lower()

    def test_register_weak_password(self, auth_service):
        """Test registration fails with weak password."""
        with pytest.raises(PasswordPolicyError):
            auth_service.register(
                email='weakpass@test.com',
                password='weak',
                first_name='Weak',
                last_name='Password'
            )

    def test_register_with_organization(self, auth_service, organization_id):
        """Test registration with organization."""
        result = auth_service.register(
            email='orguser@test.com',
            password='SecurePass123!',
            first_name='Org',
            last_name='User',
            organization_id=organization_id
        )

        assert result['user'].organization_id == organization_id


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, auth_service, active_user, user_password):
        """Test successful login."""
        result = auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        assert 'access_token' in result
        assert 'refresh_token' in result
        assert 'session_id' in result

    def test_login_invalid_email(self, auth_service, user_password):
        """Test login fails with invalid email."""
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email='nonexistent@test.com',
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

    def test_login_invalid_password(self, auth_service, active_user):
        """Test login fails with invalid password."""
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email=active_user.email,
                password='wrongpassword',
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

    def test_login_inactive_user(self, auth_service, inactive_user, user_password):
        """Test login fails for inactive user."""
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.login(
                email=inactive_user.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

        assert 'inactive' in str(exc_info.value).lower()

    def test_login_locked_user(self, auth_service, locked_user, user_password):
        """Test login fails for locked user."""
        with pytest.raises(AccountLockedError):
            auth_service.login(
                email=locked_user.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

    def test_login_unverified_email(self, auth_service, pending_user, user_password):
        """Test login fails for unverified email when required."""
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.login(
                email=pending_user.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

        assert 'verify' in str(exc_info.value).lower() or 'pending' in str(exc_info.value).lower()

    def test_login_creates_session(self, auth_service, active_user, user_password):
        """Test login creates a new session."""
        initial_count = UserSession.objects.filter(user=active_user).count()

        auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        assert UserSession.objects.filter(user=active_user).count() == initial_count + 1

    def test_login_increments_failed_attempts(self, auth_service, active_user):
        """Test failed login increments attempt counter."""
        initial_attempts = active_user.failed_login_attempts

        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email=active_user.email,
                password='wrongpassword',
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

        active_user.refresh_from_db()
        assert active_user.failed_login_attempts == initial_attempts + 1

    def test_login_locks_after_max_attempts(self, auth_service, active_user):
        """Test account gets locked after max failed attempts."""
        active_user.failed_login_attempts = 4  # One below max
        active_user.save()

        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email=active_user.email,
                password='wrongpassword',
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

        active_user.refresh_from_db()
        assert active_user.status == 'locked' or active_user.locked_until is not None


class TestLoginWith2FA:
    """Tests for login with Two-Factor Authentication."""

    def test_login_requires_2fa(self, auth_service, user_with_2fa, user_password):
        """Test login returns 2FA required for 2FA users."""
        with pytest.raises(TwoFactorRequiredError) as exc_info:
            auth_service.login(
                email=user_with_2fa.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )

        assert exc_info.value.temp_token is not None

    @patch('pyotp.TOTP.verify')
    def test_verify_2fa_success(self, mock_verify, auth_service, user_with_2fa, user_password):
        """Test successful 2FA verification."""
        mock_verify.return_value = True

        # First login to get temp token
        try:
            auth_service.login(
                email=user_with_2fa.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )
        except TwoFactorRequiredError as e:
            temp_token = e.temp_token

        # Verify 2FA
        result = auth_service.verify_2fa(
            temp_token=temp_token,
            code='123456',
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        assert 'access_token' in result
        assert 'refresh_token' in result

    def test_verify_2fa_invalid_code(self, auth_service, user_with_2fa, user_password):
        """Test 2FA verification fails with invalid code."""
        # Get temp token
        try:
            auth_service.login(
                email=user_with_2fa.email,
                password=user_password,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )
        except TwoFactorRequiredError as e:
            temp_token = e.temp_token

        with pytest.raises(AuthenticationError):
            auth_service.verify_2fa(
                temp_token=temp_token,
                code='000000',
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )


class TestLogout:
    """Tests for user logout."""

    def test_logout_success(self, auth_service, active_user, user_password):
        """Test successful logout."""
        # Login first
        login_result = auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        # Logout
        auth_service.logout(
            refresh_token=login_result['refresh_token'],
            session_id=login_result['session_id']
        )

        # Verify session is revoked
        session = UserSession.objects.get(id=login_result['session_id'])
        assert not session.is_active or session.revoked_at is not None

    def test_logout_all_sessions(self, auth_service, active_user, user_password, create_session):
        """Test logout from all sessions."""
        # Create multiple sessions
        sessions = [create_session(user=active_user) for _ in range(3)]

        auth_service.logout_all_sessions(user=active_user)

        # Verify all sessions are revoked
        for session in sessions:
            session.refresh_from_db()
            assert not session.is_active or session.revoked_at is not None


class TestTokenRefresh:
    """Tests for token refresh."""

    def test_refresh_token_success(self, auth_service, active_user, user_password):
        """Test successful token refresh."""
        # Login first
        login_result = auth_service.login(
            email=active_user.email,
            password=user_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        # Refresh tokens
        result = auth_service.refresh_tokens(
            refresh_token=login_result['refresh_token']
        )

        assert 'access_token' in result
        assert result['access_token'] != login_result['access_token']

    def test_refresh_token_invalid(self, auth_service):
        """Test refresh fails with invalid token."""
        with pytest.raises(AuthenticationError):
            auth_service.refresh_tokens(refresh_token='invalid_token')

    def test_refresh_token_expired(self, auth_service, active_user, active_session, db):
        """Test refresh fails with expired token."""
        # Create expired refresh token
        token = RefreshToken.objects.create(
            user=active_user,
            session=active_session,
            token='expired_token',
            expires_at=timezone.now() - timedelta(days=1)  # Expired
        )

        with pytest.raises(AuthenticationError):
            auth_service.refresh_tokens(refresh_token=token.token)


class TestPasswordManagement:
    """Tests for password management."""

    def test_change_password_success(self, auth_service, active_user, user_password):
        """Test successful password change."""
        new_password = 'NewSecurePass123!'

        auth_service.change_password(
            user=active_user,
            current_password=user_password,
            new_password=new_password
        )

        # Verify can login with new password
        result = auth_service.login(
            email=active_user.email,
            password=new_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        assert 'access_token' in result

    def test_change_password_wrong_current(self, auth_service, active_user):
        """Test password change fails with wrong current password."""
        with pytest.raises(InvalidCredentialsError):
            auth_service.change_password(
                user=active_user,
                current_password='wrongpassword',
                new_password='NewSecurePass123!'
            )

    def test_change_password_weak_new(self, auth_service, active_user, user_password):
        """Test password change fails with weak new password."""
        with pytest.raises(PasswordPolicyError):
            auth_service.change_password(
                user=active_user,
                current_password=user_password,
                new_password='weak'
            )

    def test_forgot_password(self, auth_service, active_user):
        """Test forgot password creates reset token."""
        result = auth_service.forgot_password(email=active_user.email)

        assert result.get('message') is not None
        # Verify token was created
        from apps.core.models import PasswordResetToken
        assert PasswordResetToken.objects.filter(user=active_user).exists()

    def test_reset_password_success(self, auth_service, active_user, db):
        """Test successful password reset."""
        from apps.core.models import PasswordResetToken

        # Create reset token
        token = PasswordResetToken.objects.create(
            user=active_user,
            token='reset_token_123',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        new_password = 'ResetPass123!'
        auth_service.reset_password(
            token=token.token,
            new_password=new_password
        )

        # Verify can login with new password
        result = auth_service.login(
            email=active_user.email,
            password=new_password,
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )

        assert 'access_token' in result


class TestSessionManagement:
    """Tests for session management."""

    def test_get_active_sessions(self, auth_service, active_user, create_session):
        """Test getting active sessions."""
        # Create sessions
        sessions = [create_session(user=active_user) for _ in range(3)]

        result = auth_service.get_active_sessions(user=active_user)

        assert len(result) >= 3

    def test_terminate_session(self, auth_service, active_user, create_session):
        """Test terminating a specific session."""
        session = create_session(user=active_user)

        auth_service.terminate_session(
            user=active_user,
            session_id=str(session.id)
        )

        session.refresh_from_db()
        assert not session.is_active or session.revoked_at is not None

    def test_terminate_session_wrong_user(self, auth_service, active_user, create_user, create_session):
        """Test cannot terminate another user's session."""
        other_user = create_user(email='other@test.com')
        session = create_session(user=other_user)

        with pytest.raises(AuthenticationError):
            auth_service.terminate_session(
                user=active_user,
                session_id=str(session.id)
            )

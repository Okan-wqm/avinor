# services/user-service/src/apps/core/services/auth_service.py
"""
Authentication Service - Comprehensive Business Logic Layer

Handles all authentication operations including:
- User registration with email verification
- Login with password validation and 2FA
- Token management (access, refresh, revocation)
- Password management (forgot, reset, change)
- Session management
- Account security (lockout, 2FA setup)
"""

import logging
import secrets
import pyotp
from typing import Dict, Optional, Tuple, List
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password

from apps.core.models import (
    User, UserSession, RefreshToken,
    PasswordResetToken, EmailVerificationToken,
    AuditLog, UserRole
)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    def __init__(self, message: str, code: str = 'auth_error', details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password"""
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, 'invalid_credentials')


class AccountLockedError(AuthenticationError):
    """Account is locked due to failed attempts"""
    def __init__(self, locked_until: timezone.datetime = None):
        message = "Account is temporarily locked due to too many failed login attempts"
        details = {'locked_until': locked_until.isoformat() if locked_until else None}
        super().__init__(message, 'account_locked', details)


class AccountInactiveError(AuthenticationError):
    """Account is not active"""
    def __init__(self, status: str):
        super().__init__(f"Account is {status}", 'account_inactive', {'status': status})


class TwoFactorRequiredError(AuthenticationError):
    """2FA verification required"""
    def __init__(self, temp_token: str, methods: List[str]):
        super().__init__(
            "Two-factor authentication required",
            '2fa_required',
            {'temp_token': temp_token, 'available_methods': methods}
        )


class InvalidTokenError(AuthenticationError):
    """Token is invalid or expired"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, 'invalid_token')


class PasswordPolicyError(AuthenticationError):
    """Password doesn't meet policy requirements"""
    def __init__(self, violations: List[str]):
        super().__init__(
            "Password does not meet security requirements",
            'password_policy',
            {'violations': violations}
        )


class AuthService:
    """
    Comprehensive authentication service implementing secure authentication flows.

    Features:
    - Secure password handling with policy enforcement
    - JWT-based authentication with refresh tokens
    - Two-factor authentication (TOTP, SMS, email)
    - Account lockout protection
    - Session management
    - Comprehensive audit logging
    """

    # Configuration
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    TEMP_TOKEN_EXPIRY_MINUTES = 5
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_HISTORY_COUNT = 5

    def __init__(self):
        self._load_settings()

    def _load_settings(self):
        """Load settings from Django settings"""
        auth_settings = getattr(settings, 'AUTH_SETTINGS', {})
        self.MAX_LOGIN_ATTEMPTS = auth_settings.get('MAX_LOGIN_ATTEMPTS', 5)
        self.LOCKOUT_DURATION_MINUTES = auth_settings.get('LOCKOUT_DURATION_MINUTES', 30)
        self.TEMP_TOKEN_EXPIRY_MINUTES = auth_settings.get('TEMP_TOKEN_EXPIRY_MINUTES', 5)
        self.PASSWORD_MIN_LENGTH = auth_settings.get('PASSWORD_MIN_LENGTH', 12)

    # ==================== REGISTRATION ====================

    @transaction.atomic
    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_id: str = None,
        **extra_fields
    ) -> Tuple[User, str]:
        """
        Register a new user account.

        Args:
            email: User's email address
            password: User's password (will be validated against policy)
            first_name: User's first name
            last_name: User's last name
            organization_id: Optional organization ID for multi-tenant
            **extra_fields: Additional user fields

        Returns:
            Tuple of (User, verification_token)

        Raises:
            AuthenticationError: If email is taken or password invalid
        """
        # Check if email is already taken
        if User.objects.filter(email__iexact=email).exists():
            raise AuthenticationError(
                "Email address is already registered",
                'email_taken'
            )

        # Validate password policy
        self._validate_password_policy(password)

        # Create user
        user = User(
            email=email.lower(),
            username=email.lower(),  # Use email as username
            first_name=first_name,
            last_name=last_name,
            organization_id=organization_id,
            status=User.Status.PENDING,
            is_active=False,
            **extra_fields
        )
        user.set_password(password)
        user.password_changed_at = timezone.now()
        user.save()

        # Create email verification token
        verification_token = EmailVerificationToken.create_for_user(user)

        # Assign default role
        self._assign_default_role(user)

        # Audit log
        AuditLog.log(
            action='register',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=None,  # User not authenticated yet
            organization_id=organization_id,
            risk_level='low',
            metadata={'registration_source': extra_fields.get('registration_source', 'web')}
        )

        # Publish event
        self._publish_event('user.registered', {
            'user_id': str(user.id),
            'email': user.email,
            'organization_id': str(organization_id) if organization_id else None,
        })

        logger.info(f"User registered: {user.email}")
        return user, verification_token.token

    def verify_email(self, token: str) -> User:
        """
        Verify user's email address using token.

        Args:
            token: Email verification token

        Returns:
            Verified User object

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(
                token=token
            )
        except EmailVerificationToken.DoesNotExist:
            raise InvalidTokenError("Invalid verification token")

        if not token_obj.is_valid:
            raise InvalidTokenError("Verification token has expired")

        user = token_obj.user

        # Mark token as used
        token_obj.use()

        # Activate user
        user.is_verified = True
        user.is_active = True
        user.status = User.Status.ACTIVE
        user.save(update_fields=['is_verified', 'is_active', 'status', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='email_verified',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            risk_level='low'
        )

        logger.info(f"Email verified: {user.email}")
        return user

    def resend_verification_email(self, email: str) -> Optional[str]:
        """
        Resend email verification token.

        Args:
            email: User's email address

        Returns:
            New verification token or None if user not found
        """
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None  # Don't reveal if email exists

        if user.is_verified:
            return None  # Already verified

        # Rate limiting
        cache_key = f"resend_verification:{user.id}"
        if cache.get(cache_key):
            raise AuthenticationError(
                "Please wait before requesting another verification email",
                'rate_limited'
            )
        cache.set(cache_key, True, timeout=60)  # 1 minute cooldown

        # Create new token
        token = EmailVerificationToken.create_for_user(user)

        logger.info(f"Verification email resent: {user.email}")
        return token.token

    # ==================== LOGIN ====================

    def login(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = '',
        device_info: str = ''
    ) -> Dict:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: User's password
            ip_address: Client IP address
            user_agent: Client user agent string
            device_info: Device information

        Returns:
            Dict with tokens and user info, or 2FA requirement

        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
            AccountInactiveError: If account is not active
            TwoFactorRequiredError: If 2FA is required
        """
        # Get user by email
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Log failed attempt for non-existent user (security)
            logger.warning(f"Login attempt for non-existent email: {email}")
            raise InvalidCredentialsError()

        # Check if account is locked
        if user.is_locked:
            raise AccountLockedError(user.locked_until)

        # Check account status
        if user.status == User.Status.DELETED:
            raise InvalidCredentialsError()  # Don't reveal deleted accounts

        if user.status == User.Status.SUSPENDED:
            raise AccountInactiveError('suspended')

        if user.status == User.Status.INACTIVE:
            raise AccountInactiveError('inactive')

        if not user.is_active:
            raise AccountInactiveError('inactive')

        # Verify password
        if not user.check_password(password):
            # Record failed attempt
            is_locked = user.record_login_failure(
                max_attempts=self.MAX_LOGIN_ATTEMPTS,
                lock_duration=self.LOCKOUT_DURATION_MINUTES
            )

            # Audit log
            AuditLog.log(
                action='login_failed',
                entity_type='user',
                entity_id=user.id,
                entity_name=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level='medium' if user.failed_login_attempts >= 3 else 'low',
                metadata={
                    'attempt_count': user.failed_login_attempts,
                    'locked': is_locked
                }
            )

            if is_locked:
                raise AccountLockedError(user.locked_until)

            remaining_attempts = self.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            raise InvalidCredentialsError(
                f"Invalid credentials. {remaining_attempts} attempts remaining."
            )

        # Check if email is verified (for pending accounts)
        if user.status == User.Status.PENDING and not user.is_verified:
            raise AuthenticationError(
                "Please verify your email address before logging in",
                'email_not_verified'
            )

        # Check if 2FA is enabled
        if user.two_factor_enabled:
            # Generate temporary token for 2FA flow
            temp_token = self._generate_temp_token(user.id, ip_address)

            available_methods = [user.two_factor_method]
            if user.two_factor_backup_codes:
                available_methods.append('backup_code')

            raise TwoFactorRequiredError(temp_token, available_methods)

        # Complete login
        return self._complete_login(user, ip_address, user_agent, device_info)

    def verify_2fa(
        self,
        temp_token: str,
        code: str,
        method: str = 'totp',
        ip_address: str = None,
        user_agent: str = '',
        device_info: str = ''
    ) -> Dict:
        """
        Verify two-factor authentication code.

        Args:
            temp_token: Temporary token from login
            code: 2FA code
            method: 2FA method (totp, sms, email, backup_code)
            ip_address: Client IP address
            user_agent: Client user agent
            device_info: Device information

        Returns:
            Dict with tokens and user info

        Raises:
            InvalidTokenError: If temp token is invalid
            AuthenticationError: If 2FA code is invalid
        """
        # Validate temp token
        user_id = self._validate_temp_token(temp_token, ip_address)
        if not user_id:
            raise InvalidTokenError("Invalid or expired session")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise InvalidTokenError("Invalid session")

        # Verify 2FA code
        is_valid = False

        if method == 'totp':
            is_valid = self._verify_totp(user, code)
        elif method == 'backup_code':
            is_valid = self._verify_backup_code(user, code)
        elif method == 'sms' or method == 'email':
            is_valid = self._verify_otp_code(user, code)

        if not is_valid:
            # Audit failed 2FA
            AuditLog.log(
                action='2fa_failed',
                entity_type='user',
                entity_id=user.id,
                entity_name=user.email,
                ip_address=ip_address,
                risk_level='high',
                metadata={'method': method}
            )
            raise AuthenticationError("Invalid verification code", '2fa_invalid')

        # Clear temp token
        self._clear_temp_token(temp_token)

        # Complete login
        return self._complete_login(user, ip_address, user_agent, device_info)

    def _complete_login(
        self,
        user: User,
        ip_address: str = None,
        user_agent: str = '',
        device_info: str = ''
    ) -> Dict:
        """
        Complete the login process after all verification.

        Creates session, generates tokens, updates login stats.
        """
        # Record successful login
        user.record_login_success(ip_address)

        # Create session
        session = UserSession.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            device_info=device_info[:255] if device_info else '',
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Generate tokens
        tokens = self._generate_tokens(
            user,
            session_id=str(session.id),
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Audit log
        AuditLog.log(
            action='login',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session.id,
            risk_level='low'
        )

        # Publish event
        self._publish_event('user.logged_in', {
            'user_id': str(user.id),
            'session_id': str(session.id),
            'ip_address': ip_address
        })

        logger.info(f"User logged in: {user.email}")

        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': 'Bearer',
            'expires_in': tokens['expires_in'],
            'user': self._serialize_user(user),
            'session_id': str(session.id)
        }

    # ==================== TOKEN MANAGEMENT ====================

    def refresh_tokens(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access token

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
        """
        try:
            token_obj = RefreshToken.objects.select_related('user').get(
                token=refresh_token
            )
        except RefreshToken.DoesNotExist:
            raise InvalidTokenError("Invalid refresh token")

        if not token_obj.is_valid:
            raise InvalidTokenError("Refresh token is expired or revoked")

        user = token_obj.user

        if not user.is_active or user.status != User.Status.ACTIVE:
            token_obj.revoke()
            raise InvalidTokenError("User account is not active")

        # Update last used
        token_obj.update_last_used()

        # Generate new access token only
        tokens = self._generate_tokens(
            user,
            refresh_token_obj=token_obj,
            generate_refresh=False
        )

        return {
            'access_token': tokens['access_token'],
            'refresh_token': refresh_token,  # Return same refresh token
            'token_type': 'Bearer',
            'expires_in': tokens['expires_in']
        }

    def logout(
        self,
        user: User,
        refresh_token: str = None,
        session_id: str = None,
        logout_all: bool = False
    ):
        """
        Logout user by revoking tokens and/or sessions.

        Args:
            user: User to logout
            refresh_token: Specific refresh token to revoke
            session_id: Specific session to end
            logout_all: If True, revoke all sessions and tokens
        """
        if logout_all:
            # Revoke all tokens
            RefreshToken.revoke_all_for_user(user)

            # End all sessions
            UserSession.objects.filter(
                user=user,
                is_active=True
            ).update(
                is_active=False,
                ended_at=timezone.now()
            )

            action = 'logout_all'
        else:
            # Revoke specific token
            if refresh_token:
                try:
                    token_obj = RefreshToken.objects.get(
                        token=refresh_token,
                        user=user
                    )
                    token_obj.revoke()
                except RefreshToken.DoesNotExist:
                    pass

            # End specific session
            if session_id:
                UserSession.objects.filter(
                    id=session_id,
                    user=user
                ).update(
                    is_active=False,
                    ended_at=timezone.now()
                )

            action = 'logout'

        # Audit log
        AuditLog.log(
            action=action,
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            session_id=session_id,
            risk_level='low'
        )

        logger.info(f"User logged out: {user.email} (all={logout_all})")

    def verify_access_token(self, token: str) -> Dict:
        """
        Verify an access token and return payload.

        Args:
            token: JWT access token

        Returns:
            Dict with token payload

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        try:
            from common.authentication import JWTTokenGenerator
            payload = JWTTokenGenerator.decode_token(token)

            return {
                'valid': True,
                'user_id': payload.get('sub'),
                'email': payload.get('email'),
                'organization_id': payload.get('organization_id'),
                'roles': payload.get('roles', []),
                'permissions': payload.get('permissions', []),
                'exp': payload.get('exp'),
                'session_id': payload.get('session_id')
            }
        except Exception as e:
            raise InvalidTokenError(str(e))

    # ==================== PASSWORD MANAGEMENT ====================

    def forgot_password(self, email: str, ip_address: str = None) -> Optional[str]:
        """
        Initiate password reset flow.

        Args:
            email: User's email address
            ip_address: Client IP address

        Returns:
            Reset token (for sending via email) or None if user not found
        """
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if email exists
            logger.info(f"Password reset requested for unknown email: {email}")
            return None

        # Rate limiting
        cache_key = f"password_reset:{user.id}"
        if cache.get(cache_key):
            raise AuthenticationError(
                "Please wait before requesting another password reset",
                'rate_limited'
            )
        cache.set(cache_key, True, timeout=60)  # 1 minute cooldown

        # Create reset token
        token = PasswordResetToken.create_for_user(user, ip_address)

        # Audit log
        AuditLog.log(
            action='password_reset_requested',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            ip_address=ip_address,
            risk_level='medium'
        )

        logger.info(f"Password reset requested: {user.email}")
        return token.token

    def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: str = None
    ) -> User:
        """
        Reset password using reset token.

        Args:
            token: Password reset token
            new_password: New password (will be validated)
            ip_address: Client IP address

        Returns:
            User object

        Raises:
            InvalidTokenError: If token is invalid or expired
            PasswordPolicyError: If password doesn't meet requirements
        """
        try:
            token_obj = PasswordResetToken.objects.select_related('user').get(
                token=token
            )
        except PasswordResetToken.DoesNotExist:
            raise InvalidTokenError("Invalid password reset token")

        if not token_obj.is_valid:
            raise InvalidTokenError("Password reset token has expired")

        user = token_obj.user

        # Validate new password
        self._validate_password_policy(new_password, user)

        # Check password history
        if not user.check_password_history(new_password):
            raise PasswordPolicyError(
                ["Password was recently used. Please choose a different password."]
            )

        # Update password
        user.add_password_to_history(user.password)
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save()

        # Mark token as used
        token_obj.use()

        # Revoke all refresh tokens (security measure)
        RefreshToken.revoke_all_for_user(user)

        # Audit log
        AuditLog.log(
            action='password_reset',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            ip_address=ip_address,
            risk_level='high'
        )

        # Publish event
        self._publish_event('user.password_reset', {
            'user_id': str(user.id),
            'email': user.email
        })

        logger.info(f"Password reset completed: {user.email}")
        return user

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        ip_address: str = None
    ) -> User:
        """
        Change user's password (requires current password).

        Args:
            user: User object
            current_password: Current password for verification
            new_password: New password
            ip_address: Client IP address

        Returns:
            Updated User object

        Raises:
            AuthenticationError: If current password is wrong
            PasswordPolicyError: If new password doesn't meet requirements
        """
        # Verify current password
        if not user.check_password(current_password):
            raise AuthenticationError(
                "Current password is incorrect",
                'invalid_password'
            )

        # Validate new password
        self._validate_password_policy(new_password, user)

        # Check password history
        if not user.check_password_history(new_password):
            raise PasswordPolicyError(
                ["Password was recently used. Please choose a different password."]
            )

        # Update password
        user.add_password_to_history(user.password)
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save()

        # Audit log
        AuditLog.log(
            action='password_changed',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            ip_address=ip_address,
            risk_level='medium'
        )

        logger.info(f"Password changed: {user.email}")
        return user

    def _validate_password_policy(self, password: str, user: User = None) -> None:
        """
        Validate password against security policy.

        Raises PasswordPolicyError if password doesn't meet requirements.
        """
        violations = []

        # Minimum length
        if len(password) < self.PASSWORD_MIN_LENGTH:
            violations.append(
                f"Password must be at least {self.PASSWORD_MIN_LENGTH} characters"
            )

        # Must contain uppercase
        if not any(c.isupper() for c in password):
            violations.append("Password must contain at least one uppercase letter")

        # Must contain lowercase
        if not any(c.islower() for c in password):
            violations.append("Password must contain at least one lowercase letter")

        # Must contain digit
        if not any(c.isdigit() for c in password):
            violations.append("Password must contain at least one number")

        # Must contain special character
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        if not any(c in special_chars for c in password):
            violations.append("Password must contain at least one special character")

        # Cannot contain email/username
        if user:
            email_parts = user.email.lower().split('@')
            if email_parts[0] in password.lower():
                violations.append("Password cannot contain your email address")
            if user.username and user.username.lower() in password.lower():
                violations.append("Password cannot contain your username")

        # Check against common passwords
        common_passwords = ['password', '12345678', 'qwerty', 'letmein']
        if password.lower() in common_passwords:
            violations.append("Password is too common")

        if violations:
            raise PasswordPolicyError(violations)

    # ==================== TWO-FACTOR AUTHENTICATION ====================

    def setup_2fa(self, user: User, method: str = 'totp') -> Dict:
        """
        Initialize 2FA setup for user.

        Args:
            user: User object
            method: 2FA method (totp, sms, email)

        Returns:
            Dict with setup information (secret, QR code, etc.)
        """
        if method == 'totp':
            # Generate TOTP secret
            secret = pyotp.random_base32()

            # Generate provisioning URI for QR code
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.email,
                issuer_name=settings.APP_NAME if hasattr(settings, 'APP_NAME') else 'Avinor'
            )

            # Store secret temporarily (not enabled until confirmed)
            cache.set(f"2fa_setup:{user.id}", {
                'secret': secret,
                'method': method
            }, timeout=600)  # 10 minutes

            return {
                'method': method,
                'secret': secret,
                'provisioning_uri': provisioning_uri,
                'message': 'Scan the QR code with your authenticator app'
            }

        elif method == 'sms':
            # Would send verification code to phone
            return {
                'method': method,
                'message': 'Verification code will be sent to your phone'
            }

        elif method == 'email':
            return {
                'method': method,
                'message': 'Verification code will be sent to your email'
            }

        raise AuthenticationError(f"Invalid 2FA method: {method}", 'invalid_method')

    def confirm_2fa_setup(self, user: User, code: str) -> Dict:
        """
        Confirm 2FA setup with verification code.

        Args:
            user: User object
            code: Verification code from authenticator

        Returns:
            Dict with backup codes
        """
        # Get setup data from cache
        cache_key = f"2fa_setup:{user.id}"
        setup_data = cache.get(cache_key)

        if not setup_data:
            raise AuthenticationError(
                "2FA setup session expired. Please start again.",
                '2fa_setup_expired'
            )

        secret = setup_data['secret']
        method = setup_data['method']

        # Verify code
        if method == 'totp':
            totp = pyotp.TOTP(secret)
            if not totp.verify(code, valid_window=1):
                raise AuthenticationError(
                    "Invalid verification code",
                    '2fa_invalid'
                )

        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Enable 2FA
        user.enable_2fa(method, secret)
        user.two_factor_backup_codes = [
            make_password(code) for code in backup_codes
        ]
        user.save()

        # Clear setup cache
        cache.delete(cache_key)

        # Audit log
        AuditLog.log(
            action='2fa_enabled',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            risk_level='medium',
            metadata={'method': method}
        )

        logger.info(f"2FA enabled for user: {user.email}")

        return {
            'enabled': True,
            'method': method,
            'backup_codes': backup_codes,
            'message': 'Save these backup codes in a secure location'
        }

    def disable_2fa(self, user: User, password: str) -> None:
        """
        Disable 2FA for user (requires password confirmation).

        Args:
            user: User object
            password: User's password for confirmation
        """
        if not user.check_password(password):
            raise AuthenticationError(
                "Invalid password",
                'invalid_password'
            )

        user.disable_2fa()

        # Audit log
        AuditLog.log(
            action='2fa_disabled',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            risk_level='high'
        )

        logger.info(f"2FA disabled for user: {user.email}")

    def regenerate_backup_codes(self, user: User, password: str) -> List[str]:
        """
        Regenerate 2FA backup codes.

        Args:
            user: User object
            password: Password confirmation

        Returns:
            List of new backup codes
        """
        if not user.check_password(password):
            raise AuthenticationError(
                "Invalid password",
                'invalid_password'
            )

        if not user.two_factor_enabled:
            raise AuthenticationError(
                "2FA is not enabled",
                '2fa_not_enabled'
            )

        # Generate new backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        user.two_factor_backup_codes = [
            make_password(code) for code in backup_codes
        ]
        user.save()

        # Audit log
        AuditLog.log(
            action='2fa_backup_codes_regenerated',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            risk_level='medium'
        )

        return backup_codes

    def _verify_totp(self, user: User, code: str) -> bool:
        """Verify TOTP code."""
        if not user.two_factor_secret:
            return False

        totp = pyotp.TOTP(user.two_factor_secret)
        return totp.verify(code, valid_window=1)

    def _verify_backup_code(self, user: User, code: str) -> bool:
        """Verify and consume backup code."""
        if not user.two_factor_backup_codes:
            return False

        code_upper = code.upper().replace('-', '').replace(' ', '')

        for i, hashed_code in enumerate(user.two_factor_backup_codes):
            if check_password(code_upper, hashed_code):
                # Remove used code
                user.two_factor_backup_codes.pop(i)
                user.save(update_fields=['two_factor_backup_codes'])
                return True

        return False

    def _verify_otp_code(self, user: User, code: str) -> bool:
        """Verify SMS/Email OTP code from cache."""
        cache_key = f"otp_code:{user.id}"
        stored_code = cache.get(cache_key)

        if stored_code and stored_code == code:
            cache.delete(cache_key)
            return True

        return False

    # ==================== SESSION MANAGEMENT ====================

    def get_active_sessions(self, user: User) -> List[Dict]:
        """
        Get all active sessions for user.

        Args:
            user: User object

        Returns:
            List of session dictionaries
        """
        sessions = UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity')

        return [
            {
                'id': str(session.id),
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'device_info': session.device_info,
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat() if session.last_activity else None,
                'is_current': False  # Would be set by caller
            }
            for session in sessions
        ]

    def terminate_session(self, user: User, session_id: str) -> None:
        """
        Terminate a specific session.

        Args:
            user: User object
            session_id: Session ID to terminate
        """
        try:
            session = UserSession.objects.get(
                id=session_id,
                user=user,
                is_active=True
            )
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()

            # Revoke associated refresh tokens
            RefreshToken.objects.filter(
                user=user,
                is_revoked=False
            ).update(is_revoked=True, revoked_at=timezone.now())

            logger.info(f"Session terminated: {session_id}")

        except UserSession.DoesNotExist:
            pass

    def terminate_all_other_sessions(
        self,
        user: User,
        current_session_id: str
    ) -> int:
        """
        Terminate all sessions except current one.

        Args:
            user: User object
            current_session_id: Current session to keep

        Returns:
            Number of terminated sessions
        """
        count = UserSession.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            id=current_session_id
        ).update(
            is_active=False,
            ended_at=timezone.now()
        )

        logger.info(f"Terminated {count} sessions for user: {user.email}")
        return count

    # ==================== HELPER METHODS ====================

    def _generate_tokens(
        self,
        user: User,
        session_id: str = None,
        refresh_token_obj: RefreshToken = None,
        ip_address: str = None,
        user_agent: str = '',
        generate_refresh: bool = True
    ) -> Dict:
        """Generate JWT access token and optionally refresh token."""
        from common.authentication import JWTTokenGenerator

        # Get user roles and permissions
        roles = user.get_roles()
        permissions = user.get_permissions()

        # Generate access token
        access_token = JWTTokenGenerator.generate_access_token(
            user_id=str(user.id),
            email=user.email,
            username=user.username,
            organization_id=str(user.organization_id) if user.organization_id else None,
            roles=roles,
            permissions=permissions,
            session_id=session_id
        )

        access_expiry = settings.JWT_SETTINGS.get(
            'ACCESS_TOKEN_LIFETIME',
            timedelta(minutes=15)
        )
        expires_in = int(access_expiry.total_seconds())

        result = {
            'access_token': access_token,
            'expires_in': expires_in
        }

        if generate_refresh:
            if refresh_token_obj:
                result['refresh_token'] = refresh_token_obj.token
            else:
                refresh_token_obj = RefreshToken.create_for_user(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                result['refresh_token'] = refresh_token_obj.token

        return result

    def _generate_temp_token(self, user_id: str, ip_address: str = None) -> str:
        """Generate temporary token for 2FA flow."""
        token = secrets.token_urlsafe(32)
        cache_key = f"temp_token:{token}"

        cache.set(cache_key, {
            'user_id': str(user_id),
            'ip_address': ip_address,
            'created_at': timezone.now().isoformat()
        }, timeout=self.TEMP_TOKEN_EXPIRY_MINUTES * 60)

        return token

    def _validate_temp_token(self, token: str, ip_address: str = None) -> Optional[str]:
        """Validate temporary token and return user_id."""
        cache_key = f"temp_token:{token}"
        data = cache.get(cache_key)

        if not data:
            return None

        # Optional: Validate IP address matches
        # if ip_address and data.get('ip_address') != ip_address:
        #     return None

        return data.get('user_id')

    def _clear_temp_token(self, token: str) -> None:
        """Clear temporary token from cache."""
        cache.delete(f"temp_token:{token}")

    def _assign_default_role(self, user: User) -> None:
        """Assign default role to new user."""
        from apps.core.models import Role

        try:
            # Try organization-specific default role
            default_role = None
            if user.organization_id:
                default_role = Role.objects.filter(
                    organization_id=user.organization_id,
                    is_default=True
                ).first()

            # Fall back to system default role
            if not default_role:
                default_role = Role.objects.filter(
                    is_system_role=True,
                    is_default=True
                ).first()

            if default_role:
                UserRole.objects.create(
                    user=user,
                    role=default_role
                )
                logger.debug(f"Default role assigned to user: {user.email}")

        except Exception as e:
            logger.warning(f"Failed to assign default role: {e}")

    def _serialize_user(self, user: User) -> Dict:
        """Serialize user object for API response."""
        return {
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'organization_id': str(user.organization_id) if user.organization_id else None,
            'status': user.status,
            'is_verified': user.is_verified,
            'two_factor_enabled': user.two_factor_enabled,
            'avatar_url': user.avatar_url,
            'timezone': user.timezone,
            'language': user.language,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }

    def _publish_event(self, event_type: str, data: Dict) -> None:
        """Publish event to message bus."""
        try:
            from common.events import EventBus
            event_bus = EventBus()
            event_bus.publish(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    # ==================== MAINTENANCE METHODS ====================

    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from database.
        Called periodically by celery task.

        Returns:
            Number of deleted tokens
        """
        now = timezone.now()

        # Cleanup refresh tokens
        refresh_count = RefreshToken.objects.filter(
            expires_at__lt=now
        ).delete()[0]

        # Cleanup password reset tokens
        reset_count = PasswordResetToken.objects.filter(
            expires_at__lt=now
        ).delete()[0]

        # Cleanup email verification tokens
        verify_count = EmailVerificationToken.objects.filter(
            expires_at__lt=now
        ).delete()[0]

        total = refresh_count + reset_count + verify_count
        logger.info(f"Cleaned up {total} expired tokens")
        return total

    def cleanup_expired_sessions(self) -> int:
        """
        Deactivate expired sessions.

        Returns:
            Number of deactivated sessions
        """
        count = UserSession.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        ).update(
            is_active=False
        )

        logger.info(f"Deactivated {count} expired sessions")
        return count

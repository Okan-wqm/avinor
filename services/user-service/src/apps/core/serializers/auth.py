# services/user-service/src/apps/core/serializers/auth.py
"""
Authentication Serializers - Comprehensive serializers for authentication flows

Includes:
- Login/Logout serializers
- Token management serializers
- Password management serializers
- 2FA setup and verification serializers
- Email verification serializers
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.core.models import User


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login request.
    Validates email and password format.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower().strip()


class TwoFactorVerifySerializer(serializers.Serializer):
    """
    Serializer for 2FA verification during login.
    """

    temp_token = serializers.CharField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=10)
    method = serializers.ChoiceField(
        choices=[
            ('totp', 'Authenticator App'),
            ('sms', 'SMS'),
            ('email', 'Email'),
            ('backup_code', 'Backup Code'),
        ],
        default='totp'
    )


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer for authentication token response.
    """

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    user = serializers.DictField()
    session_id = serializers.UUIDField(required=False)


class TwoFactorRequiredResponseSerializer(serializers.Serializer):
    """
    Response when 2FA is required during login.
    """

    message = serializers.CharField(default="Two-factor authentication required")
    temp_token = serializers.CharField()
    available_methods = serializers.ListField(
        child=serializers.CharField()
    )


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer for token refresh request.
    """

    refresh_token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout request.
    """

    refresh_token = serializers.CharField(required=False)
    logout_all = serializers.BooleanField(default=False)


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change (authenticated user).
    """

    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        """Validate password against policy."""
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters.")
        if not any(c.isupper() for c in value):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            errors.append("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            errors.append("Password must contain at least one number.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in value):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate(self, attrs):
        """Validate password confirmation and current password."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords do not match."
            })

        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': "New password must be different from current password."
            })

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request (forgot password).
    """

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Normalize email. Don't reveal if email exists."""
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        """Validate password against policy."""
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters.")
        if not any(c.isupper() for c in value):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            errors.append("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            errors.append("Password must contain at least one number.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in value):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match."
            })
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """

    token = serializers.CharField(required=True)


class ResendVerificationSerializer(serializers.Serializer):
    """
    Serializer for resending verification email.
    """

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()


# ==================== 2FA SERIALIZERS ====================

class TwoFactorSetupSerializer(serializers.Serializer):
    """
    Serializer for initiating 2FA setup.
    """

    method = serializers.ChoiceField(
        choices=[
            ('totp', 'Authenticator App'),
            ('sms', 'SMS'),
            ('email', 'Email'),
        ],
        default='totp'
    )


class TwoFactorSetupResponseSerializer(serializers.Serializer):
    """
    Response for 2FA setup initiation (TOTP).
    """

    method = serializers.CharField()
    secret = serializers.CharField(required=False)
    provisioning_uri = serializers.CharField(required=False)
    message = serializers.CharField()


class TwoFactorConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming 2FA setup.
    """

    code = serializers.CharField(required=True, min_length=6, max_length=6)


class TwoFactorConfirmResponseSerializer(serializers.Serializer):
    """
    Response for successful 2FA setup confirmation.
    """

    enabled = serializers.BooleanField()
    method = serializers.CharField()
    backup_codes = serializers.ListField(
        child=serializers.CharField()
    )
    message = serializers.CharField()


class TwoFactorDisableSerializer(serializers.Serializer):
    """
    Serializer for disabling 2FA.
    """

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class BackupCodesRegenerateSerializer(serializers.Serializer):
    """
    Serializer for regenerating backup codes.
    """

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class BackupCodesResponseSerializer(serializers.Serializer):
    """
    Response containing new backup codes.
    """

    backup_codes = serializers.ListField(
        child=serializers.CharField()
    )
    message = serializers.CharField()


# ==================== SESSION SERIALIZERS ====================

class SessionListSerializer(serializers.Serializer):
    """
    Serializer for listing user sessions.
    """

    id = serializers.UUIDField()
    ip_address = serializers.IPAddressField(allow_null=True)
    user_agent = serializers.CharField()
    device_info = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_activity = serializers.DateTimeField(allow_null=True)
    is_current = serializers.BooleanField()


class SessionTerminateSerializer(serializers.Serializer):
    """
    Serializer for terminating a session.
    """

    session_id = serializers.UUIDField(required=True)


# ==================== REGISTRATION SERIALIZERS ====================

class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)

    # Optional
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        """Ensure email is unique."""
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        """Validate password against policy."""
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters.")
        if not any(c.isupper() for c in value):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            errors.append("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            errors.append("Password must contain at least one number.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in value):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return attrs


class RegisterResponseSerializer(serializers.Serializer):
    """
    Response for successful registration.
    """

    message = serializers.CharField()
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    verification_required = serializers.BooleanField(default=True)


# ==================== TOKEN VERIFICATION SERIALIZERS ====================

class TokenVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying access token.
    """

    token = serializers.CharField(required=True)


class TokenVerifyResponseSerializer(serializers.Serializer):
    """
    Response for token verification.
    """

    valid = serializers.BooleanField()
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    organization_id = serializers.UUIDField(allow_null=True)
    roles = serializers.ListField(child=serializers.CharField())
    permissions = serializers.ListField(child=serializers.CharField())
    exp = serializers.IntegerField()
    session_id = serializers.UUIDField(required=False)

# services/user-service/src/apps/core/models/token.py
"""
Token models for authentication and verification
"""

import uuid
import secrets
from django.db import models
from django.utils import timezone
from django.conf import settings


class RefreshToken(models.Model):
    """
    Refresh token for JWT authentication.
    Stored in database for revocation capability.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)
    jti = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='JWT Token ID'
    )

    # Device/Session info
    device_info = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')

    # Status
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'refresh_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_revoked']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"RefreshToken for {self.user.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_revoked and not self.is_expired

    def revoke(self):
        """Revoke this token"""
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_revoked', 'revoked_at'])

    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])

    @classmethod
    def create_for_user(cls, user, device_info='', ip_address=None, user_agent=''):
        """Create a new refresh token for user"""
        from datetime import timedelta

        jti = str(uuid.uuid4())
        token = secrets.token_urlsafe(64)
        expires_at = timezone.now() + settings.JWT_SETTINGS.get(
            'REFRESH_TOKEN_LIFETIME',
            timedelta(days=7)
        )

        return cls.objects.create(
            user=user,
            token=token,
            jti=jti,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )

    @classmethod
    def revoke_all_for_user(cls, user):
        """Revoke all tokens for a user"""
        cls.objects.filter(user=user, is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now()
        )


class PasswordResetToken(models.Model):
    """
    Token for password reset requests
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)

    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    # Security
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"PasswordResetToken for {self.user.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def use(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    @classmethod
    def create_for_user(cls, user, ip_address=None):
        """Create a new password reset token"""
        # Invalidate existing tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        token = secrets.token_urlsafe(32)
        expiry_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY', 24)
        expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)

        return cls.objects.create(
            user=user,
            token=token,
            ip_address=ip_address,
            expires_at=expires_at
        )


class EmailVerificationToken(models.Model):
    """
    Token for email verification
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    email = models.EmailField(help_text='Email to verify')
    token = models.CharField(max_length=255, unique=True, db_index=True)

    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'email_verification_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"EmailVerificationToken for {self.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def use(self):
        """Mark token as used and verify user email"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

        # Update user verification status
        if self.email == self.user.email:
            self.user.is_verified = True
            self.user.status = 'active'
            self.user.save(update_fields=['is_verified', 'status'])

    @classmethod
    def create_for_user(cls, user, email=None):
        """Create a new email verification token"""
        email = email or user.email

        # Invalidate existing tokens for this email
        cls.objects.filter(user=user, email=email, is_used=False).update(is_used=True)

        token = secrets.token_urlsafe(32)
        expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY', 48)
        expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)

        return cls.objects.create(
            user=user,
            email=email,
            token=token,
            expires_at=expires_at
        )

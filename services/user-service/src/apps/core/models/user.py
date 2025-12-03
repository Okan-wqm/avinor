# services/user-service/src/apps/core/models/user.py
"""
User and UserProfile models for Flight Training Management System
Comprehensive implementation with multi-tenant support, 2FA, and security features.
"""

import uuid
import hashlib
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
from django.conf import settings


class UserManager(BaseUserManager):
    """Custom user manager with organization support"""

    def create_user(self, email, organization_id, password=None, **extra_fields):
        """Create and return a regular user"""
        if not email:
            raise ValueError('Email adresi zorunludur')
        if not organization_id:
            raise ValueError('Organization ID zorunludur')

        email = self.normalize_email(email)
        extra_fields.setdefault('status', User.Status.PENDING)

        user = self.model(
            email=email,
            organization_id=organization_id,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, organization_id, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', User.Status.ACTIVE)
        extra_fields.setdefault('email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, organization_id, password, **extra_fields)

    def active(self):
        """Return only active, non-deleted users"""
        return self.filter(status=User.Status.ACTIVE, deleted_at__isnull=True)

    def for_organization(self, organization_id):
        """Return users for a specific organization"""
        return self.filter(organization_id=organization_id, deleted_at__isnull=True)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for Flight Training Management System.
    Multi-tenant with comprehensive security features.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        ACTIVE = 'active', 'Aktif'
        SUSPENDED = 'suspended', 'Askıya Alındı'
        INACTIVE = 'inactive', 'Pasif'
        DELETED = 'deleted', 'Silindi'

    class Gender(models.TextChoices):
        MALE = 'male', 'Erkek'
        FEMALE = 'female', 'Kadın'
        OTHER = 'other', 'Diğer'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Belirtmek İstemiyorum'

    class TwoFactorMethod(models.TextChoices):
        APP = 'app', 'Authenticator App'
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Multi-tenant Organization
    organization_id = models.UUIDField(
        db_index=True,
        help_text='Organization this user belongs to'
    )

    # Authentication
    email = models.EmailField(
        max_length=255,
        help_text='Primary email address for authentication'
    )
    # Password is inherited from AbstractBaseUser

    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True, null=True)

    # Contact
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number format: '+999999999'. Up to 15 digits allowed."
    )
    phone_primary = models.CharField(
        validators=[phone_regex],
        max_length=50,
        blank=True,
        null=True
    )
    phone_secondary = models.CharField(
        validators=[phone_regex],
        max_length=50,
        blank=True,
        null=True
    )
    phone_emergency = models.CharField(
        validators=[phone_regex],
        max_length=50,
        blank=True,
        null=True
    )
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)

    # Demographics
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
        null=True
    )
    nationality = models.CharField(max_length=2, blank=True, null=True)  # ISO 3166-1 alpha-2
    country_of_residence = models.CharField(max_length=2, blank=True, null=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True)

    # Official Documents
    national_id_number = models.CharField(max_length=50, blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_expiry = models.DateField(blank=True, null=True)
    passport_country = models.CharField(max_length=2, blank=True, null=True)

    # Profile
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Location
    primary_location_id = models.UUIDField(blank=True, null=True, db_index=True)

    # Preferences
    language_preference = models.CharField(max_length=10, default='en')
    timezone_preference = models.CharField(max_length=50, default='UTC')
    date_format_preference = models.CharField(max_length=20, default='YYYY-MM-DD')
    notification_preferences = models.JSONField(default=dict, blank=True)

    # Account Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(blank=True, null=True)

    # Login Info
    last_login_at = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)

    # Two-Factor Authentication
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_method = models.CharField(
        max_length=20,
        choices=TwoFactorMethod.choices,
        blank=True,
        null=True
    )
    two_factor_secret = models.CharField(max_length=255, blank=True, null=True)
    two_factor_backup_codes = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        null=True,
        size=10
    )
    two_factor_verified_at = models.DateTimeField(blank=True, null=True)

    # Password Policy
    password_changed_at = models.DateTimeField(blank=True, null=True)
    must_change_password = models.BooleanField(default=False)
    password_history = ArrayField(
        models.CharField(max_length=255),
        blank=True,
        null=True,
        size=5,
        help_text='Last 5 password hashes'
    )

    # Django Auth
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    updated_by = models.UUIDField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)  # Soft delete

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['organization_id', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['primary_location_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_login_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'email'],
                name='unique_org_email'
            ),
            models.CheckConstraint(
                check=models.Q(status__in=['pending', 'active', 'suspended', 'inactive', 'deleted']),
                name='valid_user_status'
            )
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def full_name(self):
        """Return the user's full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Return preferred name or first name"""
        return self.preferred_name or self.first_name

    @property
    def is_locked(self):
        """Check if account is locked"""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def is_active(self):
        """Django's is_active property"""
        return self.status == self.Status.ACTIVE and not self.is_locked and self.deleted_at is None

    @is_active.setter
    def is_active(self, value):
        """Allow setting is_active for Django compatibility"""
        if value:
            self.status = self.Status.ACTIVE
        else:
            self.status = self.Status.INACTIVE

    @property
    def lock_remaining_minutes(self):
        """Return remaining lock time in minutes"""
        if self.is_locked:
            remaining = (self.locked_until - timezone.now()).total_seconds() / 60
            return int(remaining) if remaining > 0 else 0
        return 0

    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country_code
        ]
        return ', '.join(filter(None, parts))

    # =========================================================================
    # AUTHENTICATION METHODS
    # =========================================================================

    def set_password(self, raw_password):
        """Override to track password history"""
        # Store current password hash in history before changing
        if self.password and self.password != '':
            if not self.password_history:
                self.password_history = []
            # Add current password to history, keep only last 5
            self.password_history = [self.password] + (self.password_history or [])[:4]

        super().set_password(raw_password)
        self.password_changed_at = timezone.now()
        self.must_change_password = False

    def check_password_history(self, raw_password):
        """Check if password was recently used"""
        from django.contrib.auth.hashers import check_password

        if not self.password_history:
            return False

        for old_hash in self.password_history:
            if check_password(raw_password, old_hash):
                return True
        return False

    # =========================================================================
    # ACCOUNT MANAGEMENT METHODS
    # =========================================================================

    def lock_account(self, duration_minutes=30):
        """Lock the account for specified duration"""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until', 'updated_at'])

    def unlock_account(self):
        """Unlock the account"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts', 'updated_at'])

    def record_login_success(self, ip_address=None):
        """Record successful login"""
        self.failed_login_attempts = 0
        self.last_login_at = timezone.now()
        self.last_login_ip = ip_address
        self.last_activity_at = timezone.now()
        self.locked_until = None
        self.save(update_fields=[
            'failed_login_attempts',
            'last_login_at',
            'last_login_ip',
            'last_activity_at',
            'locked_until',
            'updated_at'
        ])

    def record_login_failure(self, max_attempts=5, lock_duration=30):
        """Record failed login attempt"""
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lock_duration)

        self.save(update_fields=['failed_login_attempts', 'locked_until', 'updated_at'])
        return self.is_locked

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])

    # =========================================================================
    # SOFT DELETE METHODS
    # =========================================================================

    def soft_delete(self, deleted_by=None):
        """Soft delete the user"""
        self.status = self.Status.DELETED
        self.deleted_at = timezone.now()
        if deleted_by:
            self.updated_by = deleted_by
        self.save(update_fields=['status', 'deleted_at', 'updated_by', 'updated_at'])

    def restore(self):
        """Restore a soft-deleted user"""
        self.status = self.Status.INACTIVE
        self.deleted_at = None
        self.save(update_fields=['status', 'deleted_at', 'updated_at'])

    # =========================================================================
    # 2FA METHODS
    # =========================================================================

    def enable_2fa(self, method, secret):
        """Enable two-factor authentication"""
        import secrets as py_secrets

        self.two_factor_enabled = True
        self.two_factor_method = method
        self.two_factor_secret = secret
        self.two_factor_verified_at = timezone.now()

        # Generate backup codes
        self.two_factor_backup_codes = [
            py_secrets.token_hex(4).upper() for _ in range(10)
        ]

        self.save(update_fields=[
            'two_factor_enabled',
            'two_factor_method',
            'two_factor_secret',
            'two_factor_verified_at',
            'two_factor_backup_codes',
            'updated_at'
        ])

        return self.two_factor_backup_codes

    def disable_2fa(self):
        """Disable two-factor authentication"""
        self.two_factor_enabled = False
        self.two_factor_method = None
        self.two_factor_secret = None
        self.two_factor_backup_codes = None
        self.two_factor_verified_at = None
        self.save(update_fields=[
            'two_factor_enabled',
            'two_factor_method',
            'two_factor_secret',
            'two_factor_backup_codes',
            'two_factor_verified_at',
            'updated_at'
        ])

    def use_backup_code(self, code):
        """Use a backup code for 2FA"""
        if not self.two_factor_backup_codes:
            return False

        code_upper = code.upper().replace('-', '').replace(' ', '')

        for i, backup_code in enumerate(self.two_factor_backup_codes):
            if backup_code == code_upper:
                # Remove used code
                self.two_factor_backup_codes.pop(i)
                self.save(update_fields=['two_factor_backup_codes', 'updated_at'])
                return True

        return False

    # =========================================================================
    # ROLE & PERMISSION METHODS
    # =========================================================================

    def get_roles(self):
        """Get user's active roles"""
        from django.utils import timezone
        now = timezone.now()

        return list(
            self.user_roles.filter(
                models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=now),
                models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now),
                revoked_at__isnull=True
            ).select_related('role').values_list('role__code', flat=True)
        )

    def get_permissions(self):
        """Get user's permissions from all active roles"""
        from django.utils import timezone
        from .role import Permission

        now = timezone.now()
        role_ids = self.user_roles.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=now),
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now),
            revoked_at__isnull=True
        ).values_list('role_id', flat=True)

        return list(
            Permission.objects.filter(
                role_permissions__role_id__in=role_ids
            ).values_list('code', flat=True).distinct()
        )

    def has_permission(self, permission_code):
        """Check if user has a specific permission"""
        return permission_code in self.get_permissions()

    def has_any_permission(self, permission_codes):
        """Check if user has any of the specified permissions"""
        user_permissions = set(self.get_permissions())
        return bool(user_permissions.intersection(permission_codes))

    def has_all_permissions(self, permission_codes):
        """Check if user has all of the specified permissions"""
        user_permissions = set(self.get_permissions())
        return set(permission_codes).issubset(user_permissions)

    def has_role(self, role_code):
        """Check if user has a specific role"""
        return role_code in self.get_roles()

    # =========================================================================
    # EMAIL VERIFICATION
    # =========================================================================

    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        if self.status == self.Status.PENDING:
            self.status = self.Status.ACTIVE
        self.save(update_fields=[
            'email_verified',
            'email_verified_at',
            'status',
            'updated_at'
        ])

    def verify_phone(self):
        """Mark phone as verified"""
        self.phone_verified = True
        self.phone_verified_at = timezone.now()
        self.save(update_fields=['phone_verified', 'phone_verified_at', 'updated_at'])


class UserSession(models.Model):
    """
    User session model for tracking active sessions.
    Supports multiple devices and session management.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    # Token info
    refresh_token_hash = models.CharField(max_length=255, db_index=True)
    access_token_jti = models.CharField(max_length=255, blank=True, null=True)

    # Device info
    device_id = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)  # web, ios, android, desktop
    device_name = models.CharField(max_length=255, blank=True, null=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    browser_version = models.CharField(max_length=50, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    os_version = models.CharField(max_length=50, blank=True, null=True)

    # Location
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    # Revocation
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_reason = models.CharField(max_length=255, blank=True, null=True)
    revoked_by = models.UUIDField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_used_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['refresh_token_hash']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Session for {self.user.email} ({self.device_type or 'unknown'})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired and self.revoked_at is None

    def revoke(self, reason=None, revoked_by=None):
        """Revoke this session"""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.revoked_by = revoked_by
        self.save(update_fields=['is_active', 'revoked_at', 'revoked_reason', 'revoked_by'])

    def update_activity(self):
        """Update last used timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])

    @classmethod
    def hash_token(cls, token):
        """Hash a token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def revoke_all_for_user(cls, user, reason=None, revoked_by=None):
        """Revoke all sessions for a user"""
        cls.objects.filter(user=user, is_active=True).update(
            is_active=False,
            revoked_at=timezone.now(),
            revoked_reason=reason,
            revoked_by=revoked_by
        )

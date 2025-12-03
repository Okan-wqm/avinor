# services/organization-service/src/apps/core/models/organization.py
"""
Organization Model

Core model for multi-tenant organization management.
Represents flight schools, flying clubs, and training centers.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator
)


class Organization(models.Model):
    """
    Organization model representing a flight school or training center.

    This is the core entity for multi-tenant architecture. All other
    entities in the system belong to an organization.
    """

    class OrganizationType(models.TextChoices):
        FLIGHT_SCHOOL = 'flight_school', 'Flight School'
        FLYING_CLUB = 'flying_club', 'Flying Club'
        UNIVERSITY = 'university', 'University Aviation Program'
        SIMULATOR_CENTER = 'simulator_center', 'Simulator Center'
        AIRLINE_TRAINING = 'airline_training', 'Airline Training Center'

    class RegulatoryAuthority(models.TextChoices):
        EASA = 'EASA', 'EASA (European)'
        FAA = 'FAA', 'FAA (United States)'
        TCCA = 'TCCA', 'TCCA (Canada)'
        CASA = 'CASA', 'CASA (Australia)'
        CAAC = 'CAAC', 'CAAC (China)'
        SHGM = 'SHGM', 'SHGM (Turkey)'
        CAA_UK = 'CAA_UK', 'CAA (United Kingdom)'
        DGCA_INDIA = 'DGCA_INDIA', 'DGCA (India)'
        OTHER = 'OTHER', 'Other'

    class SubscriptionStatus(models.TextChoices):
        TRIAL = 'trial', 'Trial'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELLED = 'cancelled', 'Cancelled'
        SUSPENDED = 'suspended', 'Suspended'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Activation'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        CANCELLED = 'cancelled', 'Cancelled'

    class TimeTrackingMethod(models.TextChoices):
        BLOCK_TIME = 'block_time', 'Block Time'
        HOBBS_TIME = 'hobbs_time', 'Hobbs Time'
        TACH_TIME = 'tach_time', 'Tach Time'
        AIRBORNE_TIME = 'airborne_time', 'Airborne Time'

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text="Organization display name"
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legal registered name"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier"
    )
    organization_type = models.CharField(
        max_length=50,
        choices=OrganizationType.choices,
        default=OrganizationType.FLIGHT_SCHOOL
    )

    # Contact Information
    email = models.EmailField(help_text="Primary contact email")
    phone = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(
        max_length=2,
        validators=[RegexValidator(r'^[A-Z]{2}$', 'Must be 2-letter country code')],
        help_text="ISO 3166-1 alpha-2 country code"
    )

    # Coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )

    # Branding
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    logo_dark_url = models.URLField(max_length=500, blank=True, null=True)
    favicon_url = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(
        max_length=7,
        default='#3B82F6',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be valid hex color')]
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#1E40AF',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be valid hex color')]
    )
    accent_color = models.CharField(
        max_length=7,
        default='#10B981',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be valid hex color')]
    )

    # White Label
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True
    )
    custom_domain_verified = models.BooleanField(default=False)
    custom_email_domain = models.CharField(max_length=255, blank=True, null=True)

    # Regional Settings
    timezone = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY')
    time_format = models.CharField(max_length=10, default='24h')
    currency_code = models.CharField(max_length=3, default='USD')
    language = models.CharField(max_length=10, default='en')

    # Operational Settings
    fiscal_year_start_month = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    week_start_day = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0=Sunday, 1=Monday, etc."
    )

    # Booking Settings
    default_booking_duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(480)]
    )
    min_booking_notice_hours = models.IntegerField(
        default=2,
        validators=[MinValueValidator(0)]
    )
    max_booking_advance_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    cancellation_notice_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(0)]
    )
    late_cancellation_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    no_show_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Flight Settings
    default_preflight_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0)]
    )
    default_postflight_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0)]
    )
    time_tracking_method = models.CharField(
        max_length=20,
        choices=TimeTrackingMethod.choices,
        default=TimeTrackingMethod.BLOCK_TIME
    )

    # Finance Settings
    auto_charge_flights = models.BooleanField(default=True)
    require_positive_balance = models.BooleanField(default=True)
    minimum_balance_warning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00')
    )
    payment_terms_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0)]
    )

    # Regulatory Information
    regulatory_authority = models.CharField(
        max_length=20,
        choices=RegulatoryAuthority.choices,
        default=RegulatoryAuthority.EASA
    )
    ato_certificate_number = models.CharField(max_length=100, blank=True, null=True)
    ato_certificate_expiry = models.DateField(blank=True, null=True)
    ato_approval_type = models.CharField(max_length=50, blank=True, null=True)

    # Subscription (ForeignKey will be set after SubscriptionPlan is created)
    subscription_plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='organizations'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL
    )
    subscription_started_at = models.DateTimeField(blank=True, null=True)
    subscription_ends_at = models.DateTimeField(blank=True, null=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True)

    # Limits (from subscription plan, cached here for performance)
    max_users = models.IntegerField(default=10)
    max_aircraft = models.IntegerField(default=5)
    max_students = models.IntegerField(default=50)
    max_locations = models.IntegerField(default=3)
    storage_limit_gb = models.IntegerField(default=10)

    # Features (from subscription plan, cached here)
    features = models.JSONField(default=dict, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    updated_by = models.UUIDField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status'], condition=models.Q(deleted_at__isnull=True)),
            models.Index(fields=['country_code']),
            models.Index(fields=['regulatory_authority']),
            models.Index(fields=['subscription_status']),
            models.Index(
                fields=['custom_domain'],
                condition=models.Q(
                    custom_domain__isnull=False,
                    custom_domain_verified=True
                ),
                name='idx_org_verified_domain'
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def soft_delete(self, deleted_by: uuid.UUID = None):
        """Soft delete the organization."""
        self.deleted_at = timezone.now()
        self.status = self.Status.CANCELLED
        if deleted_by:
            self.updated_by = deleted_by
        self.save(update_fields=['deleted_at', 'status', 'updated_by', 'updated_at'])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE and not self.is_deleted

    @property
    def is_trial(self) -> bool:
        return self.subscription_status == self.SubscriptionStatus.TRIAL

    @property
    def is_trial_expired(self) -> bool:
        if not self.trial_ends_at:
            return False
        return timezone.now() > self.trial_ends_at

    @property
    def is_subscription_active(self) -> bool:
        return self.subscription_status in [
            self.SubscriptionStatus.ACTIVE,
            self.SubscriptionStatus.TRIAL
        ]

    @property
    def days_until_trial_end(self) -> int:
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)

    @property
    def full_address(self) -> str:
        parts = filter(None, [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country_code
        ])
        return ', '.join(parts)

    def has_feature(self, feature_name: str) -> bool:
        """Check if organization has a specific feature enabled."""
        return self.features.get(feature_name, False)

    def get_setting(self, category: str, key: str, default=None):
        """Get a setting value from organization settings."""
        try:
            setting = self.settings.get(category=category, key=key)
            return setting.value
        except OrganizationSetting.DoesNotExist:
            return default

    def can_add_user(self, current_count: int = None) -> bool:
        """Check if organization can add more users."""
        if self.max_users == -1:  # Unlimited
            return True
        if current_count is None:
            return True  # Caller should provide count
        return current_count < self.max_users

    def can_add_aircraft(self, current_count: int = None) -> bool:
        """Check if organization can add more aircraft."""
        if self.max_aircraft == -1:
            return True
        if current_count is None:
            return True
        return current_count < self.max_aircraft

    def can_add_location(self, current_count: int = None) -> bool:
        """Check if organization can add more locations."""
        if self.max_locations == -1:
            return True
        if current_count is None:
            return True
        return current_count < self.max_locations


class OrganizationSetting(models.Model):
    """
    Key-value settings for organizations.

    Allows flexible configuration without schema changes.
    Settings are grouped by category for easy management.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Setting category (e.g., booking, flight, finance)"
    )
    key = models.CharField(
        max_length=100,
        help_text="Setting key within category"
    )
    value = models.JSONField(
        help_text="Setting value (JSON)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Human-readable description"
    )
    is_secret = models.BooleanField(
        default=False,
        help_text="Whether this setting contains sensitive data"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization_settings'
        ordering = ['category', 'key']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'category', 'key'],
                name='unique_org_setting'
            )
        ]
        indexes = [
            models.Index(fields=['organization', 'category']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.category}.{self.key}"

    def get_display_value(self):
        """Get value for display, masking secrets."""
        if self.is_secret:
            return '********'
        return self.value

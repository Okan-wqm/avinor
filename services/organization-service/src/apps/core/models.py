"""
Organization Service Models.
"""
import uuid
from django.db import models
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """
    Flight school or flying club organization.
    """
    class OrganizationType(models.TextChoices):
        FLIGHT_SCHOOL = 'flight_school', 'Flight School'
        FLYING_CLUB = 'flying_club', 'Flying Club'
        COMMERCIAL = 'commercial', 'Commercial Operator'
        PRIVATE = 'private', 'Private'

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    organization_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        default=OrganizationType.FLIGHT_SCHOOL
    )
    description = models.TextField(blank=True)

    # Contact Information
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2)  # ISO 3166-1 alpha-2

    # Regulatory
    caa_approval_number = models.CharField(max_length=50, blank=True)
    ato_certificate_number = models.CharField(max_length=50, blank=True)

    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')  # ISO 4217

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )

    class Meta:
        db_table = 'organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['organization_type']),
            models.Index(fields=['country']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class OrganizationMember(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Organization membership linking users to organizations.
    """
    class MemberRole(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Administrator'
        MANAGER = 'manager', 'Manager'
        INSTRUCTOR = 'instructor', 'Instructor'
        STUDENT = 'student', 'Student'
        STAFF = 'staff', 'Staff'
        MEMBER = 'member', 'Member'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user_id = models.UUIDField()  # Reference to User Service
    role = models.CharField(
        max_length=20,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER
    )

    # Membership details
    joined_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Metadata
    employee_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = ['organization', 'user_id']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.organization.name} ({self.role})"


class Location(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Physical locations like airports, hangars, classrooms.
    """
    class LocationType(models.TextChoices):
        AIRPORT = 'airport', 'Airport'
        HANGAR = 'hangar', 'Hangar'
        CLASSROOM = 'classroom', 'Classroom'
        BRIEFING_ROOM = 'briefing_room', 'Briefing Room'
        OFFICE = 'office', 'Office'
        OTHER = 'other', 'Other'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=255)
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.OTHER
    )

    # Airport specific
    icao_code = models.CharField(max_length=4, blank=True)
    iata_code = models.CharField(max_length=3, blank=True)

    # Address
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    elevation_ft = models.IntegerField(null=True, blank=True)

    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'locations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['icao_code']),
            models.Index(fields=['location_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.location_type})"


class OrganizationSettings(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Organization-specific settings and configuration.
    """
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    # Booking settings
    booking_advance_days = models.IntegerField(default=30)
    booking_minimum_hours = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    booking_cancellation_hours = models.IntegerField(default=24)
    allow_student_self_booking = models.BooleanField(default=True)

    # Training settings
    default_lesson_duration_minutes = models.IntegerField(default=60)
    require_pre_flight_briefing = models.BooleanField(default=True)
    require_post_flight_debriefing = models.BooleanField(default=True)

    # Financial settings
    hourly_rate_aircraft = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hourly_rate_instructor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    require_prepayment = models.BooleanField(default=False)

    # Notification settings
    send_booking_reminders = models.BooleanField(default=True)
    reminder_hours_before = models.IntegerField(default=24)

    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'organization_settings'

    def __str__(self):
        return f"Settings for {self.organization.name}"

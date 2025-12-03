# services/booking-service/src/apps/core/models/booking_rule.py
"""
Booking Rule Model

Defines constraints and policies for reservations.
"""

import uuid
from decimal import Decimal

from django.db import models
from django.contrib.postgres.fields import ArrayField


class BookingRule(models.Model):
    """
    Booking rules and constraints.

    Rules can be global, per-aircraft, per-instructor, or per-location.
    Higher priority rules override lower priority ones.
    """

    class RuleType(models.TextChoices):
        GLOBAL = 'global', 'Global'
        AIRCRAFT = 'aircraft', 'Aircraft Specific'
        INSTRUCTOR = 'instructor', 'Instructor Specific'
        STUDENT = 'student', 'Student Specific'
        LOCATION = 'location', 'Location Specific'
        BOOKING_TYPE = 'booking_type', 'Booking Type Specific'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Rule Scope
    rule_type = models.CharField(
        max_length=50,
        choices=RuleType.choices
    )
    target_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Target resource ID (null for global rules)"
    )
    target_booking_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Target booking type (for booking_type rules)"
    )

    # Rule Name
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Time Constraints
    # ==========================================================================

    min_booking_duration = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum booking duration in minutes"
    )
    max_booking_duration = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum booking duration in minutes"
    )
    min_notice_hours = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum notice hours before booking"
    )
    max_advance_days = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum days in advance to book"
    )

    # ==========================================================================
    # Quantity Limits
    # ==========================================================================

    max_daily_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Maximum hours per day"
    )
    max_weekly_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Maximum hours per week"
    )
    max_daily_bookings = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum bookings per day"
    )
    max_concurrent_bookings = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum concurrent active bookings"
    )

    # ==========================================================================
    # Operating Hours
    # ==========================================================================

    operating_hours = models.JSONField(
        blank=True,
        null=True,
        help_text='{"monday": {"start": "08:00", "end": "20:00"}, ...}'
    )

    # ==========================================================================
    # Buffer Rules
    # ==========================================================================

    required_buffer_minutes = models.IntegerField(
        blank=True,
        null=True,
        help_text="Required buffer between bookings"
    )
    preflight_minutes = models.IntegerField(
        blank=True,
        null=True,
        default=30,
        help_text="Default preflight buffer"
    )
    postflight_minutes = models.IntegerField(
        blank=True,
        null=True,
        default=30,
        help_text="Default postflight buffer"
    )

    # ==========================================================================
    # Authorization
    # ==========================================================================

    who_can_book = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Role codes who can book"
    )
    requires_approval_from = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Role codes who must approve"
    )

    # ==========================================================================
    # Prerequisites
    # ==========================================================================

    required_qualifications = models.JSONField(
        blank=True,
        default=list,
        help_text="Required qualifications/ratings"
    )
    required_currency = models.JSONField(
        blank=True,
        default=list,
        help_text="Required currency items"
    )

    # ==========================================================================
    # Financial Rules
    # ==========================================================================

    require_positive_balance = models.BooleanField(default=True)
    minimum_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum account balance required"
    )
    require_prepayment = models.BooleanField(default=False)
    prepayment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Prepayment percentage required"
    )

    # ==========================================================================
    # Cancellation Rules
    # ==========================================================================

    free_cancellation_hours = models.IntegerField(
        default=24,
        help_text="Hours before start for free cancellation"
    )
    late_cancellation_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        help_text="Late cancellation fee percentage"
    )
    no_show_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="No-show fee percentage"
    )

    # ==========================================================================
    # Status and Priority
    # ==========================================================================

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority rules override lower ones"
    )

    # Validity Period
    effective_from = models.DateField(blank=True, null=True)
    effective_to = models.DateField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'booking_rules'
        ordering = ['-priority', 'rule_type']
        indexes = [
            models.Index(fields=['organization_id', 'rule_type']),
            models.Index(fields=['organization_id', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

    # ==========================================================================
    # Rule Application
    # ==========================================================================

    @classmethod
    def get_applicable_rules(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        booking_type: str = None
    ):
        """Get all applicable rules sorted by priority."""
        from django.db.models import Q
        from datetime import date

        today = date.today()

        # Base query for active rules
        queryset = cls.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=today)
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=today)
        )

        # Build filter for applicable rules
        conditions = Q(rule_type=cls.RuleType.GLOBAL)

        if aircraft_id:
            conditions |= Q(rule_type=cls.RuleType.AIRCRAFT, target_id=aircraft_id)

        if instructor_id:
            conditions |= Q(rule_type=cls.RuleType.INSTRUCTOR, target_id=instructor_id)

        if student_id:
            conditions |= Q(rule_type=cls.RuleType.STUDENT, target_id=student_id)

        if location_id:
            conditions |= Q(rule_type=cls.RuleType.LOCATION, target_id=location_id)

        if booking_type:
            conditions |= Q(rule_type=cls.RuleType.BOOKING_TYPE, target_booking_type=booking_type)

        return queryset.filter(conditions).order_by('-priority')

    @classmethod
    def get_merged_rules(
        cls,
        organization_id: uuid.UUID,
        **kwargs
    ) -> dict:
        """Get merged rules with higher priority taking precedence."""
        rules = cls.get_applicable_rules(organization_id, **kwargs)

        merged = {
            # Time constraints
            'min_booking_duration': None,
            'max_booking_duration': None,
            'min_notice_hours': None,
            'max_advance_days': None,
            # Quantity limits
            'max_daily_hours': None,
            'max_weekly_hours': None,
            'max_daily_bookings': None,
            'max_concurrent_bookings': None,
            # Buffer
            'required_buffer_minutes': None,
            'preflight_minutes': 30,
            'postflight_minutes': 30,
            # Financial
            'require_positive_balance': True,
            'minimum_balance': None,
            'require_prepayment': False,
            # Cancellation
            'free_cancellation_hours': 24,
            'late_cancellation_fee_percent': Decimal('50.00'),
            'no_show_fee_percent': Decimal('100.00'),
            # Authorization
            'who_can_book': [],
            'requires_approval_from': [],
            'required_qualifications': [],
            'required_currency': [],
        }

        # Apply rules in reverse priority order (lowest first)
        for rule in reversed(list(rules)):
            for field in merged.keys():
                value = getattr(rule, field, None)
                if value is not None and value != [] and value != {}:
                    merged[field] = value

        return merged

    def is_effective(self) -> bool:
        """Check if rule is currently effective."""
        from datetime import date

        if not self.is_active:
            return False

        today = date.today()

        if self.effective_from and today < self.effective_from:
            return False

        if self.effective_to and today > self.effective_to:
            return False

        return True

    def get_operating_hours_for_day(self, day_name: str) -> dict:
        """Get operating hours for a specific day."""
        if not self.operating_hours:
            return None

        day_lower = day_name.lower()
        return self.operating_hours.get(day_lower)

    def validate_duration(self, duration_minutes: int) -> tuple:
        """Validate booking duration against rule. Returns (valid, message)."""
        if self.min_booking_duration and duration_minutes < self.min_booking_duration:
            return False, f"Minimum booking duration is {self.min_booking_duration} minutes"

        if self.max_booking_duration and duration_minutes > self.max_booking_duration:
            return False, f"Maximum booking duration is {self.max_booking_duration} minutes"

        return True, None

    def validate_notice(self, hours_until_start: float) -> tuple:
        """Validate notice period. Returns (valid, message)."""
        if self.min_notice_hours and hours_until_start < self.min_notice_hours:
            return False, f"Minimum {self.min_notice_hours} hours notice required"

        return True, None

    def validate_advance(self, days_until_start: int) -> tuple:
        """Validate advance booking. Returns (valid, message)."""
        if self.max_advance_days and days_until_start > self.max_advance_days:
            return False, f"Cannot book more than {self.max_advance_days} days in advance"

        return True, None

    def calculate_cancellation_fee(
        self,
        hours_until_start: float,
        estimated_cost: Decimal
    ) -> Decimal:
        """Calculate cancellation fee based on timing."""
        if hours_until_start >= self.free_cancellation_hours:
            return Decimal('0.00')

        if hours_until_start <= 0:
            # No-show
            fee_percent = self.no_show_fee_percent
        else:
            # Late cancellation
            fee_percent = self.late_cancellation_fee_percent

        return estimated_cost * (fee_percent / Decimal('100.00'))

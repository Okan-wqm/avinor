# services/booking-service/src/apps/core/models/booking.py
"""
Booking Model

Core reservation management for aircraft, instructors, and resources.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Booking(models.Model):
    """
    Booking model for flight and training reservations.

    Handles aircraft, instructor, and student scheduling with
    conflict detection and status workflow.
    """

    class BookingType(models.TextChoices):
        FLIGHT = 'flight', 'Flight'
        SIMULATOR = 'simulator', 'Simulator'
        GROUND_TRAINING = 'ground_training', 'Ground Training'
        MAINTENANCE = 'maintenance', 'Maintenance'
        OTHER = 'other', 'Other'

    class TrainingType(models.TextChoices):
        DUAL = 'dual', 'Dual (With Instructor)'
        SOLO = 'solo', 'Solo'
        SOLO_SUPERVISED = 'solo_supervised', 'Solo (Supervised)'
        CHECK_RIDE = 'check_ride', 'Check Ride'
        STAGE_CHECK = 'stage_check', 'Stage Check'
        PROFICIENCY = 'proficiency', 'Proficiency Check'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        CHECKED_IN = 'checked_in', 'Checked In'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    class CancellationType(models.TextChoices):
        PILOT_REQUEST = 'pilot_request', 'Pilot Request'
        INSTRUCTOR_REQUEST = 'instructor_request', 'Instructor Request'
        WEATHER = 'weather', 'Weather'
        MAINTENANCE = 'maintenance', 'Maintenance'
        ADMIN = 'admin', 'Administrative'
        OTHER = 'other', 'Other'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PREPAID = 'prepaid', 'Prepaid'
        CHARGED = 'charged', 'Charged'
        REFUNDED = 'refunded', 'Refunded'
        PARTIAL_REFUND = 'partial_refund', 'Partial Refund'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Booking Number
    booking_number = models.CharField(max_length=20, unique=True, db_index=True)

    # Type
    booking_type = models.CharField(
        max_length=50,
        choices=BookingType.choices,
        default=BookingType.FLIGHT
    )

    # Resources
    aircraft_id = models.UUIDField(blank=True, null=True, db_index=True)
    simulator_id = models.UUIDField(blank=True, null=True)
    instructor_id = models.UUIDField(blank=True, null=True, db_index=True)
    student_id = models.UUIDField(blank=True, null=True, db_index=True)
    pilot_id = models.UUIDField(blank=True, null=True)

    # Location
    location_id = models.UUIDField(db_index=True)
    departure_airport = models.CharField(max_length=4, blank=True, null=True)
    arrival_airport = models.CharField(max_length=4, blank=True, null=True)

    # Scheduled Time
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    scheduled_duration = models.IntegerField()  # minutes

    # Actual Time
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    actual_duration = models.IntegerField(blank=True, null=True)

    # Block Time (includes buffer)
    preflight_minutes = models.IntegerField(default=30)
    postflight_minutes = models.IntegerField(default=30)
    block_start = models.DateTimeField(db_index=True)
    block_end = models.DateTimeField(db_index=True)

    # Training Information
    lesson_id = models.UUIDField(blank=True, null=True)
    exercise_ids = ArrayField(
        models.UUIDField(),
        blank=True,
        default=list
    )
    training_type = models.CharField(
        max_length=50,
        choices=TrainingType.choices,
        blank=True,
        null=True
    )

    # Description
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    route = models.TextField(blank=True, null=True)
    objectives = models.TextField(blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )

    # Cancellation
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancelled_by = models.UUIDField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancellation_type = models.CharField(
        max_length=20,
        choices=CancellationType.choices,
        blank=True,
        null=True
    )
    is_late_cancellation = models.BooleanField(default=False)
    cancellation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Approval
    requires_approval = models.BooleanField(default=False)
    approved_by = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Check-in/Check-out
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_in_by = models.UUIDField(blank=True, null=True)
    checked_out_at = models.DateTimeField(blank=True, null=True)
    checked_out_by = models.UUIDField(blank=True, null=True)

    # Dispatch
    dispatched_by = models.UUIDField(blank=True, null=True)
    dispatched_at = models.DateTimeField(blank=True, null=True)
    dispatch_notes = models.TextField(blank=True, null=True)

    # Weather Briefing
    weather_briefing_done = models.BooleanField(default=False)
    weather_briefing_at = models.DateTimeField(blank=True, null=True)

    # Risk Assessment
    risk_assessment_done = models.BooleanField(default=False)
    risk_score = models.IntegerField(blank=True, null=True)
    risk_factors = models.JSONField(default=list, blank=True)

    # Prerequisites
    prerequisites_checked = models.BooleanField(default=False)
    prerequisites_met = models.BooleanField(default=False)
    prerequisite_issues = models.JSONField(default=list, blank=True)

    # Related Records
    flight_id = models.UUIDField(blank=True, null=True)

    # Recurring
    is_recurring = models.BooleanField(default=False)
    recurring_pattern_id = models.UUIDField(blank=True, null=True)
    recurrence_parent_id = models.UUIDField(blank=True, null=True)

    # Pricing
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    # Notes
    pilot_notes = models.TextField(blank=True, null=True)
    instructor_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['scheduled_start']
        indexes = [
            models.Index(fields=['organization_id', 'scheduled_start']),
            models.Index(fields=['aircraft_id', 'block_start', 'block_end']),
            models.Index(fields=['instructor_id', 'block_start', 'block_end']),
            models.Index(fields=['student_id', 'scheduled_start']),
            models.Index(fields=['status', 'scheduled_start']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(scheduled_end__gt=models.F('scheduled_start')),
                name='valid_booking_times'
            ),
            models.CheckConstraint(
                check=models.Q(block_end__gt=models.F('block_start')),
                name='valid_block_times'
            ),
        ]

    def __str__(self):
        return f"{self.booking_number}: {self.scheduled_start.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Generate booking number
        if not self.booking_number:
            self.booking_number = self._generate_booking_number()

        # Calculate block times
        if self.scheduled_start and not self.block_start:
            self.block_start = self.scheduled_start - timedelta(
                minutes=self.preflight_minutes
            )
        if self.scheduled_end and not self.block_end:
            self.block_end = self.scheduled_end + timedelta(
                minutes=self.postflight_minutes
            )

        # Calculate scheduled duration if not set
        if self.scheduled_start and self.scheduled_end and not self.scheduled_duration:
            delta = self.scheduled_end - self.scheduled_start
            self.scheduled_duration = int(delta.total_seconds() / 60)

        super().save(*args, **kwargs)

    def _generate_booking_number(self) -> str:
        """Generate a unique booking number."""
        date_str = timezone.now().strftime('%Y%m%d')
        count = Booking.objects.filter(
            organization_id=self.organization_id,
            created_at__date=timezone.now().date()
        ).count() + 1
        return f"BK-{date_str}-{count:04d}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def duration_hours(self) -> float:
        """Duration in hours."""
        return self.scheduled_duration / 60

    @property
    def is_past(self) -> bool:
        """Check if booking is in the past."""
        return self.scheduled_end < timezone.now()

    @property
    def is_today(self) -> bool:
        """Check if booking is today."""
        return self.scheduled_start.date() == timezone.now().date()

    @property
    def is_upcoming(self) -> bool:
        """Check if booking is in the future."""
        return self.scheduled_start > timezone.now()

    @property
    def can_cancel(self) -> bool:
        """Check if booking can be cancelled."""
        return self.status in [
            self.Status.DRAFT,
            self.Status.PENDING_APPROVAL,
            self.Status.SCHEDULED,
            self.Status.CONFIRMED,
        ]

    @property
    def can_check_in(self) -> bool:
        """Check if booking can be checked in."""
        if self.status != self.Status.CONFIRMED:
            return False
        # Allow check-in 2 hours before scheduled start
        check_in_window = self.scheduled_start - timedelta(hours=2)
        return timezone.now() >= check_in_window

    @property
    def can_dispatch(self) -> bool:
        """Check if booking can be dispatched."""
        return self.status == self.Status.CHECKED_IN

    @property
    def can_complete(self) -> bool:
        """Check if booking can be completed."""
        return self.status == self.Status.IN_PROGRESS

    @property
    def hours_until_start(self) -> float:
        """Hours until scheduled start."""
        delta = self.scheduled_start - timezone.now()
        return delta.total_seconds() / 3600

    @property
    def payer_id(self):
        """Get the ID of who pays for this booking."""
        return self.student_id or self.pilot_id

    # ==========================================================================
    # Status Transitions
    # ==========================================================================

    def confirm(self, confirmed_by: uuid.UUID = None):
        """Confirm the booking."""
        if self.status not in [self.Status.SCHEDULED, self.Status.PENDING_APPROVAL]:
            raise ValueError(f"Cannot confirm booking in {self.status} status")

        self.status = self.Status.CONFIRMED
        if confirmed_by:
            self.approved_by = confirmed_by
            self.approved_at = timezone.now()
        self.save()

    def check_in(self, user_id: uuid.UUID):
        """Check in for the booking."""
        if self.status != self.Status.CONFIRMED:
            raise ValueError("Booking must be confirmed to check in")

        self.status = self.Status.CHECKED_IN
        self.checked_in_at = timezone.now()
        self.checked_in_by = user_id
        self.save()

    def dispatch(self, dispatcher_id: uuid.UUID, notes: str = None):
        """Dispatch the booking (start the flight)."""
        if self.status != self.Status.CHECKED_IN:
            raise ValueError("Booking must be checked in to dispatch")

        self.status = self.Status.IN_PROGRESS
        self.actual_start = timezone.now()
        self.dispatched_by = dispatcher_id
        self.dispatched_at = timezone.now()
        if notes:
            self.dispatch_notes = notes
        self.save()

    def start(self):
        """Start the booking (alternative to dispatch)."""
        if self.status not in [self.Status.CHECKED_IN, self.Status.CONFIRMED]:
            raise ValueError(f"Cannot start booking in {self.status} status")

        self.status = self.Status.IN_PROGRESS
        self.actual_start = timezone.now()
        self.save()

    def complete(
        self,
        flight_id: uuid.UUID = None,
        actual_cost: Decimal = None
    ):
        """Complete the booking."""
        if self.status != self.Status.IN_PROGRESS:
            raise ValueError("Booking must be in progress to complete")

        self.status = self.Status.COMPLETED
        self.actual_end = timezone.now()

        if self.actual_start:
            delta = self.actual_end - self.actual_start
            self.actual_duration = int(delta.total_seconds() / 60)

        if flight_id:
            self.flight_id = flight_id
        if actual_cost:
            self.actual_cost = actual_cost
            self.payment_status = self.PaymentStatus.CHARGED

        self.save()

    def cancel(
        self,
        user_id: uuid.UUID,
        reason: str,
        cancellation_type: str = None,
        fee: Decimal = None
    ):
        """Cancel the booking."""
        if not self.can_cancel:
            raise ValueError(f"Cannot cancel booking in {self.status} status")

        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user_id
        self.cancellation_reason = reason
        self.cancellation_type = cancellation_type or self.CancellationType.OTHER

        # Check for late cancellation (default: within 24 hours)
        if self.hours_until_start < 24:
            self.is_late_cancellation = True

        if fee:
            self.cancellation_fee = fee

        self.save()

    def mark_no_show(self, user_id: uuid.UUID = None):
        """Mark booking as no-show."""
        if self.status not in [self.Status.CONFIRMED, self.Status.CHECKED_IN]:
            raise ValueError(f"Cannot mark no-show for booking in {self.status} status")

        self.status = self.Status.NO_SHOW
        self.cancelled_at = timezone.now()
        if user_id:
            self.cancelled_by = user_id
        self.cancellation_reason = "No show"
        self.save()

    def check_out(self, user_id: uuid.UUID):
        """Check out after flight."""
        self.checked_out_at = timezone.now()
        self.checked_out_by = user_id
        self.save()

    # ==========================================================================
    # Class Methods
    # ==========================================================================

    @classmethod
    def get_active_statuses(cls) -> list:
        """Get list of active (non-terminal) statuses."""
        return [
            cls.Status.SCHEDULED,
            cls.Status.CONFIRMED,
            cls.Status.CHECKED_IN,
            cls.Status.IN_PROGRESS,
        ]

    @classmethod
    def get_conflicts(
        cls,
        organization_id: uuid.UUID,
        start: timezone.datetime,
        end: timezone.datetime,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        exclude_booking_id: uuid.UUID = None
    ):
        """Find conflicting bookings."""
        from django.db.models import Q

        queryset = cls.objects.filter(
            organization_id=organization_id,
            status__in=cls.get_active_statuses()
        ).filter(
            Q(block_start__lt=end) & Q(block_end__gt=start)
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        if exclude_booking_id:
            queryset = queryset.exclude(id=exclude_booking_id)

        return queryset

    @classmethod
    def get_for_date(
        cls,
        organization_id: uuid.UUID,
        date,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None
    ):
        """Get bookings for a specific date."""
        from datetime import datetime, time

        start_of_day = timezone.make_aware(datetime.combine(date, time.min))
        end_of_day = timezone.make_aware(datetime.combine(date, time.max))

        queryset = cls.objects.filter(
            organization_id=organization_id,
            scheduled_start__gte=start_of_day,
            scheduled_start__lte=end_of_day
        ).exclude(
            status__in=[cls.Status.CANCELLED, cls.Status.DRAFT]
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        return queryset.order_by('scheduled_start')

    @classmethod
    def get_upcoming_for_resource(
        cls,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        limit: int = 10
    ):
        """Get upcoming bookings for a resource."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            scheduled_start__gte=timezone.now(),
            status__in=cls.get_active_statuses()
        )

        if resource_type == 'aircraft':
            queryset = queryset.filter(aircraft_id=resource_id)
        elif resource_type == 'instructor':
            queryset = queryset.filter(instructor_id=resource_id)
        elif resource_type == 'student':
            queryset = queryset.filter(student_id=resource_id)

        return queryset.order_by('scheduled_start')[:limit]

"""Booking Service Models."""
import uuid
from django.db import models
from django.utils import timezone
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """Aircraft/Instructor booking."""

    class BookingType(models.TextChoices):
        TRAINING = 'training', 'Training Flight'
        RENTAL = 'rental', 'Aircraft Rental'
        CHECK_RIDE = 'check_ride', 'Check Ride'
        MAINTENANCE = 'maintenance', 'Maintenance'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        CONFIRMED = 'confirmed', 'Confirmed'
        CHECKED_IN = 'checked_in', 'Checked In'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    # References
    organization_id = models.UUIDField()
    aircraft_id = models.UUIDField(null=True, blank=True)
    pilot_id = models.UUIDField()  # Primary pilot/student
    instructor_id = models.UUIDField(null=True, blank=True)
    location_id = models.UUIDField(null=True, blank=True)

    # Booking details
    booking_type = models.CharField(max_length=20, choices=BookingType.choices, default=BookingType.TRAINING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Time
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)

    # Purpose
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    lesson_id = models.UUIDField(null=True, blank=True)  # Training lesson reference

    # Route
    departure_airport = models.CharField(max_length=4, blank=True)  # ICAO
    destination_airport = models.CharField(max_length=4, blank=True)
    route = models.TextField(blank=True)

    # Confirmation
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by_id = models.UUIDField(null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by_id = models.UUIDField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Billing
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Flags
    requires_approval = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    recurring_pattern = models.JSONField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['status']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['pilot_id']),
            models.Index(fields=['instructor_id']),
            models.Index(fields=['organization_id']),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.start_time.date()}"

    @property
    def duration_hours(self):
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600


class BookingResource(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Additional resources for a booking (e.g., simulator, classroom)."""

    class ResourceType(models.TextChoices):
        SIMULATOR = 'simulator', 'Simulator'
        CLASSROOM = 'classroom', 'Classroom'
        BRIEFING_ROOM = 'briefing_room', 'Briefing Room'
        EQUIPMENT = 'equipment', 'Equipment'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='resources')
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    resource_id = models.UUIDField()
    resource_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'booking_resources'


class Schedule(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Instructor/Aircraft availability schedule."""

    class ScheduleType(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNAVAILABLE = 'unavailable', 'Unavailable'
        BLOCKED = 'blocked', 'Blocked'

    organization_id = models.UUIDField()
    user_id = models.UUIDField(null=True, blank=True)  # For instructor schedules
    aircraft_id = models.UUIDField(null=True, blank=True)  # For aircraft schedules

    schedule_type = models.CharField(max_length=20, choices=ScheduleType.choices, default=ScheduleType.AVAILABLE)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    is_recurring = models.BooleanField(default=False)
    recurring_rule = models.JSONField(null=True, blank=True)  # iCal RRULE format

    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'schedules'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['aircraft_id', 'start_time']),
        ]


class WaitlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Waitlist for fully booked slots."""

    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting'
        OFFERED = 'offered', 'Slot Offered'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        EXPIRED = 'expired', 'Expired'

    organization_id = models.UUIDField()
    user_id = models.UUIDField()

    requested_date = models.DateField()
    preferred_start_time = models.TimeField(null=True, blank=True)
    preferred_end_time = models.TimeField(null=True, blank=True)

    aircraft_type_id = models.UUIDField(null=True, blank=True)
    instructor_id = models.UUIDField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    notes = models.TextField(blank=True)

    offered_booking_id = models.UUIDField(null=True, blank=True)
    offered_at = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'waitlist_entries'
        ordering = ['created_at']

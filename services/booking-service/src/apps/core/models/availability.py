# services/booking-service/src/apps/core/models/availability.py
"""
Availability Model

Manages resource availability schedules and blocks.
"""

import uuid
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Availability(models.Model):
    """
    Availability definitions for instructors, aircraft, and other resources.

    Supports both one-time and recurring availability patterns.
    """

    class ResourceType(models.TextChoices):
        INSTRUCTOR = 'instructor', 'Instructor'
        AIRCRAFT = 'aircraft', 'Aircraft'
        SIMULATOR = 'simulator', 'Simulator'
        LOCATION = 'location', 'Location'
        CLASSROOM = 'classroom', 'Classroom'

    class AvailabilityType(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNAVAILABLE = 'unavailable', 'Unavailable'
        LIMITED = 'limited', 'Limited Availability'
        TENTATIVE = 'tentative', 'Tentative'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Resource
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices
    )
    resource_id = models.UUIDField(db_index=True)

    # Type
    availability_type = models.CharField(
        max_length=20,
        choices=AvailabilityType.choices
    )

    # Time Range
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)

    # Recurrence (RRULE format)
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="RRULE format recurrence rule"
    )
    recurrence_end_date = models.DateField(blank=True, null=True)

    # Details
    reason = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Booking Restrictions
    max_bookings = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum bookings during this period"
    )
    booking_types_allowed = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Allowed booking types, empty means all"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'availability'
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['start_datetime', 'end_datetime']),
            models.Index(fields=['organization_id', 'resource_type']),
        ]

    def __str__(self):
        return f"{self.get_resource_type_display()} {self.resource_id}: {self.get_availability_type_display()}"

    # ==========================================================================
    # Query Methods
    # ==========================================================================

    @classmethod
    def get_for_resource(
        cls,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        start: datetime,
        end: datetime
    ):
        """Get availability entries for a resource in time range."""
        from django.db.models import Q

        return cls.objects.filter(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id
        ).filter(
            Q(start_datetime__lt=end) & Q(end_datetime__gt=start)
        ).order_by('start_datetime')

    @classmethod
    def is_resource_available(
        cls,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        start: datetime,
        end: datetime,
        booking_type: str = None
    ) -> bool:
        """Check if a resource is available for the given time."""
        entries = cls.get_for_resource(
            organization_id, resource_type, resource_id, start, end
        )

        for entry in entries:
            # If unavailable, resource is not available
            if entry.availability_type == cls.AvailabilityType.UNAVAILABLE:
                return False

            # If limited and booking type not in allowed list
            if entry.availability_type == cls.AvailabilityType.LIMITED:
                if entry.booking_types_allowed and booking_type:
                    if booking_type not in entry.booking_types_allowed:
                        return False

        return True

    @classmethod
    def get_unavailable_blocks(
        cls,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        start: datetime,
        end: datetime
    ) -> list:
        """Get unavailable time blocks for a resource."""
        entries = cls.get_for_resource(
            organization_id, resource_type, resource_id, start, end
        ).filter(
            availability_type=cls.AvailabilityType.UNAVAILABLE
        )

        blocks = []
        for entry in entries:
            blocks.append({
                'start': entry.start_datetime,
                'end': entry.end_datetime,
                'reason': entry.reason,
            })

        return blocks

    # ==========================================================================
    # Instance Methods
    # ==========================================================================

    def overlaps_with(self, start: datetime, end: datetime) -> bool:
        """Check if this availability overlaps with given time range."""
        return self.start_datetime < end and self.end_datetime > start

    def get_duration_minutes(self) -> int:
        """Get duration in minutes."""
        delta = self.end_datetime - self.start_datetime
        return int(delta.total_seconds() / 60)

    def split(self, split_time: datetime) -> tuple:
        """Split availability at a given time, returns two new entries."""
        if not (self.start_datetime < split_time < self.end_datetime):
            raise ValueError("Split time must be within the availability period")

        first = Availability(
            organization_id=self.organization_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            availability_type=self.availability_type,
            start_datetime=self.start_datetime,
            end_datetime=split_time,
            reason=self.reason,
            notes=self.notes,
            created_by=self.created_by,
        )

        second = Availability(
            organization_id=self.organization_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            availability_type=self.availability_type,
            start_datetime=split_time,
            end_datetime=self.end_datetime,
            reason=self.reason,
            notes=self.notes,
            created_by=self.created_by,
        )

        return (first, second)


class OperatingHours(models.Model):
    """
    Operating hours for locations.

    Defines when a location is open for bookings.
    """

    class DayOfWeek(models.IntegerChoices):
        SUNDAY = 0, 'Sunday'
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'
        SATURDAY = 6, 'Saturday'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    location_id = models.UUIDField(db_index=True)

    # Day and Time
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    open_time = models.TimeField()
    close_time = models.TimeField()

    # Active Period
    effective_from = models.DateField(blank=True, null=True)
    effective_to = models.DateField(blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'operating_hours'
        ordering = ['day_of_week', 'open_time']
        unique_together = [
            ['organization_id', 'location_id', 'day_of_week', 'effective_from']
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.open_time} - {self.close_time}"

    @classmethod
    def get_for_date(
        cls,
        organization_id: uuid.UUID,
        location_id: uuid.UUID,
        target_date
    ):
        """Get operating hours for a specific date."""
        from django.db.models import Q

        # Convert to JS-style day of week (0=Sunday)
        python_day = target_date.weekday()
        js_day = (python_day + 1) % 7

        return cls.objects.filter(
            organization_id=organization_id,
            location_id=location_id,
            day_of_week=js_day,
            is_active=True
        ).filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=target_date)
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=target_date)
        ).first()

    def is_within_hours(self, check_time) -> bool:
        """Check if a time is within operating hours."""
        return self.open_time <= check_time <= self.close_time

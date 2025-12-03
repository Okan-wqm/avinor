# services/booking-service/src/apps/core/models/recurring_pattern.py
"""
Recurring Pattern Model

Manages recurring booking patterns for scheduled training.
"""

import uuid
from datetime import date, time, timedelta

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class RecurringPattern(models.Model):
    """
    Recurring pattern for creating repeated bookings.

    Supports daily, weekly, biweekly, and monthly recurrence.
    """

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        BIWEEKLY = 'biweekly', 'Biweekly'
        MONTHLY = 'monthly', 'Monthly'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Booking Template
    booking_template = models.JSONField(
        help_text="Template data for creating bookings"
    )

    # Recurrence Rule
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices
    )
    days_of_week = ArrayField(
        models.IntegerField(),  # 0=Sunday, 1=Monday, etc.
        blank=True,
        default=list,
        help_text="Days of week for weekly/biweekly patterns"
    )
    day_of_month = models.IntegerField(
        blank=True,
        null=True,
        help_text="Day of month for monthly patterns"
    )

    # Time Range
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    occurrence_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Max number of occurrences"
    )

    # Time of Day
    start_time = models.TimeField()
    duration_minutes = models.IntegerField()

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Progress Tracking
    created_bookings_count = models.IntegerField(default=0)
    next_occurrence_date = models.DateField(blank=True, null=True)
    last_created_date = models.DateField(blank=True, null=True)

    # Exceptions
    exception_dates = ArrayField(
        models.DateField(),
        blank=True,
        default=list,
        help_text="Dates to skip"
    )

    # Metadata
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recurring_patterns'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_frequency_display()} pattern starting {self.start_date}"

    def save(self, *args, **kwargs):
        if not self.next_occurrence_date:
            self.next_occurrence_date = self._calculate_first_occurrence()
        super().save(*args, **kwargs)

    # ==========================================================================
    # Occurrence Calculation
    # ==========================================================================

    def _calculate_first_occurrence(self) -> date:
        """Calculate the first occurrence date."""
        if self.frequency == self.Frequency.DAILY:
            return self.start_date

        if self.frequency in [self.Frequency.WEEKLY, self.Frequency.BIWEEKLY]:
            if not self.days_of_week:
                return self.start_date

            # Find the first matching day
            current = self.start_date
            for _ in range(7):
                if current.weekday() in self._convert_days_to_python():
                    return current
                current += timedelta(days=1)

        if self.frequency == self.Frequency.MONTHLY:
            if self.day_of_month:
                if self.start_date.day <= self.day_of_month:
                    return self.start_date.replace(day=self.day_of_month)
                else:
                    next_month = self.start_date.replace(day=1) + timedelta(days=32)
                    return next_month.replace(day=self.day_of_month)

        return self.start_date

    def _convert_days_to_python(self) -> list:
        """Convert JS day format (0=Sunday) to Python (0=Monday)."""
        # Input: 0=Sunday, 1=Monday, ..., 6=Saturday
        # Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
        mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        return [mapping[d] for d in self.days_of_week]

    def get_next_occurrence(self, after_date: date = None) -> date:
        """Get the next occurrence after a given date."""
        start = after_date or self.next_occurrence_date or self.start_date

        # Check end conditions
        if self.end_date and start > self.end_date:
            return None

        if self.occurrence_count and self.created_bookings_count >= self.occurrence_count:
            return None

        if self.frequency == self.Frequency.DAILY:
            next_date = start + timedelta(days=1) if after_date else start
            return self._skip_exceptions(next_date)

        if self.frequency == self.Frequency.WEEKLY:
            return self._get_next_weekly(start, weeks=1)

        if self.frequency == self.Frequency.BIWEEKLY:
            return self._get_next_weekly(start, weeks=2)

        if self.frequency == self.Frequency.MONTHLY:
            return self._get_next_monthly(start)

        return None

    def _get_next_weekly(self, after_date: date, weeks: int = 1) -> date:
        """Get next weekly/biweekly occurrence."""
        if not self.days_of_week:
            return after_date + timedelta(weeks=weeks)

        python_days = self._convert_days_to_python()
        current = after_date + timedelta(days=1)

        # Look for the next matching day within reasonable range
        for _ in range(weeks * 7 * 4):  # Look up to 4 weeks ahead
            if current.weekday() in python_days:
                # Check if we've advanced enough weeks
                week_diff = (current - self.start_date).days // 7
                if week_diff % weeks == 0:
                    return self._skip_exceptions(current)
            current += timedelta(days=1)

        return None

    def _get_next_monthly(self, after_date: date) -> date:
        """Get next monthly occurrence."""
        if not self.day_of_month:
            return None

        # Try current month
        try:
            if after_date.day < self.day_of_month:
                candidate = after_date.replace(day=self.day_of_month)
                return self._skip_exceptions(candidate)
        except ValueError:
            pass  # Day doesn't exist in this month

        # Move to next month
        next_month = after_date.replace(day=1) + timedelta(days=32)
        try:
            candidate = next_month.replace(day=self.day_of_month)
            return self._skip_exceptions(candidate)
        except ValueError:
            # Handle months with fewer days
            last_day = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return self._skip_exceptions(last_day)

    def _skip_exceptions(self, candidate: date) -> date:
        """Skip exception dates."""
        if candidate in self.exception_dates:
            return self.get_next_occurrence(candidate)
        return candidate

    # ==========================================================================
    # Status Methods
    # ==========================================================================

    def is_active(self) -> bool:
        """Check if pattern is active."""
        if self.status != self.Status.ACTIVE:
            return False

        if self.end_date and date.today() > self.end_date:
            return False

        if self.occurrence_count and self.created_bookings_count >= self.occurrence_count:
            return False

        return True

    def pause(self):
        """Pause the pattern."""
        self.status = self.Status.PAUSED
        self.save()

    def resume(self):
        """Resume the pattern."""
        if self.status == self.Status.PAUSED:
            self.status = self.Status.ACTIVE
            self.save()

    def complete(self):
        """Mark pattern as completed."""
        self.status = self.Status.COMPLETED
        self.save()

    def cancel(self):
        """Cancel the pattern."""
        self.status = self.Status.CANCELLED
        self.save()

    def add_exception(self, exception_date: date):
        """Add an exception date."""
        if exception_date not in self.exception_dates:
            self.exception_dates.append(exception_date)
            self.save()

    def remove_exception(self, exception_date: date):
        """Remove an exception date."""
        if exception_date in self.exception_dates:
            self.exception_dates.remove(exception_date)
            self.save()

    def increment_count(self, occurrence_date: date):
        """Increment the created bookings count."""
        self.created_bookings_count += 1
        self.last_created_date = occurrence_date
        self.next_occurrence_date = self.get_next_occurrence(occurrence_date)

        # Check if completed
        if self.occurrence_count and self.created_bookings_count >= self.occurrence_count:
            self.status = self.Status.COMPLETED
        elif self.end_date and self.next_occurrence_date and self.next_occurrence_date > self.end_date:
            self.status = self.Status.COMPLETED

        self.save()

    # ==========================================================================
    # Booking Generation
    # ==========================================================================

    def get_occurrences_in_range(
        self,
        start_date: date,
        end_date: date
    ) -> list:
        """Get all occurrences within a date range."""
        occurrences = []
        current = self.get_next_occurrence(start_date - timedelta(days=1))

        while current and current <= end_date:
            if current >= start_date:
                occurrences.append(current)

            current = self.get_next_occurrence(current)

        return occurrences

# services/booking-service/src/apps/core/models/waitlist.py
"""
Waitlist Model

Manages waiting list for bookings.
"""

import uuid
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone


class WaitlistEntry(models.Model):
    """
    Waitlist entry for requested time slots.

    Users can request specific times and resources, and get notified
    when slots become available.
    """

    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting'
        OFFERED = 'offered', 'Offer Sent'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        FULFILLED = 'fulfilled', 'Fulfilled'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Requester
    user_id = models.UUIDField(db_index=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_email = models.EmailField(blank=True, null=True)
    user_phone = models.CharField(max_length=20, blank=True, null=True)

    # Request Details
    requested_date = models.DateField(db_index=True)
    preferred_start_time = models.TimeField(blank=True, null=True)
    preferred_end_time = models.TimeField(blank=True, null=True)

    # Preferred Resources
    aircraft_id = models.UUIDField(blank=True, null=True)
    aircraft_name = models.CharField(max_length=100, blank=True, null=True)
    instructor_id = models.UUIDField(blank=True, null=True)
    instructor_name = models.CharField(max_length=255, blank=True, null=True)
    location_id = models.UUIDField(blank=True, null=True)

    # Booking Details
    booking_type = models.CharField(max_length=50, blank=True, null=True)
    training_type = models.CharField(max_length=50, blank=True, null=True)
    duration_minutes = models.IntegerField(blank=True, null=True)
    lesson_id = models.UUIDField(blank=True, null=True)

    # Flexibility
    flexibility_days = models.IntegerField(
        default=0,
        help_text="How many days before/after requested date is acceptable"
    )
    flexibility_hours = models.IntegerField(
        default=0,
        help_text="How many hours before/after requested time is acceptable"
    )
    any_aircraft = models.BooleanField(
        default=False,
        help_text="Accept any available aircraft"
    )
    any_instructor = models.BooleanField(
        default=False,
        help_text="Accept any available instructor"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
        db_index=True
    )

    # Offer Details
    offered_booking_id = models.UUIDField(blank=True, null=True)
    offered_at = models.DateTimeField(blank=True, null=True)
    offer_expires_at = models.DateTimeField(blank=True, null=True)
    offer_message = models.TextField(blank=True, null=True)

    # Response
    responded_at = models.DateTimeField(blank=True, null=True)
    response_notes = models.TextField(blank=True, null=True)

    # Final Booking
    fulfilled_booking_id = models.UUIDField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)

    # Priority
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority entries are processed first"
    )

    # Expiration
    expires_at = models.DateTimeField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'waitlist'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['organization_id', 'requested_date']),
            models.Index(fields=['status', 'requested_date']),
            models.Index(fields=['user_id', 'status']),
        ]

    def __str__(self):
        return f"Waitlist: {self.user_id} for {self.requested_date}"

    def save(self, *args, **kwargs):
        # Set default expiration
        if not self.expires_at:
            # Expire 1 day after requested date
            self.expires_at = timezone.make_aware(
                datetime.combine(
                    self.requested_date + timedelta(days=1),
                    datetime.min.time()
                )
            )

        super().save(*args, **kwargs)

    # ==========================================================================
    # Status Methods
    # ==========================================================================

    @property
    def is_active(self) -> bool:
        """Check if entry is still active."""
        if self.status not in [self.Status.WAITING, self.Status.OFFERED]:
            return False

        if self.expires_at and timezone.now() > self.expires_at:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return self.status == self.Status.EXPIRED

    @property
    def offer_expired(self) -> bool:
        """Check if offer has expired."""
        if self.status != self.Status.OFFERED:
            return False

        if self.offer_expires_at and timezone.now() > self.offer_expires_at:
            return True

        return False

    def send_offer(
        self,
        booking_id: uuid.UUID,
        message: str = None,
        expires_in_hours: int = 4
    ):
        """Send an offer for an available slot."""
        self.status = self.Status.OFFERED
        self.offered_booking_id = booking_id
        self.offered_at = timezone.now()
        self.offer_expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        self.offer_message = message
        self.save()

    def accept_offer(self, notes: str = None):
        """Accept the offered booking."""
        if self.status != self.Status.OFFERED:
            raise ValueError("No active offer to accept")

        if self.offer_expired:
            raise ValueError("Offer has expired")

        self.status = self.Status.ACCEPTED
        self.responded_at = timezone.now()
        self.response_notes = notes
        self.fulfilled_booking_id = self.offered_booking_id
        self.save()

    def decline_offer(self, notes: str = None):
        """Decline the offered booking."""
        if self.status != self.Status.OFFERED:
            raise ValueError("No active offer to decline")

        self.status = self.Status.DECLINED
        self.responded_at = timezone.now()
        self.response_notes = notes
        self.save()

    def fulfill(self, booking_id: uuid.UUID):
        """Mark as fulfilled with a booking."""
        self.status = self.Status.FULFILLED
        self.fulfilled_booking_id = booking_id
        self.save()

    def cancel(self, reason: str = None):
        """Cancel the waitlist entry."""
        self.status = self.Status.CANCELLED
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}" if self.notes else f"Cancelled: {reason}"
        self.save()

    def expire(self):
        """Mark as expired."""
        self.status = self.Status.EXPIRED
        self.save()

    # ==========================================================================
    # Query Methods
    # ==========================================================================

    @classmethod
    def get_active_for_date(
        cls,
        organization_id: uuid.UUID,
        target_date,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None
    ):
        """Get active waitlist entries for a date."""
        from django.db.models import Q

        queryset = cls.objects.filter(
            organization_id=organization_id,
            status__in=[cls.Status.WAITING],
        ).filter(
            Q(requested_date=target_date) |
            Q(
                requested_date__gte=target_date - timedelta(days=models.F('flexibility_days')),
                requested_date__lte=target_date + timedelta(days=models.F('flexibility_days'))
            )
        )

        # Filter by resources if specified
        if aircraft_id:
            queryset = queryset.filter(
                Q(aircraft_id=aircraft_id) | Q(any_aircraft=True)
            )

        if instructor_id:
            queryset = queryset.filter(
                Q(instructor_id=instructor_id) | Q(any_instructor=True)
            )

        return queryset.order_by('-priority', 'created_at')

    @classmethod
    def get_for_user(cls, user_id: uuid.UUID, active_only: bool = True):
        """Get waitlist entries for a user."""
        queryset = cls.objects.filter(user_id=user_id)

        if active_only:
            queryset = queryset.filter(
                status__in=[cls.Status.WAITING, cls.Status.OFFERED]
            )

        return queryset.order_by('-created_at')

    @classmethod
    def process_expired_entries(cls, organization_id: uuid.UUID = None):
        """Process and mark expired entries."""
        queryset = cls.objects.filter(
            status__in=[cls.Status.WAITING, cls.Status.OFFERED],
            expires_at__lt=timezone.now()
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        count = queryset.update(status=cls.Status.EXPIRED)
        return count

    @classmethod
    def process_expired_offers(cls, organization_id: uuid.UUID = None):
        """Process and expire unanswered offers."""
        queryset = cls.objects.filter(
            status=cls.Status.OFFERED,
            offer_expires_at__lt=timezone.now()
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Revert to waiting status
        for entry in queryset:
            entry.status = cls.Status.WAITING
            entry.offered_booking_id = None
            entry.offered_at = None
            entry.offer_expires_at = None
            entry.save()

        return queryset.count()

    def matches_slot(
        self,
        slot_start: datetime,
        slot_end: datetime,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None
    ) -> bool:
        """Check if a slot matches this waitlist entry."""
        # Check date with flexibility
        slot_date = slot_start.date()
        date_diff = abs((slot_date - self.requested_date).days)
        if date_diff > self.flexibility_days:
            return False

        # Check time with flexibility
        if self.preferred_start_time:
            from datetime import datetime as dt, timedelta as td

            pref_start = dt.combine(slot_date, self.preferred_start_time)
            actual_start = slot_start.replace(tzinfo=None)
            time_diff_hours = abs((actual_start - pref_start).total_seconds() / 3600)
            if time_diff_hours > self.flexibility_hours:
                return False

        # Check duration
        if self.duration_minutes:
            slot_duration = (slot_end - slot_start).total_seconds() / 60
            if slot_duration < self.duration_minutes:
                return False

        # Check aircraft
        if self.aircraft_id and not self.any_aircraft:
            if aircraft_id and aircraft_id != self.aircraft_id:
                return False

        # Check instructor
        if self.instructor_id and not self.any_instructor:
            if instructor_id and instructor_id != self.instructor_id:
                return False

        return True

# services/booking-service/src/apps/core/services/waitlist_service.py
"""
Waitlist Service

Manages booking waitlist operations.
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Booking, WaitlistEntry

logger = logging.getLogger(__name__)


class WaitlistService:
    """
    Service for managing waitlist.

    Handles:
    - Waitlist CRUD
    - Offer management
    - Cancellation processing
    """

    # ==========================================================================
    # Waitlist CRUD
    # ==========================================================================

    @transaction.atomic
    def add_to_waitlist(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        requested_date: date,
        duration_minutes: int = None,
        preferred_start_time: time = None,
        preferred_end_time: time = None,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        booking_type: str = None,
        flexibility_days: int = 0,
        flexibility_hours: int = 0,
        any_aircraft: bool = False,
        any_instructor: bool = False,
        notes: str = None,
        user_name: str = None,
        user_email: str = None,
        **kwargs
    ) -> WaitlistEntry:
        """Add a new waitlist entry."""
        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=requested_date,
            duration_minutes=duration_minutes,
            preferred_start_time=preferred_start_time,
            preferred_end_time=preferred_end_time,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            location_id=location_id,
            booking_type=booking_type,
            flexibility_days=flexibility_days,
            flexibility_hours=flexibility_hours,
            any_aircraft=any_aircraft,
            any_instructor=any_instructor,
            notes=notes,
            user_name=user_name,
            user_email=user_email,
            **kwargs
        )

        logger.info(
            f"Added waitlist entry for user {user_id} "
            f"on {requested_date}"
        )

        return entry

    def get_entry(self, entry_id: uuid.UUID) -> WaitlistEntry:
        """Get a waitlist entry by ID."""
        from . import WaitlistError

        try:
            return WaitlistEntry.objects.get(id=entry_id)
        except WaitlistEntry.DoesNotExist:
            raise WaitlistError(f"Waitlist entry {entry_id} not found")

    def list_entries(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID = None,
        requested_date: date = None,
        status: str = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[WaitlistEntry]:
        """List waitlist entries."""
        queryset = WaitlistEntry.objects.filter(organization_id=organization_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if requested_date:
            queryset = queryset.filter(requested_date=requested_date)

        if status:
            queryset = queryset.filter(status=status)
        elif active_only:
            queryset = queryset.filter(
                status__in=[
                    WaitlistEntry.Status.WAITING,
                    WaitlistEntry.Status.OFFERED
                ]
            )

        return list(queryset.order_by('-priority', 'created_at')[:limit])

    def update_entry(
        self,
        entry_id: uuid.UUID,
        **kwargs
    ) -> WaitlistEntry:
        """Update a waitlist entry."""
        from . import WaitlistError

        entry = self.get_entry(entry_id)

        if entry.status not in [WaitlistEntry.Status.WAITING]:
            raise WaitlistError("Cannot update entry that is not in waiting status")

        allowed_fields = [
            'requested_date', 'preferred_start_time', 'preferred_end_time',
            'aircraft_id', 'instructor_id', 'location_id',
            'duration_minutes', 'booking_type',
            'flexibility_days', 'flexibility_hours',
            'any_aircraft', 'any_instructor',
            'notes', 'priority',
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(entry, field, value)

        entry.save()
        return entry

    def cancel_entry(
        self,
        entry_id: uuid.UUID,
        reason: str = None
    ) -> WaitlistEntry:
        """Cancel a waitlist entry."""
        entry = self.get_entry(entry_id)
        entry.cancel(reason)

        logger.info(f"Cancelled waitlist entry {entry_id}")
        return entry

    # ==========================================================================
    # Offer Management
    # ==========================================================================

    def send_offer(
        self,
        entry_id: uuid.UUID,
        booking_id: uuid.UUID,
        message: str = None,
        expires_in_hours: int = 4
    ) -> WaitlistEntry:
        """Send an offer for an available slot."""
        entry = self.get_entry(entry_id)

        if entry.status != WaitlistEntry.Status.WAITING:
            from . import WaitlistError
            raise WaitlistError("Can only send offer to waiting entries")

        entry.send_offer(booking_id, message, expires_in_hours)

        logger.info(
            f"Sent offer for booking {booking_id} "
            f"to waitlist entry {entry_id}"
        )

        return entry

    def accept_offer(
        self,
        entry_id: uuid.UUID,
        notes: str = None
    ) -> WaitlistEntry:
        """Accept an offered booking."""
        from . import WaitlistError

        entry = self.get_entry(entry_id)

        if entry.status != WaitlistEntry.Status.OFFERED:
            raise WaitlistError("No active offer to accept")

        if entry.offer_expired:
            raise WaitlistError("Offer has expired")

        entry.accept_offer(notes)

        logger.info(f"Accepted offer for waitlist entry {entry_id}")
        return entry

    def decline_offer(
        self,
        entry_id: uuid.UUID,
        notes: str = None
    ) -> WaitlistEntry:
        """Decline an offered booking."""
        entry = self.get_entry(entry_id)

        if entry.status != WaitlistEntry.Status.OFFERED:
            from . import WaitlistError
            raise WaitlistError("No active offer to decline")

        entry.decline_offer(notes)

        logger.info(f"Declined offer for waitlist entry {entry_id}")
        return entry

    # ==========================================================================
    # Cancellation Processing
    # ==========================================================================

    def process_cancellation(self, cancelled_booking: Booking):
        """Process waitlist when a booking is cancelled."""
        # Find matching waitlist entries
        entries = self._find_matching_entries(cancelled_booking)

        if not entries:
            logger.info(
                f"No waitlist entries match cancelled booking "
                f"{cancelled_booking.booking_number}"
            )
            return

        # Sort by priority
        entries = sorted(entries, key=lambda e: (-e.priority, e.created_at))

        # Send offer to highest priority entry
        top_entry = entries[0]

        # Create a pending booking for the slot
        from .booking_service import BookingService
        booking_service = BookingService()

        try:
            pending_booking = booking_service.create_booking(
                organization_id=cancelled_booking.organization_id,
                location_id=cancelled_booking.location_id,
                scheduled_start=cancelled_booking.scheduled_start,
                scheduled_end=cancelled_booking.scheduled_end,
                created_by=top_entry.user_id,
                booking_type=top_entry.booking_type or cancelled_booking.booking_type,
                aircraft_id=top_entry.aircraft_id or cancelled_booking.aircraft_id,
                instructor_id=top_entry.instructor_id or cancelled_booking.instructor_id,
                student_id=top_entry.user_id,
                status=Booking.Status.PENDING_APPROVAL,
            )

            self.send_offer(
                top_entry.id,
                pending_booking.id,
                f"A slot has become available on {cancelled_booking.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
            )

            logger.info(
                f"Sent waitlist offer to user {top_entry.user_id} "
                f"for cancelled booking {cancelled_booking.booking_number}"
            )

        except Exception as e:
            logger.error(
                f"Failed to create pending booking for waitlist: {e}"
            )

    def _find_matching_entries(
        self,
        booking: Booking
    ) -> List[WaitlistEntry]:
        """Find waitlist entries matching a booking."""
        target_date = booking.scheduled_start.date()

        # Base query for active entries
        queryset = WaitlistEntry.objects.filter(
            organization_id=booking.organization_id,
            status=WaitlistEntry.Status.WAITING
        )

        # Date matching with flexibility
        queryset = queryset.filter(
            Q(requested_date=target_date) |
            Q(
                requested_date__gte=target_date - timedelta(days=7),
                requested_date__lte=target_date + timedelta(days=7),
            )
        )

        # Filter results in Python for complex logic
        matches = []
        for entry in queryset:
            if entry.matches_slot(
                booking.scheduled_start,
                booking.scheduled_end,
                booking.aircraft_id,
                booking.instructor_id
            ):
                matches.append(entry)

        return matches

    # ==========================================================================
    # Maintenance
    # ==========================================================================

    def process_expired_entries(
        self,
        organization_id: uuid.UUID = None
    ) -> int:
        """Process and expire old entries."""
        count = WaitlistEntry.process_expired_entries(organization_id)
        logger.info(f"Expired {count} waitlist entries")
        return count

    def process_expired_offers(
        self,
        organization_id: uuid.UUID = None
    ) -> int:
        """Process and expire unanswered offers."""
        count = WaitlistEntry.process_expired_offers(organization_id)
        logger.info(f"Expired {count} waitlist offers")
        return count

    def get_statistics(
        self,
        organization_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get waitlist statistics."""
        queryset = WaitlistEntry.objects.filter(organization_id=organization_id)

        if start_date:
            queryset = queryset.filter(requested_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(requested_date__lte=end_date)

        total = queryset.count()
        waiting = queryset.filter(status=WaitlistEntry.Status.WAITING).count()
        offered = queryset.filter(status=WaitlistEntry.Status.OFFERED).count()
        accepted = queryset.filter(status=WaitlistEntry.Status.ACCEPTED).count()
        declined = queryset.filter(status=WaitlistEntry.Status.DECLINED).count()
        expired = queryset.filter(status=WaitlistEntry.Status.EXPIRED).count()
        fulfilled = queryset.filter(status=WaitlistEntry.Status.FULFILLED).count()

        return {
            'total': total,
            'waiting': waiting,
            'offered': offered,
            'accepted': accepted,
            'declined': declined,
            'expired': expired,
            'fulfilled': fulfilled,
            'fulfillment_rate': (fulfilled / total * 100) if total > 0 else 0,
            'acceptance_rate': (accepted / (accepted + declined) * 100) if (accepted + declined) > 0 else 0,
        }

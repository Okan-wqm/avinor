# services/booking-service/src/apps/core/services/booking_service.py
"""
Booking Service

Core business logic for reservation management.
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone

from apps.core.models import Booking, RecurringPattern, BookingRule

logger = logging.getLogger(__name__)


class BookingService:
    """
    Service for managing bookings.

    Handles:
    - Booking CRUD
    - Conflict detection
    - Status transitions
    - Cost estimation
    - Calendar views
    """

    # ==========================================================================
    # Booking CRUD
    # ==========================================================================

    @transaction.atomic
    def create_booking(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID,
        scheduled_start: datetime,
        scheduled_end: datetime,
        created_by: uuid.UUID,
        booking_type: str = Booking.BookingType.FLIGHT,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        pilot_id: uuid.UUID = None,
        **kwargs
    ) -> Booking:
        """Create a new booking with full validation."""
        from . import (
            BookingValidationError,
            BookingConflictError,
            RuleViolationError,
        )

        # 1. Basic time validation
        self._validate_times(scheduled_start, scheduled_end)

        # 2. Get applicable rules
        rules = BookingRule.get_merged_rules(
            organization_id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            location_id=location_id,
            booking_type=booking_type,
        )

        # 3. Validate against rules
        self._validate_against_rules(
            rules,
            scheduled_start,
            scheduled_end,
            student_id or pilot_id,
            organization_id,
        )

        # 4. Check for conflicts
        conflicts = self.check_conflicts(
            organization_id,
            scheduled_start,
            scheduled_end,
            aircraft_id,
            instructor_id,
            student_id,
        )

        if conflicts:
            conflict_msgs = [c['message'] for c in conflicts]
            raise BookingConflictError(f"Conflicts detected: {', '.join(conflict_msgs)}")

        # 5. Calculate duration
        duration_minutes = int((scheduled_end - scheduled_start).total_seconds() / 60)

        # 6. Calculate block times
        preflight = kwargs.pop('preflight_minutes', rules.get('preflight_minutes', 30))
        postflight = kwargs.pop('postflight_minutes', rules.get('postflight_minutes', 30))

        block_start = scheduled_start - timedelta(minutes=preflight)
        block_end = scheduled_end + timedelta(minutes=postflight)

        # 7. Determine if approval required
        requires_approval = bool(rules.get('requires_approval_from'))

        # 8. Estimate cost
        estimated_cost = self._calculate_estimated_cost(
            aircraft_id,
            instructor_id,
            duration_minutes / 60,
        )

        # 9. Create booking
        initial_status = (
            Booking.Status.PENDING_APPROVAL if requires_approval
            else Booking.Status.SCHEDULED
        )

        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=booking_type,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            scheduled_duration=duration_minutes,
            preflight_minutes=preflight,
            postflight_minutes=postflight,
            block_start=block_start,
            block_end=block_end,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            pilot_id=pilot_id,
            status=initial_status,
            requires_approval=requires_approval,
            estimated_cost=estimated_cost,
            created_by=created_by,
            **kwargs
        )

        logger.info(
            f"Created booking {booking.booking_number} for "
            f"{scheduled_start.strftime('%Y-%m-%d %H:%M')}"
        )

        return booking

    def get_booking(self, booking_id: uuid.UUID) -> Booking:
        """Get a booking by ID."""
        from . import BookingNotFoundError

        try:
            return Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking {booking_id} not found")

    def get_by_number(self, booking_number: str) -> Booking:
        """Get a booking by number."""
        from . import BookingNotFoundError

        try:
            return Booking.objects.get(booking_number=booking_number)
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking {booking_number} not found")

    def list_bookings(
        self,
        organization_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        pilot_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        status: str = None,
        booking_type: str = None,
        exclude_cancelled: bool = True
    ) -> List[Booking]:
        """List bookings with filters."""
        queryset = Booking.objects.filter(organization_id=organization_id)

        if start_date:
            start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
            queryset = queryset.filter(scheduled_start__gte=start_dt)

        if end_date:
            end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
            queryset = queryset.filter(scheduled_start__lte=end_dt)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        if student_id:
            queryset = queryset.filter(student_id=student_id)

        if pilot_id:
            queryset = queryset.filter(pilot_id=pilot_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        if status:
            queryset = queryset.filter(status=status)
        elif exclude_cancelled:
            queryset = queryset.exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.NO_SHOW]
            )

        if booking_type:
            queryset = queryset.filter(booking_type=booking_type)

        return list(queryset.order_by('scheduled_start'))

    @transaction.atomic
    def update_booking(
        self,
        booking_id: uuid.UUID,
        updated_by: uuid.UUID,
        **kwargs
    ) -> Booking:
        """Update a booking."""
        from . import BookingStateError, BookingConflictError

        booking = self.get_booking(booking_id)

        # Check if booking can be modified
        if booking.status in [Booking.Status.COMPLETED, Booking.Status.CANCELLED]:
            raise BookingStateError(
                f"Cannot update booking in {booking.status} status"
            )

        # If times are changing, validate and check conflicts
        new_start = kwargs.get('scheduled_start', booking.scheduled_start)
        new_end = kwargs.get('scheduled_end', booking.scheduled_end)
        new_aircraft = kwargs.get('aircraft_id', booking.aircraft_id)
        new_instructor = kwargs.get('instructor_id', booking.instructor_id)

        if (new_start != booking.scheduled_start or
            new_end != booking.scheduled_end or
            new_aircraft != booking.aircraft_id or
            new_instructor != booking.instructor_id):

            self._validate_times(new_start, new_end)

            conflicts = self.check_conflicts(
                booking.organization_id,
                new_start,
                new_end,
                new_aircraft,
                new_instructor,
                exclude_booking_id=booking.id,
            )

            if conflicts:
                raise BookingConflictError("Conflicts with existing bookings")

            # Recalculate block times
            if 'scheduled_start' in kwargs or 'preflight_minutes' in kwargs:
                preflight = kwargs.get('preflight_minutes', booking.preflight_minutes)
                kwargs['block_start'] = new_start - timedelta(minutes=preflight)

            if 'scheduled_end' in kwargs or 'postflight_minutes' in kwargs:
                postflight = kwargs.get('postflight_minutes', booking.postflight_minutes)
                kwargs['block_end'] = new_end + timedelta(minutes=postflight)

            # Recalculate duration
            if 'scheduled_start' in kwargs or 'scheduled_end' in kwargs:
                kwargs['scheduled_duration'] = int(
                    (new_end - new_start).total_seconds() / 60
                )

        # Update allowed fields
        allowed_fields = [
            'scheduled_start', 'scheduled_end', 'scheduled_duration',
            'preflight_minutes', 'postflight_minutes', 'block_start', 'block_end',
            'aircraft_id', 'instructor_id', 'student_id', 'pilot_id',
            'location_id', 'departure_airport', 'arrival_airport',
            'title', 'description', 'route', 'objectives',
            'lesson_id', 'training_type',
            'pilot_notes', 'instructor_notes', 'internal_notes',
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(booking, field, value)

        booking.updated_by = updated_by
        booking.save()

        logger.info(f"Updated booking {booking.booking_number}")
        return booking

    # ==========================================================================
    # Status Transitions
    # ==========================================================================

    def confirm(
        self,
        booking_id: uuid.UUID,
        confirmed_by: uuid.UUID = None
    ) -> Booking:
        """Confirm a booking."""
        booking = self.get_booking(booking_id)
        booking.confirm(confirmed_by)

        logger.info(f"Confirmed booking {booking.booking_number}")
        return booking

    def check_in(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Booking:
        """Check in for a booking."""
        from . import BookingStateError

        booking = self.get_booking(booking_id)

        if not booking.can_check_in:
            raise BookingStateError(
                f"Cannot check in: booking status is {booking.status}"
            )

        booking.check_in(user_id)

        logger.info(f"Checked in booking {booking.booking_number}")
        return booking

    def dispatch(
        self,
        booking_id: uuid.UUID,
        dispatcher_id: uuid.UUID,
        notes: str = None
    ) -> Booking:
        """Dispatch a booking (start flight)."""
        from . import BookingStateError

        booking = self.get_booking(booking_id)

        if not booking.can_dispatch:
            raise BookingStateError(
                f"Cannot dispatch: booking status is {booking.status}"
            )

        # Perform dispatch checks
        checks = self._perform_dispatch_checks(booking)
        if not checks['passed']:
            raise BookingStateError(
                f"Dispatch checks failed: {', '.join(checks['failures'])}"
            )

        booking.dispatch(dispatcher_id, notes)

        logger.info(f"Dispatched booking {booking.booking_number}")
        return booking

    def complete(
        self,
        booking_id: uuid.UUID,
        flight_id: uuid.UUID = None,
        actual_cost: Decimal = None
    ) -> Booking:
        """Complete a booking."""
        from . import BookingStateError

        booking = self.get_booking(booking_id)

        if not booking.can_complete:
            raise BookingStateError(
                f"Cannot complete: booking status is {booking.status}"
            )

        booking.complete(flight_id, actual_cost)

        logger.info(f"Completed booking {booking.booking_number}")
        return booking

    def cancel(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        cancellation_type: str = None
    ) -> Booking:
        """Cancel a booking."""
        from . import BookingStateError

        booking = self.get_booking(booking_id)

        if not booking.can_cancel:
            raise BookingStateError(
                f"Cannot cancel: booking status is {booking.status}"
            )

        # Calculate cancellation fee
        rules = BookingRule.get_merged_rules(
            booking.organization_id,
            aircraft_id=booking.aircraft_id,
        )

        fee = None
        if booking.estimated_cost and booking.hours_until_start < rules['free_cancellation_hours']:
            if booking.hours_until_start <= 0:
                fee_percent = rules['no_show_fee_percent']
            else:
                fee_percent = rules['late_cancellation_fee_percent']

            fee = booking.estimated_cost * (fee_percent / Decimal('100'))

        booking.cancel(user_id, reason, cancellation_type, fee)

        # Process waitlist
        from .waitlist_service import WaitlistService
        WaitlistService().process_cancellation(booking)

        logger.info(f"Cancelled booking {booking.booking_number}")
        return booking

    def mark_no_show(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID = None
    ) -> Booking:
        """Mark booking as no-show."""
        booking = self.get_booking(booking_id)
        booking.mark_no_show(user_id)

        logger.info(f"Marked no-show for booking {booking.booking_number}")
        return booking

    # ==========================================================================
    # Conflict Detection
    # ==========================================================================

    def check_conflicts(
        self,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        exclude_booking_id: uuid.UUID = None
    ) -> List[Dict[str, Any]]:
        """Check for booking conflicts."""
        conflicts = []

        # Add buffer for block time
        rules = BookingRule.get_merged_rules(organization_id, aircraft_id=aircraft_id)
        preflight = rules.get('preflight_minutes', 30)
        postflight = rules.get('postflight_minutes', 30)

        block_start = start - timedelta(minutes=preflight)
        block_end = end + timedelta(minutes=postflight)

        # Aircraft conflicts
        if aircraft_id:
            aircraft_conflicts = Booking.get_conflicts(
                organization_id, block_start, block_end,
                aircraft_id=aircraft_id,
                exclude_booking_id=exclude_booking_id
            )
            for booking in aircraft_conflicts:
                conflicts.append({
                    'type': 'aircraft',
                    'resource_id': str(aircraft_id),
                    'booking_id': str(booking.id),
                    'booking_number': booking.booking_number,
                    'start': booking.block_start.isoformat(),
                    'end': booking.block_end.isoformat(),
                    'message': f"Aircraft conflict with {booking.booking_number}",
                })

        # Instructor conflicts
        if instructor_id:
            instructor_conflicts = Booking.get_conflicts(
                organization_id, block_start, block_end,
                instructor_id=instructor_id,
                exclude_booking_id=exclude_booking_id
            )
            for booking in instructor_conflicts:
                conflicts.append({
                    'type': 'instructor',
                    'resource_id': str(instructor_id),
                    'booking_id': str(booking.id),
                    'booking_number': booking.booking_number,
                    'start': booking.block_start.isoformat(),
                    'end': booking.block_end.isoformat(),
                    'message': f"Instructor conflict with {booking.booking_number}",
                })

        # Student conflicts (can't be in two places)
        if student_id:
            student_conflicts = Booking.objects.filter(
                organization_id=organization_id,
                student_id=student_id,
                status__in=Booking.get_active_statuses()
            ).filter(
                Q(block_start__lt=block_end) & Q(block_end__gt=block_start)
            )

            if exclude_booking_id:
                student_conflicts = student_conflicts.exclude(id=exclude_booking_id)

            for booking in student_conflicts:
                conflicts.append({
                    'type': 'student',
                    'resource_id': str(student_id),
                    'booking_id': str(booking.id),
                    'booking_number': booking.booking_number,
                    'message': f"Student has overlapping booking {booking.booking_number}",
                })

        return conflicts

    # ==========================================================================
    # Calendar Views
    # ==========================================================================

    def get_calendar(
        self,
        organization_id: uuid.UUID,
        view: str,
        target_date: date,
        resource_type: str = None,
        resource_ids: List[uuid.UUID] = None,
        location_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """Get calendar view data."""
        # Calculate date range based on view
        if view == 'day':
            start_date = target_date
            end_date = target_date
        elif view == 'week':
            # Start from Monday
            start_date = target_date - timedelta(days=target_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif view == 'month':
            start_date = target_date.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        else:
            start_date = target_date
            end_date = target_date

        # Get bookings
        queryset = Booking.objects.filter(
            organization_id=organization_id,
            scheduled_start__date__gte=start_date,
            scheduled_start__date__lte=end_date,
        ).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
        )

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        if resource_type == 'aircraft' and resource_ids:
            queryset = queryset.filter(aircraft_id__in=resource_ids)
        elif resource_type == 'instructor' and resource_ids:
            queryset = queryset.filter(instructor_id__in=resource_ids)

        bookings = list(queryset.order_by('scheduled_start'))

        # Format for calendar
        events = []
        for booking in bookings:
            events.append({
                'id': str(booking.id),
                'booking_number': booking.booking_number,
                'title': booking.title or booking.booking_number,
                'start': booking.scheduled_start.isoformat(),
                'end': booking.scheduled_end.isoformat(),
                'block_start': booking.block_start.isoformat(),
                'block_end': booking.block_end.isoformat(),
                'status': booking.status,
                'booking_type': booking.booking_type,
                'aircraft_id': str(booking.aircraft_id) if booking.aircraft_id else None,
                'instructor_id': str(booking.instructor_id) if booking.instructor_id else None,
                'student_id': str(booking.student_id) if booking.student_id else None,
            })

        return {
            'view': view,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'events': events,
            'total_count': len(events),
        }

    def get_user_bookings(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        upcoming_only: bool = False,
        limit: int = 20
    ) -> List[Booking]:
        """Get bookings for a specific user."""
        queryset = Booking.objects.filter(
            organization_id=organization_id
        ).filter(
            Q(student_id=user_id) |
            Q(pilot_id=user_id) |
            Q(instructor_id=user_id)
        ).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
        )

        if upcoming_only:
            queryset = queryset.filter(scheduled_start__gte=timezone.now())
            queryset = queryset.order_by('scheduled_start')
        else:
            queryset = queryset.order_by('-scheduled_start')

        return list(queryset[:limit])

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_statistics(
        self,
        organization_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """Get booking statistics."""
        queryset = Booking.objects.filter(organization_id=organization_id)

        if start_date:
            queryset = queryset.filter(scheduled_start__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(scheduled_start__date__lte=end_date)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        # Counts by status
        status_counts = queryset.values('status').annotate(count=Count('id'))

        # Total hours
        completed = queryset.filter(status=Booking.Status.COMPLETED)
        total_hours = completed.aggregate(
            total=Sum('scheduled_duration')
        )['total'] or 0

        # Cancellation stats
        cancelled = queryset.filter(status=Booking.Status.CANCELLED)
        late_cancellations = cancelled.filter(is_late_cancellation=True).count()

        # No-shows
        no_shows = queryset.filter(status=Booking.Status.NO_SHOW).count()

        return {
            'total_bookings': queryset.count(),
            'completed': completed.count(),
            'cancelled': cancelled.count(),
            'no_shows': no_shows,
            'late_cancellations': late_cancellations,
            'total_hours': total_hours / 60 if total_hours else 0,
            'by_status': {
                item['status']: item['count']
                for item in status_counts
            },
        }

    # ==========================================================================
    # Private Methods
    # ==========================================================================

    def _validate_times(self, start: datetime, end: datetime):
        """Validate booking times."""
        from . import BookingValidationError

        if end <= start:
            raise BookingValidationError("End time must be after start time")

        if start < timezone.now() - timedelta(minutes=5):
            raise BookingValidationError("Cannot book in the past")

        duration = (end - start).total_seconds() / 60
        if duration < 15:
            raise BookingValidationError("Minimum booking duration is 15 minutes")

        if duration > 480:
            raise BookingValidationError("Maximum booking duration is 8 hours")

    def _validate_against_rules(
        self,
        rules: Dict,
        start: datetime,
        end: datetime,
        payer_id: uuid.UUID,
        organization_id: uuid.UUID
    ):
        """Validate booking against rules."""
        from . import RuleViolationError

        duration_minutes = (end - start).total_seconds() / 60

        # Duration limits
        if rules.get('min_booking_duration'):
            if duration_minutes < rules['min_booking_duration']:
                raise RuleViolationError(
                    f"Minimum booking duration is {rules['min_booking_duration']} minutes"
                )

        if rules.get('max_booking_duration'):
            if duration_minutes > rules['max_booking_duration']:
                raise RuleViolationError(
                    f"Maximum booking duration is {rules['max_booking_duration']} minutes"
                )

        # Notice period
        hours_until = (start - timezone.now()).total_seconds() / 3600
        if rules.get('min_notice_hours'):
            if hours_until < rules['min_notice_hours']:
                raise RuleViolationError(
                    f"Minimum {rules['min_notice_hours']} hours notice required"
                )

        # Advance booking limit
        days_until = (start.date() - timezone.now().date()).days
        if rules.get('max_advance_days'):
            if days_until > rules['max_advance_days']:
                raise RuleViolationError(
                    f"Cannot book more than {rules['max_advance_days']} days in advance"
                )

    def _calculate_estimated_cost(
        self,
        aircraft_id: uuid.UUID,
        instructor_id: uuid.UUID,
        duration_hours: float
    ) -> Decimal:
        """Calculate estimated booking cost."""
        # Placeholder - would call finance service in production
        aircraft_rate = Decimal('150.00')  # Per hour
        instructor_rate = Decimal('75.00')  # Per hour

        cost = Decimal('0.00')

        if aircraft_id:
            cost += aircraft_rate * Decimal(str(duration_hours))

        if instructor_id:
            cost += instructor_rate * Decimal(str(duration_hours))

        return cost

    def _perform_dispatch_checks(self, booking: Booking) -> Dict[str, Any]:
        """Perform pre-dispatch checks."""
        failures = []

        # Check if booking time has arrived
        if booking.scheduled_start > timezone.now() + timedelta(hours=1):
            failures.append("Too early to dispatch - wait until closer to scheduled time")

        # Check weather briefing
        if not booking.weather_briefing_done:
            failures.append("Weather briefing not completed")

        # Check risk assessment (for training flights)
        if booking.training_type and not booking.risk_assessment_done:
            failures.append("Risk assessment not completed")

        return {
            'passed': len(failures) == 0,
            'failures': failures,
        }

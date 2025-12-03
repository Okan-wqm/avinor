# services/booking-service/src/apps/core/services/availability_service.py
"""
Availability Service

Manages resource availability and slot finding.
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Booking, Availability, BookingRule
from apps.core.models.availability import OperatingHours

logger = logging.getLogger(__name__)


class AvailabilityService:
    """
    Service for managing availability.

    Handles:
    - Availability CRUD
    - Slot finding
    - Operating hours
    - Resource availability checks
    """

    # ==========================================================================
    # Availability CRUD
    # ==========================================================================

    @transaction.atomic
    def create_availability(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        availability_type: str,
        start_datetime: datetime,
        end_datetime: datetime,
        created_by: uuid.UUID = None,
        **kwargs
    ) -> Availability:
        """Create an availability entry."""
        availability = Availability.objects.create(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            availability_type=availability_type,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            created_by=created_by,
            **kwargs
        )

        logger.info(
            f"Created {availability_type} availability for "
            f"{resource_type} {resource_id}"
        )

        return availability

    def get_availability(self, availability_id: uuid.UUID) -> Availability:
        """Get availability by ID."""
        from . import AvailabilityError

        try:
            return Availability.objects.get(id=availability_id)
        except Availability.DoesNotExist:
            raise AvailabilityError(f"Availability {availability_id} not found")

    def list_availability(
        self,
        organization_id: uuid.UUID,
        resource_type: str = None,
        resource_id: uuid.UUID = None,
        start_date: date = None,
        end_date: date = None,
        availability_type: str = None
    ) -> List[Availability]:
        """List availability entries."""
        queryset = Availability.objects.filter(organization_id=organization_id)

        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        if start_date:
            start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
            queryset = queryset.filter(end_datetime__gte=start_dt)

        if end_date:
            end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
            queryset = queryset.filter(start_datetime__lte=end_dt)

        if availability_type:
            queryset = queryset.filter(availability_type=availability_type)

        return list(queryset.order_by('start_datetime'))

    def update_availability(
        self,
        availability_id: uuid.UUID,
        **kwargs
    ) -> Availability:
        """Update an availability entry."""
        availability = self.get_availability(availability_id)

        allowed_fields = [
            'availability_type', 'start_datetime', 'end_datetime',
            'reason', 'notes', 'max_bookings', 'booking_types_allowed',
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(availability, field, value)

        availability.save()
        return availability

    def delete_availability(self, availability_id: uuid.UUID):
        """Delete an availability entry."""
        availability = self.get_availability(availability_id)
        availability.delete()

        logger.info(f"Deleted availability {availability_id}")

    # ==========================================================================
    # Availability Checks
    # ==========================================================================

    def is_resource_available(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        start: datetime,
        end: datetime,
        booking_type: str = None
    ) -> Dict[str, Any]:
        """Check if a resource is available for booking."""
        result = {
            'available': True,
            'reasons': [],
            'conflicts': [],
        }

        # Check explicit unavailability
        unavailable = Availability.objects.filter(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            availability_type=Availability.AvailabilityType.UNAVAILABLE
        ).filter(
            Q(start_datetime__lt=end) & Q(end_datetime__gt=start)
        )

        for entry in unavailable:
            result['available'] = False
            result['reasons'].append(entry.reason or 'Resource unavailable')
            result['conflicts'].append({
                'type': 'unavailability',
                'start': entry.start_datetime.isoformat(),
                'end': entry.end_datetime.isoformat(),
                'reason': entry.reason,
            })

        # Check existing bookings
        if resource_type == 'aircraft':
            existing = Booking.get_conflicts(
                organization_id, start, end,
                aircraft_id=resource_id
            )
        elif resource_type == 'instructor':
            existing = Booking.get_conflicts(
                organization_id, start, end,
                instructor_id=resource_id
            )
        else:
            existing = []

        for booking in existing:
            result['available'] = False
            result['reasons'].append(f'Conflict with booking {booking.booking_number}')
            result['conflicts'].append({
                'type': 'booking',
                'booking_id': str(booking.id),
                'booking_number': booking.booking_number,
                'start': booking.block_start.isoformat(),
                'end': booking.block_end.isoformat(),
            })

        return result

    def get_resource_schedule(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        target_date: date
    ) -> Dict[str, Any]:
        """Get a resource's schedule for a specific date."""
        start_dt = timezone.make_aware(datetime.combine(target_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(target_date, time.max))

        # Get bookings
        if resource_type == 'aircraft':
            bookings = Booking.objects.filter(
                organization_id=organization_id,
                aircraft_id=resource_id,
                scheduled_start__gte=start_dt,
                scheduled_start__lte=end_dt
            )
        elif resource_type == 'instructor':
            bookings = Booking.objects.filter(
                organization_id=organization_id,
                instructor_id=resource_id,
                scheduled_start__gte=start_dt,
                scheduled_start__lte=end_dt
            )
        else:
            bookings = Booking.objects.none()

        bookings = bookings.exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
        ).order_by('scheduled_start')

        # Get availability blocks
        availability = Availability.get_for_resource(
            organization_id, resource_type, resource_id,
            start_dt, end_dt
        )

        return {
            'date': target_date.isoformat(),
            'resource_type': resource_type,
            'resource_id': str(resource_id),
            'bookings': [
                {
                    'id': str(b.id),
                    'booking_number': b.booking_number,
                    'start': b.scheduled_start.isoformat(),
                    'end': b.scheduled_end.isoformat(),
                    'block_start': b.block_start.isoformat(),
                    'block_end': b.block_end.isoformat(),
                    'status': b.status,
                }
                for b in bookings
            ],
            'availability': [
                {
                    'id': str(a.id),
                    'type': a.availability_type,
                    'start': a.start_datetime.isoformat(),
                    'end': a.end_datetime.isoformat(),
                    'reason': a.reason,
                }
                for a in availability
            ],
        }

    # ==========================================================================
    # Available Slots
    # ==========================================================================

    def get_available_slots(
        self,
        organization_id: uuid.UUID,
        target_date: date,
        duration_minutes: int,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        slot_interval: int = 30
    ) -> List[Dict[str, Any]]:
        """Find available time slots for a given duration."""
        # Get operating hours
        operating_hours = self._get_operating_hours(
            organization_id, location_id, target_date
        )

        if not operating_hours:
            return []

        start_time = operating_hours['start']
        end_time = operating_hours['end']

        # Get existing bookings
        blocked_times = self._get_blocked_times(
            organization_id, target_date,
            aircraft_id, instructor_id
        )

        # Get unavailability blocks
        if aircraft_id:
            unavailable = Availability.get_unavailable_blocks(
                organization_id, 'aircraft', aircraft_id,
                timezone.make_aware(datetime.combine(target_date, time.min)),
                timezone.make_aware(datetime.combine(target_date, time.max))
            )
            for block in unavailable:
                blocked_times.append({
                    'start': block['start'],
                    'end': block['end'],
                })

        if instructor_id:
            unavailable = Availability.get_unavailable_blocks(
                organization_id, 'instructor', instructor_id,
                timezone.make_aware(datetime.combine(target_date, time.min)),
                timezone.make_aware(datetime.combine(target_date, time.max))
            )
            for block in unavailable:
                blocked_times.append({
                    'start': block['start'],
                    'end': block['end'],
                })

        # Calculate available slots
        slots = self._calculate_slots(
            target_date,
            start_time,
            end_time,
            blocked_times,
            duration_minutes,
            slot_interval
        )

        return slots

    def _get_operating_hours(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID,
        target_date: date
    ) -> Dict[str, time]:
        """Get operating hours for a location on a date."""
        if location_id:
            operating = OperatingHours.get_for_date(
                organization_id, location_id, target_date
            )
            if operating:
                return {
                    'start': operating.open_time,
                    'end': operating.close_time,
                }

        # Default operating hours
        return {
            'start': time(8, 0),
            'end': time(20, 0),
        }

    def _get_blocked_times(
        self,
        organization_id: uuid.UUID,
        target_date: date,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None
    ) -> List[Dict]:
        """Get blocked time periods from existing bookings."""
        start_dt = timezone.make_aware(datetime.combine(target_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(target_date, time.max))

        blocked = []

        # Aircraft bookings
        if aircraft_id:
            aircraft_bookings = Booking.objects.filter(
                organization_id=organization_id,
                aircraft_id=aircraft_id,
                scheduled_start__date=target_date
            ).exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
            )

            for booking in aircraft_bookings:
                blocked.append({
                    'start': booking.block_start,
                    'end': booking.block_end,
                    'booking_id': str(booking.id),
                })

        # Instructor bookings
        if instructor_id:
            instructor_bookings = Booking.objects.filter(
                organization_id=organization_id,
                instructor_id=instructor_id,
                scheduled_start__date=target_date
            ).exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
            )

            for booking in instructor_bookings:
                # Only add if not already blocked by aircraft
                already_blocked = any(
                    b['start'] == booking.block_start and b['end'] == booking.block_end
                    for b in blocked
                )
                if not already_blocked:
                    blocked.append({
                        'start': booking.block_start,
                        'end': booking.block_end,
                        'booking_id': str(booking.id),
                    })

        return blocked

    def _calculate_slots(
        self,
        target_date: date,
        start_time: time,
        end_time: time,
        blocked_times: List[Dict],
        duration_minutes: int,
        slot_interval: int
    ) -> List[Dict[str, Any]]:
        """Calculate available slots."""
        slots = []
        slot_duration = timedelta(minutes=duration_minutes)
        step = timedelta(minutes=slot_interval)

        current = timezone.make_aware(datetime.combine(target_date, start_time))
        day_end = timezone.make_aware(datetime.combine(target_date, end_time))

        while current + slot_duration <= day_end:
            slot_end = current + slot_duration

            # Check if slot is blocked
            is_blocked = False
            for blocked in blocked_times:
                if current < blocked['end'] and slot_end > blocked['start']:
                    is_blocked = True
                    break

            # Don't show slots in the past
            if current > timezone.now():
                if not is_blocked:
                    slots.append({
                        'start': current.isoformat(),
                        'end': slot_end.isoformat(),
                        'duration_minutes': duration_minutes,
                        'available': True,
                    })

            current += step

        return slots

    # ==========================================================================
    # Operating Hours
    # ==========================================================================

    def set_operating_hours(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID,
        day_of_week: int,
        open_time: time,
        close_time: time,
        effective_from: date = None,
        effective_to: date = None
    ) -> OperatingHours:
        """Set operating hours for a location."""
        operating, created = OperatingHours.objects.update_or_create(
            organization_id=organization_id,
            location_id=location_id,
            day_of_week=day_of_week,
            effective_from=effective_from,
            defaults={
                'open_time': open_time,
                'close_time': close_time,
                'effective_to': effective_to,
                'is_active': True,
            }
        )

        return operating

    def get_operating_hours(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID
    ) -> List[OperatingHours]:
        """Get all operating hours for a location."""
        return list(
            OperatingHours.objects.filter(
                organization_id=organization_id,
                location_id=location_id,
                is_active=True
            ).order_by('day_of_week')
        )

    def get_weekly_schedule(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get weekly operating hours schedule."""
        hours = self.get_operating_hours(organization_id, location_id)

        day_names = [
            'sunday', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday'
        ]

        schedule = {}
        for day_num, day_name in enumerate(day_names):
            day_hours = next(
                (h for h in hours if h.day_of_week == day_num),
                None
            )
            if day_hours:
                schedule[day_name] = {
                    'open': day_hours.open_time.strftime('%H:%M'),
                    'close': day_hours.close_time.strftime('%H:%M'),
                    'is_open': True,
                }
            else:
                schedule[day_name] = {
                    'is_open': False,
                }

        return schedule

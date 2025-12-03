# services/training-service/src/apps/core/events/handlers.py
"""
Event Handlers

Functions for handling events from other services.
"""

import logging
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)


def handle_flight_completed(event_data: Dict[str, Any]) -> bool:
    """
    Handle flight completed event from Flight Service.

    Updates lesson completion with flight data if associated.

    Args:
        event_data: Event data containing flight information

    Returns:
        True if handled successfully
    """
    from ..models import LessonCompletion

    try:
        flight_record_id = event_data.get('flight_record_id')
        flight_time = event_data.get('flight_time')
        dual_time = event_data.get('dual_time')
        solo_time = event_data.get('solo_time')
        pic_time = event_data.get('pic_time')
        cross_country_time = event_data.get('cross_country_time')
        night_time = event_data.get('night_time')
        instrument_time = event_data.get('instrument_time')
        landings_day = event_data.get('landings_day', 0)
        landings_night = event_data.get('landings_night', 0)

        # Find associated lesson completion
        completion = LessonCompletion.objects.filter(
            flight_record_id=flight_record_id
        ).first()

        if not completion:
            logger.debug(
                f"No lesson completion found for flight {flight_record_id}"
            )
            return True

        # Update completion with flight data
        with transaction.atomic():
            if flight_time:
                completion.flight_time = Decimal(str(flight_time))
            if dual_time:
                completion.dual_time = Decimal(str(dual_time))
            if solo_time:
                completion.solo_time = Decimal(str(solo_time))
            if pic_time:
                completion.pic_time = Decimal(str(pic_time))
            if cross_country_time:
                completion.cross_country_time = Decimal(str(cross_country_time))
            if night_time:
                completion.night_time = Decimal(str(night_time))
            if instrument_time:
                completion.instrument_time = Decimal(str(instrument_time))

            completion.landings_day = landings_day
            completion.landings_night = landings_night
            completion.save()

            # Update enrollment hours
            completion.enrollment.update_hours()

        logger.info(
            f"Updated lesson completion with flight data: {flight_record_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error handling flight completed event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_booking_confirmed(event_data: Dict[str, Any]) -> bool:
    """
    Handle booking confirmed event from Booking Service.

    Creates a scheduled lesson completion if booking is for training.

    Args:
        event_data: Event data containing booking information

    Returns:
        True if handled successfully
    """
    from ..models import LessonCompletion, StudentEnrollment, SyllabusLesson

    try:
        booking_id = event_data.get('booking_id')
        organization_id = event_data.get('organization_id')
        student_id = event_data.get('student_id')
        instructor_id = event_data.get('instructor_id')
        aircraft_id = event_data.get('aircraft_id')
        booking_type = event_data.get('booking_type')
        lesson_id = event_data.get('lesson_id')
        enrollment_id = event_data.get('enrollment_id')
        scheduled_date = event_data.get('scheduled_date')
        scheduled_start = event_data.get('scheduled_start')
        scheduled_end = event_data.get('scheduled_end')

        # Only handle training bookings with lesson/enrollment
        if booking_type != 'training' or not lesson_id or not enrollment_id:
            return True

        # Verify enrollment exists
        enrollment = StudentEnrollment.objects.filter(
            id=enrollment_id,
            organization_id=organization_id
        ).first()

        if not enrollment:
            logger.warning(
                f"Enrollment {enrollment_id} not found for booking {booking_id}"
            )
            return True

        # Verify lesson exists
        lesson = SyllabusLesson.objects.filter(
            id=lesson_id,
            organization_id=organization_id
        ).first()

        if not lesson:
            logger.warning(
                f"Lesson {lesson_id} not found for booking {booking_id}"
            )
            return True

        # Check if completion already exists for this booking
        existing = LessonCompletion.objects.filter(
            booking_id=booking_id
        ).first()

        if existing:
            logger.debug(
                f"Completion already exists for booking {booking_id}"
            )
            return True

        # Create scheduled completion
        with transaction.atomic():
            LessonCompletion.objects.create(
                organization_id=organization_id,
                enrollment=enrollment,
                lesson=lesson,
                instructor_id=instructor_id,
                aircraft_id=aircraft_id,
                booking_id=booking_id,
                scheduled_date=scheduled_date,
                scheduled_start_time=scheduled_start,
                scheduled_end_time=scheduled_end,
                status='scheduled',
            )

        logger.info(
            f"Created scheduled lesson completion for booking {booking_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error handling booking confirmed event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_user_created(event_data: Dict[str, Any]) -> bool:
    """
    Handle user created event from User Service.

    No action needed for training service currently.

    Args:
        event_data: Event data containing user information

    Returns:
        True if handled successfully
    """
    # Training service doesn't need to do anything when a user is created
    # But we log it for debugging purposes
    user_id = event_data.get('user_id')
    logger.debug(f"Received user created event for user {user_id}")
    return True


def handle_aircraft_status_changed(event_data: Dict[str, Any]) -> bool:
    """
    Handle aircraft status changed event from Aircraft Service.

    May need to notify about affected scheduled lessons.

    Args:
        event_data: Event data containing aircraft information

    Returns:
        True if handled successfully
    """
    from ..models import LessonCompletion

    try:
        aircraft_id = event_data.get('aircraft_id')
        new_status = event_data.get('status')
        organization_id = event_data.get('organization_id')

        # If aircraft becomes unavailable, find affected lessons
        if new_status in ['maintenance', 'grounded', 'inactive']:
            affected_completions = LessonCompletion.objects.filter(
                organization_id=organization_id,
                aircraft_id=aircraft_id,
                status='scheduled'
            )

            count = affected_completions.count()

            if count > 0:
                logger.warning(
                    f"Aircraft {aircraft_id} status changed to {new_status}. "
                    f"{count} scheduled lessons may be affected."
                )

                # TODO: Send notifications to instructors/students
                # about affected lessons

        return True

    except Exception as e:
        logger.error(
            f"Error handling aircraft status changed event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_instructor_availability_changed(event_data: Dict[str, Any]) -> bool:
    """
    Handle instructor availability changed event.

    May need to notify about affected scheduled lessons.

    Args:
        event_data: Event data containing availability information

    Returns:
        True if handled successfully
    """
    from ..models import LessonCompletion

    try:
        instructor_id = event_data.get('instructor_id')
        organization_id = event_data.get('organization_id')
        unavailable_dates = event_data.get('unavailable_dates', [])

        if not unavailable_dates:
            return True

        # Find affected scheduled lessons
        affected_completions = LessonCompletion.objects.filter(
            organization_id=organization_id,
            instructor_id=instructor_id,
            status='scheduled',
            scheduled_date__in=unavailable_dates
        )

        count = affected_completions.count()

        if count > 0:
            logger.warning(
                f"Instructor {instructor_id} availability changed. "
                f"{count} scheduled lessons may be affected."
            )

            # TODO: Send notifications about affected lessons

        return True

    except Exception as e:
        logger.error(
            f"Error handling instructor availability changed event: {e}",
            extra={'event_data': event_data}
        )
        return False


# Event handler registry
EVENT_HANDLERS = {
    'flight.completed': handle_flight_completed,
    'booking.confirmed': handle_booking_confirmed,
    'user.created': handle_user_created,
    'aircraft.status_changed': handle_aircraft_status_changed,
    'instructor.availability_changed': handle_instructor_availability_changed,
}


def dispatch_event(event_type: str, event_data: Dict[str, Any]) -> bool:
    """
    Dispatch an event to the appropriate handler.

    Args:
        event_type: Type of event
        event_data: Event data

    Returns:
        True if handled successfully
    """
    handler = EVENT_HANDLERS.get(event_type)

    if not handler:
        logger.debug(f"No handler registered for event type: {event_type}")
        return True

    return handler(event_data)

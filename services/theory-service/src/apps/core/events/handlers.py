# services/theory-service/src/apps/core/events/handlers.py
"""
Event Handlers

Functions for handling events from other services.
"""

import logging
from typing import Dict, Any

from django.db import transaction

logger = logging.getLogger(__name__)


def handle_training_enrollment_created(event_data: Dict[str, Any]) -> bool:
    """
    Handle training enrollment created event from Training Service.

    May auto-enroll student in associated theory courses.

    Args:
        event_data: Event data containing enrollment information

    Returns:
        True if handled successfully
    """
    from ..models import Course, CourseEnrollment
    from ..services import EnrollmentService

    try:
        organization_id = event_data.get('organization_id')
        student_id = event_data.get('student_id')
        program_type = event_data.get('program_type')

        if not program_type:
            return True

        # Find associated theory courses
        courses = Course.objects.filter(
            organization_id=organization_id,
            program_type=program_type,
            is_published=True
        )

        for course in courses:
            # Check if already enrolled
            existing = CourseEnrollment.objects.filter(
                course=course,
                user_id=student_id
            ).first()

            if not existing:
                try:
                    EnrollmentService.enroll_user(
                        organization_id=str(organization_id),
                        user_id=str(student_id),
                        course_id=str(course.id)
                    )
                    logger.info(
                        f"Auto-enrolled student {student_id} in course {course.id}"
                    )
                except ValueError as e:
                    logger.warning(
                        f"Could not auto-enroll student: {e}"
                    )

        return True

    except Exception as e:
        logger.error(
            f"Error handling training enrollment created event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_training_lesson_completed(event_data: Dict[str, Any]) -> bool:
    """
    Handle training lesson completed event from Training Service.

    May update theory course progress based on related lessons.

    Args:
        event_data: Event data containing lesson completion information

    Returns:
        True if handled successfully
    """
    # Theory service may track practical lesson completions
    # for combined ground/flight courses

    logger.debug(
        f"Received training lesson completed event",
        extra={'event_data': event_data}
    )

    return True


def handle_user_created(event_data: Dict[str, Any]) -> bool:
    """
    Handle user created event from User Service.

    No action needed for theory service currently.

    Args:
        event_data: Event data containing user information

    Returns:
        True if handled successfully
    """
    user_id = event_data.get('user_id')
    logger.debug(f"Received user created event for user {user_id}")
    return True


def handle_booking_confirmed(event_data: Dict[str, Any]) -> bool:
    """
    Handle booking confirmed event from Booking Service.

    May associate ground school bookings with course enrollments.

    Args:
        event_data: Event data containing booking information

    Returns:
        True if handled successfully
    """
    try:
        booking_type = event_data.get('booking_type')

        # Only handle ground school bookings
        if booking_type != 'ground_school':
            return True

        logger.debug(
            f"Received ground school booking event",
            extra={'event_data': event_data}
        )

        # Could create scheduled study sessions, etc.

        return True

    except Exception as e:
        logger.error(
            f"Error handling booking confirmed event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_training_program_updated(event_data: Dict[str, Any]) -> bool:
    """
    Handle training program updated event from Training Service.

    May need to update associated course configurations.

    Args:
        event_data: Event data containing program information

    Returns:
        True if handled successfully
    """
    try:
        organization_id = event_data.get('organization_id')
        program_type = event_data.get('program_type')
        min_theory_score = event_data.get('min_theory_score')

        if min_theory_score is not None:
            from ..models import Course

            # Update passing score for associated courses
            courses = Course.objects.filter(
                organization_id=organization_id,
                program_type=program_type
            )

            updated_count = courses.update(min_score_to_pass=min_theory_score)

            if updated_count > 0:
                logger.info(
                    f"Updated passing score for {updated_count} courses "
                    f"to {min_theory_score}%"
                )

        return True

    except Exception as e:
        logger.error(
            f"Error handling training program updated event: {e}",
            extra={'event_data': event_data}
        )
        return False


def handle_certificate_expiring(event_data: Dict[str, Any]) -> bool:
    """
    Handle certificate expiring notification (internal event).

    Sends reminder notifications.

    Args:
        event_data: Event data containing certificate information

    Returns:
        True if handled successfully
    """
    try:
        certificate_id = event_data.get('certificate_id')
        user_id = event_data.get('user_id')
        days_until_expiry = event_data.get('days_until_expiry')

        # TODO: Send notification to user about expiring certificate
        logger.info(
            f"Certificate {certificate_id} expires in {days_until_expiry} days"
        )

        return True

    except Exception as e:
        logger.error(
            f"Error handling certificate expiring event: {e}",
            extra={'event_data': event_data}
        )
        return False


# Event handler registry
EVENT_HANDLERS = {
    'training.enrollment_created': handle_training_enrollment_created,
    'training.lesson_completed': handle_training_lesson_completed,
    'training.program_updated': handle_training_program_updated,
    'user.created': handle_user_created,
    'booking.confirmed': handle_booking_confirmed,
    'theory.certificate_expiring': handle_certificate_expiring,
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
